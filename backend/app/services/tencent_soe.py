"""腾讯云智聆口语评测（新版）服务：签名生成 WSS URL，SecretKey 不出服务端。

产品文档：https://cloud.tencent.com/document/product/1774/107497
- 基础版（API 3.0 soe v20180724）官方已宣布即将下线，本项目直接接「口语评测(新版)」。
- 接入方式：wss://soe.cloud.tencent.com/soe/api/{appid}?{参数}（含 signature）。
- 签名：除 signature 外全部参数按字典序排序拼
  soe.cloud.tencent.com/soe/api/{appid}?k1=v1&...，
  Base64(HmacSHA1(key=SecretKey, msg=签名原文))，再整体 urlencode。
- 配置存 app_cfg 'speak.soe'（JSON）：appid / secret_id / secret_key / engine / coeff。
"""
import base64
import hashlib
import hmac
import json
import random
import uuid
from urllib.parse import quote, urlencode

from sqlalchemy.orm import Session

_HOST = "soe.cloud.tencent.com"

# 句子模式上限 30 词；段落模式 120 词
_LIMITS = {0: 10, 1: 30, 2: 120, 3: 0}


def soe_cfg(db: Session) -> dict:
    """app_cfg 'speak.soe' 存 JSON 配置；缺省安全值。"""
    from app.services.ai_enrich import get_cfg

    raw = get_cfg(db, "speak.soe", "{}")
    try:
        d = json.loads(raw) if raw else {}
        if not isinstance(d, dict):
            d = {}
    except json.JSONDecodeError:
        d = {}
    return {
        "appid": str(d.get("appid", "")),
        "secret_id": str(d.get("secret_id", "")),
        "secret_key": str(d.get("secret_key", "")),
        "engine": str(d.get("engine", "16k_en")),
        "coeff": float(d.get("coeff", 1.0)),  # 1.0 适合儿童（苛刻指数 1.0-4.0）
    }


def is_configured(cfg: dict) -> bool:
    return bool(cfg["appid"] and cfg["secret_id"] and cfg["secret_key"])


def sign(key_string: str, secret_key: str) -> str:
    """Base64(HmacSHA1(msg=签名原文, key=SecretKey))。"""
    digest = hmac.new(secret_key.encode(), key_string.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def build_soe_url(cfg: dict, ref_text: str, eval_mode: int = 1, coeff: float | None = None) -> str:
    """生成带签名的 WSS 评测地址。ref_text 超长抛 ValueError。

    voice_format=0（PCM 16k 单声道，前端 AudioWorklet 采集）。
    expired 与 timestamp 相差 24 小时（必须 <90 天）。
    """
    if not is_configured(cfg):
        raise LookupError("管理员还没有配置腾讯云口语评测（SOE）")
    limit = _LIMITS.get(eval_mode)
    if limit and len(ref_text.split()) > limit:
        raise ValueError(f"评测文本超过 {limit} 词上限")
    ts = int(__import__("time").time())
    voice_id = str(uuid.uuid4()).replace("-", "")
    params: dict[str, str | int | float] = {
        "secretid": cfg["secret_id"],
        "timestamp": ts,
        "expired": ts + 86400,
        "nonce": random.randint(1000000000, 9999999999),
        "server_engine_type": cfg["engine"],
        "voice_id": voice_id,
        "voice_format": 0,
        "eval_mode": eval_mode,
        "score_coeff": coeff if coeff is not None else cfg["coeff"],
    }
    if ref_text:
        params["ref_text"] = ref_text
    # 1) 签名原文：按字典序排序，不 urlencode
    key_string = (
        f"{_HOST}/soe/api/{cfg['appid']}?"
        + "&".join(f"{k}={params[k]}" for k in sorted(params))
    )
    params["signature"] = sign(key_string, cfg["secret_key"])
    # 2) 最终 URL：key/value 全部 urlencode
    return f"wss://{_HOST}/soe/api/{quote(str(cfg['appid']))}?" + urlencode(
        {k: str(v) for k, v in params.items()}
    )


def parse_soe_result(raw: str) -> dict:
    """解析识别阶段返回的 result 字符串（类 Python dict 文本）。

    返回 {"score": int, "pron_accuracy": float, "words": [{"w": str, "ok": bool}]}。
    优先 SuggestedScore（<0 视为无效），逐词 PronAccuracy>=60 计 ok。
    """
    text = raw or ""
    score = _extract_number(text, "SuggestedScore")
    pron = _extract_number(text, "PronAccuracy")
    if score is None or score < 0:
        score = pron if pron is not None and pron >= 0 else 0
    words: list[dict] = []
    word_accs: list[float] = []
    for chunk in text.split("Words:")[1:]:
        for m in chunk.split("{")[1:]:
            body = m.split("}")[0]
            w = _extract_field(body, "Word")
            acc = _extract_number(body, "PronAccuracy")
            if w and acc is not None and acc >= 0:
                words.append({"w": w, "ok": acc >= 60})
                word_accs.append(acc)
    if not score and word_accs:
        # 整句分无效时回退到逐词最高分
        score = max(word_accs)
    return {
        "score": int(round(score)) if score else 0,
        "pron_accuracy": round(pron, 1) if pron and pron >= 0 else None,
        "words": words,
    }


def _extract_number(text: str, field: str) -> float | None:
    import re

    m = re.search(rf"{field}:(-?[\d.]+)", text)
    return float(m.group(1)) if m else None


def _extract_field(text: str, field: str) -> str:
    import re

    m = re.search(rf"{field}:([^}}\s]+)", text)
    return m.group(1) if m else ""
