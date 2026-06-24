"""game_sessions nullable user_id no fk

Revision ID: e1c7f83a9d2b
Revises: b7e2a14f3c90
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'e1c7f83a9d2b'
down_revision: Union[str, Sequence[str], None] = 'b7e2a14f3c90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("game_sessions") as batch_op:
        batch_op.drop_constraint("game_sessions_user_id_fkey", type_="foreignkey")
        batch_op.alter_column("user_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("game_sessions") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(), nullable=False)
        batch_op.create_foreign_key(
            "game_sessions_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
