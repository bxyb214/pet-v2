"""旧数据迁移测试：映射纯函数 + 写入端到端 + 旧 bcrypt 密码登录自动升级。"""
import json

import bcrypt as _bcrypt
from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

from migrate_legacy import (  # noqa: E402
    build_mapped,
    map_codes,
    map_mastery,
    map_mistakes,
    map_plan,
    map_progress,
    map_speak_days,
    map_speak_logs,
    map_users,
    write_new,
)

from app.db import SessionLocal  # noqa: E402
from app.models.learning import Mastery, Mistake, Plan, Progress  # noqa: E402
from app.models.speak import SpeakDay, SpeakLog  # noqa: E402
from app.models.user import User  # noqa: E402


def _bc(pw: str) -> str:
    return _bcrypt.hashpw(pw.encode(), _bcrypt.gensalt(rounds=4)).decode()


def test_map_users_filters_and_roles():
    rows = [
        {"id": 1, "username": "admin", "pass_hash": "$2y$10$abc", "role": "admin", "status": "active", "perms": "", "data_rev": 5},
        {"id": 2, "username": "kid", "pass_hash": "$2y$10$def", "role": "user", "status": "active", "perms": "speak", "data_rev": 1},
        {"id": 3, "username": "locked", "pass_hash": "$2y$10$ghi", "role": "user", "status": "locked", "perms": "", "data_rev": 1},
    ]
    users, warns = map_users(rows)
    assert [u["username"] for u in users] == ["admin", "kid"]
    assert users[0]["is_admin"] is True
    assert users[1]["perms"] == "speak"
    # 旧站只有 PET 内容，迁移必须显式落到 pet（不能依赖列默认值）
    assert all(u["exam"] == "pet" for u in users)
    assert any("locked" in w for w in warns)


def test_map_codes_only_unused():
    rows = [
        {"code": "USED", "active": 1, "used_count": 1, "max_uses": 1},
        {"code": "OPEN", "active": 1, "used_count": 0, "max_uses": 3},
        {"code": "OFF", "active": 0, "used_count": 0, "max_uses": 3},
    ]
    assert map_codes(rows) == [{"code": "OPEN"}]


def test_map_mastery_merges_dims():
    rows = [
        {"user_id": 1, "word_id": "apple", "dim": "w2m"},
        {"user_id": 1, "word_id": "apple", "dim": "m2w"},
        {"user_id": 1, "word_id": "apple", "dim": "w2m"},  # 重复
        {"user_id": 1, "word_id": "sun", "dim": "spell"},
        {"user_id": 2, "word_id": "apple", "dim": "spell"},
    ]
    out = map_mastery(rows)
    assert out[1] == {"apple": "m2w,w2m", "sun": "spell"}
    assert out[2] == {"apple": "spell"}


def test_map_mistakes_dims_and_due():
    rows = [
        {"user_id": 1, "word_id": "cat", "dims_json": '["w2m","spell"]', "last_at": "2026-10-01 08:00:00"},
        {"user_id": 1, "word_id": "dog", "dims_json": "[]", "last_at": "2026-10-02 08:00:00"},  # 空 → 已毕业
        {"user_id": 1, "word_id": "bad", "dims_json": "not-json", "last_at": None},
    ]
    out = map_mistakes(rows)
    items = out[1]
    assert len(items) == 1  # dog 空维度（已毕业）与 bad 坏 JSON 均跳过，只留 cat
    cat = next(m for m in items if m["word_id"] == "cat")
    assert cat["dims"] == "spell,w2m"
    assert cat["stage"] == 0 and cat["repeats"] == 0
    assert cat["due_at"] == "2026-10-01"  # 旧欠账视为到期


def test_map_progress_reading_keys():
    rows = [
        {"user_id": 1, "group_key": "reading::t6p2", "source": "reading", "seen_json": '["2026-11-01"]', "idx": 3},
        {"user_id": 1, "group_key": "reading::t101p1", "source": "reading", "seen_json": "[]", "idx": 0},
        {"user_id": 1, "group_key": "plan::__day3", "source": "plan", "seen_json": "[]", "idx": 5},
        {"user_id": 1, "group_key": "reading::junk", "source": "reading", "seen_json": "[]", "idx": 0},
    ]
    out, warns = map_progress(rows)
    keys = {p["key"]: p for p in out[1]}
    # 1-6 → Trainer 2；101+ → Trainer 1
    assert "read:t2:6:2" in keys and keys["read:t2:6:2"]["seen"] == ["2026-11-01"]
    assert "rstudy:t2:6:2" in keys and keys["rstudy:t2:6:2"]["idx"] == 3
    assert "read:t1:101:1" in keys
    assert "rstudy:t1:101:1" not in keys  # idx=0 不记续学
    assert not any("rstudy" in k for k in keys if "101" in k)
    assert len(warns) == 1  # junk key


def test_map_plan_pet_only():
    rows = [
        {"user_id": 1, "exam": "pet", "day": 1, "state": "done"},
        {"user_id": 1, "exam": "pet", "day": 2, "state": "open"},
        {"user_id": 1, "exam": "pet", "day": 30, "state": "open"},
        {"user_id": 1, "exam": "ket", "day": 1, "state": "done"},
    ]
    out, warns = map_plan(rows)
    assert out[1] == {"length": 30, "days_done": [1]}
    assert any("ket" in w for w in warns)


def test_map_plan_caps_at_fixed_plan_days():
    """v1 PLAN_DAYS=30；脏数据 day=34 不能把 v2 计划拉成 34 天。"""
    rows = [
        {"user_id": 1, "exam": "pet", "day": 1, "state": "done"},
        {"user_id": 1, "exam": "pet", "day": 24, "state": "open"},
        {"user_id": 1, "exam": "pet", "day": 34, "state": "done"},
    ]
    out, warns = map_plan(rows, plan_days=30)
    assert out[1] == {"length": 30, "days_done": [1]}
    assert any("day=34" in w and "忽略" in w for w in warns)


def test_map_plan_infers_when_plan_days_zero():
    rows = [{"user_id": 1, "exam": "pet", "day": 12, "state": "done"}]
    out, _ = map_plan(rows)
    assert out[1] == {"length": 12, "days_done": [12]}


def test_map_speak_logs_normalizes_issues():
    rows = [
        {"user_id": 2, "mode": "talk", "scene": "sc01", "day": 3, "turns": 6, "score": 72,
         "issues_json": json.dumps(["third person s", {"text": "冠词"}], ensure_ascii=False),
         "transcript_json": json.dumps([{"role": "user", "text": "hi"}]), "created_at": None},
    ]
    out = map_speak_logs(rows)
    log = out[2][0]
    assert log["ref"] == "sc01" and log["day"] == 3
    assert json.loads(log["issues"]) == ["third person s", "冠词"]
    assert json.loads(log["transcript"])[0]["role"] == "user"


def test_map_speak_days():
    rows = [{"user_id": 2, "day": 5, "shadow_done": 1, "talk_done": 0, "score": 66}]
    out = map_speak_days(rows)
    assert out[2][0]["shadow_done"] is True and out[2][0]["talk_done"] is False


def _fake_old() -> dict:
    return {
        "pet_users": [
            {"id": 1, "username": "admin", "pass_hash": _bc("pet-test-pass"), "role": "admin",
             "status": "active", "perms": "speak", "data_rev": 9, "created_at": None},
            {"id": 2, "username": "kid1", "pass_hash": _bc("pet-test-pass"), "role": "user",
             "status": "active", "perms": "speak", "data_rev": 3, "created_at": None},
        ],
        "pet_codes": [{"code": "OPEN-1", "active": 1, "used_count": 0, "max_uses": 5}],
        "pet_mastery": [
            {"user_id": 2, "word_id": "apple", "dim": "w2m"},
            {"user_id": 2, "word_id": "apple", "dim": "spell"},
        ],
        "pet_mistakes": [
            {"user_id": 2, "word_id": "cat", "dims_json": '["m2w"]', "last_at": "2026-11-01 10:00:00"},
        ],
        "pet_progress": [
            {"user_id": 2, "group_key": "reading::t3p1", "source": "reading",
             "seen_json": '["2026-11-10"]', "idx": 2},
        ],
        "pet_plan": [
            {"user_id": 2, "exam": "pet", "day": 1, "state": "done"},
            {"user_id": 2, "exam": "pet", "day": 2, "state": "open"},
        ],
        "pet_speak": [
            {"user_id": 2, "mode": "shadow", "scene": "p1-01", "day": 1, "turns": 3, "score": 80,
             "issues_json": "[]", "transcript_json": "[]", "created_at": None},
        ],
        "pet_speak_day": [{"user_id": 2, "day": 1, "shadow_done": 1, "talk_done": 0, "score": 80}],
    }


def test_write_new_end_to_end_and_legacy_login():
    mapped, warns = build_mapped(_fake_old())
    assert warns == []
    counts = write_new(mapped)
    assert counts["users"] == 2 and counts["mastery"] == 1
    assert counts["mistakes"] == 1 and counts["progress"] == 2  # read + rstudy
    assert counts["plans"] == 1 and counts["speak_logs"] == 1 and counts["speak_days"] == 1

    db = SessionLocal()
    kid = db.query(User).filter(User.username == "kid1").one()
    assert kid.password_hash.startswith("$2")
    assert kid.exam == "pet"  # 旧站用户一律 PET
    m = db.query(Mastery).filter(Mastery.user_id == kid.id).one()
    assert m.mastered_dims == "spell,w2m"
    mi = db.query(Mistake).filter(Mistake.user_id == kid.id).one()
    assert mi.due_at == "2026-11-01"
    pkeys = sorted(p.key for p in db.query(Progress).filter(Progress.user_id == kid.id))
    assert pkeys == ["read:t2:3:1", "rstudy:t2:3:1"]
    plan = db.get(Plan, kid.id)
    assert plan.length == 2 and json.loads(plan.days_done) == [1]
    assert db.query(SpeakLog).filter(SpeakLog.user_id == kid.id).count() == 1
    assert db.get(SpeakDay, (kid.id, 1)).shadow_done is True
    db.close()

    # 旧 bcrypt 密码登录成功，且哈希升级为 argon2
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = client.post("/api/v1/auth/login", json={"username": "kid1", "password": "pet-test-pass"})
    assert r.status_code == 200, r.text
    db = SessionLocal()
    kid = db.query(User).filter(User.username == "kid1").one()
    assert kid.password_hash.startswith("$argon2")
    db.close()
    # 再登一次（argon2 路径）
    r = client.post("/api/v1/auth/login", json={"username": "kid1", "password": "pet-test-pass"})
    assert r.status_code == 200


def test_legacy_login_wrong_password_401():
    mapped, _ = build_mapped(_fake_old())
    write_new(mapped)
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = client.post("/api/v1/auth/login", json={"username": "kid1", "password": "wrong"})
    assert r.status_code == 401
