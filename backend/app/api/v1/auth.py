"""认证路由：登录 / 注册（邀请码）/ 刷新 / 初始化 claim。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import (
    hash_password,
    make_access_token,
    make_refresh_token,
    verify_password,
)
from app.db import get_db
from app.models.user import InviteCode, User
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_out(user: User) -> TokenOut:
    return TokenOut(
        access_token=make_access_token(user.id),
        refresh_token=make_refresh_token(user.id),
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        perms=user.perms,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    from app.core.security import is_legacy_hash

    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    # 旧站迁移的 bcrypt 哈希：登录成功后升级为 argon2
    if is_legacy_hash(user.password_hash):
        user.password_hash = hash_password(body.password)
        db.commit()
    return _token_out(user)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    code = (
        db.query(InviteCode)
        .filter(InviteCode.code == body.invite_code, InviteCode.used_by.is_(None))
        .first()
    )
    if code is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "邀请码无效或已被使用")
    if db.query(User).filter(User.username == body.username).first() is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "用户名已存在")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    code.used_by = user.id
    code.used_at = datetime.now(timezone.utc)
    db.commit()
    return _token_out(user)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    from app.core.security import decode_token

    user_id = decode_token(body.refresh_token, "refresh")
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh token 无效或已过期")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return _token_out(user)


@router.post("/claim", response_model=TokenOut, status_code=201)
def claim(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    """首次初始化：仅当库内无任何账号时，用邀请码创建管理员账号。"""
    settings = get_settings()
    if not settings.allow_claim:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "初始化已关闭")
    if db.query(User).count() > 0:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "系统已初始化")
    code = (
        db.query(InviteCode)
        .filter(InviteCode.code == body.invite_code, InviteCode.used_by.is_(None))
        .first()
    )
    if code is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "邀请码无效或已被使用")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.username,
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    code.used_by = user.id
    code.used_at = datetime.now(timezone.utc)
    db.commit()
    return _token_out(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
