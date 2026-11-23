import os

from alembic import context

from app.database import engine


if not os.getenv("DATABASE_URL"):
    raise RuntimeError("Set DATABASE_URL to the reviewed migration target before running Alembic.")

with engine.connect() as connection:
    context.configure(
        connection=connection,
        version_table="helpdesk_alembic_version",
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()
