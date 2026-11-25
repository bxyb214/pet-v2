"""开发环境种子数据：账号 / 邀请码 / 演示学习记录。

仅限本地开发（PET_DEV_MODE=1）：

    python -m app.seed_dev            # 幂等补齐
    python -m app.seed_dev --reset    # 清空业务数据后重建

生产容器不要执行；未开启 dev 模式时默认拒绝，确需执行加 --force。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.bootstrap import CLAIM_CODE
from app.core.config import get_settings
from app.core.security import hash_password
from app.db import Base, SessionLocal
from app.models.budget import AiSession, UsageAlert  # noqa: F401 - 注册模型供 --reset
from app.models.extra import CustomSentence, CustomWord
from app.models.learning import Mastery, Mistake, Plan, Progress
from app.models.speak import SpeakDay, SpeakLog, SpeakProfile, SpeakReview, SpeakTime
from app.models.usage import Usage
from app.models.user import InviteCode, User
from app.services import usage as usage_svc

DEV_INVITE = "DEV-INVITE"
DEFAULT_PASSWORD = "pet-dev-password"


def _today(offset: int = 0) -> str:
    base = datetime.strptime(usage_svc.today(), "%Y-%m-%d")
    return (base + timedelta(days=offset)).strftime("%Y-%m-%d")


def _reset_data(db: Session) -> None:
    """只清数据、不动 schema；schema 仍由 Alembic 管理。"""
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def _ensure_invite(db: Session, code: str) -> bool:
    if db.query(InviteCode.id).filter(InviteCode.code == code).first() is not None:
        return False
    db.add(InviteCode(code=code))
    db.flush()
    return True


def _ensure_user(
    db: Session,
    username: str,
    password: str,
    *,
    display_name: str,
    is_admin: bool,
    ai_enabled: bool,
    exam: str = "pet",
) -> tuple[User, bool]:
    user = db.query(User).filter(User.username == username).first()
    if user is not None:
        return user, False
    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        is_admin=is_admin,
        ai_enabled=ai_enabled,
        exam=exam,
    )
    db.add(user)
    db.flush()
    return user, True


def _ensure_mastery(db: Session, user_id: int, word_id: str, dims: str) -> bool:
    if db.get(Mastery, (user_id, word_id)) is not None:
        return False
    db.add(Mastery(user_id=user_id, word_id=word_id, mastered_dims=dims))
    return True


def _ensure_mistake(
    db: Session,
    user_id: int,
    word_id: str,
    *,
    dims: str,
    stage: int,
    due_at: str,
    repeats: int = 0,
) -> bool:
    if db.get(Mistake, (user_id, word_id)) is not None:
        return False
    db.add(
        Mistake(
            user_id=user_id,
            word_id=word_id,
            dims=dims,
            stage=stage,
            due_at=due_at,
            repeats=repeats,
        )
    )
    return True


def _ensure_progress(db: Session, user_id: int, key: str, seen: list[str], idx: int) -> bool:
    if db.get(Progress, (user_id, key)) is not None:
        return False
    db.add(Progress(user_id=user_id, key=key, seen=json.dumps(seen), idx=idx))
    return True


def _ensure_plan(db: Session, user_id: int) -> bool:
    if db.get(Plan, user_id) is not None:
        return False
    now_ms = int(datetime.now().timestamp() * 1000)
    db.add(
        Plan(
            user_id=user_id,
            length=10,
            days_done=json.dumps(["1", "2"]),
            reading_length=10,
            reading_days_done=json.dumps(["1"]),
            reading_books=json.dumps(["t1", "t2"]),
            plan_updated_at=now_ms,
            reading_updated_at=now_ms,
        )
    )
    return True


def _ensure_custom_word(db: Session, user_id: int) -> bool:
    exists = (
        db.query(CustomWord.id)
        .filter(CustomWord.user_id == user_id, CustomWord.word == "weather")
        .first()
    )
    if exists is not None:
        return False
    db.add(
        CustomWord(
            user_id=user_id,
            word="weather",
            pos="n.",
            definition="天气",
            example_en="The weather is nice today.",
            example_cn="今天天气很好。",
            bank="",
            exam="pet",
            source="manual",
        )
    )
    return True


def _ensure_custom_sentence(db: Session, user_id: int) -> bool:
    sid = "t2:1:1:the weather is nice today"
    exists = (
        db.query(CustomSentence.id)
        .filter(CustomSentence.user_id == user_id, CustomSentence.sid == sid)
        .first()
    )
    if exists is not None:
        return False
    db.add(
        CustomSentence(
            user_id=user_id,
            sid=sid,
            book="t2",
            test_no=1,
            part=1,
            en="The weather is nice today.",
            cn="今天天气很好。",
            key="weather / nice",
            note="开发演示",
        )
    )
    return True


def _ensure_speak(db: Session, user_id: int) -> bool:
    changed = False
    for day, score in ((1, 82), (2, 88), (3, 79)):
        if db.get(SpeakDay, (user_id, day)) is None:
            db.add(
                SpeakDay(
                    user_id=user_id,
                    day=day,
                    shadow_done=True,
                    make_done=True,
                    talk_done=day < 3,
                    score=score,
                )
            )
            changed = True
    for day, mode, seconds in (
        (usage_svc.today(), "shadow", 300),
        (usage_svc.today(), "make", 240),
        (_today(-1), "talk", 600),
    ):
        if db.get(SpeakTime, (user_id, day, mode)) is None:
            db.add(SpeakTime(user_id=user_id, day=day, mode=mode, seconds=seconds))
            changed = True

    log = (
        db.query(SpeakLog)
        .filter(SpeakLog.user_id == user_id, SpeakLog.mode == "shadow", SpeakLog.ref == "s01")
        .first()
    )
    if log is None:
        log = SpeakLog(
            user_id=user_id,
            mode="shadow",
            ref="s01",
            sentence_id="s01-1",
            day=1,
            turns=1,
            score=86,
            issues="[]",
            words="[]",
            transcript=json.dumps(["Nice to meet you."], ensure_ascii=False),
            summary="开发演示：跟读问候语。",
        )
        db.add(log)
        db.flush()
        changed = True

    review = (
        db.query(SpeakReview.id)
        .filter(
            SpeakReview.user_id == user_id,
            SpeakReview.child_said == "I like play football.",
        )
        .first()
    )
    if review is None:
        db.add(
            SpeakReview(
                user_id=user_id,
                log_id=log.id,
                child_said="I like play football.",
                improved_en="I like playing football.",
                improved_cn="我喜欢踢足球。",
                focus="grammar",
                dims=json.dumps(["grammar"]),
                stage=0,
                due_at=usage_svc.today(),
                repeats=0,
                done=False,
            )
        )
        changed = True

    if db.get(SpeakProfile, user_id) is None:
        db.add(
            SpeakProfile(
                user_id=user_id,
                built_day=usage_svc.today(),
                content="Dev seed learner profile: confident speaker, needs past-tense practice.",
            )
        )
        changed = True
    return changed


def _ensure_usage(db: Session, user_id: int) -> bool:
    if db.get(Usage, (user_id, usage_svc.today())) is not None:
        return False
    usage_svc.record(
        db,
        user_id,
        rt_seconds=600,
        rt_ai_seconds=200,
        rt_audio_in_tok=4200,
        rt_audio_out_tok=2500,
        rt_text_in_tok=800,
        rt_text_out_tok=600,
        soe_calls=3,
        llm_in_tok=2400,
        llm_out_tok=1200,
        tts_calls=2,
        tts_chars=48,
    )
    return True


def _seed_demo(db: Session, kid: User) -> bool:
    changed = False
    for word_id, dims in (
        ("b0", "m2w,w2m,spell"),
        ("b1", "m2w,w2m,spell"),
        ("b2", "m2w,w2m,spell"),
        ("g0", "m2w"),
    ):
        changed |= _ensure_mastery(db, kid.id, word_id, dims)

    changed |= _ensure_mistake(
        db, kid.id, "b3", dims="w2m,spell", stage=0, due_at=usage_svc.today()
    )
    changed |= _ensure_mistake(
        db, kid.id, "g1", dims="m2w", stage=2, due_at=_today(-1), repeats=1
    )
    changed |= _ensure_mistake(
        db, kid.id, "d0", dims="w2m,m2w", stage=1, due_at=_today(2)
    )

    changed |= _ensure_progress(
        db, kid.id, "listen:t1:1:1", [_today(-2)], 1
    )
    changed |= _ensure_progress(
        db, kid.id, "read:t2:1:all", [_today(-1)], 1
    )
    changed |= _ensure_progress(
        db, kid.id, "rstudy:t2:1:1", [_today(-1)], 3
    )
    changed |= _ensure_progress(
        db, kid.id, "math:v:g3-40", ["done"], 100
    )

    changed |= _ensure_plan(db, kid.id)
    changed |= _ensure_custom_word(db, kid.id)
    changed |= _ensure_custom_sentence(db, kid.id)
    changed |= _ensure_speak(db, kid.id)
    changed |= _ensure_usage(db, kid.id)
    return changed


def run_seed(
    *,
    reset: bool = False,
    password: str = DEFAULT_PASSWORD,
    force: bool = False,
) -> dict[str, int]:
    """执行种子并返回统计。idempotent：重复执行不会重复插入。"""
    settings = get_settings()
    if not settings.dev_mode and not force:
        raise SystemExit("PET_DEV_MODE!=1：拒绝灌入开发数据；确需执行请加 --force")
    if not password or len(password) < 6:
        raise SystemExit("开发账号密码至少 6 位")

    with SessionLocal() as db:
        if reset:
            _reset_data(db)

        _ensure_invite(db, CLAIM_CODE)
        _ensure_invite(db, DEV_INVITE)

        admin, _ = _ensure_user(
            db,
            "admin",
            password,
            display_name="开发管理员",
            is_admin=True,
            ai_enabled=True,
        )
        kid, _ = _ensure_user(
            db,
            "kid",
            password,
            display_name="开发学生",
            is_admin=False,
            ai_enabled=True,
        )
        _ensure_user(
            db,
            "kid-free",
            password,
            display_name="未开通 AI",
            is_admin=False,
            ai_enabled=False,
        )

        if _seed_demo(db, kid):
            # 让已有浏览器里的旧 rev 触发一次 pull → merge，而不是静默忽略新数据
            kid.data_rev = (kid.data_rev or 1) + 1
        db.commit()

        return {
            "users": db.query(User).count(),
            "invites": db.query(InviteCode).count(),
            "mastery": db.query(Mastery).count(),
            "mistakes": db.query(Mistake).count(),
            "progress": db.query(Progress).count(),
            "plans": db.query(Plan).count(),
            "speak_days": db.query(SpeakDay).count(),
            "usages": db.query(Usage).count(),
            "admin_id": admin.id,
            "kid_id": kid.id,
        }


def main() -> None:
    ap = argparse.ArgumentParser(description="PET v2 开发种子数据（仅 PET_DEV_MODE=1）")
    ap.add_argument("--reset", action="store_true", help="先清空所有业务数据")
    ap.add_argument("--force", action="store_true", help="非 dev 模式下强制执行（不推荐）")
    ap.add_argument(
        "--password",
        default=os.environ.get("PET_SEED_PASSWORD") or DEFAULT_PASSWORD,
        help="三个开发账号的统一密码（默认读 PET_SEED_PASSWORD）",
    )
    args = ap.parse_args()

    stats = run_seed(reset=args.reset, password=args.password, force=args.force)
    print("\n[seed] 完成：", ", ".join(f"{k}={v}" for k, v in stats.items()))
    print("\n开发账号（仅本地）：")
    print(f"  admin    / {args.password}  管理员，AI 已开通")
    print(f"  kid      / {args.password}  学生，AI 已开通")
    print(f"  kid-free / {args.password}  学生，AI 未开通（验证 403 闸门）")
    print(f"\n邀请码：{CLAIM_CODE}（空库首个管理员）、{DEV_INVITE}")
    print("提示：浏览器若已有旧 localStorage，请用无痕窗口或先清空本地数据再看演示数据。\n")


if __name__ == "__main__":
    main()
