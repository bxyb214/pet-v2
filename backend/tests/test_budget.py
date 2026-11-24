"""AI 预算、告警与 Realtime 会话跟踪（P0-1 / P0-2）。"""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.budget import AiSession, UsageAlert
from app.models.usage import Usage
from app.models.user import InviteCode, User
from app.services import budget, usage as usage_svc

client = TestClient(app)


def _user(db, name: str, *, ai: bool = True, daily=None, monthly=None) -> User:
    u = User(
        username=name,
        password_hash="x",
        perms="speak",
        ai_enabled=ai,
        ai_daily_budget_milli=daily,
        ai_monthly_budget_milli=monthly,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


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


def _register_kid() -> str:
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
    kid.perms = "speak"
    db.commit()
    db.close()
    return r.json()["access_token"]


def test_not_enabled_blocks_paid_endpoints():
    _claim_admin()
    token = _register_kid()
    db = SessionLocal()
    u = _user(db, "nokid", ai=False)
    ok, st = budget.check_access(db, u)
    assert ok is False
    assert st["reason"] == "not_enabled"
    assert st["blocked"] is True
    db.close()

    r = client.post("/api/v1/speak/help", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "AI_NOT_ENABLED"


def test_budget_zero_returns_429():
    _claim_admin()
    token = _register_kid()
    db = SessionLocal()
    kid = db.query(User).filter(User.username == "kid").one()
    kid.ai_enabled = True
    kid.ai_daily_budget_milli = 0
    db.commit()
    db.close()

    r = client.post("/api/v1/speak/help", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 429
    body = r.json()["detail"]
    assert body["code"] == "AI_BUDGET_EXHAUSTED"
    assert body["reset_at"]


def test_daily_stage_alerts_deduplicated():
    db = SessionLocal()
    u = _user(db, "dayu", daily=100, monthly=100_000)
    usage_svc.record(db, u.id, soe_calls=80)  # 80 milli = 80%
    st = budget.status(db, u)
    assert st["daily"]["stage"] == 1
    assert st["blocked"] is False
    assert db.query(UsageAlert).filter_by(user_id=u.id, stage=1).count() == 1

    # 再次查询不重复写告警
    budget.status(db, u)
    assert db.query(UsageAlert).filter_by(user_id=u.id, stage=1).count() == 1

    usage_svc.record(db, u.id, soe_calls=30)  # 110 milli > 100
    st = budget.status(db, u)
    assert st["daily"]["stage"] == 2
    assert st["reason"] == "daily_exhausted"
    assert st["blocked"] is True
    assert db.query(UsageAlert).filter_by(user_id=u.id, stage=2).count() == 1
    db.close()


def test_monthly_limit_blocks_even_if_daily_has_room():
    db = SessionLocal()
    u = _user(db, "monu", daily=10_000, monthly=100)
    usage_svc.record(db, u.id, soe_calls=110)
    st = budget.status(db, u)
    assert st["daily"]["stage"] == 0
    assert st["monthly"]["stage"] == 2
    assert st["reason"] == "monthly_exhausted"
    assert st["max_session_sec"] == 0
    db.close()


def test_max_session_sec_follows_remaining_budget():
    db = SessionLocal()
    u = _user(db, "seclimit", daily=10, monthly=100_000)
    st = budget.status(db, u)
    per_sec = budget.cost_per_sec_milli(db)
    assert st["max_session_sec"] == budget.max_session_sec(10, per_sec)
    assert 0 < st["max_session_sec"] < budget.MAX_SESSION_SEC
    db.close()


def test_session_end_is_idempotent_per_session():
    db = SessionLocal()
    u = _user(db, "sessu", daily=10_000, monthly=100_000)
    sess = budget.session_start(db, u, "talk", 800)
    assert sess["session_id"] > 0
    first = budget.session_end(db, u, 60, 20, sess["session_id"])
    assert first["est_cost_milli"] > 0

    row = db.get(Usage, (u.id, usage_svc.today()))
    cost = row.est_cost_milli
    assert row.rt_seconds == 60

    second = budget.session_end(db, u, 60, 20, sess["session_id"])
    assert second.get("duplicate") is True
    assert second["est_cost_milli"] == 0
    db.refresh(row)
    assert row.est_cost_milli == cost

    srow = db.get(AiSession, sess["session_id"])
    assert srow.status == "closed" and srow.seconds == 60
    db.close()


def test_session_end_ignores_other_users_session():
    db = SessionLocal()
    owner = _user(db, "owner", daily=10_000)
    other = _user(db, "other", daily=10_000)
    sess = budget.session_start(db, owner, "talk")
    out = budget.session_end(db, other, 60, 20, sess["session_id"])
    assert out.get("ignored") is True
    assert out["est_cost_milli"] == 0
    assert db.get(AiSession, sess["session_id"]).status == "open"
    db.close()


def test_sweep_closes_stale_session_at_cap():
    db = SessionLocal()
    u = _user(db, "stale", daily=10_000, monthly=100_000)
    row = AiSession(
        user_id=u.id,
        mode="talk",
        status="open",
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    assert budget.sweep_sessions(db, u.id) == 1
    db.refresh(row)
    assert row.status == "expired"
    assert row.seconds == budget.MAX_SESSION_SEC
    usage_row = db.get(Usage, (u.id, usage_svc.today()))
    assert usage_row is not None and usage_row.rt_seconds == budget.MAX_SESSION_SEC
    db.close()
