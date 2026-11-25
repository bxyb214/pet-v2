"""空库初始化：确保初始化邀请码存在。

容器启动顺序（Dockerfile CMD / deploy/docker-compose.dev.yml）：

    alembic upgrade head
    python -m app.bootstrap
    uvicorn ...

只做幂等数据补齐，不建表（schema 仍由 Alembic 管理）。
前端会把邀请码转成大写，因此固定写入 CLAIM。
"""

from __future__ import annotations

from app.db import SessionLocal
from app.models.user import InviteCode, User

CLAIM_CODE = "CLAIM"


def ensure_claim_invite() -> bool:
    """空库且没有 CLAIM 时插入；已有账号或已有该码时返回 False。"""
    with SessionLocal() as db:
        if db.query(User.id).first() is not None:
            return False
        exists = db.query(InviteCode.id).filter(InviteCode.code == CLAIM_CODE).first()
        if exists is not None:
            return False
        db.add(InviteCode(code=CLAIM_CODE))
        db.commit()
        return True


def main() -> None:
    created = ensure_claim_invite()
    if created:
        print(f"[bootstrap] 空库已创建初始化邀请码 {CLAIM_CODE}")
    else:
        print("[bootstrap] 无需创建初始化邀请码（已有账号或 CLAIM 已存在）")


if __name__ == "__main__":
    main()
