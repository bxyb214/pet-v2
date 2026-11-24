"""口语板块模型（S 组）：练习记录 + 90 天打卡 + 画像 + 会后复盘句。"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SpeakLog(Base):
    """一次跟读 / 对话记录（服务端独占，不走同步通道）。"""

    __tablename__ = "speak_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    mode: Mapped[str] = mapped_column(String(16))  # shadow | talk
    ref: Mapped[str] = mapped_column(String(128), default="")  # pack id / scene id / 自由标记
    sentence_id: Mapped[str] = mapped_column(String(32), default="")  # 跟读句 id（难度选句用）
    day: Mapped[int] = mapped_column(Integer, default=0)  # 90 天计划第几天，0=不在计划内
    turns: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)  # shadow 0-100；talk 取整轮均分
    issues: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组：问题摘要
    words: Mapped[str] = mapped_column(Text, default="[]")  # JSON：SOE 逐词 [{"w","ok"}]
    transcript: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组：逐句
    summary: Mapped[str] = mapped_column(String(512), default="")  # LLM 会话摘要（画像用）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SpeakDay(Base):
    """90 天计划打卡（user_id + day 主键）。"""

    __tablename__ = "speak_days"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[int] = mapped_column(Integer, primary_key=True)
    shadow_done: Mapped[bool] = mapped_column(Boolean, default=False)
    make_done: Mapped[bool] = mapped_column(Boolean, default=False)
    talk_done: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class SpeakPlan(Base):
    """用户手动创建的口语计划（天数；0/无行 = 默认 90 天）。"""

    __tablename__ = "speak_plans"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    length: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class SpeakTime(Base):
    """按天按模式的真实练习秒数（服务端累计，刷新不丢）。"""

    __tablename__ = "speak_times"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD（北京时间）
    mode: Mapped[str] = mapped_column(String(16), primary_key=True)  # shadow | make | talk
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class SpeakProfile(Base):
    """学习者画像（L2 层，user 主键，每天首次会话前重建缓存）。"""

    __tablename__ = "speak_profiles"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    built_day: Mapped[str] = mapped_column(String(10), default="")  # 重建日期 YYYY-MM-DD
    content: Mapped[str] = mapped_column(Text, default="")  # 英文画像文本，注入 instructions
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class SpeakReview(Base):
    """会后复盘句（§5.5）：孩子原话 → PET 优化句，走记忆曲线（与 Mistake 同构）。"""

    __tablename__ = "speak_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    log_id: Mapped[int] = mapped_column(Integer, index=True, default=0)  # 来源会话 speak_logs.id
    child_said: Mapped[str] = mapped_column(Text, default="")  # 孩子原话
    improved_en: Mapped[str] = mapped_column(Text, default="")  # PET B1 优化句
    improved_cn: Mapped[str] = mapped_column(Text, default="")
    focus: Mapped[str] = mapped_column(String(64), default="")  # grammar | vocab | phrase
    dims: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组：还欠的维度
    stage: Mapped[int] = mapped_column(Integer, default=0)  # 记忆曲线阶段（1/2/4/7/15 天）
    due_at: Mapped[str] = mapped_column(String(10), default="")  # 到期日 YYYY-MM-DD
    repeats: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[bool] = mapped_column(Boolean, default=False)  # 全维度毕业
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
