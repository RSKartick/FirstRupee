"""Calendar arithmetic used by every deterministic engine. Every function takes an explicit reference date; none reads the clock."""

from __future__ import annotations

import calendar
from datetime import date


def add_months(d: date, months: int) -> date:
    """Add calendar months, clamping the day to the target month's last day (31 Jan + 1 month = 28/29 Feb)."""
    index = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(index, 12)
    month = month0 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _complete_months(start: date, end: date) -> int:
    """Largest n >= 0 such that add_months(start, n) <= end."""
    n = (end.year - start.year) * 12 + (end.month - start.month)
    while n > 0 and add_months(start, n) > end:
        n -= 1
    return max(n, 0)


def months_until(as_of: date, target: date) -> int:
    """Whole calendar months from `as_of` to `target`.

    * target later than as_of  -> positive whole months (a partial month does not count).
    * target equal to as_of    -> 0 (due today).
    * target earlier than as_of -> negative (at least -1), so a deadline that passed yesterday is still recognised as passed.
    """
    if target >= as_of:
        return _complete_months(as_of, target)
    return -max(1, _complete_months(target, as_of))

