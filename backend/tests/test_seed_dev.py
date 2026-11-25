"""开发种子：账号/演示数据齐全，重复执行不重复插入。"""
from app.bootstrap import CLAIM_CODE
from app.db import SessionLocal
from app.models.learning import Mastery, Mistake, Plan, Progress
from app.models.usage import Usage
from app.models.user import InviteCode, User
from app.seed_dev import DEFAULT_PASSWORD, DEV_INVITE, run_seed


def _snapshot() -> dict[str, int]:
    with SessionLocal() as db:
        kid = db.query(User).filter(User.username == "kid").one()
        return {
            "users": db.query(User).count(),
            "invites": db.query(InviteCode).count(),
            "mastery": db.query(Mastery).filter(Mastery.user_id == kid.id).count(),
            "mistakes": db.query(Mistake).filter(Mistake.user_id == kid.id).count(),
            "progress": db.query(Progress).filter(Progress.user_id == kid.id).count(),
            "plans": db.query(Plan).filter(Plan.user_id == kid.id).count(),
            "usages": db.query(Usage).filter(Usage.user_id == kid.id).count(),
        }


def test_seed_creates_accounts_and_demo_data():
    stats = run_seed(reset=True, password=DEFAULT_PASSWORD, force=True)
    assert stats["users"] == 3
    with SessionLocal() as db:
        codes = {row.code for row in db.query(InviteCode).all()}
        assert {CLAIM_CODE, DEV_INVITE} <= codes
        for name in ("admin", "kid", "kid-free"):
            assert db.query(User).filter(User.username == name).one()
    snap = _snapshot()
    assert snap["mastery"] == 4
    assert snap["mistakes"] == 3
    assert snap["progress"] == 4
    assert snap["plans"] == 1
    assert snap["usages"] == 1


def test_seed_is_idempotent():
    run_seed(reset=True, password=DEFAULT_PASSWORD, force=True)
    before = _snapshot()
    with SessionLocal() as db:
        rev_before = db.query(User).filter(User.username == "kid").one().data_rev

    run_seed(password=DEFAULT_PASSWORD, force=True)

    assert _snapshot() == before
    with SessionLocal() as db:
        kid = db.query(User).filter(User.username == "kid").one()
        assert kid.data_rev == rev_before
