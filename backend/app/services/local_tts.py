"""本地 TTS（Piper sidecar）：配置解析、缓存键、合成与限流。

sidecar 是无状态的「文本 → WAV」服务；缓存、LRU、限流都在 api 进程里，
与 Qwen TTS 共用 `data/tts/`。本地合成不记 usage、不产生费用。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.models.user import User
from app.services import tts_cache
from app.services.tts_text import has_cjk, normalize_for_tts, truncate_text

DEFAULT_SIDECAR = "http://tts:8100"
DEFAULT_VOICE = "en_GB-alan-medium"
DEFAULT_VOICE_ZH = "zh_CN-huayan-medium"
MIN_WAV_BYTES = 1000
_MIN_ENFORCE_SEC = 60.0
_TOUCH_SEC = 6 * 3600

_VOICE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")


class LocalTtsBusy(RuntimeError):
    """sidecar 队列已满（429）。"""


def _as_bool(v: object, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    return default


def _clean_sidecar(raw: str) -> str:
    s = (raw or DEFAULT_SIDECAR).strip().rstrip("/")
    try:
        u = urlparse(s)
    except ValueError:
        return DEFAULT_SIDECAR
    if u.scheme not in ("http", "https") or not u.netloc or u.username or u.password:
        return DEFAULT_SIDECAR
    return s


def local_cfg(db: Session) -> dict:
    """app_cfg 'speak.local'；兼容未来按语言的 voices/speeds/max_chars 对象。"""
    from app.services.ai_enrich import get_cfg

    raw = get_cfg(db, "speak.local", "{}")
    try:
        d = json.loads(raw) if raw else {}
        if not isinstance(d, dict):
            d = {}
    except json.JSONDecodeError:
        d = {}

    def nested(group: str, key: str) -> object:
        g = d.get(group)
        return g.get(key) if isinstance(g, dict) else None

    def pick_str(*values: object, default: str = "") -> str:
        for v in values:
            if isinstance(v, str) and v.strip():
                return v.strip()
        return default

    def pick_num(*values: object, default: float = 0.0) -> float:
        for v in values:
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str) and v.strip():
                try:
                    return float(v)
                except ValueError:
                    continue
        return default

    voice = pick_str(d.get("voice"), nested("voices", "en"), default=DEFAULT_VOICE)
    if not _VOICE_RE.match(voice):
        voice = DEFAULT_VOICE
    voice_zh = pick_str(d.get("voice_zh"), nested("voices", "zh"), default=DEFAULT_VOICE_ZH)
    if not _VOICE_RE.match(voice_zh):
        voice_zh = DEFAULT_VOICE_ZH
    speed = pick_num(d.get("speed"), nested("speeds", "en"), default=0.95)
    speed = min(2.0, max(0.5, speed))
    max_chars = pick_num(d.get("max_chars"), nested("max_chars", "en"), default=300)
    max_chars = min(400, max(50, int(max_chars)))
    rate = pick_num(d.get("rate_per_min"), default=30)
    rate = min(300, max(1, int(rate)))
    version = pick_str(d.get("cache_version"), default="piper1")
    if not _VERSION_RE.match(version):
        version = "piper1"
    pronounce = d.get("pronounce")
    if not isinstance(pronounce, dict):
        pronounce = {}
    pronounce = {
        str(k).strip(): str(v).strip()
        for k, v in pronounce.items()
        if str(k).strip() and str(v).strip()
    }
    return {
        "enabled": _as_bool(d.get("enabled"), False),
        "engine": "piper",
        "voice": voice,
        "voice_zh": voice_zh,
        "voices": {"en": voice, "zh": voice_zh},
        "speed": speed,
        "sidecar": _clean_sidecar(pick_str(d.get("sidecar"), default=DEFAULT_SIDECAR)),
        "max_chars": max_chars,
        "cache_version": version,
        "rate_per_min": rate,
        "pronounce": pronounce,
    }


def public_cfg(db: Session) -> dict:
    cfg = local_cfg(db)
    return {
        "enabled": cfg["enabled"],
        "engine": cfg["engine"],
        "voice": cfg["voice"],
        "voices": cfg["voices"],
        "speed": cfg["speed"],
        "cache_version": cfg["cache_version"],
        "max_chars": cfg["max_chars"],
        "path": "/api/v1/speak/tts/local",
    }


def detect_lang(text: str) -> str:
    """含汉字即按中文朗读（SOE 建议是中英混排，用中文音色整体读）。"""
    return "zh" if has_cjk(text) else "en"


def _normalize_zh(text: str) -> str:
    """中文只折叠空白；不展开英文缩写、不截到第一个汉字。"""
    return re.sub(r"\s+", " ", text or "").strip()


def prepare_text(cfg: dict, text: str) -> tuple[str, str, str]:
    """返回 (规范化文本, 语言, 音色)。"""
    lang = detect_lang(text)
    if lang == "zh":
        norm = _normalize_zh(text)
    else:
        norm = normalize_for_tts(text, cfg.get("pronounce"))
    norm = truncate_text(norm, int(cfg["max_chars"]))
    if not norm:
        raise ValueError("没有可朗读的文本")
    return norm, lang, cfg["voices"][lang]


def cache_key(cfg: dict, voice: str, normalized: str) -> str:
    payload = (
        f"{cfg['engine']}|{voice}|{cfg['speed']:.2f}|"
        f"{cfg['cache_version']}|{normalized}"
    )
    return hashlib.sha1(payload.encode()).hexdigest()


def _cached_path(cfg: dict, text: str) -> tuple[Path | None, str, str, str]:
    norm, lang, voice = prepare_text(cfg, text)
    p = Path(tts_cache.cache_dir()) / f"{cache_key(cfg, voice, norm)}.wav"
    if p.is_file() and p.stat().st_size >= MIN_WAV_BYTES:
        return p, norm, lang, voice
    return None, norm, lang, voice


def get_cached(cfg: dict, text: str) -> tuple[Path | None, str, str, str]:
    return _cached_path(cfg, text)


_last_enforce = 0.0


def _maybe_enforce(db: Session) -> None:
    global _last_enforce
    now = time.monotonic()
    if now - _last_enforce < _MIN_ENFORCE_SEC:
        return
    _last_enforce = now
    tts_cache.enforce_tts_cache(tts_cache.cache_dir(), tts_cache.tts_cache_cfg(db))


def _call_sidecar(cfg: dict, text: str, voice: str = "") -> tuple[bytes, int]:
    started = time.monotonic()
    try:
        resp = httpx.post(
            f"{cfg['sidecar']}/synth",
            json={"text": text, "voice": voice or cfg["voice"], "speed": cfg["speed"]},
            # 连接失败（sidecar 未启动）要尽快报错，让前端及时回退浏览器朗读；
            # 合成本身可以慢一些。容器网络内 1s 连不上就是没起。
            timeout=httpx.Timeout(60.0, connect=1.0),
        )
    except httpx.HTTPError as e:
        raise RuntimeError(f"本地 TTS 连接失败：{e}") from e
    ms = int((time.monotonic() - started) * 1000)
    if resp.status_code == 429:
        raise LocalTtsBusy("本地 TTS 正忙，请稍后再试")
    if resp.status_code >= 400:
        raise RuntimeError(f"本地合成失败（HTTP {resp.status_code}）：{resp.text[:160]}")
    return resp.content, ms


def synthesize(db: Session, cfg: dict, text: str) -> dict:
    """未命中才调用 sidecar；返回与 Qwen TTS 相同的 url 契约。"""
    norm, lang, voice = prepare_text(cfg, text)
    d = Path(tts_cache.cache_dir())
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{cache_key(cfg, voice, norm)}.wav"
    if f.is_file() and f.stat().st_size >= MIN_WAV_BYTES:
        return _out(f, True, norm, 0, lang, voice)
    # 开发模式也走真实 sidecar：sidecar 没起时直接失败（502），
    # 让前端回退浏览器朗读；不要返回提示音假装成功。
    data, ms = _call_sidecar(cfg, norm, voice)
    if len(data) < MIN_WAV_BYTES:
        raise RuntimeError("本地合成返回的音频过小")
    tts_cache.store_atomic(f, data)
    _maybe_enforce(db)
    return _out(f, False, norm, ms, lang, voice)


def _out(f: Path, cached: bool, text: str, ms: int, lang: str, voice: str) -> dict:
    return {
        "url": f"/api/v1/speak/tts/file/{f.name}",
        "mime": "audio/wav",
        "cached": cached,
        "chars": len(text),
        "provider": "piper",
        "lang": lang,
        "voice": voice,
        "ms": ms,
    }


_touched: dict[str, float] = {}
_buckets: dict[int, list[float]] = {}
# Qwen 示范单独计数，避免和本地合成的 30 次/分钟互相挤占
qwen_buckets: dict[int, list[float]] = {}


def touch(path: Path) -> None:
    """GET 命中时更新 mtime（节流），让 LRU 近似按访问时间淘汰。"""
    now = time.monotonic()
    if now - _touched.get(path.name, 0.0) < _TOUCH_SEC:
        return
    if len(_touched) > 5000:
        _touched.clear()
    _touched[path.name] = now
    try:
        os.utime(path, None)
    except OSError:
        pass


def allow(user: User, per_min: int, store: dict[int, list[float]] | None = None) -> bool:
    """按用户限流（单进程近似）；管理员跳过，供预生成脚本使用。"""
    if getattr(user, "is_admin", False):
        return True
    buckets = _buckets if store is None else store
    now = time.monotonic()
    if len(buckets) > 1000:
        buckets.clear()
    q = buckets.setdefault(user.id, [])
    q[:] = [t for t in q if now - t < 60.0]
    if len(q) >= per_min:
        return False
    q.append(now)
    return True
