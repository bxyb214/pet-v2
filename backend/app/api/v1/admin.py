"""管理后台：配置管理（F-5，M2）。明文 Key 回显尾 4 位；JSON 配置脱敏 api_key/secret_key。"""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db import get_db
from app.services import ai_enrich, usage as usage_svc

router = APIRouter(prefix="/admin", tags=["admin"])

_SECRET_KEYS = {"llm.api_key"}
_SECRET_JSON_FIELDS = {"api_key", "secret_key"}


class CfgIn(BaseModel):
    key: str = Field(max_length=64)
    value: str = Field(default="", max_length=2000)


def _mask(key: str, value: str) -> str:
    if key in _SECRET_KEYS and value:
        return "****" + value[-4:]
    if value.startswith("{"):
        try:
            d = json.loads(value)
            if isinstance(d, dict):
                masked = {
                    k: ("****" + v[-4:] if k in _SECRET_JSON_FIELDS and v else v)
                    for k, v in d.items()
                }
                return json.dumps(masked, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    return value


@router.get("/cfg")
def get_cfg(
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.query(ai_enrich.AppCfg).all()
    return {r.key: _mask(r.key, r.value) for r in rows}


@router.put("/cfg")
def put_cfg(
    body: CfgIn,
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    value = _unmask_merge(db, body.key, body.value)
    ai_enrich.set_cfg(db, body.key, value)
    return {"key": body.key, "value": _mask(body.key, value)}


def _unmask_merge(db: Session, key: str, value: str) -> str:
    """前端回填的是掩码值（****xxxx）：与库中原值一致则还原为原值，避免覆盖真 Key。"""
    old = ai_enrich.get_cfg(db, key)
    if not old:
        return value
    if old.startswith("{") and value.startswith("{"):
        try:
            old_d = json.loads(old)
            new_d = json.loads(value)
            if isinstance(old_d, dict) and isinstance(new_d, dict):
                for f in _SECRET_JSON_FIELDS:
                    m = str(old_d.get(f, ""))
                    if m and new_d.get(f) in ("****" + m[-4:], m):
                        new_d[f] = m
                return json.dumps(new_d, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    if value == _mask(key, old):
        return old
    return value


@router.get("/usage")
def admin_usage(
    day: str = "",
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """当日全站用量与按用户明细（只记录不限流）。"""
    return usage_svc.admin_day(db, day)


@router.get("/usage/summary")
def admin_usage_summary(
    month: str = "",
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """月度汇总（YYYY-MM，缺省当月）：按用户汇总 token / 次数 / 预估费用。"""
    month = month or usage_svc.today()[:7]
    return usage_svc.admin_month(db, month)
