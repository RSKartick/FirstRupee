"""Runs Alembic migrations to head. Used at application start-up and by the migration test on a clean database."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.session import BACKEND_ROOT, resolve_database_url

_STARTUP_LOCK_ID = 5066622619342907461


@contextmanager
def database_startup_lock(database_url: str | None = None) -> Iterator[None]:
    """Serialize schema migration and catalogue seeding across simultaneous API cold starts."""
    resolved = resolve_database_url(database_url or get_settings().database_url)
    if make_url(resolved).get_backend_name() != "postgresql":
        yield
        return

    lock_engine = create_engine(resolved, poolclass=NullPool)
    try:
        with lock_engine.begin() as connection:
            connection.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": _STARTUP_LOCK_ID})
            yield
    finally:
        lock_engine.dispose()


def run_migrations(database_url: str | None = None) -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.attributes["database_url"] = database_url or resolve_database_url(get_settings().database_url)
    command.upgrade(config, "head")
