"""usage 记账 + 画像 + 会后复盘 + speak_logs.summary

Revision ID: c77a01f4b210
Revises: eda43aedbffd
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c77a01f4b210"
down_revision: Union[str, Sequence[str], None] = "eda43aedbffd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usages",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("rt_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rt_ai_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rt_audio_in_tok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rt_audio_out_tok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rt_text_in_tok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rt_text_out_tok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("soe_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_in_tok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_out_tok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("est_cost_milli", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "day"),
    )
    op.add_column("speak_logs", sa.Column("summary", sa.String(length=512), nullable=False, server_default=""))
    op.create_table(
        "speak_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("built_day", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "speak_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("log_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("child_said", sa.Text(), nullable=False, server_default=""),
        sa.Column("improved_en", sa.Text(), nullable=False, server_default=""),
        sa.Column("improved_cn", sa.Text(), nullable=False, server_default=""),
        sa.Column("focus", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("dims", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("stage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_at", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("repeats", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_speak_reviews_user_id", "speak_reviews", ["user_id"])
    op.create_index("ix_speak_reviews_log_id", "speak_reviews", ["log_id"])


def downgrade() -> None:
    op.drop_index("ix_speak_reviews_log_id", table_name="speak_reviews")
    op.drop_index("ix_speak_reviews_user_id", table_name="speak_reviews")
    op.drop_table("speak_reviews")
    op.drop_table("speak_profiles")
    op.drop_column("speak_logs", "summary")
    op.drop_table("usages")
