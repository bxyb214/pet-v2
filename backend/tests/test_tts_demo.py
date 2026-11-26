"""跟读示范 Qwen：登录即可、免费不记账、缓存与限流。"""
import pytest
from fastapi.testclient import TestClient

from app.api.v1 import speak_media
from app.db import SessionLocal
from app.main import app
from app.models.usage import Usage
from app.models.user import InviteCode, User
from app.services import local_tts, qwen_speak

client = TestClient(app)
PWD = "pet-test-pass"


@pytest.fixture(autouse=True)
def _clear_demo_buckets():
    local_tts.qwen_buckets.clear()
    yield
    local_tts.qwen_buckets.clear()


def _register(code: str) -> tuple[str, int]:
    db = SessionLocal()
    db.add(InviteCode(code=code))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/register",
        json={"username": code.lower(), "password": PWD, "invite_code": code},
    )
    assert r.status_code == 201, r.text
    db = SessionLocal()
    uid = db.query(User).filter(User.username == code.lower()).one().id
    db.close()
    return r.json()["access_token"], uid


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _fake_tts(calls: list[str]):
    def fake(_db, _dir, text, voice=""):
        calls.append(text)
        return {
            "url": "/api/v1/speak/tts/file/" + "a" * 40 + ".wav",
            "mime": "audio/wav",
            "cached": len(calls) > 1,
            "chars": len(text),
        }

    return fake


def test_demo_requires_login():
    r = client.post("/api/v1/speak/tts/demo", json={"text": "Hello there."})
    assert r.status_code == 401


def test_demo_is_free_even_when_paid_ai_disabled(monkeypatch):
    token, uid = _register("INV-DEMO-FREE")
    db = SessionLocal()
    user = db.get(User, uid)
    assert user is not None
    user.ai_enabled = False
    db.commit()
    db.close()

    calls: list[str] = []
    monkeypatch.setattr(qwen_speak, "tts", _fake_tts(calls))

    r = client.post(
        "/api/v1/speak/tts/demo", json={"text": "I went to the park."}, headers=_h(token)
    )
    assert r.status_code == 200, r.text
    assert r.json()["provider"] == "qwen"
    assert calls == ["I went to the park."]

    db = SessionLocal()
    assert db.query(Usage).filter(Usage.user_id == uid).count() == 0
    db.close()


def test_demo_second_call_hits_cache(monkeypatch):
    token, _ = _register("INV-DEMO-CACHE")
    calls: list[str] = []
    monkeypatch.setattr(qwen_speak, "tts", _fake_tts(calls))

    first = client.post("/api/v1/speak/tts/demo", json={"text": "Hello."}, headers=_h(token))
    second = client.post("/api/v1/speak/tts/demo", json={"text": "Hello."}, headers=_h(token))
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True


def test_demo_without_qwen_key_returns_503():
    token, _ = _register("INV-DEMO-NOKEY")
    r = client.post("/api/v1/speak/tts/demo", json={"text": "Hello."}, headers=_h(token))
    assert r.status_code == 503


def test_demo_rate_limit(monkeypatch):
    token, _ = _register("INV-DEMO-RATE")
    monkeypatch.setattr(speak_media, "_DEMO_RATE_PER_MIN", 2)
    monkeypatch.setattr(qwen_speak, "tts", _fake_tts([]))

    assert client.post(
        "/api/v1/speak/tts/demo", json={"text": "One."}, headers=_h(token)
    ).status_code == 200
    assert client.post(
        "/api/v1/speak/tts/demo", json={"text": "Two."}, headers=_h(token)
    ).status_code == 200
    assert client.post(
        "/api/v1/speak/tts/demo", json={"text": "Three."}, headers=_h(token)
    ).status_code == 429
