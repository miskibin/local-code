"""add task_id to chatsession

Revision ID: 0002_chatsession_task_id
Revises: 0001_initial
Create Date: 2026-04-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_chatsession_task_id"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chatsession", sa.Column("task_id", sa.String(), nullable=True))
    op.create_index("ix_chatsession_task_id", "chatsession", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_chatsession_task_id", "chatsession")
    op.drop_column("chatsession", "task_id")
