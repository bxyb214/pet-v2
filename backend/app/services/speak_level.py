"""口语 AI 提示词的级别描述：KET=A2，PET=B1，其余按 B1 兜底。

只影响提示词措辞，不改评分/额度/数据表。
"""

from sqlalchemy.orm import Session

from app.models.user import User

_LEVELS = {
    "ket": {
        "name": "KET (A2 Key for Schools)",
        "cefr": "A2",
        "award": "Cambridge KET Merit (优秀) level",
        "plain": "a plain A2 answer",
    },
    "pet": {
        "name": "PET (B1 Preliminary for Schools)",
        "cefr": "B1",
        "award": "Cambridge PET Merit (优秀) level",
        "plain": "a plain B1 answer",
    },
}


def exam_level(exam: str | None) -> dict[str, str]:
    return _LEVELS.get((exam or "pet").lower(), _LEVELS["pet"])


def exam_of(db: Session, user_id: int) -> str:
    user = db.get(User, user_id)
    return (user.exam if user and user.exam else "pet").lower()
