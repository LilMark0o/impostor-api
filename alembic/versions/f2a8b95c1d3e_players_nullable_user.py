"""players nullable user_id no fk

Revision ID: f2a8b95c1d3e
Revises: e1c7f83a9d2b
Create Date: 2026-06-24
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'f2a8b95c1d3e'
down_revision: Union[str, Sequence[str], None] = 'e1c7f83a9d2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL so IF EXISTS makes this idempotent regardless of constraint name.
    op.execute("ALTER TABLE players DROP CONSTRAINT IF EXISTS players_user_id_fkey")
    op.execute("ALTER TABLE players ALTER COLUMN user_id DROP NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE players ALTER COLUMN user_id SET NOT NULL")
    op.execute(
        "ALTER TABLE players ADD CONSTRAINT players_user_id_fkey "
        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
    )
