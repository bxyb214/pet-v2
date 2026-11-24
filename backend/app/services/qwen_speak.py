"""Qwen Realtime / TTS 服务（S 组）：配置读 app_cfg，密钥不出服务端。"""
import json

import httpx
from sqlalchemy.orm import Session

from app.models.speak import SpeakLog

_TIMEOUT = 30.0

# 跟读评测：只回 JSON，不聊天（语义与旧站一致）
_SHADOW_INSTRUCTIONS = """You are a pronunciation checker for a PET speaking app. You do NOT chat and you never reply with questions.
The student reads ONE target English sentence aloud. Judge how well the attempt matches it.
Reply with ONE compact JSON object and nothing else — no markdown, no explanation, no extra words:
{"transcript":"what you actually heard","score":0-100,"words":[{"w":"target word","ok":true}],"tips":["中文建议1","中文建议2"],"say":"one short English encouragement"}
Rules: "words" must list the words of the TARGET sentence in order, ok=true only if the student said that word correctly; score 90+ near perfect, 60-75 understandable with errors, below 60 hard to follow; "tips" in simplified Chinese, at most 2, concrete (which sound or which word); "say" one short sentence of encouragement.
If you hear no speech at all, reply with the same JSON shape using transcript "", score 0 and one tip asking the student to read louder.
Remember: output JSON only, never chat, never ask questions."""

_TALK_BASE = """You are a warm, patient PET (B1 Preliminary for Schools) speaking examiner and coach.
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
    lines.append(_TALK_BASE)
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
        lines.append(f"This is day {day} of a 90-day speaking plan.")
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


def tts_cache_cfg(db: Session) -> int:
    """TTS 缓存上限（MB），存 app_cfg 'speak.tts_cache'，默认 512。"""
    from app.services.ai_enrich import get_cfg

    raw = get_cfg(db, "speak.tts_cache", "")
    try:
        d = json.loads(raw) if raw else {}
        return max(16, int(d.get("max_mb", 512)))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 512


def _wav_files(cache_dir: str) -> list:
    from pathlib import Path

    d = Path(cache_dir)
    if not d.is_dir():
        return []
    return [p for p in d.glob("*.wav") if p.is_file()]


def tts_cache_stats(cache_dir: str, max_mb: int) -> dict:
    files = _wav_files(cache_dir)
    total = sum(p.stat().st_size for p in files)
    return {"files": len(files), "bytes": total, "max_mb": max_mb}


def clear_tts_cache(cache_dir: str) -> int:
    n = 0
    for p in _wav_files(cache_dir):
        try:
            p.unlink()
            n += 1
        except OSError:
            continue
    return n


def enforce_tts_cache(cache_dir: str, max_mb: int) -> int:
    """按 mtime 做 LRU：超过上限时删最久未用的文件，直到回到上限内。"""
    limit = max_mb * 1024 * 1024
    files = sorted(_wav_files(cache_dir), key=lambda p: p.stat().st_mtime)
    total = sum(p.stat().st_size for p in files)
    removed = 0
    for p in files:
        if total <= limit:
            break
        try:
            size = p.stat().st_size
            p.unlink()
            total -= size
            removed += 1
        except OSError:
            continue
    return removed


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
        f.write_bytes(audio)
        enforce_tts_cache(cache_dir, tts_cache_cfg(db))
    return {
        "url": f"/api/v1/speak/tts/file/{f.name}",
        "mime": "audio/wav",
        "cached": cached,
        "chars": len(text),
    }
