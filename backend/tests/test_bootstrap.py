"""空库初始化邀请码：只补一次，且不打扰已有账号的库。"""
from app.bootstrap import CLAIM_CODE, ensure_claim_invite
from app.db import SessionLocal
from app.models.user import InviteCode, User


def _codes() -> list[str]:
    with SessionLocal() as db:
        return [row.code for row in db.query(InviteCode).all()]


def test_empty_db_creates_claim_once():
    assert ensure_claim_invite() is True
    assert _codes() == [CLAIM_CODE]
    assert ensure_claim_invite() is False
    assert _codes() == [CLAIM_CODE]


def test_existing_user_skips_bootstrap():
    with SessionLocal() as db:
        db.add(User(username="existing", password_hash="x"))
        db.commit()
    assert ensure_claim_invite() is False
    assert _codes() == []
