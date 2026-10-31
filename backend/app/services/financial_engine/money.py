"""Exact decimal helpers. Engines receive Decimal values and only emit fixed-point strings. No binary floating point is used for money."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

CENT = Decimal("0.01")
ZERO = Decimal("0")


def D(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise TypeError("Engines accept Decimal values only; convert via strings.")
    return Decimal(str(value))


def q2(value: Any) -> Decimal:
    return D(value).quantize(CENT, rounding=ROUND_HALF_UP)


def safe_div(numerator: Any, denominator: Any) -> Decimal | None:
    """Division that returns None (unknown) instead of raising or returning infinity."""
    den = D(denominator)
    if den == 0:
        return None
    return D(numerator) / den


def dstr(value: Any) -> str | None:
    if value is None:
        return None
    return f"{q2(value):.2f}"


def plain(value: Any) -> Any:
    """Convert engine values to JSON-safe primitives."""
    if isinstance(value, Decimal):
        return dstr(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [plain(v) for v in value]
    return value


def _group_indian(whole: str) -> str:
    if len(whole) <= 3:
        return whole
    head, tail = whole[:-3], whole[-3:]
    parts: list[str] = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def fmt_inr(value: Any) -> str:
    """Indian digit grouping, e.g. 1234567 -> ₹12,34,567."""
    if value is None:
        return "n/a"
    amount = q2(value)
    sign = "-" if amount < 0 else ""
    whole, frac = f"{abs(amount):.2f}".split(".")
    suffix = "" if frac == "00" else f".{frac}"
    return f"{sign}₹{_group_indian(whole)}{suffix}"
