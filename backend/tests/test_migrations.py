"""Alembic migrations run on a clean database and produce the expected schema."""

import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.db.migrate import run_migrations


def test_migrations_build_the_full_schema_on_a_clean_database():
    workdir = tempfile.mkdtemp(prefix="firstrupee-migrate-")
    url = f"sqlite:///{Path(workdir) / 'clean.db'}"
    run_migrations(url)
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    expected = {"users", "auth_sessions", "investor_profiles", "profile_debts", "readiness_results", "assets",
                "market_observations", "evidence_sources", "research_analyses", "simulation_results", "decision_passports"}
    assert expected <= tables
    engine.dispose()


def test_migrations_are_idempotent():
    workdir = tempfile.mkdtemp(prefix="firstrupee-migrate-")
    url = f"sqlite:///{Path(workdir) / 'twice.db'}"
    run_migrations(url)
    run_migrations(url)
