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
        json={"username": "admin", "password": "pet-test-pass", "invite_code": "TEST-INVITE-1"},
    )
    assert r.status_code == 201
    assert r.json()["is_admin"] is True


def test_claim_blocked_when_initialized():
    _add_invite("TEST-INVITE-2")
    client.post(
        "/api/v1/auth/claim",
        json={"username": "admin0", "password": "pet-test-pass", "invite_code": "TEST-INVITE-2"},
    )
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": "x", "password": "pet-test-pass", "invite_code": "TEST-INVITE-2"},
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
        json={"username": "kid", "password": "pet-test-pass", "invite_code": "TEST-INVITE-3"},
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
        json={"username": "kid2", "password": "pet-test-pass", "invite_code": "TEST-INVITE-4"},
    )
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "kid3", "password": "pet-test-pass", "invite_code": "TEST-INVITE-4"},
    )
    assert r.status_code == 400


def test_refresh_flow():
    _add_invite("TEST-INVITE-5")
    client.post(
        "/api/v1/auth/claim",
        json={"username": "admin", "password": "pet-test-pass", "invite_code": "TEST-INVITE-5"},
    )
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "pet-test-pass"})
    refresh_token = r.json()["refresh_token"]
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 200
    assert r2.json()["access_token"]


def _login_token(username: str, password: str) -> str:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_update_me_display_name():
    _add_invite("TEST-INVITE-6")
    client.post(
        "/api/v1/auth/register",
        json={"username": "nick", "password": "pet-test-pass", "invite_code": "TEST-INVITE-6"},
    )
    token = _login_token("nick", "pet-test-pass")
    h = {"Authorization": f"Bearer {token}"}
    r = client.put("/api/v1/auth/me", json={"display_name": "小明"}, headers=h)
    assert r.status_code == 200
    assert r.json()["display_name"] == "小明"
    me = client.get("/api/v1/auth/me", headers=h)
    assert me.json()["display_name"] == "小明"


def test_change_password_flow():
    _add_invite("TEST-INVITE-7")
    client.post(
        "/api/v1/auth/register",
        json={"username": "pwuser", "password": "pet-test-pass", "invite_code": "TEST-INVITE-7"},
    )
    token = _login_token("pwuser", "pet-test-pass")
    h = {"Authorization": f"Bearer {token}"}
    # 旧密码错 → 400
    r = client.post(
        "/api/v1/auth/me/password",
        json={"old_password": "wrong", "new_password": "newpass-123"},
        headers=h,
    )
    assert r.status_code == 400
    # 旧密码对 → 200 并返回新 token
    r = client.post(
        "/api/v1/auth/me/password",
        json={"old_password": "pet-test-pass", "new_password": "newpass-123"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["access_token"]
    # 新密码能登录，旧密码不能
    assert client.post("/api/v1/auth/login", json={"username": "pwuser", "password": "newpass-123"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"username": "pwuser", "password": "pet-test-pass"}).status_code == 401


def test_admin_reset_user_password():
    _add_invite("TEST-INVITE-8A")
    client.post(
        "/api/v1/auth/claim",
        json={"username": "root", "password": "pet-test-pass", "invite_code": "TEST-INVITE-8A"},
    )
    _add_invite("TEST-INVITE-8")
    client.post(
        "/api/v1/auth/register",
        json={"username": "victim", "password": "pet-test-pass", "invite_code": "TEST-INVITE-8"},
    )
    admin_token = _login_token("root", "pet-test-pass")
    user_token = _login_token("victim", "pet-test-pass")
    # 非管理员 → 403
    r = client.post("/api/v1/admin/users/999/reset_password", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 403
    users = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    uid = next(u["id"] for u in users if u["username"] == "victim")
    r = client.post(f"/api/v1/admin/users/{uid}/reset_password", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    temp = r.json()["temp_password"]
    assert temp.startswith("pet-") and len(temp) == 12
    # 旧密码失效，临时密码可登录
    assert client.post("/api/v1/auth/login", json={"username": "victim", "password": "pet-test-pass"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "victim", "password": temp}).status_code == 200
