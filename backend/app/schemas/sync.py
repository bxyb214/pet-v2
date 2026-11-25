"""同步相关 Pydantic 模型。"""
from pydantic import BaseModel, Field


class MasteryItem(BaseModel):
    word_id: str = Field(max_length=160)
    mastered_dims: list[str] = Field(default_factory=list)


class MistakeItem(BaseModel):
    word_id: str = Field(max_length=160)
    dims: list[str] = Field(default_factory=list)
    stage: int = Field(default=0, ge=0, le=4)
    due_at: str = Field(default="", max_length=10)  # ISO 日期或空
    repeats: int = Field(default=0, ge=0)


class ProgressItem(BaseModel):
    key: str = Field(max_length=128)
    seen: list[str] = Field(default_factory=list)
    idx: int = Field(default=0, ge=0)


class PlanData(BaseModel):
    length: int = Field(default=0)  # 任意天数，0=未生成
    days_done: list[str] = Field(default_factory=list)
    reading_length: int = Field(default=0)  # 阅读计划天数，0=未生成
    reading_days_done: list[str] = Field(default_factory=list)
    reading_books: list[str] = Field(default_factory=list)  # 阅读计划覆盖的教材 id；空=全部
    plan_updated_at: int = Field(default=0, ge=0)  # 词汇计划结构变更时间（epoch ms）
    reading_updated_at: int = Field(default=0, ge=0)  # 阅读计划结构变更时间（epoch ms）


class CustomWordItem(BaseModel):
    id: int = Field(default=0, ge=0)  # 本地列表 key 用，合并以 word 为业务键
    word: str = Field(max_length=64)
    pos: str = Field(default="", max_length=64)
    definition: str = Field(default="", max_length=256)
    example_en: str = Field(default="", max_length=512)
    example_cn: str = Field(default="", max_length=512)
    bank: str = Field(default="", max_length=16)  # 所属词库（管理员导入时有值）
    exam: str = Field(default="", max_length=16)  # 级别（管理员导入时有值）


class CustomSentenceItem(BaseModel):
    sid: str = Field(max_length=160)  # 业务键 book:test:part:en小写
    book: str = Field(default="t2", max_length=16)
    test_no: int = Field(default=0, ge=0)
    part: int = Field(default=0, ge=0)
    en: str = Field(max_length=512)
    cn: str = Field(default="", max_length=512)
    key: str = Field(default="", max_length=256)
    note: str = Field(default="", max_length=2048)


class SyncData(BaseModel):
    mastery: list[MasteryItem] = Field(default_factory=list)
    mistakes: list[MistakeItem] = Field(default_factory=list)
    progress: list[ProgressItem] = Field(default_factory=list)
    plan: PlanData = Field(default_factory=PlanData)
    custom_words: list[CustomWordItem] = Field(default_factory=list)
    custom_sentences: list[CustomSentenceItem] = Field(default_factory=list)


class SyncPushIn(BaseModel):
    rev: int = Field(ge=1)
    data: SyncData
