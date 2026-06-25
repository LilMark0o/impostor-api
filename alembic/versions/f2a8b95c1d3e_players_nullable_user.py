"""players nullable user_id no fk

Revision ID: f2a8b95c1d3e
Revises: e1c7f83a9d2b
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'f2a8b95c1d3e'
down_revision: Union[str, Sequence[str], None] = 'e1c7f83a9d2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_constraint("players_user_id_fkey", type_="foreignkey")
        batch_op.alter_column("user_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(), nullable=False)
        batch_op.create_foreign_key(
            "players_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
