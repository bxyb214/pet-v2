"""AI 预算、告警与 Realtime 会话跟踪（P0-1 / P0-2）。

- 每条付费请求先过 `check_access`：未开通 403；日/月额度用尽 429。
- 告警按日/月周期去重写入 `usage_alerts`（80% 与 100% 各一条）。
- `ai_sessions` 跟踪 Realtime 会话；超过 30 分钟未结束的，按上限估算补记，避免白用。
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import AiSession, UsageAlert
from app.models.usage import Usage
from app.models.user import User
from app.services import usage as usage_svc
from app.services.ai_enrich import get_cfg

_CST = timezone(timedelta(hours=8))
DEFAULT_BUDGET = {
    "daily_milli": 500,
    "monthly_milli": 10000,
    "alert_ratio": 0.8,
    "hard_stop": True,
    "currency": "CNY",
    "timezone": "Asia/Shanghai",
}
# 一次 Realtime 会话的上限（秒）：15–30 分钟，防止漏记时无限补记
MAX_SESSION_SEC = 1800
# 超过该时长仍未收到 session_end，视为异常结束
STALE_MINUTES = 30


def budget_cfg(db: Session) -> dict:
    raw = get_cfg(db, "ai.budget", "")
    cfg = dict(DEFAULT_BUDGET)
    if raw:
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                for k in ("daily_milli", "monthly_milli"):
                    if d.get(k) is not None:
                        cfg[k] = max(0, int(d[k]))
                if d.get("alert_ratio") is not None:
                    cfg["alert_ratio"] = min(1.0, max(0.1, float(d["alert_ratio"])))
                if isinstance(d.get("hard_stop"), bool):
                    cfg["hard_stop"] = d["hard_stop"]
                if d.get("currency"):
                    cfg["currency"] = str(d["currency"])[:8]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return cfg


def user_limits(db: Session, user: User) -> dict:
    cfg = budget_cfg(db)
    daily = user.ai_daily_budget_milli
    monthly = user.ai_monthly_budget_milli
    return {
        "daily_milli": cfg["daily_milli"] if daily is None else max(0, int(daily)),
        "monthly_milli": cfg["monthly_milli"] if monthly is None else max(0, int(monthly)),
        "alert_ratio": cfg["alert_ratio"],
        "hard_stop": cfg["hard_stop"],
        "currency": cfg["currency"],
    }


def used_today(db: Session, user_id: int) -> int:
    row = db.get(Usage, (user_id, usage_svc.today()))
    return int(row.est_cost_milli or 0) if row else 0


def used_month(db: Session, user_id: int) -> int:
    return usage_svc.month_used(db, user_id, usage_svc.today()[:7])


def _stage(used: int, budget: int, ratio: float) -> int:
    if budget <= 0:
        return 2
    if used >= budget:
        return 2
    return 1 if used >= budget * ratio else 0


def _reset_at(period: str) -> str:
    now = datetime.now(_CST)
    if period == "day":
        nxt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        year, month = now.year, now.month + 1
        if month > 12:
            year, month = year + 1, 1
        nxt = now.replace(
            year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    return nxt.isoformat()


def _record_alerts(db: Session, user_id: int, stages: dict[str, tuple[int, str]]) -> None:
    """stages: {period: (stage, period_key)}；只写 1/2，按唯一键去重。"""
    for period, (stage, key) in stages.items():
        if stage <= 0:
            continue
        exists = (
            db.query(UsageAlert)
            .filter(
                UsageAlert.user_id == user_id,
                UsageAlert.period == period,
                UsageAlert.period_key == key,
                UsageAlert.stage == stage,
            )
            .first()
        )
        if exists is None:
            db.add(
                UsageAlert(user_id=user_id, period=period, period_key=key, stage=stage)
            )
    db.commit()


def cost_per_sec_milli(db: Session) -> float:
    """每秒 Realtime 的估算费用（0.001 元）：音频输入 7 tok/s + 输出约 1/3 秒。"""
    p = usage_svc.prices(db)
    cost_yuan = (
        usage_svc.AUDIO_IN_TPS * p["rt_audio_in"] / 1e6
        + (usage_svc.AUDIO_OUT_TPS / 3) * p["rt_audio_out"] / 1e6
        + 3 * p["rt_text_out"] / 1e6
    )
    return max(0.001, cost_yuan * 1000)


def max_session_sec(remaining_milli: int, per_sec: float) -> int:
    if remaining_milli <= 0:
        return 0
    return int(min(MAX_SESSION_SEC, remaining_milli / per_sec))


def status(db: Session, user: User) -> dict:
    """当前用户额度状态（含告警去重写入）。"""
    sweep_sessions(db, user.id)
    limits = user_limits(db, user)
    day_used = used_today(db, user.id)
    month_used = used_month(db, user.id)
    today = usage_svc.today()
    day_stage = _stage(day_used, limits["daily_milli"], limits["alert_ratio"])
    month_stage = _stage(month_used, limits["monthly_milli"], limits["alert_ratio"])
    _record_alerts(
        db,
        user.id,
        {
            "day": (day_stage, today),
            "month": (month_stage, today[:7]),
        },
    )
    day_remaining = max(0, limits["daily_milli"] - day_used)
    month_remaining = max(0, limits["monthly_milli"] - month_used)
    remaining = min(day_remaining, month_remaining)
    enabled = bool(getattr(user, "ai_enabled", False))
    reason = ""
    message = ""
    if not enabled:
        reason = "not_enabled"
        message = "此功能调用外部 AI 接口，有费用，需要找小淏开通。"
    elif day_stage >= 2:
        reason = "daily_exhausted"
        message = "今日 AI 额度已用完，免费功能仍可用。"
    elif month_stage >= 2:
        reason = "monthly_exhausted"
        message = "本月 AI 额度已用完，免费功能仍可用。"
    blocked = bool(reason) and (not enabled or limits["hard_stop"])
    per_sec = cost_per_sec_milli(db)
    return {
        "ai_enabled": enabled,
        "speak_enabled": True,
        "daily": {
            "used_milli": day_used,
            "budget_milli": limits["daily_milli"],
            "ratio": round(day_used / limits["daily_milli"], 3) if limits["daily_milli"] else 1.0,
            "stage": day_stage,
            "reset_at": _reset_at("day"),
        },
        "monthly": {
            "used_milli": month_used,
            "budget_milli": limits["monthly_milli"],
            "ratio": round(month_used / limits["monthly_milli"], 3)
            if limits["monthly_milli"]
            else 1.0,
            "stage": month_stage,
            "reset_at": _reset_at("month"),
        },
        "remaining_milli": remaining,
        "max_session_sec": max_session_sec(remaining, per_sec),
        "blocked": blocked,
        "reason": reason,
        "message": message,
        "alert_stage": max(day_stage, month_stage),
    }


def check_access(db: Session, user: User) -> tuple[bool, dict]:
    """返回 (放行, 状态)。未开通或额度用尽时放行=False。"""
    st = status(db, user)
    if not st["ai_enabled"]:
        return False, st
    if st["blocked"]:
        return False, st
    return True, st


# ---------------------------------------------------------------- 会话跟踪


def session_start(db: Session, user: User, mode: str, instructions_chars: int = 1200) -> dict:
    """SDP 握手创建会话记录，返回 session_id 与可用时长。"""
    st = status(db, user)
    tok, _ = usage_svc.estimate_text_tokens(instructions_chars)
    row = AiSession(user_id=user.id, mode=mode, text_in_tok=tok, status="open")
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "session_id": row.id,
        "max_session_sec": st["max_session_sec"],
        "remaining_milli": st["remaining_milli"],
    }


def _open_session(db: Session, user_id: int, session_id: int = 0) -> AiSession | None:
    if session_id:
        row = db.get(AiSession, session_id)
        if row is not None and row.user_id == user_id and row.status == "open":
            return row
        return None
    return (
        db.query(AiSession)
        .filter(AiSession.user_id == user_id, AiSession.status == "open")
        .order_by(AiSession.id.desc())
        .first()
    )


def session_abort(db: Session, session_id: int) -> None:
    """SDP 协商失败：关闭会话但不记账，避免被超时补记。"""
    row = db.get(AiSession, session_id)
    if row is not None and row.status == "open":
        row.status = "closed"
        row.closed_at = datetime.now(timezone.utc)
        row.seconds = 0
        row.ai_seconds = 0
        row.est_cost_milli = 0
        db.commit()


def session_end(
    db: Session, user: User, seconds: int, ai_seconds: int = 0, session_id: int = 0
) -> dict:
    """关闭会话并按秒数记账；找不到会话时仍按上报秒数记账（兼容旧客户端）。

    同一 `session_id` 只记一次：正常结束与 `sendBeacon` 补报同时到达时，
    第二次直接返回 duplicate，避免重复扣额度。
    """
    seconds = max(0, min(int(seconds), MAX_SESSION_SEC))
    ai_seconds = max(0, min(int(ai_seconds), MAX_SESSION_SEC))
    if session_id:
        row = db.get(AiSession, session_id)
        if row is None or row.user_id != user.id:
            st = status(db, user)
            return {"est_cost_milli": 0, "remaining_milli": st["remaining_milli"], "ignored": True}
        if row.status != "open":
            st = status(db, user)
            return {
                "est_cost_milli": 0,
                "remaining_milli": st["remaining_milli"],
                "duplicate": True,
            }
    else:
        row = _open_session(db, user.id, 0)
    text_in_tok = row.text_in_tok if row else usage_svc.estimate_text_tokens()[0]
    _, text_out_tok = usage_svc.estimate_text_tokens(0, ai_seconds or seconds // 3)
    usage_row = usage_svc.record_session(
        db, user.id, seconds, ai_seconds, text_in_tok=text_in_tok, text_out_tok=text_out_tok
    )
    if row is not None:
        row.status = "closed"
        row.closed_at = datetime.now(timezone.utc)
        row.seconds = seconds
        row.ai_seconds = ai_seconds or seconds // 3
        row.est_cost_milli = usage_row.est_cost_milli
        db.commit()
    st = status(db, user)
    return {"est_cost_milli": usage_row.est_cost_milli, "remaining_milli": st["remaining_milli"]}


def sweep_sessions(db: Session, user_id: int | None = None) -> int:
    """把超过 30 分钟仍 open 的会话按上限（30 分钟）补记并关闭。"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_MINUTES)
    q = db.query(AiSession).filter(AiSession.status == "open", AiSession.started_at < cutoff)
    if user_id is not None:
        q = q.filter(AiSession.user_id == user_id)
    rows = q.all()
    for row in rows:
        seconds = MAX_SESSION_SEC
        ai_seconds = seconds // 3
        _, text_out = usage_svc.estimate_text_tokens(0, ai_seconds)
        usage_row = usage_svc.record_session(
            db,
            row.user_id,
            seconds,
            ai_seconds,
            text_in_tok=row.text_in_tok,
            text_out_tok=text_out,
        )
        row.status = "expired"
        row.closed_at = datetime.now(timezone.utc)
        row.seconds = seconds
        row.ai_seconds = ai_seconds
        row.est_cost_milli = usage_row.est_cost_milli
    if rows:
        db.commit()
    return len(rows)


# ---------------------------------------------------------------- 管理端


def reset_alerts(db: Session, user_id: int, period: str = "") -> int:
    q = db.query(UsageAlert).filter(UsageAlert.user_id == user_id)
    if period:
        q = q.filter(UsageAlert.period == period)
    n = q.delete(synchronize_session=False)
    db.commit()
    return n


def alert_rows(db: Session, month: str = "") -> list[dict]:
    month = month or usage_svc.today()[:7]
    rows = (
        db.query(UsageAlert)
        .filter(UsageAlert.period_key.like(f"{month}%"))
        .order_by(UsageAlert.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "username": usage_svc._username(db, r.user_id),
            "period": r.period,
            "period_key": r.period_key,
            "stage": r.stage,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def month_report(db: Session, month: str) -> dict:
    """月度报表：按日汇总 + 按人汇总 + 月末预测（按已过天数线性外推）。"""
    rows = (
        db.query(Usage)
        .filter(Usage.day.like(f"{month}-%"))
        .order_by(Usage.day)
        .all()
    )
    days: dict[str, dict] = {}
    for r in rows:
        d = days.setdefault(
            r.day,
            {"day": r.day, "rt_seconds": 0, "soe_calls": 0, "llm_tok": 0, "tts_chars": 0, "est_cost_milli": 0},
        )
        d["rt_seconds"] += r.rt_seconds
        d["soe_calls"] += r.soe_calls
        d["llm_tok"] += r.llm_in_tok + r.llm_out_tok
        d["tts_chars"] += r.tts_chars
        d["est_cost_milli"] += r.est_cost_milli
    total = sum(d["est_cost_milli"] for d in days.values())
    now = datetime.now(_CST)
    days_in_month = (
        (now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    ).day
    elapsed = now.day if month == now.strftime("%Y-%m") else days_in_month
    projection = round(total / elapsed * days_in_month) if elapsed else 0
    by_user = usage_svc.admin_month(db, month)
    return {
        "month": month,
        "total_cost_milli": total,
        "projection_cost_milli": projection,
        "days_in_month": days_in_month,
        "elapsed_days": elapsed,
        "daily": [days[k] for k in sorted(days)],
        "users": by_user["users"],
    }


def export_rows(db: Session, month: str) -> list[list[str]]:
    rows = (
        db.query(Usage)
        .filter(Usage.day.like(f"{month}-%"))
        .order_by(Usage.day, Usage.user_id)
        .all()
    )
    out = [["date", "user", "rt_seconds", "soe_calls", "llm_in", "llm_out", "tts_chars", "est_cost_milli"]]
    for r in rows:
        out.append(
            [
                r.day,
                usage_svc._username(db, r.user_id),
                str(r.rt_seconds),
                str(r.soe_calls),
                str(r.llm_in_tok),
                str(r.llm_out_tok),
                str(r.tts_chars),
                str(r.est_cost_milli),
            ]
        )
    return out


def count_alerts_today(db: Session) -> int:
    return int(
        db.query(func.count(UsageAlert.id))
        .filter(UsageAlert.period == "day", UsageAlert.period_key == usage_svc.today())
        .scalar()
        or 0
    )
