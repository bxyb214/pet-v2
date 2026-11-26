"""Piper TTS sidecar：POST /synth 返回 WAV 字节，不做磁盘缓存。

缓存、LRU、鉴权、限流全部由 api 负责；这里只保证「文本 → 音频」。
"""
from __future__ import annotations

import io
import os
import threading
import time
import wave
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from piper import PiperVoice, SynthesisConfig

_RAW_VOICES = os.environ.get("PIPER_VOICES") or os.environ.get(
    "PIPER_VOICE", "en_GB-alan-medium,zh_CN-huayan-medium"
)
VOICES = [v.strip() for v in _RAW_VOICES.split(",") if v.strip()] or ["en_GB-alan-medium"]
DEFAULT_VOICE = VOICES[0]
DATA_DIR = Path(os.environ.get("PIPER_DATA_DIR", "/models"))
MAX_TEXT = int(os.environ.get("TTS_MAX_TEXT", "400"))
MAX_QUEUE = int(os.environ.get("TTS_MAX_QUEUE", "4"))

_voices: dict[str, PiperVoice] = {}
_model_bytes = 0
_sem = threading.BoundedSemaphore(1)
_wait_lock = threading.Lock()
_waiting = 0
_stats = {"requests": 0, "errors": 0, "total_ms": 0}


def _load_voice(name: str) -> PiperVoice:
    model = DATA_DIR / f"{name}.onnx"
    config = DATA_DIR / f"{name}.onnx.json"
    if not model.is_file() or not config.is_file():
        raise RuntimeError(f"voice files missing under {DATA_DIR}: {name}")
    return PiperVoice.load(str(model), config_path=str(config))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _model_bytes
    for name in VOICES:
        _voices[name] = _load_voice(name)
    _model_bytes = sum(p.stat().st_size for p in DATA_DIR.glob("*.onnx*"))
    yield


app = FastAPI(title="pet-tts", version="0.1.0", lifespan=lifespan)


class SynthIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    voice: str = Field(default="", max_length=64)
    speed: float = Field(default=0.95, ge=0.5, le=2.0)


def _rss_mb() -> int:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


@app.get("/healthz")
def healthz() -> dict:
    ready = bool(_voices)
    return {
        "ok": ready,
        "ready": ready,
        "engine": "piper",
        "voice": DEFAULT_VOICE,
        "voices": sorted(_voices),
        "model_bytes": _model_bytes,
        "rss_mb": _rss_mb(),
    }


@app.get("/stats")
def stats() -> dict:
    total = _stats["total_ms"]
    n = _stats["requests"]
    return {
        "engine": "piper",
        "voice": DEFAULT_VOICE,
        "voices": sorted(_voices),
        "requests": n,
        "errors": _stats["errors"],
        "avg_ms": int(total / n) if n else 0,
        "queue": _waiting,
    }


@app.post("/synth")
def synth(body: SynthIn) -> Response:
    global _waiting
    voice = body.voice or DEFAULT_VOICE
    model = _voices.get(voice)
    if model is None:
        raise HTTPException(400, f"voice not loaded: {voice} (available: {', '.join(sorted(_voices))})")

    with _wait_lock:
        if _waiting >= MAX_QUEUE:
            raise HTTPException(429, "busy")
        _waiting += 1
    started = time.monotonic()
    acquired = False
    try:
        acquired = _sem.acquire(timeout=60)
        if not acquired:
            raise HTTPException(429, "busy")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            model.synthesize_wav(
                body.text,
                wav,
                syn_config=SynthesisConfig(length_scale=1.0 / body.speed),
            )
        data = buf.getvalue()
        ms = int((time.monotonic() - started) * 1000)
        _stats["requests"] += 1
        _stats["total_ms"] += ms
        return Response(
            content=data,
            media_type="audio/wav",
            headers={"X-TTS-Ms": str(ms), "X-TTS-Engine": "piper", "X-TTS-Voice": voice},
        )
    except HTTPException:
        _stats["errors"] += 1
        raise
    except Exception as exc:  # noqa: BLE001
        _stats["errors"] += 1
        raise HTTPException(500, f"synthesis failed: {exc}") from exc
    finally:
        if acquired:
            _sem.release()
        with _wait_lock:
            _waiting -= 1
