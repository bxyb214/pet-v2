"""用户与邀请码模型。"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(64), default="")
    # 历史权限位（旧站迁移保留）：不再参与鉴权；口语对所有登录用户开放，付费能力由 ai_enabled 控制
    perms: Mapped[str] = mapped_column(String(256), default="")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    data_rev: Mapped[int] = mapped_column(Integer, default=1)  # 同步乐观锁版本号
    # 当前学习的考试级别：pet / ket /（预留 fce / junior）；决定显示哪套词库与教材
    exam: Mapped[str] = mapped_column(String(16), default="pet")
    # AI 权限总开关：普通账号注册时默认关闭，管理员按需开通；管理员账号默认开通
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # 一次性 AI 总额度覆盖（0.001 元）；NULL = 使用全局 ai.budget.credit_milli
    ai_credit_milli: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class InviteCode(Base):
    """注册邀请码（沿用旧 pet_codes 语义）。"""

    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    used_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
