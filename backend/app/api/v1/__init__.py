"""API v1 路由汇总。"""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_ai,
    auth,
    media,
    speak,
    speak_local,
    speak_media,
    sync,
    usage,
    words,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(sync.router)
api_router.include_router(media.router)
api_router.include_router(speak.router)
api_router.include_router(speak_local.router)
api_router.include_router(speak_media.router)
api_router.include_router(usage.router)
api_router.include_router(words.router)
api_router.include_router(admin.router)
api_router.include_router(admin_ai.router)
