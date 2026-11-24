"""预算与告警模型：告警去重 + Realtime 会话跟踪（超时补记）。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UsageAlert(Base):
    """按日/月周期去重的告警记录：同一周期同一档只记一次。"""

    __tablename__ = "usage_alerts"
    __table_args__ = (
        UniqueConstraint("user_id", "period", "period_key", "stage", name="uq_usage_alert"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    period: Mapped[str] = mapped_column(String(8))  # day | month
    period_key: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD / YYYY-MM
    stage: Mapped[int] = mapped_column(Integer)  # 1=80%，2=100%
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AiSession(Base):
    """Realtime 会话跟踪：sdp 创建，session_end 关闭，超时按上限估算补记。"""

    __tablename__ = "ai_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    mode: Mapped[str] = mapped_column(String(16), default="talk")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | closed | expired
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    ai_seconds: Mapped[int] = mapped_column(Integer, default=0)
    text_in_tok: Mapped[int] = mapped_column(Integer, default=0)
    est_cost_milli: Mapped[int] = mapped_column(Integer, default=0)
