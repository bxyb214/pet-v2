"""口语媒体路由：Qwen TTS 与 TTS 缓存静态读取。

- `/speak/tts/demo` 只服务跟读「听示范」：登录即可、不记用量，命中缓存不产生费用。
- `/speak/tts` 保留付费语义（旧接口/管理页测试）。
- 未命中才调用模型并写缓存；返回可浏览器缓存的静态 URL。
- 缓存上限（默认 1024MB）与 LRU 在 `services/tts_cache.py`，本地 Piper 共用。
"""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_paid_ai
from app.db import get_db
from app.models.user import User
from app.services import dev_mock, local_tts, qwen_speak, usage
from app.services.tts_cache import cache_dir, repair_wav_file

router = APIRouter(prefix="/speak", tags=["speak"])

_NAME_RE = re.compile(r"^[0-9a-f]{40}\.wav$")
_DEMO_RATE_PER_MIN = 30


class TtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    voice: str = Field(default="", max_length=64)


@router.post("/tts")
def tts(body: TtsIn, user: User = Depends(require_paid_ai), db: Session = Depends(get_db)) -> dict:
    if dev_mock.is_dev():
        return dev_mock.tts_payload()
    try:
        out = qwen_speak.tts(db, cache_dir(), body.text, body.voice)
        usage.record_tts(db, user.id, int(out.get("chars", 0)), bool(out.get("cached")))
        return out
    except PermissionError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))


@router.post("/tts/demo")
def tts_demo(
    body: TtsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """跟读示范：Qwen 合成 + 磁盘缓存；免费、不记用量，只做每用户限流。"""
    if dev_mock.is_dev():
        return dev_mock.tts_payload()
    if not local_tts.allow(user, _DEMO_RATE_PER_MIN, local_tts.qwen_buckets):
        raise HTTPException(429, "示范请求过于频繁，请稍后再试")
    try:
        out = qwen_speak.tts(db, cache_dir(), body.text, body.voice)
        return {**out, "provider": "qwen"}
    except PermissionError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))


@router.get("/tts/file/{name}")
def tts_file(name: str) -> FileResponse:
    """只读缓存音频：文件名即 sha1，内容不可变，可长期缓存。"""
    if not _NAME_RE.match(name):
        raise HTTPException(404, "音频不存在")
    f = Path(cache_dir()) / name
    if not f.is_file():
        raise HTTPException(404, "音频不存在")
    repair_wav_file(f)
    return FileResponse(
        f,
        media_type="audio/wav",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
