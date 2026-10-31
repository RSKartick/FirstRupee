"""Alembic environment. The database URL comes from the application settings (or from the caller via config.attributes),
so the same migrations run against SQLite and PostgreSQL. Batch mode is enabled so SQLite can alter tables."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, pool

import app.db.types  # noqa: F401  (registers the custom decimal type for autogenerate)
import app.models.tables  # noqa: F401  (registers every model on Base.metadata)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import resolve_database_url

config = context.config
database_url = config.attributes.get("database_url") or resolve_database_url(get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=database_url, target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, poolclass=pool.NullPool, connect_args=connect_args)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
