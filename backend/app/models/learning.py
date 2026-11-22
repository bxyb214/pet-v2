"""学习数据模型：mastery / mistakes(SRS) / progress / plan。"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Mastery(Base):
    __tablename__ = "mastery"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_id: Mapped[str] = mapped_column(String(160), primary_key=True)  # 兼容阅读自定义句 sid
    mastered_dims: Mapped[str] = mapped_column(String(128), default="")  # 逗号分隔


class Mistake(Base):
    """错题：dims 维度记账 + 记忆曲线间隔重复（1/2/4/7/15 天）。

    word_id 兼容阅读自定义句 sid（最长 160）。
    """

    __tablename__ = "mistakes"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    dims: Mapped[str] = mapped_column(String(128), default="")  # 还欠哪些维度
    stage: Mapped[int] = mapped_column(Integer, default=0)  # 间隔序列下标 0..4
    due_at: Mapped[str] = mapped_column(String(10), default="")  # ISO 日期
    repeats: Mapped[int] = mapped_column(Integer, default=0)  # 已通过间隔次数


class Progress(Base):
    __tablename__ = "progress"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    seen: Mapped[str] = mapped_column(String(4096), default="[]")  # JSON 数组
    idx: Mapped[int] = mapped_column(Integer, default=0)


class Plan(Base):
    __tablename__ = "plans"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    length: Mapped[int] = mapped_column(Integer, default=0)  # 任意天数，0=未生成
    days_done: Mapped[str] = mapped_column(String(4096), default="[]")  # JSON 数组
    reading_length: Mapped[int] = mapped_column(Integer, default=0)  # 阅读计划天数，0=未生成
    reading_days_done: Mapped[str] = mapped_column(String(4096), default="[]")  # JSON 数组
    reading_books: Mapped[str] = mapped_column(String(256), default="[]")  # 覆盖的教材 id 数组，空=全部
