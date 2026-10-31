"""Readiness, timing, research, simulator, passport and assistant endpoints (all owner-scoped)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import csrf_protected, current_user, database, reference_date
from app.core.errors import NotFoundError
from app.models.tables import User
from app.repositories import owned as repo
from app.schemas.analysis import ChatRequest, PassportRequest, ResearchRequest, SimulationRequest, TimingRequest
from app.services import workflow

readiness_router = APIRouter(prefix="/readiness", tags=["readiness"])
timing_router = APIRouter(prefix="/timing", tags=["timing"])
research_router = APIRouter(prefix="/research", tags=["research"])
simulator_router = APIRouter(prefix="/simulator", tags=["simulator"])
passport_router = APIRouter(prefix="/passport", tags=["passport"])
assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])


@readiness_router.post("/analyze", dependencies=[Depends(csrf_protected)])
def analyze_readiness(body: dict[str, Any], user: User = Depends(current_user), db: Session = Depends(database),
                      as_of: date = Depends(reference_date)) -> dict[str, Any]:
    profile_id = int(body.get("profile_id", 0))
    row = workflow.get_owned_profile(db, user, profile_id)
    return {"readiness": workflow.readiness_for(db, row, as_of)}


@readiness_router.get("/{profile_id}")
def get_readiness(profile_id: int, user: User = Depends(current_user), db: Session = Depends(database),
                  as_of: date = Depends(reference_date)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, profile_id)
    return {"readiness": workflow.readiness_for(db, row, as_of)}


@timing_router.post("/analyze", dependencies=[Depends(csrf_protected)])
def analyze_timing(body: TimingRequest, user: User = Depends(current_user), db: Session = Depends(database),
                   as_of: date = Depends(reference_date)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, body.profile_id)
    return workflow.timing_for(db, user, row, body.asset_id, as_of)


@research_router.post("/analyze", status_code=201, dependencies=[Depends(csrf_protected)])
def analyze_research(body: ResearchRequest, user: User = Depends(current_user), db: Session = Depends(database),
                     as_of: date = Depends(reference_date)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, body.profile_id)
    return {"analysis": workflow.research_for(db, user, row, body.asset_id, as_of)}


@research_router.get("/profile/{profile_id}")
def list_research(profile_id: int, user: User = Depends(current_user), db: Session = Depends(database)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, profile_id)
    items = repo.list_research(db, user.id, row.id)
    return {"analyses": [
        {"id": r.id, "asset_id": r.asset_id, "asset_name": r.result["asset"]["name"], "evaluator_status": r.evaluator_status,
         "created_at": r.created_at.isoformat()}
        for r in items
    ]}


@research_router.get("/{analysis_id}")
def get_research(analysis_id: int, user: User = Depends(current_user), db: Session = Depends(database)) -> dict[str, Any]:
    row = repo.get_research(db, user.id, analysis_id)
    if row is None:
        raise NotFoundError("Research analysis not found.")
    return {"analysis": dict(row.result) | {"analysis_id": row.id, "created_at": row.created_at.isoformat()}}


@simulator_router.post("/run", status_code=201, dependencies=[Depends(csrf_protected)])
def run_simulator(body: SimulationRequest, user: User = Depends(current_user), db: Session = Depends(database),
                  as_of: date = Depends(reference_date)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, body.profile_id) if body.profile_id is not None else None
    return {"simulation": workflow.simulate_for(db, user, row, body, as_of)}


@simulator_router.get("/{simulation_id}")
def get_simulation(simulation_id: int, user: User = Depends(current_user), db: Session = Depends(database)) -> dict[str, Any]:
    row = repo.get_simulation(db, user.id, simulation_id)
    if row is None:
        raise NotFoundError("Simulation not found.")
    return {"simulation": row.result}


@passport_router.post("/generate", status_code=201, dependencies=[Depends(csrf_protected)])
def generate_passport(body: PassportRequest, user: User = Depends(current_user), db: Session = Depends(database),
                      as_of: date = Depends(reference_date)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, body.profile_id)
    return {"passport": workflow.generate_passport(db, user, row, body, as_of)}


@passport_router.get("/profile/{profile_id}")
def list_passports(profile_id: int, user: User = Depends(current_user), db: Session = Depends(database)) -> dict[str, Any]:
    row = workflow.get_owned_profile(db, user, profile_id)
    return {"passports": [workflow.passport_summary(p) for p in repo.list_passports(db, user.id, row.id)]}


@passport_router.get("/{passport_id}")
def get_passport(passport_id: int, user: User = Depends(current_user), db: Session = Depends(database)) -> dict[str, Any]:
    row = repo.get_passport(db, user.id, passport_id)
    if row is None:
        raise NotFoundError("Decision Passport not found.")
    return {"passport": row.snapshot}


@assistant_router.post("/chat", dependencies=[Depends(csrf_protected)])
def chat(body: ChatRequest, user: User = Depends(current_user), db: Session = Depends(database),
         as_of: date = Depends(reference_date)) -> dict[str, Any]:
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    return workflow.assistant_for(db, user, body.profile_id, messages, as_of)
