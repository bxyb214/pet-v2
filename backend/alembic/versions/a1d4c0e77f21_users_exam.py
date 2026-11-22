"""users.exam：用户当前学习的考试级别（KET / PET / 预留 FCE、初中英语）

Revision ID: a1d4c0e77f21
Revises: c77a01f4b210
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1d4c0e77f21"
down_revision: Union[str, Sequence[str], None] = "c77a01f4b210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 已有用户全部按 PET 起算（旧站只有 PET 内容）
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("exam", sa.String(length=16), nullable=False, server_default="pet")
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("exam")
