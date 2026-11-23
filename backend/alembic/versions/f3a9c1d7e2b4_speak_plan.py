"""speak: user-created plan length

Revision ID: f3a9c1d7e2b4
Revises: b7c1f2a90d34
Create Date: 2026-11-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a9c1d7e2b4"
down_revision: Union[str, Sequence[str], None] = "b7c1f2a90d34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "speak_plans",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("length", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("speak_plans")
