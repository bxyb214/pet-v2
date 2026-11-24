"""用量记账 + 画像 + 会后复盘测试（M1/M2）。

记账：换算系数、20 词折 1 次、LLM usage、端到端上报。
复盘：mock LLM 选句改写 → 记忆曲线（划维度/毕业/回 1 天）。
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.speak import SpeakLog, SpeakReview
from app.models.usage import Usage
from app.models.user import InviteCode, User
from app.services import usage as usage_svc

client = TestClient(app)


def _fresh_user(username: str, *, speak: bool = True, admin: bool = False) -> str:
    db = SessionLocal()
    db.add(InviteCode(code=f"INV-{username}"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": username, "password": "pet-test-pass", "invite_code": f"INV-{username}"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).one()
    if speak:
        u.perms = (u.perms or "") + "speak"
    u.is_admin = admin  # 每个测试都是空库首个 claim 用户（默认管理员），必须显式设置
    db.commit()
    db.close()
    return token


def test_record_session_token_conversion():
    db = SessionLocal()
    row = usage_svc.record_session(db, 1, seconds=1800, ai_seconds=600)
    assert row.rt_audio_in_tok == 1800 * 7
    assert row.rt_audio_out_tok == 600 * 12.5 == 7500
    # 0.076 + 0.09 = 0.166 元 → 166 milli（text/soe/llm 均 0）
    assert row.est_cost_milli == 166
    # 二次累加（同一行 upsert）
    row = usage_svc.record_session(db, 1, seconds=600)
    assert row.rt_audio_in_tok == 1800 * 7 + 600 * 7
    db.close()


def test_record_soe_word_folding():
    db = SessionLocal()
    usage_svc.record_soe(db, 2, "I like playing football with my friends at the weekend")  # 12 词 → 1 次
    usage_svc.record_soe(db, 2, " ".join(["word"] * 45))  # 45 词 → 3 次
    row = db.get(Usage, (2, usage_svc.today()))
    assert row.soe_calls == 4
    db.close()


def test_record_llm_usage():
    db = SessionLocal()
    usage_svc.record_llm(db, 3, {"prompt_tokens": 1200, "completion_tokens": 90})
    row = db.get(Usage, (3, usage_svc.today()))
    assert row.llm_in_tok == 1200 and row.llm_out_tok == 90
    assert row.est_cost_milli == round((1200 / 1e6 * 0.8 + 90 / 1e6 * 2.7) * 1000)
    db.close()


def test_session_end_and_usage_today_api():
    token = _fresh_user("usageu")
    r = client.post(
        "/api/v1/speak/session_end",
        json={"seconds": 900, "ai_seconds": 300},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    r = client.get("/api/v1/speak/usage_today", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["rt_seconds"] == 900 and body["rt_ai_seconds"] == 300


def test_admin_usage_endpoints():
    token = _fresh_user("usageadmin", admin=True)
    # 先产生一条数据
    client.post(
        "/api/v1/speak/session_end",
        json={"seconds": 300},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = client.get("/api/v1/admin/usage", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["users"] and body["users"][0]["rt_seconds"] == 300
    month = usage_svc.today()[:7]
    r = client.get(f"/api/v1/admin/usage/summary?month={month}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["month"] == month


def test_admin_usage_requires_admin():
    token = _fresh_user("notadmin")
    r = client.get("/api/v1/admin/usage", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def _mock_chat(monkeypatch, payload):
    """mock ai_enrich.chat 返回固定 JSON。"""

    def fake_chat(db, messages, max_tokens=300, temperature=0.2):
        return payload, {"prompt_tokens": 500, "completion_tokens": 60}

    monkeypatch.setattr("app.services.ai_enrich.chat", fake_chat)


def test_review_generate_and_grade(monkeypatch):
    token = _fresh_user("revu")
    db = SessionLocal()
    db.add(
        SpeakLog(
            user_id=db.query(User).filter(User.username == "revu").one().id,
            mode="talk",
            transcript=json.dumps(
                [
                    {"role": "user", "text": "I go to school yesterday"},
                    {"role": "assistant", "text": "Oh, you went to school yesterday. What did you do?"},
                    {"role": "user", "text": "I play football"},
                ]
            ),
        )
    )
    db.commit()
    log_id = db.query(SpeakLog).order_by(SpeakLog.id.desc()).first().id
    db.close()

    _mock_chat(
        monkeypatch,
        [
            {
                "child_said": "I go to school yesterday",
                "improved_en": "I went to school yesterday.",
                "improved_cn": "我昨天去了学校。",
                "focus": "grammar",
                "dims": ["grammar:past-tense"],
            },
            {
                "child_said": "I play football",
                "improved_en": "I played football after school.",
                "improved_cn": "我放学后踢了足球。",
                "focus": "grammar",
                "dims": ["grammar:past-tense", "vocab:after-school"],
            },
        ],
    )
    r = client.post("/api/v1/speak/review", json={"log_id": log_id}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    assert items[0]["due_at"] == usage_svc.today()

    # 评分 88 + 划掉一个维度 → 另一维度仍欠，stage 前进
    rid = items[1]["id"]
    r = client.post(
        "/api/v1/speak/review/grade",
        json={"id": rid, "score": 88, "dims_ok": ["grammar:past-tense"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dims"] == ["vocab:after-school"]
    assert body["stage"] == 1 and body["done"] is False

    # 再划掉最后一个维度 → 毕业
    r = client.post(
        "/api/v1/speak/review/grade",
        json={"id": rid, "score": 92, "dims_ok": ["vocab:after-school"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()["done"] is True

    # 低分回 1 天：新建一条，score=40 → 全维度重欠、回到今天
    r = client.post("/api/v1/speak/review", json={"log_id": log_id}, headers={"Authorization": f"Bearer {token}"})
    rid2 = r.json()["items"][0]["id"]
    r = client.post(
        "/api/v1/speak/review/grade",
        json={"id": rid2, "score": 40, "dims_ok": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["stage"] == 0 and body["due_at"] == usage_svc.today() and body["done"] is False


def test_review_due_and_boot_warmup(monkeypatch):
    token = _fresh_user("warmu")
    db = SessionLocal()
    uid = db.query(User).filter(User.username == "warmu").one().id
    db.add(
        SpeakReview(
            user_id=uid, log_id=0, child_said="x", improved_en="I went to school yesterday.",
            improved_cn="", focus="grammar", dims=json.dumps(["grammar:past-tense"]),
            stage=0, due_at=usage_svc.today(),
        )
    )
    db.commit()
    db.close()
    r = client.get("/api/v1/speak/review/due", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    # boot（mock LLM 画像）注入热身句
    _mock_chat(monkeypatch, {"text": "Today: no speaking practice yet today."})
    r = client.post("/api/v1/speak/boot", json={"mode": "talk"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert "I went to school yesterday." in body["instructions"]
    assert body["warmup"] == ["I went to school yesterday."]


def test_log_talk_triggers_summary(monkeypatch):
    token = _fresh_user("summu")
    _mock_chat(monkeypatch, {"text": "The child talked about school; past tense needs work."})
    r = client.post(
        "/api/v1/speak/log",
        json={
            "mode": "talk",
            "turns": 4,
            "score": 75,
            "transcript": [
                {"role": "user", "text": "I like football"},
                {"role": "assistant", "text": "Great! Who do you play with?"},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    db = SessionLocal()
    row = db.query(SpeakLog).order_by(SpeakLog.id.desc()).first()
    assert "past tense" in row.summary
    db.close()
    # 画像应能读到摘要（mock chat 下内容为 profile 文本本身）
    r = client.get("/api/v1/speak/review/due", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_profile_fallback_without_llm():
    """无 Key：画像降级为确定性文本，boot 不报错。"""
    token = _fresh_user("nollmu")
    r = client.post("/api/v1/speak/boot", json={"mode": "talk"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "Today:" in r.json()["instructions"]


def test_review_not_found():
    token = _fresh_user("rev404")
    r = client.post("/api/v1/speak/review", json={"log_id": 99999}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
