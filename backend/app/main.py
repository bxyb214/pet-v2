"""FastAPI 入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 同源部署（nginx 反代），收紧可见 deploy/nginx.conf
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# schema 由 Alembic 管理：启动前 `alembic upgrade head`（见 Dockerfile CMD）
# 开发环境首次准备：cd backend && alembic upgrade head


@app.get("/api/v1/healthz")
def healthz() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "version": app.version,
        "app": s.app_name,
        "dev_mode": s.dev_mode,
    }
