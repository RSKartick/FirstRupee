"""Runs Alembic migrations to head. Used at application start-up and by the migration test on a clean database."""

from __future__ import annotations

from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.db.session import BACKEND_ROOT, resolve_database_url


def run_migrations(database_url: str | None = None) -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.attributes["database_url"] = database_url or resolve_database_url(get_settings().database_url)
    command.upgrade(config, "head")
