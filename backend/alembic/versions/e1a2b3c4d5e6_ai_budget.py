"""AI 预算与计量补全：用户开关/预算、usage TTS 列、告警与会话表

Revision ID: e1a2b3c4d5e6
Revises: c9d1e2f3a4b5
Create Date: 2026-11-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "c9d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("ai_daily_budget_milli", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("ai_monthly_budget_milli", sa.Integer(), nullable=True))

    op.add_column("usages", sa.Column("tts_calls", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("usages", sa.Column("tts_chars", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "usages", sa.Column("tts_cache_hits", sa.Integer(), nullable=False, server_default="0")
    )

    op.add_column(
        "speak_logs",
        sa.Column("sentence_id", sa.String(length=32), nullable=False, server_default=""),
    )
    op.add_column(
        "speak_logs", sa.Column("words", sa.Text(), nullable=False, server_default="[]")
    )

    op.create_table(
        "usage_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.String(length=8), nullable=False),
        sa.Column("period_key", sa.String(length=10), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "period", "period_key", "stage", name="uq_usage_alert"),
    )
    op.create_index("ix_usage_alerts_user_id", "usage_alerts", ["user_id"])

    op.create_table(
        "ai_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="talk"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text_in_tok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("est_cost_milli", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_ai_sessions_user_id", "ai_sessions", ["user_id"])

    # 现有管理员保持可用；普通用户默认关闭付费 AI（可按需在管理页开通）
    op.execute("UPDATE users SET ai_enabled = 1 WHERE is_admin = 1")


def downgrade() -> None:
    op.drop_index("ix_ai_sessions_user_id", table_name="ai_sessions")
    op.drop_table("ai_sessions")
    op.drop_index("ix_usage_alerts_user_id", table_name="usage_alerts")
    op.drop_table("usage_alerts")
    op.drop_column("speak_logs", "words")
    op.drop_column("speak_logs", "sentence_id")
    op.drop_column("usages", "tts_cache_hits")
    op.drop_column("usages", "tts_chars")
    op.drop_column("usages", "tts_calls")
    op.drop_column("users", "ai_monthly_budget_milli")
    op.drop_column("users", "ai_daily_budget_milli")
    op.drop_column("users", "ai_enabled")
