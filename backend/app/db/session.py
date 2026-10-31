"""Engine and session factory. SQLite is the default; any SQLAlchemy URL (for example PostgreSQL) can be supplied via DATABASE_URL."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def resolve_database_url(url: str) -> str:
    """Relative SQLite paths are anchored to the backend directory so the working directory never matters."""
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        database = parsed.database or ""
        if database and database != ":memory:" and not Path(database).is_absolute():
            absolute = (BACKEND_ROOT / database).resolve()
            absolute.parent.mkdir(parents=True, exist_ok=True)
            parsed = parsed.set(database=str(absolute))
    return parsed.render_as_string(hide_password=False)


def build_engine(url: str | None = None) -> Engine:
    resolved = resolve_database_url(url or get_settings().database_url)
    is_sqlite = resolved.startswith("sqlite")
    engine = create_engine(
        resolved,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
