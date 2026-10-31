"""Clock helpers. Persisted timestamps are naive UTC. Deterministic engines never call these directly:
the reference date is injected through the `reference_date` dependency so every calculation can be reproduced."""

from __future__ import annotations

from datetime import UTC, date, datetime


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def utc_today() -> date:
    return datetime.now(UTC).date()
