"""用户端 AI 用量统计响应模型（M4）。"""

from pydantic import BaseModel


class BudgetPeriodOut(BaseModel):
    used_milli: int
    budget_milli: int
    ratio: float
    stage: int
    reset_at: str


class AiStatusOut(BaseModel):
    ai_enabled: bool
    speak_enabled: bool
    daily: BudgetPeriodOut
    monthly: BudgetPeriodOut
    remaining_milli: int
    max_session_sec: int
    blocked: bool
    reason: str
    message: str
    alert_stage: int


class UsageMetricsOut(BaseModel):
    rt_seconds: int = 0
    rt_ai_seconds: int = 0
    soe_calls: int = 0
    llm_in_tok: int = 0
    llm_out_tok: int = 0
    llm_tok: int = 0
    tts_calls: int = 0
    tts_chars: int = 0
    tts_cache_hits: int = 0
    est_cost_milli: int = 0


class UsageTotalsOut(UsageMetricsOut):
    active_days: int = 0


class UsageDayOut(UsageMetricsOut):
    day: str


class UsageTotalsBundle(BaseModel):
    today: UsageTotalsOut
    week: UsageTotalsOut
    month: UsageTotalsOut
    year: UsageTotalsOut


class MyUsageOut(BaseModel):
    month: str
    status: AiStatusOut
    totals: UsageTotalsBundle
    days: list[UsageDayOut]
