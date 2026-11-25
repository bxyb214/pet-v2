"""custom_words.bank/exam：管理员批量导入生词时标注所属词库与级别

Revision ID: b8e2f6a9c3d1
Revises: e1a2b3c4d5e6
Create Date: 2026-11-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e2f6a9c3d1"
down_revision: Union[str, Sequence[str], None] = "e1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 旧数据 = 学生手动添加，无词库归属（空串；custom 页展示时归「手动添加」）
    with op.batch_alter_table("custom_words") as batch:
        batch.add_column(sa.Column("bank", sa.String(length=16), nullable=False, server_default=""))
        batch.add_column(sa.Column("exam", sa.String(length=16), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("custom_words") as batch:
        batch.drop_column("exam")
        batch.drop_column("bank")
