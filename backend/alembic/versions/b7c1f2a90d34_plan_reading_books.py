"""plans.reading_books：阅读计划覆盖的教材（JSON 数组，空=未指定）

Revision ID: b7c1f2a90d34
Revises: a1d4c0e77f21
Create Date: 2026-11-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1f2a90d34"
down_revision: Union[str, Sequence[str], None] = "a1d4c0e77f21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 老计划的阅读计划都覆盖全部教材 → 空数组即「全部」，无需回填
    with op.batch_alter_table("plans") as batch:
        batch.add_column(
            sa.Column("reading_books", sa.String(length=256), nullable=False, server_default="[]")
        )


def downgrade() -> None:
    with op.batch_alter_table("plans") as batch:
        batch.drop_column("reading_books")
