"""TTS 缓存：统计 / LRU 清理 / 静态 URL / 记账（P0-2 / P1-4 / P2-2）。"""
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.v1.speak_media import cache_dir
from app.db import SessionLocal
from app.main import app
from app.models.usage import Usage
from app.services import ai_enrich, qwen_speak, usage as usage_svc

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
    assert qwen_speak.tts_cache_cfg(db) == 512
    ai_enrich.set_cfg(db, "speak.tts_cache", '{"max_mb": 64}')
    assert qwen_speak.tts_cache_cfg(db) == 64
    ai_enrich.set_cfg(db, "speak.tts_cache", '{"max_mb": 1}')
    assert qwen_speak.tts_cache_cfg(db) == 16  # 下限 16MB
    db.close()


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
