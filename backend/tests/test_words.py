"""自加词 + 管理配置测试（V11 / F-5）。"""
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models.user import InviteCode

client = TestClient(app)
HEAD = {}


def _setup_admin() -> None:
    db = SessionLocal()
    db.add(InviteCode(code="V-INVITE"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": "admin", "password": "pet-test-pass", "invite_code": "V-INVITE"},
    )
    HEAD.update({"Authorization": f"Bearer {r.json()['access_token']}"})


def test_custom_word_crud():
    _setup_admin()
    # 手动带全字段添加
    r = client.post(
        "/api/v1/words/custom",
        headers=HEAD,
        json={"word": "shadow", "pos": "n.", "definition": "影子", "example_en": "The cat has a long shadow.", "example_cn": "猫有一个长影子。"},
    )
    assert r.status_code == 201
    wid = r.json()["id"]
    assert r.json()["word"] == "shadow"

    # 列表可见
    lst = client.get("/api/v1/words/custom", headers=HEAD).json()
    assert [w["word"] for w in lst] == ["shadow"]

    # 人工修正
    r2 = client.put(f"/api/v1/words/custom/{wid}", headers=HEAD, json={"word": "shadow", "pos": "n.", "definition": "阴影；影子"})
    assert r2.status_code == 200
    assert r2.json()["definition"] == "阴影；影子"

    # 删除
    assert client.delete(f"/api/v1/words/custom/{wid}", headers=HEAD).status_code == 204
    assert client.get("/api/v1/words/custom", headers=HEAD).json() == []


def test_enrich_without_key_returns_503():
    _setup_admin()
    r = client.post("/api/v1/words/custom/enrich", headers=HEAD, json={"word": "apple"})
    assert r.status_code == 503
    assert "AI Key" in r.json()["detail"]


def test_add_with_auto_enrich_no_key_returns_503():
    _setup_admin()
    r = client.post("/api/v1/words/custom", headers=HEAD, json={"word": "apple"})
    assert r.status_code == 503


def test_admin_cfg_masking():
    _setup_admin()
    r = client.put("/api/v1/admin/cfg", headers=HEAD, json={"key": "llm.api_key", "value": "sk-abcdef123456"})
    assert r.status_code == 200
    assert r.json()["value"] == "****3456"

    got = client.get("/api/v1/admin/cfg", headers=HEAD).json()
    assert got["llm.api_key"] == "****3456"


def test_admin_cfg_requires_admin():
    # 未登录 → 401
    assert client.get("/api/v1/admin/cfg").status_code == 401
