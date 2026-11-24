"""口语媒体路由：Qwen TTS（懒缓存 + 静态 URL + 计量）。

P0-2 / P0-3 / P1-4 / P2-2：
- 未命中才调用模型并写缓存；命中不计费。
- 返回可浏览器缓存的静态 URL，不再把 base64 WAV 塞进 JSON。
- 缓存 512MB 上限，按 mtime LRU；管理页可查看/清理。
"""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import require_paid_ai
from app.db import get_db
from app.models.user import User
from app.services import dev_mock, qwen_speak, usage

router = APIRouter(prefix="/speak", tags=["speak"])

_NAME_RE = re.compile(r"^[0-9a-f]{40}\.wav$")


def cache_dir() -> str:
    """缓存目录与 sqlite 同级（./data/tts）；生产 compose 挂卷即可持久化。"""
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    return str(Path(db_path).parent / "tts")


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


@router.get("/tts/file/{name}")
def tts_file(name: str) -> FileResponse:
    """只读缓存音频：文件名即 sha1，内容不可变，可长期缓存。"""
    if not _NAME_RE.match(name):
        raise HTTPException(404, "音频不存在")
    f = Path(cache_dir()) / name
    if not f.is_file():
        raise HTTPException(404, "音频不存在")
    return FileResponse(
        f,
        media_type="audio/wav",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
