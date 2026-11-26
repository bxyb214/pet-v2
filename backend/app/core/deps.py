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
    raise HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        {"code": "AI_CREDIT_EXHAUSTED", "message": st["message"]},
    )


def require_paid_ai(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """付费 AI 闸门：账号已开通 + 一次性总额度未用尽。

    未开通 → 403 AI_NOT_ENABLED；额度用尽 → 429 AI_CREDIT_EXHAUSTED。
    管理员账号不受总额度拦截。detail 为对象，前端统一读取 code/message。
    """
    check_paid_or_raise(db, user)
    return user
