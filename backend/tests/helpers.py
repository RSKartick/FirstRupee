"""HTTP helpers for API tests."""

from __future__ import annotations

from typing import Any


def register(client, email: str, password: str = "correct-horse-battery", name: str = "Tester") -> str:
    response = client.post("/api/auth/register", json={"email": email, "password": password, "display_name": name})
    assert response.status_code == 201, response.text
    return response.json()["csrf_token"]


def csrf(client) -> dict[str, str]:
    token = client.get("/api/auth/me").json()["csrf_token"]
    assert token, "client is not authenticated"
    return {"X-CSRF-Token": token}


def profile_payload(display_name: str = "Tester", **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "display_name": display_name,
        "age_range": "TWENTY_TO_THIRTY",
        "employment_status": "SALARIED",
        "monthly_income": "60000.00",
        "essential_expenses": "25000.00",
        "nonessential_expenses": "5000.00",
        "monthly_emi": "5000.00",
        "other_commitments": "0.00",
        "total_savings": "400000.00",
        "liquid_savings": "300000.00",
        "emergency_reserves": "150000.00",
        "goal_reserved_amount": "20000.00",
        "current_investments": "0.00",
        "existing_liabilities": "0.00",
        "monthly_investment_designated": "0.00",
        "debts": [],
        "investment_experience": "BEGINNER",
        "goal_name": None,
        "goal_category": None,
        "goal_amount": None,
        "goal_deadline": None,
        "goal_importance": None,
        "goal_liquidity": "LOW",
        "questionnaire": {
            "drawdown_reaction": "REASSESS_THESIS",
            "preferred_horizon": "OVER_SEVEN_YEARS",
            "gains_reaction": "KEEP_PLAN",
            "loss_impact_on_expenses": "NO_IMPACT",
            "income_stability": "VERY_STABLE",
        },
    }
    payload.update(overrides)
    return payload
