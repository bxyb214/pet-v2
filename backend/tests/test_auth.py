"""auth 冒烟测试：claim → login → me → refresh → register（邀请码）。"""
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models.user import InviteCode


def _add_invite(code: str) -> None:
    db = SessionLocal()
    db.add(InviteCode(code=code))
    db.commit()
    db.close()


client = TestClient(app)


def test_healthz():
    r = client.get("/api/v1/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_claim_creates_admin():
    _add_invite("TEST-INVITE-1")
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": "admin", "password": "secret123", "invite_code": "TEST-INVITE-1"},
    )
    assert r.status_code == 201
    assert r.json()["is_admin"] is True


def test_claim_blocked_when_initialized():
    _add_invite("TEST-INVITE-2")
    client.post(
        "/api/v1/auth/claim",
        json={"username": "admin0", "password": "secret123", "invite_code": "TEST-INVITE-2"},
    )
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": "x", "password": "secret123", "invite_code": "TEST-INVITE-2"},
    )
    assert r.status_code == 403


def test_login_wrong_password():
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token():
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_register_with_invite_and_me():
    _add_invite("TEST-INVITE-3")
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "kid", "password": "secret123", "invite_code": "TEST-INVITE-3"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "kid"
    assert me.json()["is_admin"] is False


def test_register_reused_invite_rejected():
    _add_invite("TEST-INVITE-4")
    client.post(
        "/api/v1/auth/register",
        json={"username": "kid2", "password": "secret123", "invite_code": "TEST-INVITE-4"},
    )
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "kid3", "password": "secret123", "invite_code": "TEST-INVITE-4"},
    )
    assert r.status_code == 400


def test_refresh_flow():
    _add_invite("TEST-INVITE-5")
    client.post(
        "/api/v1/auth/claim",
        json={"username": "admin", "password": "secret123", "invite_code": "TEST-INVITE-5"},
    )
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
    refresh_token = r.json()["refresh_token"]
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 200
    assert r2.json()["access_token"]
