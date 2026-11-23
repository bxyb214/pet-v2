"""管理后台：配置管理（F-5，M2）。明文 Key 回显尾 4 位；JSON 配置脱敏 api_key/secret_key。"""
import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import effective_perms, require_admin
from app.db import get_db
from app.models.user import InviteCode, User
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


# ---------------------------------------------------------------- 邀请码 / 账号
class CodeIn(BaseModel):
    count: int = Field(default=1, ge=1, le=20)
    prefix: str = Field(default="PET", max_length=8)


def _gen_code(prefix: str) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 去掉易混的 I/O/0/1
    body = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{prefix}-{body[:4]}-{body[4:]}"


@router.get("/codes")
def list_codes(
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    """邀请码列表：未用的排前面，附使用者用户名。"""
    rows = db.query(InviteCode).order_by(InviteCode.used_by.isnot(None), InviteCode.id.desc()).all()
    user_ids = [r.used_by for r in rows if r.used_by]
    names = {
        u.id: u.username
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}
    return [
        {
            "code": r.code,
            "used": r.used_by is not None,
            "used_by": names.get(r.used_by or 0, ""),
            "used_at": r.used_at.isoformat() if r.used_at else None,
        }
        for r in rows
    ]


@router.post("/codes")
def make_codes(
    body: CodeIn,
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[str]:
    """批量生成邀请码，返回明文列表（只在此刻可见）。"""
    made: list[str] = []
    for _ in range(body.count):
        for _try in range(5):
            code = _gen_code(body.prefix)
            if db.query(InviteCode).filter(InviteCode.code == code).first() is None:
                db.add(InviteCode(code=code))
                made.append(code)
                break
    db.commit()
    return made


@router.get("/users")
def list_users(
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [_user_row(u) for u in db.query(User).order_by(User.id).all()]


class PermIn(BaseModel):
    speak: bool


def _user_row(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name,
        "is_admin": u.is_admin,
        "perms": effective_perms(u),
        "created_at": u.created_at.isoformat() if getattr(u, "created_at", None) else None,
    }


@router.put("/users/{user_id}/perms")
def set_user_perms(
    user_id: int,
    body: PermIn,
    _admin: object = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """开通 / 关闭某个账号的口语权限（只动 speak 位，!listen 等其他标记原样保留）。

    管理员默认开通，但允许显式关闭：关闭时写入 `!speak`，effective_perms 不再补 speak。
    """
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    others = [
        p for p in (u.perms or "").split(",")
        if p.strip() and p.strip() not in ("speak", "!speak")
    ]
    if body.speak:
        u.perms = ",".join(others + ["speak"])
    elif u.is_admin:
        u.perms = ",".join(others + ["!speak"])
    else:
        u.perms = ",".join(others)
    db.commit()
    return _user_row(u)
