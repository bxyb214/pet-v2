"""FastAPI 入口。"""
from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import get_settings, require_production_secret

settings = get_settings()
require_production_secret(settings)

app = FastAPI(title=settings.app_name, version="0.2.0")

# 同源部署：生产由 nginx 反代 /api，开发由 Vite 代理 /api 到 8000。
# 因此不启用 CORS；allow_origins=["*"] + credentials 本身也会被浏览器拒绝。

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
