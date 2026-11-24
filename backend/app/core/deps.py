"""认证依赖：从 Authorization 头解析 access token。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    user_id = decode_token(cred.credentials, "access")
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "凭证无效或已过期")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user


def effective_perms(user: User) -> str:
    """实际生效的权限串：管理员默认拥有口语权限，但可用 `!speak` 显式关闭；普通用户按 perms。"""
    parts = [p.strip() for p in (user.perms or "").split(",") if p.strip()]
    if user.is_admin:
        if "!speak" in parts:
            parts = [p for p in parts if p != "!speak"]
        elif "speak" not in parts:
            parts.append("speak")
    return ",".join(parts)


def _has_perm(user: User, perm: str) -> bool:
    return perm in effective_perms(user).split(",")


def require_speak(user: User = Depends(get_current_user)) -> User:
    """口语权限（S 组）：perms 含 speak 才可使用（管理员默认开通）。AI 调用有费用，提示找小淏开通。"""
    if not _has_perm(user, "speak"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "由于 AI 调用产生费用，请联系小淏开通口语功能")
    return user


def check_paid_or_raise(db: Session, user: User) -> dict:
    """手动版付费闸门：用于同一路由内只有部分模式计费的场景（如 /speak/boot）。"""
    from app.services import budget

    ok, st = budget.check_access(db, user)
    if ok:
        return st
    if not st["ai_enabled"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {"code": "AI_NOT_ENABLED", "message": st["message"]},
        )
    reset_at = st["daily"]["reset_at"] if st["reason"] == "daily_exhausted" else st["monthly"]["reset_at"]
    raise HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        {"code": "AI_BUDGET_EXHAUSTED", "message": st["message"], "reset_at": reset_at},
    )


def require_paid_ai(
    user: User = Depends(require_speak),
    db: Session = Depends(get_db),
) -> User:
    """付费 AI 闸门（P0-1）：口语权限 + 管理员开通 + 日/月预算未用尽。

    未开通 → 403 AI_NOT_ENABLED；额度用尽 → 429 AI_BUDGET_EXHAUSTED。
    detail 为对象，前端统一读取 code/message。
    """
    check_paid_or_raise(db, user)
    return user
