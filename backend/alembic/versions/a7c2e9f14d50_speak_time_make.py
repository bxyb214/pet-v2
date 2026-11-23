"""speak: make_done + per-day practice seconds

Revision ID: a7c2e9f14d50
Revises: f3a9c1d7e2b4
Create Date: 2026-11-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c2e9f14d50"
down_revision: Union[str, Sequence[str], None] = "f3a9c1d7e2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "speak_days",
        sa.Column("make_done", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.create_table(
        "speak_times",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("user_id", "day", "mode"),
    )


def downgrade() -> None:
    op.drop_table("speak_times")
    op.drop_column("speak_days", "make_done")
