"""AI 用量记账（U 组）：按人按天，只记录不限流。单价存 pet_cfg('usage.prices')。

记账点全部在服务端（客户端不可信）：
- Realtime：会话关闭时前端上报秒数，服务端按官方换算率折算 token（7 / 12.5 tok/s）
- SOE：soe_url 每签发一次计 1 次（按参考文本词数折算，20 词 1 次）
- LLM：从 API 响应 usage 里取 prompt/completion tokens
"""

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.usage import Usage
from app.services.ai_enrich import get_cfg

# 官方换算系数与默认单价（元/百万 token；SOE 元/次）。调价改配置不改代码。
AUDIO_IN_TPS = 7
AUDIO_OUT_TPS = 12.5
DEFAULT_PRICES = {
    "rt_audio_in": 6.0,
    "rt_audio_out": 12.0,
    "rt_text_in": 1.5,
    "rt_text_out": 4.5,
    "soe": 0.001,
    "llm_in": 0.8,
    "llm_out": 2.7,
}

_CST = timezone(timedelta(hours=8))


def today() -> str:
    """北京时间 YYYY-MM-DD（记账与到期日均按北京时区）。"""
    return datetime.now(_CST).strftime("%Y-%m-%d")


def prices(db: Session) -> dict:
    raw = get_cfg(db, "usage.prices", "")
    if not raw:
        return dict(DEFAULT_PRICES)
    import json

    try:
        d = json.loads(raw)
        if isinstance(d, dict):
            merged = dict(DEFAULT_PRICES)
            merged.update({k: float(v) for k, v in d.items() if k in DEFAULT_PRICES})
            return merged
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return dict(DEFAULT_PRICES)


def record(db: Session, user_id: int, **inc: int) -> Usage:
    """累加字段并按当前单价重算预估费用（幂等重算，改价后次日行自动按新价）。"""
    row = db.get(Usage, (user_id, today()))
    if row is None:
        row = Usage(user_id=user_id, day=today())
        db.add(row)
        db.flush()  # 让列默认值（0）落到实例上，避免 None + int
    for k, v in inc.items():
        if v and hasattr(row, k):
            setattr(row, k, (getattr(row, k) or 0) + int(v))
    p = prices(db)
    cost = (
        row.rt_audio_in_tok / 1e6 * p["rt_audio_in"]
        + row.rt_audio_out_tok / 1e6 * p["rt_audio_out"]
        + row.rt_text_in_tok / 1e6 * p["rt_text_in"]
        + row.rt_text_out_tok / 1e6 * p["rt_text_out"]
        + row.soe_calls * p["soe"]
        + row.llm_in_tok / 1e6 * p["llm_in"]
        + row.llm_out_tok / 1e6 * p["llm_out"]
    )
    row.est_cost_milli = round(cost * 1000)
    db.commit()
    return row


def record_session(db: Session, user_id: int, seconds: int, ai_seconds: int = 0) -> Usage:
    """Realtime 会话关闭：按秒数折算音频 token（ai_seconds 缺省按 1/3 估）。"""
    seconds = max(0, int(seconds))
    ai = max(0, int(ai_seconds)) if ai_seconds else seconds // 3
    return record(
        db,
        user_id,
        rt_seconds=seconds,
        rt_ai_seconds=ai,
        rt_audio_in_tok=round(seconds * AUDIO_IN_TPS),
        rt_audio_out_tok=round(ai * AUDIO_OUT_TPS),
    )


def record_soe(db: Session, user_id: int, ref_text: str) -> None:
    """SOE 签发计数：参考文本按 20 词折 1 次（腾讯口径），至少 1 次。"""
    words = len(ref_text.split())
    calls = max(1, math.ceil(words / 20)) if ref_text.strip() else 1
    record(db, user_id, soe_calls=calls)


def record_llm(db: Session, user_id: int, usage: dict | None) -> None:
    """LLM 响应 usage（OpenAI 兼容格式）：prompt_tokens / completion_tokens。"""
    if not usage:
        return
    try:
        record(
            db,
            user_id,
            llm_in_tok=int(usage.get("prompt_tokens", 0)),
            llm_out_tok=int(usage.get("completion_tokens", 0)),
        )
    except (TypeError, ValueError):
        pass


def day_row(db: Session, user_id: int, day: str = "") -> dict:
    row = db.get(Usage, (user_id, day or today()))
    if row is None:
        return {"day": day or today(), "rt_seconds": 0, "soe_calls": 0, "llm_in_tok": 0, "llm_out_tok": 0, "est_cost_milli": 0}
    return {
        "day": row.day,
        "rt_seconds": row.rt_seconds,
        "rt_ai_seconds": row.rt_ai_seconds,
        "soe_calls": row.soe_calls,
        "llm_in_tok": row.llm_in_tok,
        "llm_out_tok": row.llm_out_tok,
        "est_cost_milli": row.est_cost_milli,
    }


def _username(db: Session, user_id: int) -> str:
    from app.models.user import User

    u = db.get(User, user_id)
    return u.username if u else f"#{user_id}"


def admin_day(db: Session, day: str = "") -> dict:
    day = day or today()
    rows = db.query(Usage).filter(Usage.day == day).all()
    return {
        "day": day,
        "total_cost_milli": sum(r.est_cost_milli for r in rows),
        "users": [
            {
                "user_id": r.user_id,
                "username": _username(db, r.user_id),
                "rt_seconds": r.rt_seconds,
                "soe_calls": r.soe_calls,
                "llm_in_tok": r.llm_in_tok,
                "llm_out_tok": r.llm_out_tok,
                "est_cost_milli": r.est_cost_milli,
            }
            for r in rows
        ],
    }


def admin_month(db: Session, month: str) -> dict:
    """month = 'YYYY-MM'：按用户汇总整月费用与用量。"""
    like = f"{month}-%"
    rows = (
        db.query(
            Usage.user_id,
            func.sum(Usage.rt_seconds),
            func.sum(Usage.soe_calls),
            func.sum(Usage.llm_in_tok),
            func.sum(Usage.llm_out_tok),
            func.sum(Usage.est_cost_milli),
        )
        .filter(Usage.day.like(like))
        .group_by(Usage.user_id)
        .all()
    )
    return {
        "month": month,
        "total_cost_milli": sum(r[5] or 0 for r in rows),
        "users": [
            {
                "user_id": r[0],
                "username": _username(db, r[0]),
                "rt_seconds": r[1] or 0,
                "soe_calls": r[2] or 0,
                "llm_in_tok": r[3] or 0,
                "llm_out_tok": r[4] or 0,
                "est_cost_milli": r[5] or 0,
            }
            for r in rows
        ],
    }
