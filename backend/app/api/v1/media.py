"""课程视频鉴权：签发短时效媒体令牌 + 供 nginx auth_request 校验。

视频文件仍由 nginx `sendfile` 直出（Range/断点续播），不经过 FastAPI；
但 `/media/math/` 现在挂 `auth_request`，只有带合法媒体令牌的请求才能取流。
令牌放查询串（`?mt=`）而不是 Cookie：iOS AirPlay 由电视端取流，带不了 Cookie。
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import decode_token, make_media_token
from app.db import get_db
from app.models.user import User

router = APIRouter(prefix="/media", tags=["media"])

MEDIA_TOKEN_HEADER = "X-Media-Token"


@router.post("/token")
def issue_token(user: User = Depends(get_current_user)) -> dict:
    """登录用户换取媒体令牌（默认 6 小时）；前端拼到视频 URL 的 `mt` 参数。"""
    token, exp = make_media_token(user.id)
    return {"token": token, "expires_at": exp}


@router.get("/auth", status_code=status.HTTP_204_NO_CONTENT)
def check_media_token(
    response: Response,
    x_media_token: str = Header(default="", alias=MEDIA_TOKEN_HEADER),
    db: Session = Depends(get_db),
) -> Response:
    """nginx 内部子请求：令牌有效且用户仍存在 → 204，否则 401。"""
    user_id = decode_token(x_media_token, "media") if x_media_token else None
    if user_id is None or db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "视频访问需要登录")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
