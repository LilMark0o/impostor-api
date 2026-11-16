"""game_player_results hint column

Revision ID: b4d7c9e12a01
Revises: f2a8b95c1d3e
Create Date: 2026-11-15
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'b4d7c9e12a01'
down_revision: Union[str, Sequence[str], None] = 'f2a8b95c1d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: rows created before hints were stored simply have none.
    op.add_column(
        "game_player_results",
        sa.Column("hint", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("game_player_results", "hint")
