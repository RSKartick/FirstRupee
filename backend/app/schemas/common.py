"""Shared validated types.

Money and percentages are accepted as strings or numbers, parsed with Decimal (never binary float), checked for finiteness,
sign, precision and magnitude, and serialised back to JSON as fixed two-decimal strings.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import BeforeValidator, PlainSerializer

MAX_AMOUNT = Decimal("100000000000")  # ₹10,000 crore: an upper bound for any single field


def _bounded_decimal(lower: Decimal, upper: Decimal, places: int, label: str) -> Callable[[Any], Decimal]:
    quantum = Decimal(1).scaleb(-places)

    def _validate(value: Any) -> Decimal:
        if isinstance(value, bool):
            raise ValueError(f"{label} must be a number")
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(f"{label} must be a finite number")
            value = repr(value)
        if isinstance(value, int):
            value = str(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "").replace("₹", "")
            if cleaned == "":
                raise ValueError(f"{label} is required")
            try:
                parsed = Decimal(cleaned)
            except InvalidOperation as exc:
                raise ValueError(f"{label} must be a valid number") from exc
        elif isinstance(value, Decimal):
            parsed = value
        else:
            raise ValueError(f"{label} must be a number")
        if not parsed.is_finite():
            raise ValueError(f"{label} must be a finite number")
        if abs(parsed) > upper:
            raise ValueError(f"{label} exceeds the supported maximum")
        if parsed < lower:
            raise ValueError(f"{label} must be {lower} or more")
        if parsed != parsed.quantize(quantum):
            raise ValueError(f"{label} allows at most {places} decimal places")
        return parsed.quantize(quantum)

    return _validate


def _serialise_money(value: Decimal) -> str:
    return f"{value:.2f}"


Money = Annotated[
    Decimal,
    BeforeValidator(_bounded_decimal(Decimal("0"), MAX_AMOUNT, 2, "Amount")),
    PlainSerializer(_serialise_money, return_type=str, when_used="json"),
]

Pct = Annotated[
    Decimal,
    BeforeValidator(_bounded_decimal(Decimal("0"), Decimal("100"), 2, "Percentage")),
    PlainSerializer(_serialise_money, return_type=str, when_used="json"),
]
