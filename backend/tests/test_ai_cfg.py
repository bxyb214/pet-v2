"""管理页把未填字段存成空串时的回退默认值（llm / speak.qwen）。"""
from app.db import SessionLocal
from app.services import ai_enrich, qwen_speak


class _Resp:
    def __init__(self, body: dict):
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._body


def _put(db, key: str, value: str) -> None:
    ai_enrich.set_cfg(db, key, value)


def test_chat_empty_cfg_falls_back_to_defaults(monkeypatch):
    db = SessionLocal()
    _put(db, "llm.api_key", "sk-test")
    _put(db, "llm.base_url", "")
    _put(db, "llm.model", "")

    seen: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update({"url": url, "model": json["model"]})
        return _Resp({"choices": [{"message": {"content": '{"ok": true}'}}], "usage": {}})

    monkeypatch.setattr(ai_enrich.httpx, "post", fake_post)
    data, _ = ai_enrich.chat(db, [{"role": "user", "content": "hi"}])
    db.close()

    assert data == {"ok": True}
    assert seen["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert seen["model"] == "qwen3.8-flash"


def test_qwen_cfg_empty_values_use_defaults():
    db = SessionLocal()
    _put(db, "speak.qwen", '{"base": "", "workspace": "ws-1", "model": "", "voice": "", "tts_model": ""}')
    cfg = qwen_speak.qwen_cfg(db)
    db.close()

    assert cfg["base"] == "https://dashscope.aliyuncs.com"
    assert cfg["model"] == "qwen3.8-omni-flash-realtime"
    assert cfg["voice"] == "Tina"
    assert cfg["tts_model"] == "qwen3-tts-flash"
    assert cfg["workspace"] == "ws-1"
