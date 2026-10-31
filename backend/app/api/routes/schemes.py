"""Indian Government & Statutory Investment Schemes API Endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_user, database
from app.core.errors import NotFoundError
from app.models.tables import User
from app.services import workflow
from app.services.schemes import (
    SCHEMES,
    calculate_scheme_growth,
    evaluate_profile_fit,
    get_all_schemes,
    get_scheme_by_id,
)

schemes_router = APIRouter(prefix="/schemes", tags=["schemes"])


class SchemeCalculateRequest(BaseModel):
    scheme_id: str
    monthly_deposit: float = Field(default=0.0, ge=0.0)
    lump_sum: float = Field(default=0.0, ge=0.0)
    horizon_years: int | None = Field(default=None, ge=1, le=50)
    tax_bracket_pct: float = Field(default=30.0, ge=0.0, le=50.0)


@schemes_router.get("")
def list_schemes(category: str | None = Query(default=None)) -> dict[str, Any]:
    items = get_all_schemes(category)
    return {
        "schemes": [s.to_dict() for s in items],
        "count": len(items),
        "total": len(SCHEMES),
    }


@schemes_router.get("/{scheme_id}")
def get_scheme(scheme_id: str) -> dict[str, Any]:
    scheme = get_scheme_by_id(scheme_id)
    if scheme is None:
        raise NotFoundError(f"Scheme '{scheme_id}' was not found in catalog.")
    return {"scheme": scheme.to_dict()}


@schemes_router.post("/calculate")
def calculate_growth(body: SchemeCalculateRequest) -> dict[str, Any]:
    try:
        result = calculate_scheme_growth(
            scheme_id=body.scheme_id,
            monthly_deposit=body.monthly_deposit,
            lump_sum=body.lump_sum,
            horizon_years=body.horizon_years,
            tax_bracket_pct=body.tax_bracket_pct,
        )
        return {"calculation": result}
    except ValueError as err:
        raise NotFoundError(str(err))


@schemes_router.get("/profile/{profile_id}")
def evaluate_for_profile(
    profile_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(database),
) -> dict[str, Any]:
    profile_row = workflow.get_owned_profile(db, user, profile_id)
    profile_data = {
        "id": profile_row.id,
        "display_name": profile_row.display_name,
        "monthly_income": float(profile_row.monthly_income or 0),
        "monthly_expenses": float(profile_row.essential_expenses or 0) + float(profile_row.discretionary_expenses or 0),
        "monthly_surplus": float(profile_row.monthly_income or 0) - (float(profile_row.essential_expenses or 0) + float(profile_row.discretionary_expenses or 0)),
        "goal_horizon_months": profile_row.goal_horizon_months,
        "goal_name": profile_row.goal_name,
        "goal_target_amount": float(profile_row.goal_target_amount or 0),
        "investment_experience": profile_row.investment_experience,
    }

    evaluations = evaluate_profile_fit(profile_data)
    return {
        "profile_id": profile_id,
        "display_name": profile_row.display_name,
        "evaluations": evaluations,
    }
