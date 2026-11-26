"""用户端 AI 用量统计（M4）：鉴权、零值、区间汇总与用户隔离。"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.usage import Usage
from app.models.user import InviteCode, User
from app.services import budget
from app.services import usage as usage_svc

client = TestClient(app)


def _register(username: str) -> tuple[str, int]:
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
    user = db.query(User).filter(User.username == username).one()
    uid = user.id
    db.close()
    return r.json()["access_token"], uid


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _insert(user_id: int, day: str, **fields) -> None:
    db = SessionLocal()
    db.add(Usage(user_id=user_id, day=day, **fields))
    db.commit()
    db.close()


def test_usage_me_requires_auth():
    assert client.get("/api/v1/usage/me").status_code == 401


def test_new_user_returns_zeroes():
    token, _ = _register("fresh")
    d = client.get("/api/v1/usage/me", headers=_h(token)).json()

    assert d["month"] == usage_svc.today()[:7]
    assert d["status"]["ai_enabled"] is True
    assert d["status"]["unlimited"] is False
    assert d["status"]["credit"]["used_milli"] == 0
    assert d["status"]["credit"]["budget_milli"] == budget.DEFAULT_BUDGET["credit_milli"]
    assert d["totals"]["today"]["est_cost_milli"] == 0
    assert d["totals"]["week"]["active_days"] == 0
    assert d["totals"]["month"]["active_days"] == 0
    assert d["totals"]["year"]["active_days"] == 0
    assert d["days"] == []
    assert "user_id" not in d


def test_totals_and_user_isolation():
    token_a, uid_a = _register("usage-a")
    token_b, uid_b = _register("usage-b")
    today = usage_svc.today()
    month = today[:7]
    year = today[:4]
    other_day = f"{month}-02" if today == f"{month}-01" else f"{month}-01"

    _insert(
        uid_a,
        today,
        rt_seconds=120,
        rt_ai_seconds=40,
        soe_calls=2,
        llm_in_tok=100,
        llm_out_tok=50,
        tts_calls=1,
        tts_chars=300,
        tts_cache_hits=2,
        est_cost_milli=12,
    )
    _insert(uid_a, other_day, rt_seconds=60, soe_calls=1, est_cost_milli=7)
    _insert(uid_a, f"{int(year) - 1}-12-31", est_cost_milli=500)
    _insert(uid_b, today, rt_seconds=999, soe_calls=999, est_cost_milli=999)

    d = client.get(f"/api/v1/usage/me?month={month}", headers=_h(token_a)).json()

    # 只返回当前用户：B 的 999 不出现在任何汇总/明细
    assert d["days"]
    assert all("user_id" not in row for row in d["days"])
    assert all(row["est_cost_milli"] != 999 for row in d["days"])
    assert [row["day"] for row in d["days"]] == sorted([today, other_day])
    assert d["totals"]["month"]["est_cost_milli"] == 19
    assert d["totals"]["month"]["active_days"] == 2
    assert d["totals"]["today"]["est_cost_milli"] == 12
    assert d["totals"]["today"]["soe_calls"] == 2
    assert d["totals"]["today"]["llm_tok"] == 150
    # 今年汇总包含本月行，不包含去年 500
    assert d["totals"]["year"]["est_cost_milli"] == 19
    # 本周汇总按周一至今计算（与测试数据独立核对）
    expected_week = sum(
        cost
        for day, cost in ((today, 12), (other_day, 7))
        if usage_svc.week_start() <= day <= today
    )
    assert d["totals"]["week"]["est_cost_milli"] == expected_week
    # 总额度按账号生命周期累计（含去年那笔 500）
    assert d["status"]["credit"]["used_milli"] == 519

    # B 只能看到自己的 999
    db = client.get("/api/v1/usage/me", headers=_h(token_b)).json()
    assert db["totals"]["today"]["est_cost_milli"] == 999
    assert all(row["est_cost_milli"] != 12 for row in db["days"])


def test_month_filter_and_validation():
    token, _ = _register("months")
    headers = _h(token)

    empty = client.get("/api/v1/usage/me?month=2020-01", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["month"] == "2020-01"
    assert empty.json()["days"] == []
    assert empty.json()["totals"]["month"]["est_cost_milli"] == 0

    assert client.get("/api/v1/usage/me?month=2026-13", headers=headers).status_code == 422
    assert client.get("/api/v1/usage/me?month=abc", headers=headers).status_code == 422
