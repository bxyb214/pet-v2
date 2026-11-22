"""API v1 路由汇总。"""
from fastapi import APIRouter

from app.api.v1 import admin, auth, speak, sync, words

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(sync.router)
api_router.include_router(speak.router)
api_router.include_router(words.router)
api_router.include_router(admin.router)
