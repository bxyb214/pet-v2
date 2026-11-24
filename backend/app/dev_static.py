"""本地开发用静态挂载：让 uvicorn 在 8088 同端口直出 `frontend/dist`。

仅 `tools/dev_local.py` 使用；生产仍由 nginx 直出静态文件，本模块不参与容器运行。
"""
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse

# 与 deploy/nginx.conf 的缓存策略保持一致：入口与题库每次协商，哈希资源长缓存
NO_CACHE = "no-cache"
ASSET_CACHE = "public, max-age=2592000"
MEDIA_CACHE = "private, max-age=3600"


def _safe_file(root: Path, rel: str) -> Path | None:
    """把 URL 相对路径解析到 root 内；越界或不存在返回 None。"""
    target = (root / rel).resolve()
    if target == root or root in target.parents:
        return target if target.is_file() else None
    return None


def _cache_control(rel: str) -> str:
    if rel.endswith(".html") or (rel.startswith("data/") and rel.endswith(".json")):
        return NO_CACHE
    return ASSET_CACHE


def _mount_media(app: FastAPI, media_root: Path) -> None:
    """`/media/math/*`：校验媒体令牌后直出，替代 nginx 的 auth_request。"""
    from app.core.security import decode_token
    from app.db import SessionLocal
    from app.models.user import User

    @app.api_route("/media/math/{file_path:path}", methods=["GET", "HEAD"],
                   include_in_schema=False)
    def serve_media(
        file_path: str,
        mt: str = "",
        x_media_token: str = Header(default=""),
    ) -> FileResponse:
        token = mt or x_media_token
        user_id = decode_token(token, "media") if token else None
        if user_id is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "视频访问需要登录")
        with SessionLocal() as db:
            if db.get(User, user_id) is None:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "视频访问需要登录")
        target = _safe_file(media_root, file_path)
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        # Starlette 的 FileResponse 原生支持 Range，可用于拖动进度条
        return FileResponse(target, headers={"Cache-Control": MEDIA_CACHE})


def mount_static(app: FastAPI, dist: Path, media_root: Path | None = None) -> None:
    """在 API 路由之后挂载静态站点；调用顺序决定路由优先级。"""
    dist = dist.resolve()
    index = dist / "index.html"

    if media_root is not None:
        _mount_media(app, media_root.resolve())

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        rel = full_path.strip("/")
        if rel == "api" or rel.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        if rel == "media" or rel.startswith("media/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        if rel:
            found = _safe_file(dist, rel)
            if found is not None:
                return FileResponse(found, headers={"Cache-Control": _cache_control(rel)})
            # 缺失的 JS/CSS/图片直接 404，避免错误地被回成 index.html
            if Path(rel).suffix:
                raise HTTPException(status.HTTP_404_NOT_FOUND)
        if not index.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "前端未构建：先执行 npm run build")
        return FileResponse(index, headers={"Cache-Control": NO_CACHE})
