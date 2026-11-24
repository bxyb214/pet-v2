"""认证安全：argon2 密码哈希 + JWT；兼容旧站 bcrypt（$2y$）哈希，登录后自动升级。"""
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def is_legacy_hash(hashed: str) -> bool:
    """旧站 PHP password_hash 产生的 bcrypt（$2y$/$2a$/$2b$）。"""
    return hashed.startswith(("$2y$", "$2a$", "$2b$"))


def verify_password(plain: str, hashed: str) -> bool:
    if is_legacy_hash(hashed):
        try:
            return _bcrypt.checkpw(plain.encode(), hashed.encode())
        except ValueError:
            return False
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def _make_token(sub: str, token_type: str, lifetime: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def make_access_token(user_id: int) -> str:
    s = get_settings()
    return _make_token(str(user_id), "access", timedelta(hours=s.access_token_hours))


def make_refresh_token(user_id: int) -> str:
    s = get_settings()
    return _make_token(str(user_id), "refresh", timedelta(days=s.refresh_token_days))


def make_media_token(user_id: int) -> tuple[str, int]:
    """媒体令牌：只能用于 /media/math 取流，不能调业务接口。

    放 URL 查询串是因为 <video> 与 AirPlay 接收端无法携带 Authorization 头；
    有效期因此要足够看完一节课（默认 6 小时）。
    """
    s = get_settings()
    lifetime = timedelta(hours=s.media_token_hours)
    token = _make_token(str(user_id), "media", lifetime)
    exp = int((datetime.now(timezone.utc) + lifetime).timestamp())
    return token, exp


def decode_token(token: str, expected_type: str) -> int | None:
    """校验并解码，返回 user_id；无效/类型不符返回 None。"""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    sub = payload.get("sub")
    return int(sub) if sub is not None and str(sub).isdigit() else None
