"""speak API 测试：权限 / boot 提示词 / log→days 打卡 / 无 Key 503。

conftest 每个测试后清空数据，因此每个测试用 _fresh_user() 独立建号。
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models.user import InviteCode, User

client = TestClient(app)


def _fresh_user(username: str = "speaker") -> str:
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


def test_requires_speak_perm():
    # 未开通 speak 的用户 → 403
    db = SessionLocal()
    db.add(InviteCode(code="INV-nospeak"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "nospeak", "password": "secret123", "invite_code": "INV-nospeak"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]
    r = client.post("/api/v1/speak/boot", json={"mode": "talk"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_boot_shadow_instructions():
    token = _fresh_user()
    r = client.post(
        "/api/v1/speak/boot",
        json={"mode": "shadow", "day": 3, "target": "My name is Chen."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "pronunciation checker" in body["instructions"]
    assert "My name is Chen." in body["instructions"]
    assert "Day 3" in body["instructions"]


def test_boot_talk_with_scene_and_patterns():
    token = _fresh_user()
    r = client.post(
        "/api/v1/speak/boot",
        json={
            "mode": "talk", "day": 5, "scene_title": "Shopping",
            "scene_focus": "ask prices", "patterns": ["How much is...?"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "Scene: Shopping" in body["instructions"]
    assert "How much is...?" in body["instructions"]


def test_log_creates_day_checkin():
    token = _fresh_user()
    H = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/speak/log", json={"mode": "shadow", "ref": "p1-intro", "day": 1, "turns": 5, "score": 88}, headers=H).status_code == 200
    assert client.post("/api/v1/speak/log", json={"mode": "talk", "ref": "c101", "day": 1, "turns": 6, "score": 75}, headers=H).status_code == 200
    d = client.get("/api/v1/speak/days", headers=H).json()
    assert d["days"][0]["day"] == 1
    assert d["days"][0]["shadow_done"] is True
    assert d["days"][0]["talk_done"] is True
    assert d["days"][0]["score"] == 88  # 历史最高


def test_boot_talk_includes_history_avg():
    token = _fresh_user()
    H = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/speak/log", json={"mode": "talk", "day": 0, "score": 70, "issues": ["third person s"]}, headers=H)
    r = client.post("/api/v1/speak/boot", json={"mode": "talk"}, headers=H)
    body = r.json()
    assert body["avg"] == 70
    assert "third person s" in body["instructions"]


def test_sdp_without_key_503():
    token = _fresh_user()
    r = client.post(
        "/api/v1/speak/sdp",
        json={"sdp": "v=0 o=- 1 1 IN IP4 127.0.0.1 s=-", "mode": "shadow"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 503


def test_tts_without_key_503():
    token = _fresh_user()
    r = client.post("/api/v1/speak/tts", json={"text": "hello"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 503


def test_instructions_pure_functions():
    from app.services.qwen_speak import build_instructions
    s = build_instructions("shadow", 0, "Hello world.")
    assert "never chat" in s
    s2 = build_instructions("talk", 9, "", scene_title="S", patterns=["a", "b"], issues=["x"], avg_score=70)
    assert "day 9" in s2
    assert "70/100" in s2
    assert "  1) x" in s2
