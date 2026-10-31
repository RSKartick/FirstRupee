"""Test configuration: a fresh SQLite file per test session, no LLM provider, and a pinned reference date (2026-10-31)."""

from __future__ import annotations

import os
import tempfile
from datetime import date

_TMP = tempfile.mkdtemp(prefix="firstrupee-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["LLM_PROVIDER"] = "none"
os.environ["LLM_API_KEY"] = ""
os.environ["COOKIE_SECURE"] = "false"
os.environ["FIRSTRUPEE_OFFLINE_SEED"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import reference_date  # noqa: E402
from app.main import create_app  # noqa: E402

REFERENCE_DATE = date(2026, 10, 31)


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.dependency_overrides[reference_date] = lambda: REFERENCE_DATE
    return application


@pytest.fixture(scope="session")
def base_client(app):
    """Runs start-up (migrations + seeding) exactly once for the session."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def _application_started(base_client):
    """Every test session runs migrations and seeding once, even when a test does not request a client fixture."""
    yield


@pytest.fixture()
def new_client(app, base_client):
    """A client with its own cookie jar; the application is already started."""
    return TestClient(app)
