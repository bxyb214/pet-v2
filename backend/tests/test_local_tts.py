"""本地 TTS：配置解析、文本规范化、缓存命中、接口鉴权与限流。"""
import json

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.user import InviteCode
from app.services import ai_enrich, local_tts, tts_cache
from app.services.tts_text import normalize_for_tts, truncate_text

client = TestClient(app)
PWD = "pet-test-pass"


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """缓存目录与限流桶都按测试隔离，避免上次运行留下的音频让合成被跳过。"""
    monkeypatch.setattr(tts_cache, "cache_dir", lambda: str(tmp_path))
    local_tts._buckets.clear()
    yield
    local_tts._buckets.clear()


def _set_cfg(value: dict | None) -> None:
    db = SessionLocal()
    ai_enrich.set_cfg(db, "speak.local", "" if value is None else json.dumps(value))
    db.close()


def _register(code: str) -> str:
    db = SessionLocal()
    db.add(InviteCode(code=code))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/register",
        json={"username": code.lower(), "password": PWD, "invite_code": code},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_config_endpoint_defaults_off():
    _set_cfg(None)
    r = client.get("/api/v1/speak/tts/config")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["engine"] == "piper"
    assert body["voice"] == "en_GB-alan-medium"
    assert body["path"] == "/api/v1/speak/tts/local"


def test_normalize_for_tts():
    assert normalize_for_tts("I like e.g. apples & pears 100%.") == (
        "I like for example apples and pears 100 percent."
    )
    assert normalize_for_tts("The PET exam") == "The P E T exam"
    assert normalize_for_tts("Mrs. Smith met Mr. Li.") == "Missus Smith met Mister Li."
    assert normalize_for_tts("Hello 你好") == "Hello"
    assert normalize_for_tts("read this", {"read": "reed"}) == "reed this"
    assert normalize_for_tts("   ") == ""


def test_truncate_keeps_sentence_boundary():
    text = "First sentence. Second sentence is much longer."
    out = truncate_text(text, 20)
    assert out == "First sentence."
    zh = "第一句建议先慢一点。第二句建议重音再清晰一点，注意尾音。"
    assert truncate_text(zh, 18) == "第一句建议先慢一点。"


def test_local_cfg_clamps_and_rejects_bad_sidecar():
    _set_cfg(
        {
            "enabled": "true",
            "speed": 9,
            "max_chars": 9999,
            "rate_per_min": 0,
            "sidecar": "http://user:pa55@evil:1",
            "voice": "bad voice!",
        }
    )
    db = SessionLocal()
    cfg = local_tts.local_cfg(db)
    db.close()
    assert cfg["enabled"] is True
    assert cfg["speed"] == 2.0
    assert cfg["max_chars"] == 400
    assert cfg["rate_per_min"] == 1
    assert cfg["sidecar"] == local_tts.DEFAULT_SIDECAR
    assert cfg["voice"] == local_tts.DEFAULT_VOICE
    assert cfg["voice_zh"] == local_tts.DEFAULT_VOICE_ZH


def test_chinese_text_uses_chinese_voice(monkeypatch):
    _set_cfg(
        {
            "enabled": True,
            "cache_version": "zh1",
            "voice": "en_GB-alan-medium",
            "voice_zh": "zh_CN-huayan-medium",
        }
    )
    token = _register("INV-LOCAL-ZH")
    calls: list[str] = []

    def fake_sidecar(_cfg, _text, voice=""):
        calls.append(voice)
        return b"RIFF" + b"z" * 2048, 5

    monkeypatch.setattr(local_tts, "_call_sidecar", fake_sidecar)
    text = "漏读了 really，跟着示范逐词读完整。"

    first = client.post("/api/v1/speak/tts/local", json={"text": text}, headers=_h(token))
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["lang"] == "zh"
    assert body["voice"] == "zh_CN-huayan-medium"
    assert calls == ["zh_CN-huayan-medium"]

    hit = client.get("/api/v1/speak/tts/local", params={"text": text, "v": "zh1"})
    assert hit.status_code == 200
    assert hit.headers["x-tts-lang"] == "zh"
    assert len(calls) == 1


def test_synth_then_get_from_cache(monkeypatch):
    _set_cfg({"enabled": True, "cache_version": "test1", "sidecar": "http://tts:8100"})
    token = _register("INV-LOCAL1")
    calls = {"n": 0}

    def fake_sidecar(_cfg, _text, _voice=""):
        calls["n"] += 1
        return b"RIFF" + b"x" * 2048, 7

    monkeypatch.setattr(local_tts, "_call_sidecar", fake_sidecar)

    first = client.post(
        "/api/v1/speak/tts/local", json={"text": "Hello there."}, headers=_h(token)
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["cached"] is False
    assert body["provider"] == "piper"
    assert body["url"].startswith("/api/v1/speak/tts/file/")

    second = client.post(
        "/api/v1/speak/tts/local", json={"text": "Hello there."}, headers=_h(token)
    )
    assert second.json()["cached"] is True
    assert calls["n"] == 1

    hit = client.get(
        "/api/v1/speak/tts/local", params={"text": "Hello there.", "v": "test1"}
    )
    assert hit.status_code == 200
    assert hit.headers["content-type"].startswith("audio/wav")
    assert "immutable" in hit.headers["cache-control"]

    miss = client.get("/api/v1/speak/tts/local", params={"text": "never generated"})
    assert miss.status_code == 404
    assert calls["n"] == 1  # GET 永不合成


def test_disabled_and_requires_login():
    _set_cfg({"enabled": False})
    token = _register("INV-LOCAL2")

    assert client.post("/api/v1/speak/tts/local", json={"text": "Hi."}).status_code == 401
    assert (
        client.post(
            "/api/v1/speak/tts/local", json={"text": "Hi."}, headers=_h(token)
        ).status_code
        == 503
    )
    assert (
        client.get("/api/v1/speak/tts/local", params={"text": "Hi."}).status_code == 404
    )


def test_per_user_rate_limit(monkeypatch):
    _set_cfg({"enabled": True, "rate_per_min": 1, "cache_version": "test3"})
    token = _register("INV-LOCAL3")
    monkeypatch.setattr(
        local_tts, "_call_sidecar", lambda _cfg, _text, _voice="": (b"RIFF" + b"y" * 2048, 3)
    )

    ok = client.post(
        "/api/v1/speak/tts/local", json={"text": "One."}, headers=_h(token)
    )
    assert ok.status_code == 200, ok.text
    blocked = client.post(
        "/api/v1/speak/tts/local", json={"text": "Two."}, headers=_h(token)
    )
    assert blocked.status_code == 429
