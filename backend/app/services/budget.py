"""AI 总额度、告警与 Realtime 会话跟踪（P0-1 / P0-2）。

- 每个账号有一笔**一次性总额度**（默认 0.5 元）；用完后付费 AI 暂停，直到管理员调高。
- 每条付费请求先过 `check_access`：未开通 403；总额度用尽 429。
- 管理员账号不受总额度拦截（仍记账并展示），避免把自己锁死。
- 告警按总额度的 80% / 100% 去重写入 `usage_alerts`（period=total）。
- `ai_sessions` 跟踪 Realtime 会话；超过 30 分钟未结束的，按上限估算补记，避免白用。
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.budget import AiSession, UsageAlert
from app.models.usage import Usage
from app.models.user import User
from app.services import usage as usage_svc
from app.services.ai_enrich import get_cfg

_CST = timezone(timedelta(hours=8))
DEFAULT_BUDGET = {
    "credit_milli": 500,  # 普通账号默认一次性总额度：0.5 元
    "alert_ratio": 0.8,
    "hard_stop": True,
    "currency": "CNY",
}
# 总额度告警的周期键：一次账号生命周期只记一次
CREDIT_PERIOD = "total"
CREDIT_PERIOD_KEY = "all"
# 一次 Realtime 会话的上限（秒）：15–30 分钟，防止漏记时无限补记
MAX_SESSION_SEC = 1800
# 超过该时长仍未收到 session_end，视为异常结束
STALE_MINUTES = 30


def budget_cfg(db: Session) -> dict:
    """全局默认额度配置（兼容旧日/月预算 JSON，读不到新键时用默认）。"""
    raw = get_cfg(db, "ai.budget", "")
    cfg = dict(DEFAULT_BUDGET)
    if raw:
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                if d.get("credit_milli") is not None:
                    cfg["credit_milli"] = max(0, int(d["credit_milli"]))
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
    credit = user.ai_credit_milli
    return {
        "credit_milli": cfg["credit_milli"] if credit is None else max(0, int(credit)),
        "alert_ratio": cfg["alert_ratio"],
        "hard_stop": cfg["hard_stop"],
        "currency": cfg["currency"],
    }


def used_total(db: Session, user_id: int) -> int:
    """账号生命周期内累计预估费用（0.001 元）。"""
    return usage_svc.total_used(db, user_id)


def _stage(used: int, budget: int, ratio: float) -> int:
    if budget <= 0:
        return 2
    if used >= budget:
        return 2
    return 1 if used >= budget * ratio else 0


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
    used = used_total(db, user.id)
    stage = _stage(used, limits["credit_milli"], limits["alert_ratio"])
    enabled = bool(getattr(user, "ai_enabled", False))
    # 管理员是额度管理者，不受总额度拦截，也不写额度告警，但仍展示用量
    unlimited = bool(getattr(user, "is_admin", False))
    if not unlimited:
        _record_alerts(db, user.id, {CREDIT_PERIOD: (stage, CREDIT_PERIOD_KEY)})
    remaining = max(0, limits["credit_milli"] - used)
    reason = ""
    message = ""
    if not enabled:
        reason = "not_enabled"
        message = "此功能调用外部 AI 接口，有费用，需要找小淏开通。"
    elif stage >= 2 and not unlimited:
        reason = "credit_exhausted"
        message = "AI 总额度已用完，免费功能仍可用；需要更多额度请联系小淏。"
    blocked = bool(reason) and (not enabled or limits["hard_stop"])
    per_sec = cost_per_sec_milli(db)
    return {
        "ai_enabled": enabled,
        "speak_enabled": True,
        "unlimited": unlimited,
        "credit": {
            "used_milli": used,
            "budget_milli": limits["credit_milli"],
            "ratio": round(used / limits["credit_milli"], 3)
            if limits["credit_milli"]
            else 1.0,
            "stage": stage,
        },
        "remaining_milli": remaining,
        "max_session_sec": MAX_SESSION_SEC
        if unlimited
        else max_session_sec(remaining, per_sec),
        "blocked": blocked,
        "reason": reason,
        "message": message,
        "alert_stage": stage,
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


def _month_range_utc(month: str) -> tuple[datetime, datetime]:
    """北京时间的自然月 → UTC 的 [start, end) 片刻（库里的 created_at 为 UTC）。"""
    try:
        year, mon = int(month[:4]), int(month[5:7])
        if not 1 <= mon <= 12:
            raise ValueError
    except (TypeError, ValueError):
        today = usage_svc.today()
        year, mon = int(today[:4]), int(today[5:7])
    start = datetime(year, mon, 1, tzinfo=_CST)
    year2, mon2 = (year + 1, 1) if mon == 12 else (year, mon + 1)
    end = datetime(year2, mon2, 1, tzinfo=_CST)
    return (
        start.astimezone(timezone.utc).replace(tzinfo=None),
        end.astimezone(timezone.utc).replace(tzinfo=None),
    )


def alert_rows(db: Session, month: str = "") -> list[dict]:
    month = month or usage_svc.today()[:7]
    start, end = _month_range_utc(month)
    rows = (
        db.query(UsageAlert)
        .filter(
            or_(
                UsageAlert.period_key.like(f"{month}%"),
                (
                    (UsageAlert.period == CREDIT_PERIOD)
                    & (UsageAlert.created_at >= start)
                    & (UsageAlert.created_at < end)
                ),
            )
        )
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
    """今日（北京时间）新产生的额度告警数。"""
    now = datetime.now(_CST)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start.astimezone(timezone.utc).replace(tzinfo=None)
    return int(
        db.query(func.count(UsageAlert.id))
        .filter(UsageAlert.created_at >= start_utc)
        .scalar()
        or 0
    )
