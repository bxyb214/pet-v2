"""sync API 全流程测试：pull → push → 冲突 409 → 合并重试。"""
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models.user import InviteCode

client = TestClient(app)
HEAD = {}


def _setup_user() -> None:
    db = SessionLocal()
    db.add(InviteCode(code="SYNC-INVITE"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": "syncer", "password": "secret123", "invite_code": "SYNC-INVITE"},
    )
    body = r.json()
    HEAD.clear()
    HEAD.update({"Authorization": f"Bearer {body['access_token']}"})


def test_pull_initial():
    _setup_user()
    r = client.get("/api/v1/sync/pull", headers=HEAD)
    assert r.status_code == 200
    body = r.json()
    assert body["rev"] == 1
    assert body["data"]["mastery"] == []
    assert body["data"]["plan"]["length"] == 0


def test_push_roundtrip():
    _setup_user()
    payload = {
        "rev": 1,
        "data": {
            "mastery": [{"word_id": "w1", "mastered_dims": ["spell"]}],
            "mistakes": [{"word_id": "w2", "dims": ["w2m"], "stage": 0, "due_at": "2026-11-23", "repeats": 0}],
            "progress": [{"key": "reading-101", "seen": ["q1"], "idx": 1}],
            "plan": {"length": 30, "days_done": ["1"]},
        },
    }
    r = client.post("/api/v1/sync/push", headers=HEAD, json=payload)
    assert r.status_code == 200
    assert r.json()["rev"] == 2

    pull = client.get("/api/v1/sync/pull", headers=HEAD).json()
    assert pull["data"]["mastery"][0]["word_id"] == "w1"
    assert pull["data"]["plan"]["days_done"] == ["1"]


def test_push_conflict_409_and_merge_retry():
    _setup_user()
    # 先成功 push 一次，把服务端 rev 推到 2
    first = {
        "rev": 1,
        "data": {
            "mastery": [{"word_id": "w1", "mastered_dims": ["spell"]}],
            "mistakes": [],
            "progress": [{"key": "reading-101", "seen": ["q1"], "idx": 1}],
            "plan": {"length": 30, "days_done": ["1"]},
        },
    }
    assert client.post("/api/v1/sync/push", headers=HEAD, json=first).status_code == 200

    # 客户端 A 用旧 rev 1 push → 409，返回服务端 rev=2 全量
    stale = {
        "rev": 1,
        "data": {
            "mastery": [{"word_id": "w1", "mastered_dims": ["w2m"]}],
            "mistakes": [],
            "progress": [],
            "plan": {"length": 0, "days_done": ["2"]},
        },
    }
    r = client.post("/api/v1/sync/push", headers=HEAD, json=stale)
    assert r.status_code == 409
    conflict = r.json()["detail"]
    assert conflict["rev"] == 2

    # 合并后用新 rev 重试 → 成功，且服务端旧数据未丢（叠加而非覆盖）
    from app.services.merge import merge_sync_data

    merged = merge_sync_data(conflict["data"], stale["data"])
    retry = client.post(
        "/api/v1/sync/push",
        headers=HEAD,
        json={"rev": conflict["rev"], "data": merged},
    )
    assert retry.status_code == 200
    final = retry.json()["data"]
    assert sorted(m["word_id"] for m in final["mastery"]) == ["w1"]
    assert sorted(final["mastery"][0]["mastered_dims"]) == ["spell", "w2m"]
    assert final["plan"]["days_done"] == ["1", "2"]
    assert final["progress"][0]["seen"] == ["q1"]


def test_sync_requires_auth():
    assert client.get("/api/v1/sync/pull").status_code == 401
    assert client.post("/api/v1/sync/push", json={"rev": 1, "data": {}}).status_code == 401
