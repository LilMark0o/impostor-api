"""game_sessions

Revision ID: b7e2a14f3c90
Revises: a3f8c21d9e05
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7e2a14f3c90'
down_revision: Union[str, Sequence[str], None] = 'a3f8c21d9e05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = sa.inspect(op.get_bind()).get_table_names()

    if "game_sessions" not in existing:
        op.create_table(
            "game_sessions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("mode", sa.String(), nullable=False),
            sa.Column("difficulty", sa.String(), nullable=False),
            sa.Column("n_impostors", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "game_player_results" not in existing:
        op.create_table(
            "game_player_results",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("session_id", sa.String(), nullable=False),
            sa.Column("player_id", sa.String(), nullable=False),
            sa.Column("player_name", sa.String(), nullable=False),
            sa.Column("is_impostor", sa.Boolean(), nullable=False),
            sa.Column("category_shown", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("game_player_results")
    op.drop_table("game_sessions")
