"""Clock helpers. Persisted timestamps are naive UTC. Deterministic engines never call these directly:
the reference date is injected through the `reference_date` dependency so every calculation can be reproduced."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def utc_today() -> date:
    return datetime.now(UTC).date()


def ist_today() -> date:
    """Current calendar date in Indian Standard Time (Asia/Kolkata, UTC+05:30)."""
    return datetime.now(IST).date()
