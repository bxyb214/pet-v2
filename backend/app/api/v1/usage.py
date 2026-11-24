"""用户端 AI 用量统计（M4）：只返回当前登录用户的数据。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.usage import MyUsageOut
from app.services import budget
from app.services import usage as usage_svc

router = APIRouter(prefix="/usage", tags=["usage"])

# YYYY-MM；月份限定 01–12，避免把任意字符串带进 LIKE 查询
MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


@router.get("/me", response_model=MyUsageOut)
def my_usage(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MyUsageOut:
    """当前用户的额度状态、今日/本周/所选月/今年汇总与所选月逐日明细。"""
    today = usage_svc.today()
    m = month or today[:7]
    return MyUsageOut(
        month=m,
        status=budget.status(db, user),
        totals={
            "today": usage_svc.user_range_totals(db, user.id, today, today),
            "week": usage_svc.user_range_totals(db, user.id, usage_svc.week_start(), today),
            "month": usage_svc.user_range_totals(db, user.id, f"{m}-01", f"{m}-31"),
            "year": usage_svc.user_range_totals(db, user.id, f"{today[:4]}-01-01", today),
        },
        days=usage_svc.user_month_days(db, user.id, m),
    )
