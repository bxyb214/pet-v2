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


def _has_perm(user: User, perm: str) -> bool:
    return perm in (user.perms or "").split(",")


def require_speak(user: User = Depends(get_current_user)) -> User:
    """口语权限（S 组）：perms 含 speak 才可使用。AI 调用有费用，提示找小淏开通。"""
    if not _has_perm(user, "speak"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "由于 AI 调用产生费用，请联系小淏开通口语功能")
    return user
