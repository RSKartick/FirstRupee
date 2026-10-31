"""Deterministic test fixtures for the financial engines (no database)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.services.financial_engine.dates import add_months
from app.services.financial_engine.money import D
from app.services.financial_engine.readiness import DebtItem, FinancialProfile

AS_OF = date(2026, 10, 31)
GOOD_QUESTIONNAIRE: dict[str, str] = {
    "drawdown_reaction": "REASSESS_THESIS",
    "preferred_horizon": "OVER_SEVEN_YEARS",
    "gains_reaction": "KEEP_PLAN",
    "loss_impact_on_expenses": "NO_IMPACT",
    "income_stability": "VERY_STABLE",
}


def healthy(**overrides: Any) -> FinancialProfile:
    """A complete, positive profile that classifies READY_TO_EXPLORE. Coverage is exactly 6 months."""
    data: dict[str, Any] = dict(
        income=D("60000"), essential=D("25000"), nonessential=D("5000"), emi=D("5000"), other=D("0"),
        total_savings=D("400000"), liquid=D("300000"), emergency=D("150000"), goal_reserved=D("20000"),
        current_investments=D("0"), liabilities=D("0"), designated=D("0"), employment_status="SALARIED",
        experience="BEGINNER", goal_name=None, goal_amount=None, goal_deadline=None, goal_liquidity="LOW",
        goal_importance=None, questionnaire=dict(GOOD_QUESTIONNAIRE), debts=(), profile_id=1,
    )
    data.update(overrides)
    return FinancialProfile(**data)


def rahul(as_of: date = AS_OF) -> FinancialProfile:
    """Fictional demo investor: 10-month goal, ₹4,000 surplus, one month of essentials in the emergency reserve."""
    return FinancialProfile(
        income=D("30000"), essential=D("20000"), nonessential=D("2000"), emi=D("4000"), other=D("0"),
        total_savings=D("30000"), liquid=D("25000"), emergency=D("20000"), goal_reserved=D("5000"),
        current_investments=D("0"), liabilities=D("60000"), designated=D("0"), employment_status="SALARIED",
        experience="BEGINNER", goal_name="Laptop and relocation fund", goal_amount=D("50000"),
        goal_deadline=add_months(as_of, 10), goal_liquidity="HIGH", goal_importance="HIGH",
        questionnaire={"drawdown_reaction": "WAIT", "preferred_horizon": "UNDER_1_YEAR", "gains_reaction": "KEEP_PLAN",
                       "loss_impact_on_expenses": "AFFECTS_ESSENTIALS", "income_stability": "SOMEWHAT_STABLE"},
        debts=(DebtItem("PERSONAL_LOAN", D("60000"), D("14"), D("4000"), 18, False),),
        profile_id=101,
    )


def priya(as_of: date = AS_OF) -> FinancialProfile:
    """Fictional demo investor: 120-month goal, ₹40,000 surplus, ₹15,000 designated monthly."""
    return FinancialProfile(
        income=D("80000"), essential=D("30000"), nonessential=D("5000"), emi=D("5000"), other=D("0"),
        total_savings=D("300000"), liquid=D("280000"), emergency=D("250000"), goal_reserved=D("30000"),
        current_investments=D("0"), liabilities=D("400000"), designated=D("15000"), employment_status="SALARIED",
        experience="BEGINNER", goal_name="Long-term wealth creation", goal_amount=D("2500000"),
        goal_deadline=add_months(as_of, 120), goal_liquidity="LOW", goal_importance="HIGH",
        questionnaire={"drawdown_reaction": "REASSESS_THESIS", "preferred_horizon": "OVER_SEVEN_YEARS",
                       "gains_reaction": "KEEP_PLAN", "loss_impact_on_expenses": "NO_IMPACT",
                       "income_stability": "VERY_STABLE"},
        debts=(DebtItem("CAR_LOAN", D("400000"), D("9.5"), D("5000"), 96, False),),
        profile_id=102,
    )


def priced_series_points(start: date, end: date, price_fn) -> list[tuple[date, Decimal]]:
    """Calendar-daily observations; price_fn(day_index, day) -> float."""
    from datetime import timedelta

    out: list[tuple[date, Decimal]] = []
    day = start
    index = 0
    while day <= end:
        out.append((day, Decimal(f"{price_fn(index, day):.4f}")))
        day += timedelta(days=1)
        index += 1
    return out
