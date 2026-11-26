"""TTS 缓存：统计 / LRU 清理 / 静态 URL / 记账（P0-2 / P1-4 / P2-2）。"""
import io
import os
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.v1.speak_media import cache_dir
from app.db import SessionLocal
from app.main import app
from app.models.usage import Usage
from app.services import ai_enrich, qwen_speak, tts_cache
from app.services import usage as usage_svc

client = TestClient(app)


def test_cache_stats_lru_and_clear(tmp_path):
    files = []
    for i, size in enumerate([1024 * 1024, 2 * 1024 * 1024, 1024 * 1024]):
        p = tmp_path / f"{i:040x}.wav"
        p.write_bytes(b"x" * size)
        os.utime(p, (1000 + i, 1000 + i))
        files.append(p)
    (tmp_path / "note.txt").write_text("not cached")

    stats = qwen_speak.tts_cache_stats(str(tmp_path), 512)
    assert stats["files"] == 3
    assert stats["bytes"] == 4 * 1024 * 1024

    # 上限 3MB：删掉最久未用的 1MB 文件
    assert qwen_speak.enforce_tts_cache(str(tmp_path), 3) == 1
    assert not files[0].exists()
    assert files[1].exists() and files[2].exists()

    assert qwen_speak.clear_tts_cache(str(tmp_path)) == 2
    assert qwen_speak.tts_cache_stats(str(tmp_path), 512)["files"] == 0


def test_tts_cache_cfg_bounds():
    db = SessionLocal()
    assert qwen_speak.tts_cache_cfg(db) == 1024
    ai_enrich.set_cfg(db, "speak.tts_cache", '{"max_mb": 64}')
    assert qwen_speak.tts_cache_cfg(db) == 64
    ai_enrich.set_cfg(db, "speak.tts_cache", '{"max_mb": 1}')
    assert qwen_speak.tts_cache_cfg(db) == 16  # 下限 16MB
    db.close()


def test_normalize_streaming_wav_header():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00\x00" * 120)
    raw = bytearray(buf.getvalue())
    raw[4:8] = b"\xbf\xff\xff\x7f"  # 云端流式 WAV 的假 RIFF 长度
    raw[40:44] = b"\x9b\xff\xff\x7f"  # 假 data 长度
    fixed = tts_cache.normalize_wav(bytes(raw))
    assert int.from_bytes(fixed[4:8], "little") == len(raw) - 8
    assert int.from_bytes(fixed[40:44], "little") == len(raw) - 44
    with wave.open(io.BytesIO(fixed), "rb") as r:
        assert r.getnframes() == 120

    # 正确的头部不会被改动
    assert tts_cache.normalize_wav(bytes(buf.getvalue())) == bytes(buf.getvalue())
    # 非 WAV 原样返回
    assert tts_cache.normalize_wav(b"ID3\x04not-wave") == b"ID3\x04not-wave"


def test_repair_wav_file_fixes_cached_header(tmp_path):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 80)
    raw = bytearray(buf.getvalue())
    raw[4:8] = b"\xbf\xff\xff\x7f"
    raw[40:44] = b"\x9b\xff\xff\x7f"
    p = tmp_path / f"{'c' * 40}.wav"
    p.write_bytes(raw)

    tts_cache.repair_wav_file(p)
    fixed = p.read_bytes()
    assert int.from_bytes(fixed[4:8], "little") == len(fixed) - 8
    assert int.from_bytes(fixed[40:44], "little") == len(fixed) - 44

    # 再跑一次不改变内容
    tts_cache.repair_wav_file(p)
    assert p.read_bytes() == fixed


def test_record_tts_bills_only_on_miss():
    db = SessionLocal()
    usage_svc.record_tts(db, 42, 100, cached=True)
    row = db.get(Usage, (42, usage_svc.today()))
    assert row.tts_cache_hits == 1
    assert row.tts_calls == 0
    assert row.est_cost_milli == 0

    usage_svc.record_tts(db, 42, 100, cached=False)
    db.refresh(row)
    assert row.tts_calls == 1
    assert row.tts_chars == 100
    assert row.est_cost_milli == 8  # 100 字符 × 0.08 元/千字符
    db.close()


def test_tts_file_served_with_immutable_cache_header():
    d = Path(cache_dir())
    d.mkdir(parents=True, exist_ok=True)
    name = "a" * 40 + ".wav"
    f = d / name
    payload = b"RIFF" + b"x" * 200
    try:
        f.write_bytes(payload)
        r = client.get(f"/api/v1/speak/tts/file/{name}")
        assert r.status_code == 200
        assert r.content == payload
        assert "immutable" in r.headers["cache-control"]
    finally:
        f.unlink(missing_ok=True)

    assert client.get("/api/v1/speak/tts/file/not-a-hash.wav").status_code == 404
    assert client.get(f"/api/v1/speak/tts/file/{'b' * 40}.wav").status_code == 404
