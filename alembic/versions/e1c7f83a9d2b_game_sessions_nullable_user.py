"""game_sessions nullable user_id no fk

Revision ID: e1c7f83a9d2b
Revises: b7e2a14f3c90
Create Date: 2026-06-24
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'e1c7f83a9d2b'
down_revision: Union[str, Sequence[str], None] = 'b7e2a14f3c90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE game_sessions DROP CONSTRAINT IF EXISTS game_sessions_user_id_fkey")
    op.execute("ALTER TABLE game_sessions ALTER COLUMN user_id DROP NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE game_sessions ALTER COLUMN user_id SET NOT NULL")
    op.execute(
        "ALTER TABLE game_sessions ADD CONSTRAINT game_sessions_user_id_fkey "
        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
    )
