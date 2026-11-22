"""配置与自加词模型。"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AppCfg(Base):
    """Key 类配置存库（S5/M2）：管理页编辑，代码与前端零 Key。"""

    __tablename__ = "app_cfg"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class CustomWord(Base):
    """手动添加单词（V11）：AI 自动配例句/词性/释义，可人工修正。"""

    __tablename__ = "custom_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    word: Mapped[str] = mapped_column(String(64), index=True)
    pos: Mapped[str] = mapped_column(String(64), default="")  # 词性
    definition: Mapped[str] = mapped_column(String(256), default="")  # 释义
    example_en: Mapped[str] = mapped_column(Text, default="")
    example_cn: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(16), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CustomSentence(Base):
    """手动添加精读句子（R10）：挂到教材 test+part，进同步通道。"""

    __tablename__ = "custom_sentences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    sid: Mapped[str] = mapped_column(String(160), index=True)  # 业务键 book:test:part:en小写
    book: Mapped[str] = mapped_column(String(16), default="t2")
    test_no: Mapped[int] = mapped_column(Integer, default=0)
    part: Mapped[int] = mapped_column(Integer, default=0)
    en: Mapped[str] = mapped_column(Text)
    cn: Mapped[str] = mapped_column(Text, default="")
    key: Mapped[str] = mapped_column(String(256), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
