"""管理后台：账号口语权限开关（PUT /admin/users/{id}/perms）。"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.user import InviteCode, User

client = TestClient(app)


def _claim(username: str) -> str:
    db = SessionLocal()
    db.add(InviteCode(code=f"INV-{username}"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": username, "password": "pet-test-pass", "invite_code": f"INV-{username}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _register(username: str) -> int:
    db = SessionLocal()
    db.add(InviteCode(code=f"INV-{username}"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "pet-test-pass", "invite_code": f"INV-{username}"},
    )
    assert r.status_code == 201, r.text
    db = SessionLocal()
    uid = db.query(User).filter(User.username == username).one().id
    db.close()
    return uid


def test_toggle_speak_perm_for_user():
    admin = _claim("boss")  # 空库首个 claim → 管理员
    uid = _register("kid")
    H = {"Authorization": f"Bearer {admin}"}

    # 初始未开通
    rows = client.get("/api/v1/admin/users", headers=H).json()
    kid = next(r for r in rows if r["id"] == uid)
    assert "speak" not in kid["perms"].split(",")

    # 开通
    r = client.put(f"/api/v1/admin/users/{uid}/perms", json={"speak": True}, headers=H)
    assert r.status_code == 200, r.text
    assert "speak" in r.json()["perms"].split(",")

    # 孩子侧立刻能用口语接口
    login = client.post("/api/v1/auth/login", json={"username": "kid", "password": "pet-test-pass"})
    kidH = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=kidH).json()["perms"].split(",").count("speak") == 1
    assert client.post("/api/v1/speak/boot", json={"mode": "shadow"}, headers=kidH).status_code == 200

    # 关闭
    r = client.put(f"/api/v1/admin/users/{uid}/perms", json={"speak": False}, headers=H)
    assert r.status_code == 200
    assert "speak" not in r.json()["perms"].split(",")
    assert client.post("/api/v1/speak/boot", json={"mode": "shadow"}, headers=kidH).status_code == 403


def test_toggle_keeps_other_flags():
    admin = _claim("boss2")
    uid = _register("kid2")
    db = SessionLocal()
    u = db.get(User, uid)
    u.perms = "!listen"
    db.commit()
    db.close()

    H = {"Authorization": f"Bearer {admin}"}
    r = client.put(f"/api/v1/admin/users/{uid}/perms", json={"speak": True}, headers=H)
    assert r.status_code == 200
    db = SessionLocal()
    perms = set(db.get(User, uid).perms.split(","))
    db.close()
    assert perms == {"!listen", "speak"}


def test_admin_can_close_and_reopen_own_speak():
    """管理员默认开通，但也能显式关闭自己的口语权限，且不影响管理后台。"""
    admin = _claim("boss4")
    H = {"Authorization": f"Bearer {admin}"}
    me = client.get("/api/v1/auth/me", headers=H).json()
    assert "speak" in me["perms"].split(",")
    uid = me["id"]

    r = client.put(f"/api/v1/admin/users/{uid}/perms", json={"speak": False}, headers=H)
    assert r.status_code == 200
    assert "speak" not in r.json()["perms"].split(",")
    assert client.post("/api/v1/speak/boot", json={"mode": "shadow"}, headers=H).status_code == 403
    assert client.get("/api/v1/admin/users", headers=H).status_code == 200

    r = client.put(f"/api/v1/admin/users/{uid}/perms", json={"speak": True}, headers=H)
    assert r.status_code == 200
    assert "speak" in r.json()["perms"].split(",")
    assert client.post("/api/v1/speak/boot", json={"mode": "shadow"}, headers=H).status_code == 200


def test_toggle_requires_admin_and_existing_user():
    _claim("boss3")
    uid = _register("kid3")
    not_admin = client.post(
        "/api/v1/auth/login", json={"username": "kid3", "password": "pet-test-pass"}
    ).json()["access_token"]
    r = client.put(
        f"/api/v1/admin/users/{uid}/perms",
        json={"speak": True},
        headers={"Authorization": f"Bearer {not_admin}"},
    )
    assert r.status_code == 403

    admin = client.post(
        "/api/v1/auth/login", json={"username": "boss3", "password": "pet-test-pass"}
    ).json()["access_token"]
    r = client.put(
        "/api/v1/admin/users/99999/perms",
        json={"speak": True},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert r.status_code == 404
