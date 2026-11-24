"""媒体令牌测试：签发需登录；取流只认 media 类型；过期/未知用户拒绝。"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models.user import InviteCode, User

client = TestClient(app)


def _fresh_user(username: str = "viewer") -> tuple[str, int]:
    db = SessionLocal()
    db.add(InviteCode(code=f"INV-{username}"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": username, "password": "pet-test-pass", "invite_code": f"INV-{username}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"], r.json()["user_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_issue_requires_login():
    r = client.post("/api/v1/media/token")
    assert r.status_code == 401


def test_issue_and_use_media_token():
    token, _ = _fresh_user()
    r = client.post("/api/v1/media/token", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"] and body["expires_at"] > int(datetime.now(timezone.utc).timestamp())

    ok = client.get("/api/v1/media/auth", headers={"X-Media-Token": body["token"]})
    assert ok.status_code == 204
    assert ok.content == b""


def test_access_token_is_not_media_token():
    token, _ = _fresh_user()
    r = client.get("/api/v1/media/auth", headers={"X-Media-Token": token})
    assert r.status_code == 401


def test_missing_or_garbage_token_rejected():
    assert client.get("/api/v1/media/auth").status_code == 401
    assert client.get("/api/v1/media/auth", headers={"X-Media-Token": "nope"}).status_code == 401


def test_expired_media_token_rejected():
    _, uid = _fresh_user()
    s = get_settings()
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    expired = jwt.encode(
        {"sub": str(uid), "type": "media", "iat": int(past.timestamp()) - 60, "exp": int(past.timestamp())},
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )
    assert client.get("/api/v1/media/auth", headers={"X-Media-Token": expired}).status_code == 401


def test_token_for_deleted_user_rejected():
    token, uid = _fresh_user()
    media = client.post("/api/v1/media/token", headers=_auth(token)).json()["token"]
    db = SessionLocal()
    u = db.get(User, uid)
    db.delete(u)
    db.commit()
    db.close()
    assert client.get("/api/v1/media/auth", headers={"X-Media-Token": media}).status_code == 401
