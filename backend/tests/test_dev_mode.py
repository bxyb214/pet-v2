"""开发/测试环境：DEV 标识 + 不调用外部 AI 的确定性结果。"""
import base64

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models.user import InviteCode, User

client = TestClient(app)


@pytest.fixture
def dev(monkeypatch):
    monkeypatch.setenv("PET_DEV_MODE", "1")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("PET_DEV_MODE", raising=False)
    get_settings.cache_clear()


def _fresh_user(username: str = "devkid") -> str:
    db = SessionLocal()
    db.add(InviteCode(code=f"INV-{username}"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": username, "password": "secret123", "invite_code": f"INV-{username}"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).one()
    u.perms = "speak"
    db.commit()
    db.close()
    return token


def test_healthz_reports_dev_mode(dev):
    body = client.get("/api/v1/healthz").json()
    assert body["status"] == "ok"
    assert body["dev_mode"] is True


def test_dev_mode_off_by_default():
    get_settings.cache_clear()
    assert client.get("/api/v1/healthz").json()["dev_mode"] is False


def test_dev_sdp_and_soe_never_call_external_services(dev):
    token = _fresh_user()
    H = {"Authorization": f"Bearer {token}"}
    sdp = client.post("/api/v1/speak/sdp", json={"sdp": "v=0\n" * 10, "mode": "talk"}, headers=H)
    assert sdp.status_code == 503
    assert "开发环境" in sdp.json()["detail"]
    soe = client.post("/api/v1/speak/soe_url", json={"ref_text": "I like football."}, headers=H)
    assert soe.status_code == 503
    assert "开发环境" in soe.json()["detail"]


def test_dev_session_end_does_not_record_cost(dev):
    token = _fresh_user("devcost")
    r = client.post(
        "/api/v1/speak/session_end",
        json={"seconds": 60, "mode": "talk"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["est_cost_milli"] == 0


def test_dev_improve_returns_optimal_sentence(dev):
    token = _fresh_user("devtalk")
    r = client.post(
        "/api/v1/speak/improve",
        json={"text": "i like play football", "last_ai_text": "What do you like?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["improved_en"] == "I like playing football."
    assert body["dims"] == ["grammar:sentence"]


def test_dev_help_and_check_are_deterministic(dev):
    token = _fresh_user("devhelp")
    H = {"Authorization": f"Bearer {token}"}
    help_r = client.post(
        "/api/v1/speak/help", json={"scene_title": "Shopping"}, headers=H
    )
    assert help_r.status_code == 200
    assert "Shopping" in help_r.json()["cn"]

    check_r = client.post(
        "/api/v1/speak/check",
        json={"pattern": "I like...", "sentence": "i like play football"},
        headers=H,
    )
    assert check_r.status_code == 200
    assert check_r.json()["ok"] is True
    assert check_r.json()["improved"] == "I like playing football."


def test_dev_tts_returns_playable_wav(dev):
    token = _fresh_user("devtts")
    r = client.post(
        "/api/v1/speak/tts", json={"text": "Hello"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mime"] == "audio/wav"
    assert body["dev"] is True
    raw = base64.b64decode(body["b64"])
    assert raw.startswith(b"RIFF")
    assert len(raw) > 1000


def test_dev_enrich_word(dev):
    token = _fresh_user("devword")
    r = client.post(
        "/api/v1/words/custom/enrich",
        json={"word": "pencil"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pos"] == "n."
    assert "pencil" in body["definition"]
    assert "pencil" in body["example_en"]


def test_dev_review_from_transcript_without_llm(dev):
    token = _fresh_user("devreview")
    H = {"Authorization": f"Bearer {token}"}
    log = client.post(
        "/api/v1/speak/log",
        json={
            "mode": "talk",
            "day": 0,
            "turns": 1,
            "transcript": [{"role": "user", "text": "i like play football"}],
        },
        headers=H,
    )
    assert log.status_code == 200, log.text
    r = client.post("/api/v1/speak/review", json={"log_id": log.json()["log_id"]}, headers=H)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["child_said"] == "i like play football"
    assert items[0]["improved_en"] == "I like playing football."
