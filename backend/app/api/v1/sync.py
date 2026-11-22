"""同步路由：pull / push（rev 乐观锁，409 冲突回最新全量）。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.extra import CustomSentence, CustomWord
from app.models.learning import Mastery, Mistake, Plan, Progress
from app.models.user import User
from app.schemas.sync import SyncData, SyncPushIn
from app.services.merge import merge_sync_data

router = APIRouter(prefix="/sync", tags=["sync"])


def _read_data(db: Session, user_id: int) -> dict:
    plan = db.get(Plan, user_id)
    return {
        "mastery": [
            {"word_id": m.word_id, "mastered_dims": m.mastered_dims.split(",")}
            for m in db.query(Mastery).filter(Mastery.user_id == user_id)
        ],
        "mistakes": [
            {
                "word_id": m.word_id,
                "dims": m.dims.split(",") if m.dims else [],
                "stage": m.stage,
                "due_at": m.due_at,
                "repeats": m.repeats,
            }
            for m in db.query(Mistake).filter(Mistake.user_id == user_id)
        ],
        "progress": [
            {"key": p.key, "seen": json.loads(p.seen or "[]"), "idx": p.idx}
            for p in db.query(Progress).filter(Progress.user_id == user_id)
        ],
        "plan": (
            {
                "length": plan.length,
                "days_done": json.loads(plan.days_done or "[]"),
                "reading_length": plan.reading_length,
                "reading_days_done": json.loads(plan.reading_days_done or "[]"),
                "reading_books": json.loads(plan.reading_books or "[]"),
            }
            if plan
            else {
                "length": 0, "days_done": [], "reading_length": 0,
                "reading_days_done": [], "reading_books": [],
            }
        ),
        "custom_words": [
            {
                "id": w.id,
                "word": w.word,
                "pos": w.pos,
                "definition": w.definition,
                "example_en": w.example_en,
                "example_cn": w.example_cn,
            }
            for w in db.query(CustomWord).filter(CustomWord.user_id == user_id)
        ],
        "custom_sentences": [
            {
                "sid": s.sid,
                "book": s.book,
                "test_no": s.test_no,
                "part": s.part,
                "en": s.en,
                "cn": s.cn,
                "key": s.key,
                "note": s.note,
            }
            for s in db.query(CustomSentence).filter(CustomSentence.user_id == user_id)
        ],
    }


def _write_data(db: Session, user_id: int, data: SyncData) -> None:
    db.query(Mastery).filter(Mastery.user_id == user_id).delete()
    db.query(Mistake).filter(Mistake.user_id == user_id).delete()
    db.query(Progress).filter(Progress.user_id == user_id).delete()
    db.query(Plan).filter(Plan.user_id == user_id).delete()
    db.query(CustomWord).filter(CustomWord.user_id == user_id).delete()
    db.query(CustomSentence).filter(CustomSentence.user_id == user_id).delete()

    for item in data.mastery:
        db.add(Mastery(user_id=user_id, word_id=item.word_id,
                       mastered_dims=",".join(sorted(set(item.mastered_dims)))))
    for item in data.mistakes:
        db.add(Mistake(user_id=user_id, word_id=item.word_id,
                       dims=",".join(sorted(set(item.dims))),
                       stage=item.stage, due_at=item.due_at, repeats=item.repeats))
    for item in data.progress:
        db.add(Progress(user_id=user_id, key=item.key,
                        seen=json.dumps(sorted(set(item.seen))), idx=item.idx))
    plan = db.get(Plan, user_id)
    if plan is None:
        plan = Plan(user_id=user_id)
        db.add(plan)
    plan.length = data.plan.length
    plan.days_done = json.dumps(sorted(set(data.plan.days_done), key=int))
    plan.reading_length = data.plan.reading_length
    plan.reading_days_done = json.dumps(sorted(set(data.plan.reading_days_done), key=int))
    plan.reading_books = json.dumps(sorted(set(data.plan.reading_books)))

    for item in data.custom_words:
        db.add(CustomWord(user_id=user_id, word=item.word, pos=item.pos,
                          definition=item.definition, example_en=item.example_en,
                          example_cn=item.example_cn))

    for item in data.custom_sentences:
        db.add(CustomSentence(user_id=user_id, sid=item.sid, book=item.book,
                              test_no=item.test_no, part=item.part,
                              en=item.en, cn=item.cn, key=item.key, note=item.note))


@router.get("/pull")
def pull(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"rev": user.data_rev, "data": _read_data(db, user.id)}


@router.post("/push")
def push(
    body: SyncPushIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if body.rev != user.data_rev:
        raise HTTPException(
            status_code=409,
            detail={"message": "rev 冲突", "rev": user.data_rev, "data": _read_data(db, user.id)},
        )

    server_data = _read_data(db, user.id)
    client_data = body.data.model_dump()
    merged = merge_sync_data(server_data, client_data)
    _write_data(db, user.id, SyncData(**merged))
    user.data_rev += 1
    db.commit()
    db.refresh(user)
    return {"rev": user.data_rev, "data": merged}
