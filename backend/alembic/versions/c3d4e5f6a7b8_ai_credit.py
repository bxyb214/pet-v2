"""AI 改为一次性总额度：默认开启付费 AI，新账号默认 0.5 元

Revision ID: c3d4e5f6a7b8
Revises: b8e2f6a9c3d1
Create Date: 2026-11-26

- 新增 users.ai_credit_milli（NULL = 全局 ai.budget.credit_milli，默认 500 = 0.5 元）。
- 存量账号升级后重新获得 0.5 元：把历史已用计入总额度，避免升级即被拦。
- 普通账号默认开启付费 AI（仍可在管理页按人关闭）。
- 旧的日/月预算列保留在库中但不再使用（避免 SQLite 重建表的风险）。
- 旧日/月告警作废，避免与总额度告警混淆。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b8e2f6a9c3d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ai_credit_milli", sa.Integer(), nullable=True))

    # 存量账号：历史已用 + 0.5 元，升级后仍有一笔可用的新额度
    op.execute(
        "UPDATE users SET ai_credit_milli = 500 + COALESCE("
        "(SELECT SUM(est_cost_milli) FROM usages WHERE usages.user_id = users.id), 0)"
    )
    op.execute("UPDATE users SET ai_enabled = 1")
    op.execute("DELETE FROM usage_alerts")


def downgrade() -> None:
    op.drop_column("users", "ai_credit_milli")
