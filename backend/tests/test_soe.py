"""腾讯 SOE（口语评测新版）测试：签名确定性 / URL 参数 / result 解析 / 路由 / 管理配置脱敏。"""
import base64
import hashlib
import hmac
import json
from urllib.parse import parse_qs, unquote, urlparse

from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models.user import InviteCode, User
from app.services import tencent_soe

client = TestClient(app)

_CFG = {
    "appid": "1300000000",
    "secret_id": "AKIDexample0000",
    "secret_key": "GuWTexamplekey0000",
    "engine": "16k_en",
    "coeff": 1.0,
}


def _fresh_user(username: str, perm: str = "speak") -> str:
    db = SessionLocal()
    db.add(InviteCode(code=f"INV-{username}"))
    db.commit()
    db.close()
    r = client.post(
        "/api/v1/auth/claim",
        json={"username": username, "password": "pet-test-pass", "invite_code": f"INV-{username}"},
    )
    assert r.status_code == 201, r.text
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).one()
    u.perms = perm
    db.commit()
    db.close()
    return r.json()["access_token"]


def test_sign_deterministic():
    msg = "soe.cloud.tencent.com/soe/api/1300000000?eval_mode=1&score_coeff=1.0"
    sig = tencent_soe.sign(msg, _CFG["secret_key"])
    expect = base64.b64encode(
        hmac.new(_CFG["secret_key"].encode(), msg.encode(), hashlib.sha1).digest()
    ).decode()
    assert sig == expect
    assert sig == tencent_soe.sign(msg, _CFG["secret_key"])


def test_build_url_sorted_and_signed():
    url = tencent_soe.build_soe_url(_CFG, "Hello world.", 1)
    assert url.startswith("wss://soe.cloud.tencent.com/soe/api/1300000000?")
    q = parse_qs(urlparse(url).query)
    for k in ("secretid", "timestamp", "expired", "nonce", "server_engine_type", "voice_id", "eval_mode", "score_coeff", "signature", "ref_text"):
        assert k in q, k
    assert q["eval_mode"] == ["1"]
    assert q["server_engine_type"] == ["16k_en"]
    assert unquote(q["ref_text"][0]) == "Hello world."
    # 签名可用「排序后未 urlencode 的原文」复算验证
    params = {k: v[0] for k, v in q.items() if k != "signature"}
    key_string = "soe.cloud.tencent.com/soe/api/1300000000?" + "&".join(
        f"{k}={params[k]}" for k in sorted(params)
    )
    assert q["signature"][0] == tencent_soe.sign(key_string, _CFG["secret_key"])


def test_build_url_ref_text_limit():
    try:
        tencent_soe.build_soe_url(_CFG, " ".join(["word"] * 31), 1)
        raise AssertionError("should raise")
    except ValueError as e:
        assert "30" in str(e)


def test_build_url_not_configured():
    try:
        tencent_soe.build_soe_url(
            {"appid": "", "secret_id": "", "secret_key": "", "engine": "16k_en", "coeff": 1.0},
            "hi", 1,
        )
        raise AssertionError("should raise")
    except LookupError:
        pass


def test_parse_soe_result():
    raw = (
        "SuggestedScore:87.4 PronAccuracy:82.1 PronFluency:0.9 PronCompletion:1.0 "
        "Words:[{PronAccuracy:91.2 PronFluency:0.98 Word:hello Tag:0 PhoneInfo:[]}"
        "{PronAccuracy:45.0 PronFluency:0.8 Word:world Tag:0 PhoneInfo:[]}]"
    )
    r = tencent_soe.parse_soe_result(raw)
    assert r["score"] == 87
    assert r["pron_accuracy"] == 82.1
    assert r["words"] == [{"w": "hello", "ok": True}, {"w": "world", "ok": False}]


def test_parse_soe_result_negative_score_fallback():
    raw = "SuggestedScore:-0.36 PronAccuracy:-1 Words:[{PronAccuracy:70 Word:apple}]"
    r = tencent_soe.parse_soe_result(raw)
    assert r["score"] == 70  # SuggestedScore<0 → 回退 PronAccuracy


def test_soe_url_route_503_then_ok():
    from app.services.ai_enrich import set_cfg

    token = _fresh_user("soeuser")
    H = {"Authorization": f"Bearer {token}"}

    # 未配置 → 503
    r = client.post("/api/v1/speak/soe_url", json={"ref_text": "Hi."}, headers=H)
    assert r.status_code == 503

    # 配置后 → 200 且 URL 带签名
    db = SessionLocal()
    set_cfg(db, "speak.soe", json.dumps(_CFG))
    db.close()
    r = client.post("/api/v1/speak/soe_url", json={"ref_text": "Hi."}, headers=H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"].startswith("wss://soe.cloud.tencent.com/soe/api/")
    assert "signature=" in body["url"]


def test_qwen38_requires_workspace():
    from app.services.qwen_speak import webrtc_url

    cfg = {"workspace": "", "base": "https://dashscope.aliyuncs.com"}
    try:
        webrtc_url(cfg, "qwen3.8-omni-flash-realtime")
        raise AssertionError("should raise")
    except RuntimeError as e:
        assert "workspace" in str(e)
    url = webrtc_url({**cfg, "workspace": "ws1"}, "qwen3.8-omni-flash-realtime")
    assert url == "https://ws1.cn-beijing.maas.aliyuncs.com/api/v1/webrtc/realtime?model=qwen3.8-omni-flash-realtime"


def test_admin_mask_soe_json():
    from app.services.ai_enrich import get_cfg, set_cfg

    token = _fresh_user("adm1", perm="")
    db = SessionLocal()
    u = db.query(User).filter(User.username == "adm1").one()
    u.is_admin = True
    db.commit()
    db.close()
    H = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    set_cfg(db, "speak.soe", json.dumps(_CFG))
    db.close()

    r = client.get("/api/v1/admin/cfg", headers=H)
    assert r.status_code == 200
    soe = json.loads(r.json()["speak.soe"])
    assert soe["secret_key"] == "****0000"
    assert soe["appid"] == _CFG["appid"]

    # 回写掩码值 → 不覆盖真 Key
    soe["coeff"] = 1.5
    r = client.put("/api/v1/admin/cfg", headers=H, json={"key": "speak.soe", "value": json.dumps(soe)})
    assert r.status_code == 200
    db = SessionLocal()
    merged = json.loads(get_cfg(db, "speak.soe"))
    db.close()
    assert merged["secret_key"] == _CFG["secret_key"]
    assert merged["coeff"] == 1.5
