import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool


def database_engine():
    url = make_url(os.getenv("DATABASE_URL", "postgresql://helpdesk@localhost:5432/helpdesk"))
    if url.drivername in {"postgresql", "postgres"}:
        url = url.set(drivername="postgresql+psycopg")
    pool_mode = os.getenv("DB_POOL_MODE", "session")
    if pool_mode not in {"session", "transaction"}:
        raise ValueError("DB_POOL_MODE must be session or transaction.")
    if url.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must point to PostgreSQL.")
    connect_args = {"connect_timeout": 5}
    if pool_mode == "transaction":
        return create_engine(
            url, poolclass=NullPool, connect_args={**connect_args, "prepare_threshold": None}
        )
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, connect_args=connect_args)


engine = database_engine()


def get_db() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
