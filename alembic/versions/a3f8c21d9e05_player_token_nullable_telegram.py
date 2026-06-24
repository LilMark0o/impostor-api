"""player_token_nullable_telegram

Revision ID: a3f8c21d9e05
Revises: c24b8d2842c1
Create Date: 2026-06-24

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3f8c21d9e05'
down_revision: Union[str, Sequence[str], None] = 'c24b8d2842c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make telegram_id nullable
    op.alter_column("players", "telegram_id", existing_type=sa.BigInteger(), nullable=True)
    # Add token column
    op.add_column("players", sa.Column("token", sa.String(), nullable=True))
    # Populate existing rows with UUID
    op.execute(
        "UPDATE players SET token = gen_random_uuid()::text WHERE token IS NULL"
    )
    op.alter_column("players", "token", nullable=False)
    op.create_unique_constraint("uq_players_token", "players", ["token"])


def downgrade() -> None:
    op.drop_constraint("uq_players_token", "players", type_="unique")
    op.drop_column("players", "token")
    op.alter_column("players", "telegram_id", existing_type=sa.BigInteger(), nullable=False)
