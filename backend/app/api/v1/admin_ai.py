"""管理后台 · 额度 / 报表 / AI 配置摘要 / TTS 缓存（P0-1 / P0-4 / P1-4 / P2-3）。"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.admin import _user_row
from app.api.v1.speak_media import cache_dir
from app.core.deps import require_admin
from app.db import get_db
from app.models.user import User
from app.services import ai_enrich, budget, qwen_speak, tencent_soe, usage as usage_svc

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------- 概览 / 价格


@router.get("/ai/overview")
def ai_overview(
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    day = usage_svc.admin_day(db)
    users = db.query(User).all()
    enabled = sum(1 for u in users if u.ai_enabled)
    qwen = qwen_speak.qwen_cfg(db)
    soe = tencent_soe.soe_cfg(db)
    max_mb = qwen_speak.tts_cache_cfg(db)
    return {
        "today": day,
        "users_total": len(users),
        "ai_enabled_users": enabled,
        "alerts_today": budget.count_alerts_today(db),
        "providers": {
            "llm": bool((ai_enrich.get_cfg(db, "llm.api_key") or "").strip()),
            "qwen": bool(qwen["api_key"] or (ai_enrich.get_cfg(db, "llm.api_key") or "").strip()),
            "qwen_workspace": bool(qwen["workspace"]),
            "qwen_model": qwen["model"],
            "fallback_model": qwen["fallback_model"],
            "soe": tencent_soe.is_configured(soe),
        },
        "tts_cache": qwen_speak.tts_cache_stats(cache_dir(), max_mb),
    }


class PricesIn(BaseModel):
    prices: dict | None = None
    budget: dict | None = None
    tts_cache: dict | None = None


def _prices_payload(db: Session) -> dict:
    return {
        "prices": usage_svc.prices(db),
        "budget": budget.budget_cfg(db),
        "tts_cache": {"max_mb": qwen_speak.tts_cache_cfg(db)},
    }


@router.get("/ai/prices")
def get_prices(
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return _prices_payload(db)


@router.put("/ai/prices")
def put_prices(
    body: PricesIn,
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    if body.prices is not None:
        merged = usage_svc.prices(db)
        for k, v in body.prices.items():
            if k in merged:
                merged[k] = max(0.0, float(v))
        ai_enrich.set_cfg(db, "usage.prices", json.dumps(merged, ensure_ascii=False))
    if body.budget is not None:
        merged = budget.budget_cfg(db)
        for k in ("daily_milli", "monthly_milli"):
            if body.budget.get(k) is not None:
                merged[k] = max(0, int(body.budget[k]))
        if body.budget.get("alert_ratio") is not None:
            merged["alert_ratio"] = min(1.0, max(0.1, float(body.budget["alert_ratio"])))
        if isinstance(body.budget.get("hard_stop"), bool):
            merged["hard_stop"] = body.budget["hard_stop"]
        ai_enrich.set_cfg(db, "ai.budget", json.dumps(merged, ensure_ascii=False))
    if body.tts_cache is not None and body.tts_cache.get("max_mb") is not None:
        max_mb = max(16, int(body.tts_cache["max_mb"]))
        ai_enrich.set_cfg(db, "speak.tts_cache", json.dumps({"max_mb": max_mb}))
    return _prices_payload(db)


# ---------------------------------------------------------------- 用户额度


class AiQuotaIn(BaseModel):
    enabled: bool | None = None
    daily_milli: int | None = Field(default=None, ge=0, le=1_000_000)
    monthly_milli: int | None = Field(default=None, ge=0, le=10_000_000)


@router.put("/users/{user_id}/ai")
def set_user_ai(
    user_id: int,
    body: AiQuotaIn,
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """开通/关闭付费 AI，并可按人覆盖日/月预算（传 null 恢复全局默认）。"""
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "用户不存在")
    fields = body.model_fields_set
    if body.enabled is not None:
        u.ai_enabled = bool(body.enabled)
    if "daily_milli" in fields:
        u.ai_daily_budget_milli = body.daily_milli
    if "monthly_milli" in fields:
        u.ai_monthly_budget_milli = body.monthly_milli
    db.commit()
    return _user_row(db, u)


@router.post("/users/{user_id}/ai/reset_alert")
def reset_user_alert(
    user_id: int,
    period: str = "",
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    if db.get(User, user_id) is None:
        raise HTTPException(404, "用户不存在")
    return {"removed": budget.reset_alerts(db, user_id, period)}


# ---------------------------------------------------------------- 报表 / 告警


@router.get("/usage/alerts")
def usage_alerts(
    month: str = "",
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    month = month or usage_svc.today()[:7]
    return {"month": month, "items": budget.alert_rows(db, month)}


@router.get("/usage/report")
def usage_report(
    month: str = "",
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    month = month or usage_svc.today()[:7]
    return budget.month_report(db, month)


@router.get("/usage/export")
def usage_export(
    month: str = "",
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    month = month or usage_svc.today()[:7]
    rows = budget.export_rows(db, month)
    csv = "\n".join(",".join(_csv_cell(c) for c in row) for row in rows)
    return PlainTextResponse(
        csv,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ai-usage-{month}.csv"'},
    )


def _csv_cell(v: str) -> str:
    s = str(v)
    return '"' + s.replace('"', '""') + '"' if "," in s or '"' in s else s


# ---------------------------------------------------------------- TTS 缓存


@router.get("/tts_cache")
def tts_cache(
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return qwen_speak.tts_cache_stats(cache_dir(), qwen_speak.tts_cache_cfg(db))


@router.delete("/tts_cache")
def clear_tts_cache(
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    removed = qwen_speak.clear_tts_cache(cache_dir())
    return {"removed": removed, **qwen_speak.tts_cache_stats(cache_dir(), qwen_speak.tts_cache_cfg(db))}


# ---------------------------------------------------------------- 连通性测试


@router.post("/test/{kind}")
def test_provider(
    kind: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """最小连通性检查：LLM/TTS 会真实调用一次；SOE/Realtime 只校验配置与签名。"""
    from app.services import dev_mock

    if dev_mock.is_dev():
        return {"ok": True, "detail": "开发环境：跳过外部调用", "dev": True}
    if kind == "llm":
        try:
            data, llm_usage = ai_enrich.chat(
                db, [{"role": "user", "content": "Reply with OK only."}], max_tokens=8
            )
            usage_svc.record_llm(db, admin.id, llm_usage)
            return {"ok": True, "detail": str(data.get("text") or data)[:80]}
        except LookupError as e:
            return {"ok": False, "detail": str(e)}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "detail": str(e)[:200]}
    if kind == "tts":
        try:
            out = qwen_speak.tts(db, cache_dir(), "Hello.", "")
            usage_svc.record_tts(db, admin.id, int(out.get("chars", 0)), bool(out.get("cached")))
            return {"ok": True, "detail": "合成成功", "cached": out.get("cached")}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "detail": str(e)[:200]}
    if kind == "soe":
        cfg = tencent_soe.soe_cfg(db)
        if not tencent_soe.is_configured(cfg):
            return {"ok": False, "detail": "AppID / SecretId / SecretKey 未配置完整"}
        try:
            tencent_soe.build_soe_url(cfg, "hello", 0)
            return {"ok": True, "detail": "配置完整，签名生成成功（未发起评测）"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "detail": str(e)[:200]}
    if kind == "realtime":
        cfg = qwen_speak.qwen_cfg(db)
        keys = [cfg["api_key"], ai_enrich.get_cfg(db, "llm.api_key") or ""]
        if not any(keys):
            return {"ok": False, "detail": "未配置 Qwen API Key"}
        if cfg["model"].startswith("qwen3.8") and not cfg["workspace"]:
            return {"ok": False, "detail": "qwen3.8 系列需要配置业务空间 ID"}
        return {
            "ok": True,
            "detail": "配置完整（未建立真实会话）",
            "model": cfg["model"],
            "fallback_model": cfg["fallback_model"],
            "vad": qwen_speak.pick_vad(cfg, cfg["model"]),
        }
    raise HTTPException(404, "未知的测试类型")
