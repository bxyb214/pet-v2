"""管理后台 AI 配置 / 用户额度 / 报表 / 缓存接口（P0-1 / P0-4 / P1-4 / P2-3）。"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.user import InviteCode, User
from app.services import budget, usage as usage_svc

client = TestClient(app)


def _claim_admin() -> str:
    db = SessionLocal()
    db.add(InviteCode(code="INV-BOSS"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": "boss", "password": "pet-test-pass", "invite_code": "INV-BOSS"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _register_kid() -> tuple[str, int]:
    db = SessionLocal()
    db.add(InviteCode(code="INV-KID"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "kid", "password": "pet-test-pass", "invite_code": "INV-KID"},
    )
    assert r.status_code == 201, r.text
    db = SessionLocal()
    kid = db.query(User).filter(User.username == "kid").one()
    uid = kid.id
    db.close()
    return r.json()["access_token"], uid


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_set_user_ai_quota_and_restore_default():
    admin = _claim_admin()
    _, uid = _register_kid()
    H = _h(admin)

    rows = client.get("/api/v1/admin/users", headers=H).json()
    kid_row = next(r for r in rows if r["id"] == uid)
    assert kid_row["ai_enabled"] is False
    assert kid_row["credit_custom"] is False
    assert kid_row["default_credit_milli"] == budget.DEFAULT_BUDGET["credit_milli"]

    r = client.put(
        f"/api/v1/admin/users/{uid}/ai",
        json={"enabled": True, "credit_milli": 1000},
        headers=H,
    )
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["ai_enabled"] is True
    assert row["ai_credit_milli"] == 1000
    assert row["credit_budget_milli"] == 1000
    assert row["credit_custom"] is True

    # 显式 null 恢复全局默认
    r = client.put(f"/api/v1/admin/users/{uid}/ai", json={"credit_milli": None}, headers=H)
    row = r.json()
    assert row["ai_credit_milli"] is None
    assert row["credit_budget_milli"] == budget.DEFAULT_BUDGET["credit_milli"]
    assert row["credit_custom"] is False

    # 关闭 AI
    r = client.put(f"/api/v1/admin/users/{uid}/ai", json={"enabled": False}, headers=H)
    assert r.json()["ai_enabled"] is False

    r = client.put("/api/v1/admin/users/99999/ai", json={"enabled": True}, headers=H)
    assert r.status_code == 404


def test_quota_requires_admin():
    _claim_admin()
    kid, uid = _register_kid()
    r = client.put(f"/api/v1/admin/users/{uid}/ai", json={"enabled": True}, headers=_h(kid))
    assert r.status_code == 403


def test_prices_and_budget_config():
    admin = _claim_admin()
    H = _h(admin)

    r = client.put(
        "/api/v1/admin/ai/prices",
        json={
            "prices": {"soe": 0.002, "tts_per_kchar": 0.1},
            "budget": {
                "credit_milli": 1234,
                "alert_ratio": 0.5,
                "hard_stop": False,
            },
            "tts_cache": {"max_mb": 64},
        },
        headers=H,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prices"]["soe"] == 0.002
    assert body["prices"]["tts_per_kchar"] == 0.1
    assert body["budget"]["credit_milli"] == 1234
    assert body["budget"]["alert_ratio"] == 0.5
    assert body["budget"]["hard_stop"] is False
    assert body["tts_cache"]["max_mb"] == 64

    again = client.get("/api/v1/admin/ai/prices", headers=H).json()
    assert again["budget"]["credit_milli"] == 1234
    db = SessionLocal()
    assert usage_svc.prices(db)["soe"] == 0.002
    assert budget.budget_cfg(db)["hard_stop"] is False
    db.close()


def test_overview_report_export_and_alerts():
    admin = _claim_admin()
    _, uid = _register_kid()
    H = _h(admin)

    # 给 kid 一个很小的总额度，制造一条 80% 告警
    client.put(f"/api/v1/admin/users/{uid}/ai", json={"enabled": True, "credit_milli": 100}, headers=H)
    db = SessionLocal()
    usage_svc.record(db, uid, soe_calls=80, tts_chars=100)
    kid = db.get(User, uid)
    budget.status(db, kid)  # 触发告警写入
    db.close()

    ov = client.get("/api/v1/admin/ai/overview", headers=H)
    assert ov.status_code == 200
    body = ov.json()
    assert body["ai_enabled_users"] >= 1
    assert body["alerts_today"] >= 1
    assert set(body["providers"]) >= {"llm", "qwen", "soe"}
    assert body["tts_cache"]["max_mb"] > 0

    month = usage_svc.today()[:7]
    rep = client.get(f"/api/v1/admin/usage/report?month={month}", headers=H)
    assert rep.status_code == 200
    report = rep.json()
    assert report["month"] == month
    assert report["total_cost_milli"] >= 80
    assert report["projection_cost_milli"] >= report["total_cost_milli"]
    assert any(u["user_id"] == uid for u in report["users"])

    csv = client.get(f"/api/v1/admin/usage/export?month={month}", headers=H)
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[0].startswith("date,user")
    assert "kid" in csv.text

    alerts = client.get(f"/api/v1/admin/usage/alerts?month={month}", headers=H).json()
    assert any(a["user_id"] == uid and a["stage"] == 1 for a in alerts["items"])

    r = client.post(f"/api/v1/admin/users/{uid}/ai/reset_alert", headers=H)
    assert r.status_code == 200
    assert r.json()["removed"] >= 1
    left = client.get(f"/api/v1/admin/usage/alerts?month={month}", headers=H).json()
    assert all(a["user_id"] != uid for a in left["items"])

    r = client.post("/api/v1/admin/users/99999/ai/reset_alert", headers=H)
    assert r.status_code == 404


def test_tts_cache_admin_endpoints():
    admin = _claim_admin()
    H = _h(admin)
    r = client.get("/api/v1/admin/tts_cache", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"files", "bytes", "max_mb"}

    r = client.delete("/api/v1/admin/tts_cache", headers=H)
    assert r.status_code == 200
    assert r.json()["removed"] >= 0


def test_connection_tests_are_safe_without_keys():
    admin = _claim_admin()
    H = _h(admin)

    r = client.post("/api/v1/admin/test/soe", headers=H)
    assert r.status_code == 200
    assert r.json()["ok"] is False

    r = client.post("/api/v1/admin/test/realtime", headers=H)
    assert r.status_code == 200
    assert r.json()["ok"] is False

    r = client.post("/api/v1/admin/test/nope", headers=H)
    assert r.status_code == 404


def test_user_rows_no_perms_and_legacy_endpoint_removed():
    """口语不再按人限制：用户列表不返回 perms，旧权限接口已删除。"""
    admin = _claim_admin()
    _, uid = _register_kid()
    H = _h(admin)

    rows = client.get("/api/v1/admin/users", headers=H).json()
    assert all("perms" not in r for r in rows)

    r = client.put(f"/api/v1/admin/users/{uid}/perms", json={"speak": True}, headers=H)
    assert r.status_code == 404
