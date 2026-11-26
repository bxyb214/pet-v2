"""speak API 测试：登录即可用 / AI 闸门 / boot 提示词 / log→days 打卡 / 无 Key 503。

conftest 每个测试后清空数据，因此每个测试用 _fresh_user() 独立建号。
"""
import json

from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models.user import InviteCode

client = TestClient(app)


def _fresh_user(username: str = "speaker") -> str:
    db = SessionLocal()
    db.add(InviteCode(code=f"INV-{username}"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": username, "password": "pet-test-pass", "invite_code": f"INV-{username}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _register(username: str) -> str:
    db = SessionLocal()
    db.add(InviteCode(code=f"INV-{username}"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "pet-test-pass", "invite_code": f"INV-{username}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def test_speak_free_endpoints_open_without_perm():
    """口语不再按人限制：普通账号默认开通付费 AI，免费接口始终可用。"""
    token = _register("nospeak")
    H = {"Authorization": f"Bearer {token}"}

    assert client.post("/api/v1/speak/boot", json={"mode": "shadow"}, headers=H).status_code == 200
    assert client.get("/api/v1/speak/days", headers=H).status_code == 200
    assert client.get("/api/v1/speak/plan", headers=H).status_code == 200
    assert client.get("/api/v1/speak/ai_status", headers=H).status_code == 200
    assert client.post("/api/v1/speak/boot", json={"mode": "talk"}, headers=H).status_code == 200

    # 管理员显式关闭后，付费接口仍 403
    db = SessionLocal()
    from app.models.user import User

    u = db.query(User).filter(User.username == "nospeak").one()
    u.ai_enabled = False
    db.commit()
    db.close()
    r = client.post("/api/v1/speak/boot", json={"mode": "talk"}, headers=H)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "AI_NOT_ENABLED"


def test_help_available_to_ordinary_user_with_credit():
    """普通账号默认有总额度，「怎么说？」不再 403/429；未配 Key 时才是 503。"""
    token = _register("helper")
    r = client.post(
        "/api/v1/speak/help", json={}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 503


def test_auth_me_has_no_perms_field():
    token = _fresh_user("boss")
    H = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/auth/me", headers=H)
    assert me.status_code == 200
    assert "perms" not in me.json()
    assert client.post("/api/v1/speak/boot", json={"mode": "shadow"}, headers=H).status_code == 200


def test_boot_shadow_instructions():
    token = _fresh_user()
    r = client.post(
        "/api/v1/speak/boot",
        json={"mode": "shadow", "day": 3, "target": "My name is Chen."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "pronunciation checker" in body["instructions"]
    assert "My name is Chen." in body["instructions"]
    assert "Day 3" in body["instructions"]


def test_boot_talk_with_scene_and_patterns():
    token = _fresh_user()
    r = client.post(
        "/api/v1/speak/boot",
        json={
            "mode": "talk", "day": 5, "scene_title": "Shopping",
            "scene_focus": "ask prices", "patterns": ["How much is...?"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "Scene: Shopping" in body["instructions"]
    assert "How much is...?" in body["instructions"]


def test_log_creates_day_checkin():
    token = _fresh_user()
    H = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/speak/log", json={"mode": "shadow", "ref": "p1-intro", "day": 1, "turns": 5, "score": 88}, headers=H).status_code == 200
    assert client.post("/api/v1/speak/log", json={"mode": "make", "day": 1, "turns": 1}, headers=H).status_code == 200
    assert client.post("/api/v1/speak/log", json={"mode": "talk", "ref": "c101", "day": 1, "turns": 6, "score": 75}, headers=H).status_code == 200
    d = client.get("/api/v1/speak/days", headers=H).json()
    assert d["days"][0]["day"] == 1
    assert d["days"][0]["shadow_done"] is True
    assert d["days"][0]["make_done"] is True
    assert d["days"][0]["talk_done"] is True
    assert d["days"][0]["score"] == 88  # 历史最高


def test_boot_talk_includes_history_avg():
    token = _fresh_user()
    H = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/speak/log", json={"mode": "talk", "day": 0, "score": 70, "issues": ["third person s"]}, headers=H)
    r = client.post("/api/v1/speak/boot", json={"mode": "talk"}, headers=H)
    body = r.json()
    assert body["avg"] == 70
    assert "third person s" in body["instructions"]


def test_sdp_without_key_503():
    token = _fresh_user()
    r = client.post(
        "/api/v1/speak/sdp",
        json={"sdp": "v=0 o=- 1 1 IN IP4 127.0.0.1 s=-", "mode": "shadow"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 503


def test_tts_without_key_503():
    token = _fresh_user()
    r = client.post("/api/v1/speak/tts", json={"text": "hello"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 503


def test_instructions_pure_functions():
    from app.services.qwen_speak import build_instructions
    s = build_instructions("shadow", 0, "Hello world.")
    assert "never chat" in s
    s2 = build_instructions("talk", 9, "", scene_title="S", patterns=["a", "b"], issues=["x"], avg_score=70)
    assert "day 9" in s2
    assert "70/100" in s2
    assert "  1) x" in s2


def test_speak_plan_crud():
    token = _fresh_user("planner")
    H = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/speak/plan", headers=H).json()["length"] == 0
    assert client.put("/api/v1/speak/plan", json={"length": 30}, headers=H).json()["length"] == 30
    assert client.get("/api/v1/speak/plan", headers=H).json()["length"] == 30
    assert client.put("/api/v1/speak/plan", json={"length": 0}, headers=H).status_code == 422
    assert client.put("/api/v1/speak/plan", json={"length": 91}, headers=H).status_code == 422
    assert client.delete("/api/v1/speak/plan", headers=H).json()["length"] == 0


def test_review_import_and_grade():
    token = _fresh_user("importer")
    H = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/v1/speak/log",
        json={
            "mode": "talk", "day": 3, "turns": 1,
            "transcript": [{"role": "user", "text": "I go school by bus."}],
        },
        headers=H,
    )
    assert r.status_code == 200
    log_id = r.json()["log_id"]
    payload = {
        "log_id": log_id,
        "items": [{
            "child_said": "I go school by bus.",
            "improved_en": "I go to school by bus.",
            "improved_cn": "我坐公交车上学。",
            "focus": "grammar",
            "dims": ["grammar:preposition"],
        }],
    }
    r = client.post("/api/v1/speak/review/import", json=payload, headers=H)
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["improved_en"] == "I go to school by bus."
    # 幂等：重复导入不新增
    r2 = client.post("/api/v1/speak/review/import", json=payload, headers=H)
    assert len(r2.json()["items"]) == 1
    # 评分过关 → 维度划掉并毕业
    g = client.post(
        "/api/v1/speak/review/grade",
        json={"id": item["id"], "score": 90, "dims_ok": ["grammar:preposition"]},
        headers=H,
    )
    assert g.status_code == 200
    assert g.json()["done"] is True


def test_speak_time_accumulates():
    token = _fresh_user("timer")
    H = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/speak/time/today", headers=H).json()["totals"]["talk"] == 0
    r = client.post("/api/v1/speak/time", json={"mode": "talk", "seconds": 120}, headers=H)
    assert r.status_code == 200
    assert r.json()["totals"]["talk"] == 120
    client.post("/api/v1/speak/time", json={"mode": "talk", "seconds": 30}, headers=H)
    client.post("/api/v1/speak/time", json={"mode": "shadow", "seconds": 45}, headers=H)
    totals = client.get("/api/v1/speak/time/today", headers=H).json()["totals"]
    assert totals == {"shadow": 45, "make": 0, "talk": 150}
    assert client.post("/api/v1/speak/time", json={"mode": "talk", "seconds": 0}, headers=H).status_code == 422


def test_new_plan_resets_day_checks():
    token = _fresh_user("planner2")
    H = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/speak/log", json={"mode": "talk", "day": 1, "turns": 1}, headers=H)
    assert client.get("/api/v1/speak/days", headers=H).json()["days"]
    client.put("/api/v1/speak/plan", json={"length": 30}, headers=H)
    assert client.get("/api/v1/speak/days", headers=H).json()["days"] == []


def test_shadow_recent_dedupes_sentence_ids():
    """计划日会为同一句写多条日志；最近记录按 sentence_id 去重。"""
    token = _fresh_user("shadowu")
    H = {"Authorization": f"Bearer {token}"}
    for day in (0, 1, 2):
        r = client.post(
            "/api/v1/speak/log",
            json={
                "mode": "shadow", "ref": "p1", "day": day, "score": 80,
                "sentence_id": "s1", "words": [{"w": "this", "ok": False}],
            },
            headers=H,
        )
        assert r.status_code == 200
    client.post(
        "/api/v1/speak/log",
        json={
            "mode": "shadow", "ref": "p1", "day": 0, "score": 90,
            "sentence_id": "s2", "words": [{"w": "that", "ok": True}],
        },
        headers=H,
    )
    r = client.get("/api/v1/speak/shadow/recent?limit=10", headers=H)
    assert r.status_code == 200
    items = r.json()["items"]
    assert [i["sentence_id"] for i in items] == ["s2", "s1"]
    assert items[1]["weak_words"] == ["this"]


def test_shadow_log_keeps_only_best_score_and_eval():
    """同一句反复练：只留最高分和那次评分给出的评价内容，低分重试不新增记录。"""
    from app.models.speak import SpeakLog

    token = _fresh_user("shadowbest")
    H = {"Authorization": f"Bearer {token}"}
    base = {"mode": "shadow", "ref": "p1", "sentence_id": "s1", "day": 0, "turns": 1}
    for score, issues, words in (
        (70, ["旧评价"], [{"w": "a", "ok": False}]),
        (92, ["漏读了 a，跟着示范逐词读完整。"], [{"w": "a", "ok": True}]),
        (80, ["更低的评价"], []),
    ):
        r = client.post(
            "/api/v1/speak/log",
            json={**base, "score": score, "issues": issues, "words": words},
            headers=H,
        )
        assert r.status_code == 200

    items = client.get("/api/v1/speak/shadow/recent?limit=10", headers=H).json()["items"]
    assert len(items) == 1
    assert items[0]["score"] == 92
    assert items[0]["weak_words"] == []

    db = SessionLocal()
    rows = db.query(SpeakLog).filter(SpeakLog.mode == "shadow").all()
    assert len(rows) == 1
    assert rows[0].score == 92
    assert json.loads(rows[0].issues) == ["漏读了 a，跟着示范逐词读完整。"]
    db.close()


def test_shadow_recent_uses_best_score_across_days():
    """计划日各写一行时，最近记录取该句历史最高分（而不是最后一行）。"""
    from app.models.speak import SpeakLog

    token = _fresh_user("shadowday")
    H = {"Authorization": f"Bearer {token}"}
    for day, score in ((1, 70), (2, 95), (1, 75)):
        client.post(
            "/api/v1/speak/log",
            json={
                "mode": "shadow", "ref": "p1", "sentence_id": "s1",
                "day": day, "score": score, "words": [{"w": "x", "ok": score >= 90}],
            },
            headers=H,
        )
    items = client.get("/api/v1/speak/shadow/recent?limit=10", headers=H).json()["items"]
    assert len(items) == 1
    assert items[0]["score"] == 95
    assert items[0]["weak_words"] == []
    # 每天仍然只有一条记录（第 1 天取较高的 75，第 2 天 95）
    db = SessionLocal()
    rows = db.query(SpeakLog).filter(SpeakLog.mode == "shadow").all()
    assert sorted((r.day, r.score) for r in rows) == [(1, 75), (2, 95)]
    db.close()
