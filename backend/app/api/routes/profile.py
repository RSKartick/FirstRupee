from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import csrf_protected, current_user, database, reference_date
from app.models.tables import InvestorProfile, User
from app.repositories import owned as repo
from app.schemas.profile import ProfileIn
from app.services import workflow

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def list_profiles(user: User = Depends(current_user), db: Session = Depends(database)) -> dict[str, Any]:
    rows = repo.list_profiles(db, user.id)
    return {"profiles": [
        {"id": r.id, "display_name": r.display_name, "monthly_income": f"{r.monthly_income:.2f}", "goal_name": r.goal_name,
         "is_demo_clone": r.is_demo_clone, "updated_at": r.updated_at.isoformat()}
        for r in rows
    ]}


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(csrf_protected)])
def create_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(database),
                   as_of: date = Depends(reference_date)) -> dict[str, Any]:
    workflow.validate_goal_date(body.goal_deadline, as_of)
    row = InvestorProfile(user_id=user.id, display_name=body.display_name, age_range=body.age_range,
                          employment_status=body.employment_status, monthly_income=body.monthly_income,
                          essential_expenses=body.essential_expenses, total_savings=body.total_savings,
                          liquid_savings=body.liquid_savings, investment_experience=body.investment_experience)
    workflow.apply_profile_input(row, body)
    db.add(row)
    db.commit()
    readiness = workflow.readiness_for(db, row, as_of)
    return {"profile": workflow.profile_out(row), "readiness": readiness}


@router.get("/{profile_id}")
def get_profile(profile_id: int, user: User = Depends(current_user), db: Session = Depends(database)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, profile_id)
    return {"profile": workflow.profile_out(row)}


@router.put("/{profile_id}", dependencies=[Depends(csrf_protected)])
def update_profile(profile_id: int, body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(database),
                   as_of: date = Depends(reference_date)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, profile_id)
    workflow.validate_goal_date(body.goal_deadline, as_of)
    workflow.apply_profile_input(row, body)
    db.commit()
    readiness = workflow.readiness_for(db, row, as_of)
    return {"profile": workflow.profile_out(row), "readiness": readiness}


@router.delete("/{profile_id}", dependencies=[Depends(csrf_protected)])
def delete_profile(profile_id: int, user: User = Depends(current_user), db: Session = Depends(database)) -> Response:
    row = workflow.get_owned_profile(db, user, profile_id)
    db.delete(row)  # cascades to debts, readiness, research, simulations and passports
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
