"""initial schema with users and per-user ownership

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    op.create_table(
        "chatsession",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("pinned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chatsession_owner_id", "chatsession", ["owner_id"])
    op.create_index("ix_chatsession_is_pinned", "chatsession", ["is_pinned"])

    op.create_table(
        "chatmessage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chatsession.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chatmessage_session_id", "chatmessage", ["session_id"])

    op.create_table(
        "messagetrace",
        sa.Column("ai_message_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("trace_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chatsession.id"]),
        sa.PrimaryKeyConstraint("ai_message_id"),
    )
    op.create_index("ix_messagetrace_session_id", "messagetrace", ["session_id"])

    op.create_table(
        "mcpserverconfig",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("connection", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )

    op.create_table(
        "mcpserveruserflag",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "name"),
    )

    op.create_table(
        "toolflag",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "name"),
    )

    op.create_table(
        "skillflag",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "name"),
    )

    op.create_table(
        "savedartifact",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False, server_default=""),
        sa.Column("source_kind", sa.String(), nullable=True),
        sa.Column("source_code", sa.String(), nullable=True),
        sa.Column("parent_artifact_ids", sa.JSON(), nullable=False),
        sa.Column("payload_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_savedartifact_owner_id", "savedartifact", ["owner_id"])
    op.create_index("ix_savedartifact_session_id", "savedartifact", ["session_id"])
    op.create_index("ix_savedartifact_pinned", "savedartifact", ["pinned"])

    op.create_table(
        "savedtask",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("source_session_id", sa.String(), nullable=True),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("creator", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_savedtask_owner_id", "savedtask", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_savedtask_owner_id", "savedtask")
    op.drop_table("savedtask")
    op.drop_index("ix_savedartifact_pinned", "savedartifact")
    op.drop_index("ix_savedartifact_session_id", "savedartifact")
    op.drop_index("ix_savedartifact_owner_id", "savedartifact")
    op.drop_table("savedartifact")
    op.drop_table("skillflag")
    op.drop_table("toolflag")
    op.drop_table("mcpserveruserflag")
    op.drop_table("mcpserverconfig")
    op.drop_index("ix_messagetrace_session_id", "messagetrace")
    op.drop_table("messagetrace")
    op.drop_index("ix_chatmessage_session_id", "chatmessage")
    op.drop_table("chatmessage")
    op.drop_index("ix_chatsession_is_pinned", "chatsession")
    op.drop_index("ix_chatsession_owner_id", "chatsession")
    op.drop_table("chatsession")
    op.drop_index("ix_user_email", "user")
    op.drop_table("user")
