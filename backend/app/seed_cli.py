"""Explicit CLI for bootstrapping or refreshing public market observations."""

from __future__ import annotations

import argparse
import os

from app.db.migrate import database_startup_lock, run_migrations, schema_is_at_head
from app.db.session import SessionLocal
from app.seed import seed_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the public market catalogue.")
    parser.add_argument("--live", action="store_true", required=True, help="Fetch market data from live public providers.")
    parser.parse_args()

    os.environ.pop("FIRSTRUPEE_OFFLINE_SEED", None)
    with database_startup_lock():
        run_migrations()
        if not schema_is_at_head():
            raise SystemExit("Database schema is not at the current Alembic head; catalogue refresh was skipped.")
        with SessionLocal() as session:
            seed_catalog(session)


if __name__ == "__main__":
    main()
