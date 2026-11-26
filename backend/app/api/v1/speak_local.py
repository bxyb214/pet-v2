"""本地 TTS 路由：公开配置 / 只读缓存 / 登录后按需合成。

- GET 永不合成：只读 `data/tts` 里已预生成的音频，公开但不消耗 CPU。
- POST 需要登录，不走付费闸门；本地合成免费，不记 usage。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.services import local_tts

router = APIRouter(prefix="/speak", tags=["speak"])

_IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}


class LocalTtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=400)


@router.get("/tts/config")
def tts_config(db: Session = Depends(get_db)) -> dict:
    """前端启动时拉取；公开只读，不返回 sidecar 地址与 pronounce 表。"""
    return local_tts.public_cfg(db)


@router.get("/tts/local")
def tts_local(
    text: str = Query(min_length=1, max_length=400),
    v: str = Query(default="", max_length=32),
    db: Session = Depends(get_db),
) -> FileResponse:
    """只读预热缓存；未命中返回 404，由前端回退浏览器朗读并后台预热。"""
    cfg = local_tts.local_cfg(db)
    if not cfg["enabled"]:
        raise HTTPException(404, "本地音频未预热")
    try:
        f, _, lang, voice = local_tts.get_cached(cfg, text)
    except ValueError:
        raise HTTPException(404, "本地音频未预热")
    if f is None:
        raise HTTPException(404, "本地音频未预热")
    local_tts.touch(f)
    return FileResponse(
        f,
        media_type="audio/wav",
        headers={
            **_IMMUTABLE,
            "X-TTS-Engine": cfg["engine"],
            "X-TTS-Lang": lang,
            "X-TTS-Voice": voice,
        },
    )


@router.post("/tts/local")
def tts_local_synth(
    body: LocalTtsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    cfg = local_tts.local_cfg(db)
    if not cfg["enabled"]:
        raise HTTPException(503, "本地 TTS 未启用")
    if not local_tts.allow(user, int(cfg["rate_per_min"])):
        raise HTTPException(429, "本地 TTS 请求过于频繁，请稍后再试")
    try:
        return local_tts.synthesize(db, cfg, body.text)
    except local_tts.LocalTtsBusy as e:
        raise HTTPException(429, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
