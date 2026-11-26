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


class _SdpResp:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self) -> dict:
        return {"error": {"message": "Invalid API-key provided."}}


def test_speak_key_falls_back_to_llm_key_on_401(monkeypatch):
    db = SessionLocal()
    _put(db, "llm.api_key", "good-key")
    _put(
        db,
        "speak.qwen",
        '{"base": "https://dashscope.aliyuncs.com", '
        '"model": "qwen3.5-omni-flash-realtime", "api_key": "bad-key"}',
    )

    used: list[str] = []

    def fake_post(url, content=None, headers=None, timeout=None):
        used.append(headers["Authorization"])
        if headers["Authorization"].endswith("bad-key"):
            return _SdpResp(401, '{"error":{"message":"Invalid API-key provided."}}')
        return _SdpResp(200, "v=0\r\no=- 1 1 IN IP4 0.0.0.0\r\n")

    monkeypatch.setattr(qwen_speak.httpx, "post", fake_post)
    out = qwen_speak.proxy_sdp(db, "v=0\r\n", "shadow")
    db.close()

    assert used == ["Bearer bad-key", "Bearer good-key"]
    assert out["sdp"].startswith("v=")
    assert out["model"] == "qwen3.5-omni-flash-realtime"


def test_speak_key_not_retried_on_other_errors(monkeypatch):
    db = SessionLocal()
    _put(db, "llm.api_key", "good-key")
    _put(db, "speak.qwen", '{"base": "https://dashscope.aliyuncs.com", '
         '"model": "qwen3.5-omni-flash-realtime", "api_key": "bad-key"}')

    used: list[str] = []

    def fake_post(url, content=None, headers=None, timeout=None):
        used.append(headers["Authorization"])
        return _SdpResp(500, "boom")

    monkeypatch.setattr(qwen_speak.httpx, "post", fake_post)
    try:
        qwen_speak.proxy_sdp(db, "v=0\r\n", "shadow")
    except RuntimeError as e:
        assert "HTTP 500" in str(e)
    else:
        raise AssertionError("应当抛 RuntimeError")
    db.close()
    assert len(used) == 1


def test_403_error_explains_workspace_access(monkeypatch):
    db = SessionLocal()
    _put(db, "speak.qwen", '{"workspace": "ws-test", "api_key": "k"}')

    def fake_post(url, content=None, headers=None, timeout=None):
        return _SdpResp(403, '{"error":{"message":"Workspace endpoint access denied"}}')

    monkeypatch.setattr(qwen_speak.httpx, "post", fake_post)
    try:
        qwen_speak.proxy_sdp(db, "v=0\r\n", "shadow")
    except RuntimeError as e:
        text = str(e)
        assert "HTTP 403" in text and "业务空间" in text and "开通此模型" in text
    else:
        raise AssertionError("应当抛 RuntimeError")
    finally:
        db.close()


class _AsrResp:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self) -> dict:
        return self._body


def test_transcribe_uses_chat_completions_input_audio(monkeypatch):
    """百炼没有 /audio/transcriptions：转写走 chat/completions + input_audio data URI。

    speak Key 失效（401）时应回退 llm Key；返回 content 即转写文本。
    """
    db = SessionLocal()
    _put(db, "llm.api_key", "good-key")
    _put(
        db,
        "speak.qwen",
        '{"base": "https://dashscope.aliyuncs.com", "api_key": "bad-key"}',
    )
    seen: dict = {}
    used: list[str] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        used.append(headers["Authorization"])
        seen.update({"url": url, "json": json})
        if headers["Authorization"].endswith("bad-key"):
            return _AsrResp(401, {"error": {"message": "invalid api key"}})
        return _AsrResp(200, {"choices": [{"message": {"content": "I usually say hello."}}]})

    monkeypatch.setattr(qwen_speak.httpx, "post", fake_post)
    text = qwen_speak.transcribe(db, b"\x00" * 1600, "audio/webm;codecs=opus")
    db.close()

    assert text == "I usually say hello."
    assert used == ["Bearer bad-key", "Bearer good-key"]
    assert seen["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    payload = seen["json"]
    assert payload["model"] == "qwen3-asr-flash"
    assert payload["asr_options"]["language"] == "en"
    content = payload["messages"][0]["content"][0]
    assert content["type"] == "input_audio"
    assert content["input_audio"]["data"].startswith("data:audio/webm;base64,")
