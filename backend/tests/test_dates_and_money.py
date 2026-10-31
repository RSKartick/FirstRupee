from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.profile import ProfileIn
from app.services.financial_engine.dates import add_months, months_until
from app.services.financial_engine.money import fmt_inr, safe_div, dstr


@pytest.mark.parametrize("start,months,expected", [
    (date(2026, 1, 31), 1, date(2026, 2, 28)),
    (date(2024, 1, 31), 1, date(2024, 2, 29)),        # leap year
    (date(2024, 2, 29), 12, date(2025, 2, 28)),       # leap day rolls to 28 Feb
    (date(2026, 12, 31), 1, date(2027, 1, 31)),       # year boundary
    (date(2026, 11, 30), -1, date(2026, 10, 30)),
])
def test_add_months_clamps_to_month_end(start, months, expected):
    assert add_months(start, months) == expected


@pytest.mark.parametrize("as_of,target,expected", [
    (date(2026, 10, 31), date(2026, 10, 31), 0),      # same day: due today
    (date(2026, 10, 31), date(2026, 11, 1), 0),       # next day: less than one whole month
    (date(2026, 10, 31), date(2026, 11, 29), 0),      # month boundary, not yet a full month
    (date(2026, 10, 31), date(2026, 11, 30), 1),      # month-end clamp counts as a full month
    (date(2026, 12, 31), date(2027, 12, 31), 12),     # year boundary, full year
    (date(2024, 2, 29), date(2025, 2, 28), 12),       # leap year to non-leap year
    (date(2026, 10, 31), date(2027, 8, 31), 10),      # Rahul's 10-month goal
])
def test_months_until_whole_calendar_months(as_of, target, expected):
    assert months_until(as_of, target) == expected


def test_expired_by_one_day_is_recognised_as_past():
    # Previous day must be negative, not zero: a deadline passed yesterday is not "due today".
    assert months_until(date(2027, 1, 1), date(2026, 12, 31)) < 0


def test_expired_by_a_year_is_negative():
    assert months_until(date(2027, 10, 31), date(2026, 10, 31)) == -12


def test_indian_grouping_and_signs():
    assert fmt_inr(Decimal("1234567")) == "₹12,34,567"
    assert fmt_inr(Decimal("30000")) == "₹30,000"
    assert fmt_inr(Decimal("-4000")) == "-₹4,000"
    assert fmt_inr(Decimal("1234.5")) == "₹1,234.50"


def test_unknown_division_returns_none_not_infinity():
    assert safe_div(Decimal("5"), Decimal("0")) is None
    assert dstr(Decimal("10")) == "10.00"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "abc", "-5", "1000.123", "1e20", True])
def test_money_rejects_invalid_values(bad):
    payload = {
        "display_name": "Tester", "age_range": "TWENTY_TO_THIRTY", "employment_status": "SALARIED",
        "monthly_income": bad, "essential_expenses": "1000", "total_savings": "1000", "liquid_savings": "1000",
        "investment_experience": "BEGINNER",
    }
    with pytest.raises(ValidationError):
        ProfileIn.model_validate(payload)


def test_money_accepts_grouped_strings_and_serialises_fixed_point():
    data = ProfileIn.model_validate({
        "display_name": "Tester", "age_range": "TWENTY_TO_THIRTY", "employment_status": "SALARIED",
        "monthly_income": "30,000", "essential_expenses": 20000.5, "total_savings": "1000", "liquid_savings": "1000",
        "investment_experience": "BEGINNER",
    })
    assert data.monthly_income == Decimal("30000.00")
    assert data.model_dump(mode="json")["essential_expenses"] == "20000.50"
