"""plans.plan_updated_at / reading_updated_at：计划结构变更时间

Revision ID: c9d1e2f3a4b5
Revises: a7c2e9f14d50
Create Date: 2026-11-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "a7c2e9f14d50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 老数据没有时间戳 → 0，继续按原并集语义合并；用户下次创建/删除时写入当前时间
    with op.batch_alter_table("plans") as batch:
        batch.add_column(sa.Column("plan_updated_at", sa.BigInteger(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("reading_updated_at", sa.BigInteger(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("plans") as batch:
        batch.drop_column("reading_updated_at")
        batch.drop_column("plan_updated_at")
