"""Qwen Realtime / TTS 服务（S 组）：配置读 app_cfg，密钥不出服务端。"""
import base64
import json

import httpx
from sqlalchemy.orm import Session

from app.models.speak import SpeakLog
from app.services import speak_level
from app.services.tts_cache import (
    clear_tts_cache,
    enforce_tts_cache,
    normalize_wav,
    tts_cache_cfg,
    tts_cache_stats,
)

__all__ = [
    "build_instructions",
    "clear_tts_cache",
    "enforce_tts_cache",
    "pick_model",
    "pick_vad",
    "pick_voice",
    "proxy_sdp",
    "qwen_cfg",
    "recent_issues",
    "transcribe",
    "tts",
    "tts_cache_cfg",
    "tts_cache_stats",
    "webrtc_url",
]

_TIMEOUT = 30.0

# 跟读评测：只回 JSON，不聊天（语义与旧站一致）
_SHADOW_INSTRUCTIONS = """You are a pronunciation checker for an English speaking app. You do NOT chat and you never reply with questions.
The student reads ONE target English sentence aloud. Judge how well the attempt matches it.
Reply with ONE compact JSON object and nothing else — no markdown, no explanation, no extra words:
{"transcript":"what you actually heard","score":0-100,"words":[{"w":"target word","ok":true}],"tips":["中文建议1","中文建议2"],"say":"one short English encouragement"}
Rules: "words" must list the words of the TARGET sentence in order, ok=true only if the student said that word correctly; score 90+ near perfect, 60-75 understandable with errors, below 60 hard to follow; "tips" in simplified Chinese, at most 2, concrete (which sound or which word); "say" one short sentence of encouragement.
If you hear no speech at all, reply with the same JSON shape using transcript "", score 0 and one tip asking the student to read louder.
Remember: output JSON only, never chat, never ask questions."""

_TALK_BASE = """You are a warm, patient {name} speaking examiner and coach.
You are role-playing the examiner / English-speaking partner. Talk naturally, one or two short sentences per turn, and always end with a question so the student keeps talking.
Keep the whole lesson encouraging: the student should feel it is easy to speak.

Scaffolding rules (follow strictly, in order, when the student struggles — long silence, gives up, asks in Chinese, or answers far below their ability):
1. WAIT: repeat your question with simpler words in English (recast), then wait about 8 seconds. Never repeat more than twice.
2. HINT in Chinese: give only the key word(s), e.g. "你可以说 'weekend'（周末）". Use the hint tool when available so the text appears on screen.
3. MODEL: give ONE simple English sentence the student can copy, with Chinese translation, then ask the student to try, then re-ask your question.
Never correct the student mid-sentence, never interrupt their speech, never explain grammar rules. If the session has lasted about 12 minutes, wind down warmly: praise today's work and say goodbye so they can do the review exercise."""


def qwen_cfg(db: Session) -> dict:
    """app_cfg 'speak.qwen' 存 JSON 配置；缺省安全值。"""
    from app.services.ai_enrich import get_cfg

    raw = get_cfg(db, "speak.qwen", "{}")
    try:
        d = json.loads(raw) if raw else {}
        if not isinstance(d, dict):
            d = {}
    except json.JSONDecodeError:
        d = {}

    def pick(key: str, default: str = "") -> str:
        """管理页会把未填项存成空串：空串视同未配置，回退默认值。"""
        v = d.get(key)
        return v.strip() if isinstance(v, str) and v.strip() else default

    return {
        "base": pick("base", "https://dashscope.aliyuncs.com"),
        "workspace": pick("workspace"),
        "api_key": pick("api_key"),
        # 2026-11 最新：Qwen3.8-Omni-Flash-Realtime（支持 Function Call / MCP / semantic_vad）。
        # 注意：qwen3.8 系列必须绑定业务空间（workspace）调用；旧的 qwen3.5-omni-flash-realtime
        # 仍可用 dashscope 直连，作为回退（配置 model 即可切换）。
        "model": pick("model", "qwen3.8-omni-flash-realtime"),
        # A/B：主模型失败时自动回退一次；留空不启用
        "fallback_model": pick("fallback_model"),
        "voice": pick("voice", "Tina"),
        "shadow_model": pick("shadow_model"),
        "voice_shadow": pick("voice_shadow"),
        # 轮次检测：留空按模型默认；audio-3.1 建议 smart_turn_v2
        "vad": pick("vad"),
        "mcp": pick("mcp").lower() in ("1", "true", "yes", "on"),
        "tts_model": pick("tts_model", "qwen3-tts-flash"),
        "tts_voice": pick("tts_voice", "Ryan"),
        # 造句页转写（V11 流程重做）：录一句传一次，OpenAI 兼容 audio/transcriptions
        "asr_model": pick("asr_model", "qwen3-asr-flash"),
    }


def pick_vad(cfg: dict, model: str) -> str:
    """轮次检测类型：显式配置优先；audio-3.1 默认 smart_turn_v2，其他默认 semantic_vad。"""
    if cfg["vad"]:
        return cfg["vad"]
    return "smart_turn_v2" if "audio-3" in model else "semantic_vad"


def pick_voice(cfg: dict, mode: str) -> str:
    if mode == "shadow":
        if cfg["voice_shadow"]:
            return cfg["voice_shadow"]
        if cfg["shadow_model"] and "audio-3" in cfg["shadow_model"]:
            return "longanqian_v3.1"
        return cfg["voice"]
    return cfg["voice"]


def pick_model(cfg: dict, mode: str) -> str:
    return cfg["shadow_model"] if mode == "shadow" and cfg["shadow_model"] else cfg["model"]


def webrtc_url(cfg: dict, model: str) -> str:
    if cfg["workspace"]:
        base = f"https://{cfg['workspace']}.cn-beijing.maas.aliyuncs.com"
    else:
        if model.startswith("qwen3.8"):
            # qwen3.8 系列 Realtime 必须绑定业务空间，dashscope 直连不可用
            raise RuntimeError("qwen3.8 系列模型需要在管理页配置业务空间 ID（workspace）")
        base = cfg["base"].rstrip("/")
    return f"{base}/api/v1/webrtc/realtime?model={model}"


def build_instructions(
    mode: str,
    day: int,
    target: str,
    scene_title: str = "",
    scene_focus: str = "",
    patterns: list[str] | None = None,
    issues: list[str] | None = None,
    avg_score: int = 0,
    profile: str = "",
    warmup: list[str] | None = None,
    exam: str = "pet",
) -> str:
    """拼会话提示词。shadow = 评测 JSON；talk = 场景/句型对话。"""
    lines: list[str] = []
    if mode == "shadow":
        lines.append(_SHADOW_INSTRUCTIONS)
        if target:
            lines.append(f'Target sentence for shadowing: "{target}"')
        if day > 0:
            lines.append(f"Day {day} of the plan.")
        return "\n".join(lines)
    lines.append(_TALK_BASE.format(name=speak_level.exam_level(exam)["name"]))
    if scene_title:
        lines.append(f"Scene: {scene_title}")
    if scene_focus:
        lines.append(f"Scene focus: {scene_focus}")
    if patterns:
        lines.append("Today's target patterns (the student has just practised these):")
        for i, pt in enumerate(patterns):
            lines.append(f'  ({i + 1}) "{pt}"')
        lines.append(
            "These are example sentences, not facts about the student — do not repeat their content "
            "as if it were known. Just use them as language targets."
        )
        lines.append(
            "Your job: run the conversation so that the student naturally uses these patterns. "
            'Ask questions that pull for them. If an answer does not use the pattern, say '
            '"You can say: ..." with ONE short model sentence, ask the student to repeat it, '
            "then ask the question again. Never speak as if you were the student, never list the "
            "patterns, never explain grammar."
        )
    if avg_score > 0:
        lines.append(f"The student's average score so far is {avg_score}/100.")
    if issues:
        lines.append("Problems seen in earlier sessions (work on these naturally, do not list them):")
        for i, t in enumerate(issues[:5]):
            lines.append(f"  {i + 1}) {t}")
    if warmup:
        lines.append(
            "Start the session with a warm-up: ask questions that lead the student to say each of these "
            "review sentences naturally, one by one, before the main topic. Do not show the sentences as text."
        )
        for i, w in enumerate(warmup[:3]):
            lines.append(f'  ({i + 1}) "{w}"')
    if profile:
        lines.append("Learner profile (today, for your reference only — never read it aloud):")
        lines.append(profile[:600])
    if day > 0:
        lines.append(f"This is day {day} of the speaking plan.")
    return "\n".join(lines)


def recent_issues(db: Session, user_id: int, limit: int = 8) -> list[str]:
    rows = (
        db.query(SpeakLog)
        .filter(SpeakLog.user_id == user_id, SpeakLog.mode == "talk")
        .order_by(SpeakLog.id.desc())
        .limit(10)
        .all()
    )
    out: list[str] = []
    for r in rows:
        try:
            out.extend(x for x in json.loads(r.issues or "[]") if x)
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out[:limit]


def _api_keys(db: Session, cfg: dict) -> list[str]:
    """口语 Key 优先；Authorization 失败时回退 llm.api_key（只配了一个百炼 Key 也能用）。"""
    from app.services.ai_enrich import get_cfg

    keys = [cfg["api_key"]] if cfg["api_key"] else []
    llm = (get_cfg(db, "llm.api_key") or "").strip()
    if llm and llm not in keys:
        keys.append(llm)
    return keys


def proxy_sdp(db: Session, sdp: str, mode: str) -> dict:
    """带 Key 换 SDP。Key 不回传。失败抛 RuntimeError(带消息)。

    P1-1：主模型失败（非 2xx / 网络错误）且配置了 fallback_model 时，自动回退一次。
    """
    cfg = qwen_cfg(db)
    keys = _api_keys(db, cfg)
    if not keys:
        raise PermissionError("管理员还没有配置 Qwen API Key")
    primary = pick_model(cfg, mode)
    models = [primary]
    if cfg["fallback_model"] and cfg["fallback_model"] != primary:
        models.append(cfg["fallback_model"])

    last_error = ""
    for model in models:
        url = webrtc_url(cfg, model)
        body = ""
        status_code = 0
        for key in keys:
            try:
                resp = httpx.post(
                    url,
                    content=sdp,
                    headers={"Content-Type": "application/sdp", "Authorization": f"Bearer {key}"},
                    timeout=_TIMEOUT,
                )
            except httpx.HTTPError as e:
                status_code = 0
                body = str(e)
                break
            body = resp.text
            status_code = resp.status_code
            if 200 <= status_code < 300 and body.lstrip().startswith("v="):
                return {
                    "sdp": body,
                    "model": model,
                    "voice": pick_voice(cfg, mode),
                    "vad": pick_vad(cfg, model),
                    "url": url,
                }
            if status_code not in (401, 403):
                break  # 不是 Key 的问题，不再换 Key 重试
        last_error = _sdp_error_message(body, status_code, model)
        if len(models) > 1:
            continue  # 主模型失败 → 试回退模型
    raise RuntimeError(last_error)


def _sdp_error_message(body: str, status_code: int, model: str) -> str:
    msg = ""
    try:
        j = json.loads(body)
        msg = j.get("error", {}).get("message") or j.get("message", "")
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    if not msg:
        msg = (body or str(status_code))[:200]
    if status_code == 403:
        msg += "（请在管理页确认：Key 属于已配置的业务空间，且该空间已开通此模型）"
    return f"连接语音服务失败（HTTP {status_code}，{model}）：{msg}"


def tts(db: Session, cache_dir: str, text: str, voice: str = "") -> dict:
    """TTS + sha1 磁盘缓存。返回可缓存的静态 URL（不再回传 base64）。

    未命中才调用模型并写缓存；失败不写缓存，避免把错误音频固化。
    """
    import hashlib
    from pathlib import Path

    cfg = qwen_cfg(db)
    keys = _api_keys(db, cfg)
    if not keys:
        raise PermissionError("管理员还没有配置 Qwen API Key")
    text = text.strip()[:300]
    if not text:
        raise ValueError("文本为空")
    voice = voice or cfg["tts_voice"]
    model = cfg["tts_model"]

    d = Path(cache_dir)
    d.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{model}|{voice}|{text}".encode()).hexdigest()
    f = d / f"{key}.wav"
    cached = f.is_file() and f.stat().st_size >= 1000
    if not cached:
        audio_url = ""
        status_code, detail = 0, ""
        for api_key in keys:
            resp = httpx.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": {"text": text, "voice": voice, "language_type": "English"}},
                timeout=40.0,
            )
            status_code = resp.status_code
            try:
                audio_url = resp.json()["output"]["audio"]["url"]
            except (json.JSONDecodeError, KeyError, TypeError):
                audio_url = ""
            if audio_url:
                break
            detail = resp.text[:160]
            if status_code not in (401, 403):
                break  # 不是 Key 的问题，不再换 Key 重试
        if not audio_url:
            raise RuntimeError(f"合成失败（HTTP {status_code}）：{detail}")
        audio = httpx.get(audio_url, timeout=40.0).content
        if len(audio) < 1000:
            raise RuntimeError("下载合成音频失败")
        f.write_bytes(normalize_wav(audio))
        enforce_tts_cache(cache_dir, tts_cache_cfg(db))
    return {
        "url": f"/api/v1/speak/tts/file/{f.name}",
        "mime": "audio/wav",
        "cached": cached,
        "chars": len(text),
    }


def _transcript_text(resp: httpx.Response) -> str:
    """从 OpenAI 兼容 chat.completion 里取转写文本（content 可能是字符串或分段数组）。"""
    try:
        choices = resp.json().get("choices") or []
        message = choices[0].get("message") or {}
    except (ValueError, AttributeError, IndexError, TypeError):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [str(p.get("text", "")) for p in content if isinstance(p, dict)]
        return "".join(parts).strip()
    return ""


def transcribe(db: Session, audio: bytes, mime: str) -> str:
    """造句页录音转英文文本（qwen3-asr-flash）。

    百炼没有 OpenAI 的 /audio/transcriptions：Qwen-ASR 走 OpenAI 兼容的
    chat/completions，音频以 `input_audio` + base64 data URI 传入。
    没听到语音时返回空串；失败抛 RuntimeError（端点转 502）。
    """
    cfg = qwen_cfg(db)
    keys = _api_keys(db, cfg)
    if not keys:
        raise PermissionError("管理员还没有配置 Qwen API Key")
    if not audio or len(audio) < 800:  # <0.1s 的录音当没说话
        return ""
    if len(audio) > 10 * 1024 * 1024:
        raise RuntimeError("录音文件超过 10MB，请缩短后重试")
    mime = (mime or "audio/webm").split(";")[0].strip() or "audio/webm"
    data_uri = f"data:{mime};base64,{base64.b64encode(audio).decode()}"
    payload = {
        "model": cfg["asr_model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": data_uri}},
                ],
            }
        ],
        "asr_options": {"language": "en", "enable_itn": True},
    }
    url = f"{cfg['base'].rstrip('/')}/compatible-mode/v1/chat/completions"
    last_error = ""
    for api_key in keys:
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=60.0,
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"转写服务连接失败：{e}") from e
        if 200 <= resp.status_code < 300:
            return _transcript_text(resp)
        last_error = f"转写失败（HTTP {resp.status_code}）：{resp.text[:160]}"
        if resp.status_code not in (401, 403):
            break  # 不是 Key 的问题，不再换 Key 重试
    raise RuntimeError(last_error or "转写失败")
