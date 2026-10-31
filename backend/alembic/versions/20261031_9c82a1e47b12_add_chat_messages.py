"""add chat_messages table for persistent assistant history

Revision ID: 9c82a1e47b12
Revises: 0b68d3488497
Create Date: 2026-10-31 18:48:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c82a1e47b12"
down_revision: Union[str, None] = "0b68d3488497"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "chat_messages" not in inspector.get_table_names():
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("profile_id", sa.Integer(), nullable=True),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["profile_id"], ["investor_profiles.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("chat_messages", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_chat_messages_profile_id"), ["profile_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_chat_messages_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "chat_messages" in inspector.get_table_names():
        with op.batch_alter_table("chat_messages", schema=None) as batch_op:
            batch_op.drop_index(batch_op.f("ix_chat_messages_user_id"))
            batch_op.drop_index(batch_op.f("ix_chat_messages_profile_id"))
        op.drop_table("chat_messages")
