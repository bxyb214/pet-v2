"""AI 用量记账模型（U 组）：按人按天，只记录不限流（2026-11-22 用户确认）。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Usage(Base):
    """每人每天的 AI 用量与预估费用（est_cost_milli 单位 0.001 元，避免浮点）。"""

    __tablename__ = "usages"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # 北京时间 YYYY-MM-DD
    rt_seconds: Mapped[int] = mapped_column(Integer, default=0)  # Realtime 会话总秒数
    rt_ai_seconds: Mapped[int] = mapped_column(Integer, default=0)  # AI 说话秒数
    rt_audio_in_tok: Mapped[int] = mapped_column(Integer, default=0)
    rt_audio_out_tok: Mapped[int] = mapped_column(Integer, default=0)
    rt_text_in_tok: Mapped[int] = mapped_column(Integer, default=0)
    rt_text_out_tok: Mapped[int] = mapped_column(Integer, default=0)
    soe_calls: Mapped[int] = mapped_column(Integer, default=0)  # SOE 评测次数（20 词 1 次）
    llm_in_tok: Mapped[int] = mapped_column(Integer, default=0)
    llm_out_tok: Mapped[int] = mapped_column(Integer, default=0)
    est_cost_milli: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
