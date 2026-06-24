"""Bootstrap Alembic version tracking for DBs created before Alembic was set up.

If `alembic_version` doesn't exist yet, stamps the DB at the initial revision
so `alembic upgrade head` only applies the *new* migrations.
On a fresh DB (no tables at all) this is a no-op and `alembic upgrade head`
runs all migrations from scratch as normal.
"""
import os
import sys

from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("DATABASE_URL not set, skipping bootstrap", file=sys.stderr)
    sys.exit(0)

# Alembic env.py strips asyncpg; do the same here for the sync check.
sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

INITIAL_REVISION = "c24b8d2842c1"

engine = create_engine(sync_url)
try:
    with engine.connect() as conn:
        existing = inspect(engine).get_table_names()

        if "alembic_version" in existing:
            print("alembic_version already exists — nothing to bootstrap")
            sys.exit(0)

        if "users" not in existing:
            # Fresh DB: let alembic upgrade head do everything from scratch.
            print("Fresh DB detected — alembic upgrade head will run all migrations")
            sys.exit(0)

        # DB has tables but no version tracking: stamp at initial revision so
        # upgrade head only applies the new migrations.
        conn.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"
            )
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
            {"rev": INITIAL_REVISION},
        )
        conn.commit()
        print(f"Bootstrapped alembic_version at {INITIAL_REVISION}")
finally:
    engine.dispose()
