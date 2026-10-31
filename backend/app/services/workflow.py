"""Orchestration. Routes stay thin: they authenticate, validate ownership and call one function here.
Each function is owner-scoped and persists a reproducible snapshot where the product requires one."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.clock import utcnow
from app.core.errors import NotFoundError, ValidationProblem
from app.data_sources.demo_catalog import DEMO_PROFILES
from app.data_sources.provider import get_provider
from app.models.tables import (
    Asset,
    DecisionPassportRow,
    InvestorProfile,
    ProfileDebt,
    ReadinessResultRow,
    ResearchAnalysisRow,
    SimulationRow,
    User,
)
from app.repositories import owned as repo
from app.schemas.profile import ProfileIn, ProfileOut
from app.services.ai_engine import assistant as assistant_engine
from app.services.ai_engine.evaluator import evaluate
from app.services.ai_engine.research import run_research
from app.services.financial_engine.dates import add_months
from app.services.financial_engine.market import market_snapshot
from app.services.financial_engine.money import D
from app.services.financial_engine.readiness import DebtItem, FinancialProfile, assess_readiness
from app.services.financial_engine.rules import (
    EVALUATOR_VERSION,
    PROMPT_VERSION,
    READINESS_RULE_VERSION,
    SIMULATOR_VERSION,
    TIMING_RULE_VERSION,
)
from app.services.financial_engine.timing import assess_timing
from app.services.passport.composer import compose
from app.services.simulator.engine import AssetSeries, SimulationError, run_simulation

MAX_GOAL_YEARS = 100


# --------------------------------------------------------------------------- profiles

def get_owned_profile(db: Session, user: User, profile_id: int) -> InvestorProfile:
    row = repo.get_profile(db, user.id, profile_id)
    if row is None:
        raise NotFoundError("Investor profile not found.")
    return row


def validate_goal_date(deadline: date | None, as_of: date) -> None:
    if deadline is None:
        return
    if deadline < as_of:
        raise ValidationProblem("The goal deadline is in the past. Enter a future date so the horizon can be assessed.")
    if deadline > add_months(as_of, MAX_GOAL_YEARS * 12):
        raise ValidationProblem(f"The goal deadline is more than {MAX_GOAL_YEARS} years away.")


def apply_profile_input(row: InvestorProfile, data: ProfileIn) -> None:
    row.display_name = data.display_name
    row.age_range = data.age_range
    row.employment_status = data.employment_status
    row.monthly_income = data.monthly_income
    row.essential_expenses = data.essential_expenses
    row.nonessential_expenses = data.nonessential_expenses
    row.monthly_emi = data.monthly_emi
    row.other_commitments = data.other_commitments
    row.total_savings = data.total_savings
    row.liquid_savings = data.liquid_savings
    row.emergency_reserves = data.emergency_reserves
    row.goal_reserved_amount = data.goal_reserved_amount
    row.current_investments = data.current_investments
    row.existing_liabilities = data.existing_liabilities
    row.monthly_investment_designated = data.monthly_investment_designated
    row.investment_experience = data.investment_experience
    row.goal_name = data.goal_name
    row.goal_category = data.goal_category
    row.goal_amount = data.goal_amount
    row.goal_deadline = data.goal_deadline
    row.goal_importance = data.goal_importance
    row.goal_liquidity = data.goal_liquidity
    row.questionnaire = data.questionnaire.model_dump() if data.questionnaire else None
    row.debts = [ProfileDebt(**debt.model_dump()) for debt in data.debts]
    row.updated_at = utcnow()


def profile_out(row: InvestorProfile) -> dict[str, Any]:
    return ProfileOut.model_validate({
        "id": row.id,
        "display_name": row.display_name,
        "age_range": row.age_range,
        "employment_status": row.employment_status,
        "monthly_income": row.monthly_income,
        "essential_expenses": row.essential_expenses,
        "nonessential_expenses": row.nonessential_expenses,
        "monthly_emi": row.monthly_emi,
        "other_commitments": row.other_commitments,
        "total_savings": row.total_savings,
        "liquid_savings": row.liquid_savings,
        "emergency_reserves": row.emergency_reserves,
        "goal_reserved_amount": row.goal_reserved_amount,
        "current_investments": row.current_investments,
        "existing_liabilities": row.existing_liabilities,
        "monthly_investment_designated": row.monthly_investment_designated,
        "debts": [
            {"id": d.id, "debt_type": d.debt_type, "outstanding_amount": d.outstanding_amount,
             "interest_rate_pct": d.interest_rate_pct, "emi_amount": d.emi_amount,
             "remaining_months": d.remaining_months, "is_overdue": d.is_overdue}
            for d in row.debts
        ],
        "investment_experience": row.investment_experience,
        "goal_name": row.goal_name,
        "goal_category": row.goal_category,
        "goal_amount": row.goal_amount,
        "goal_deadline": row.goal_deadline,
        "goal_importance": row.goal_importance,
        "goal_liquidity": row.goal_liquidity,
        "questionnaire": row.questionnaire,
        "is_demo_clone": row.is_demo_clone,
        "demo_key": row.demo_key,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }).model_dump(mode="json")


def financial_from_row(row: InvestorProfile) -> FinancialProfile:
    return FinancialProfile(
        income=D(row.monthly_income),
        essential=D(row.essential_expenses),
        nonessential=D(row.nonessential_expenses),
        emi=D(row.monthly_emi),
        other=D(row.other_commitments),
        total_savings=D(row.total_savings),
        liquid=D(row.liquid_savings),
        emergency=D(row.emergency_reserves),
        goal_reserved=D(row.goal_reserved_amount),
        current_investments=D(row.current_investments),
        liabilities=D(row.existing_liabilities),
        designated=D(row.monthly_investment_designated),
        employment_status=row.employment_status,
        experience=row.investment_experience,
        goal_name=row.goal_name,
        goal_amount=D(row.goal_amount) if row.goal_amount is not None else None,
        goal_deadline=row.goal_deadline,
        goal_liquidity=row.goal_liquidity,
        goal_importance=row.goal_importance,
        questionnaire=dict(row.questionnaire) if row.questionnaire else None,
        debts=tuple(
            DebtItem(debt_type=d.debt_type, outstanding=D(d.outstanding_amount), rate_pct=D(d.interest_rate_pct),
                     emi=D(d.emi_amount), remaining_months=d.remaining_months, is_overdue=d.is_overdue)
            for d in row.debts
        ),
        profile_id=row.id,
    )


def readiness_for(db: Session, row: InvestorProfile, as_of: date) -> dict[str, Any]:
    """Cached result is reused only when rule version, profile timestamp AND reference date all match."""
    cached = repo.latest_readiness(db, row.id)
    if (cached and cached.rule_version == READINESS_RULE_VERSION and cached.profile_updated_at == row.updated_at
            and cached.as_of == as_of):
        return dict(cached.result)
    result = assess_readiness(financial_from_row(row), as_of, row.updated_at.isoformat())
    db.add(ReadinessResultRow(profile_id=row.id, rule_version=READINESS_RULE_VERSION, profile_updated_at=row.updated_at,
                              as_of=as_of, status=result["status"], result=result))
    db.commit()
    return result


# --------------------------------------------------------------------------- demo

def demo_profile_input(key: str, as_of: date) -> ProfileIn:
    if key not in DEMO_PROFILES:
        raise NotFoundError("Demo investor not found.")
    spec = DEMO_PROFILES[key]
    payload = {k: spec[k] for k in (
        "display_name", "age_range", "employment_status", "monthly_income", "essential_expenses", "nonessential_expenses",
        "monthly_emi", "other_commitments", "total_savings", "liquid_savings", "emergency_reserves", "goal_reserved_amount",
        "current_investments", "existing_liabilities", "monthly_investment_designated", "debts", "investment_experience",
        "goal_name", "goal_category", "goal_amount", "goal_importance", "goal_liquidity", "questionnaire")}
    payload["goal_deadline"] = add_months(as_of, spec["goal_horizon_months"])
    return ProfileIn.model_validate(payload)


def clone_demo_profile(db: Session, user: User, key: str, as_of: date) -> InvestorProfile:
    data = demo_profile_input(key, as_of)
    row = InvestorProfile(user_id=user.id, is_demo_clone=True, demo_key=key, monthly_income=data.monthly_income,
                          essential_expenses=data.essential_expenses, total_savings=data.total_savings,
                          liquid_savings=data.liquid_savings, investment_experience=data.investment_experience,
                          display_name=data.display_name, age_range=data.age_range, employment_status=data.employment_status)
    apply_profile_input(row, data)
    row.is_demo_clone = True
    row.demo_key = key
    db.add(row)
    db.commit()
    return row


# --------------------------------------------------------------------------- market and timing

def _asset_series(db: Session, asset: Asset) -> AssetSeries:
    provider = get_provider()
    return AssetSeries(asset_id=asset.id, symbol=asset.symbol, name=asset.name, is_synthetic=asset.is_synthetic,
                       source=asset.data_source, observations=provider.observations(db, asset.id))


def market_for(db: Session, asset: Asset, as_of: date) -> dict[str, Any]:
    series = _asset_series(db, asset)
    return market_snapshot(series.observations, as_of, asset_name=asset.name, is_synthetic=asset.is_synthetic,
                           source=asset.data_source)


def timing_for(db: Session, user: User, row: InvestorProfile, asset_id: int | None, as_of: date) -> dict[str, Any]:
    readiness = readiness_for(db, row, as_of)
    market = None
    if asset_id is not None:
        asset = repo.get_asset(db, asset_id)
        if asset is None:
            raise NotFoundError("Instrument not found.")
        market = market_for(db, asset, as_of)
    timing = assess_timing(financial_from_row(row), readiness, market, as_of)
    return {"timing": timing, "readiness": readiness}


# --------------------------------------------------------------------------- research

def _asset_meta(asset: Asset) -> dict[str, Any]:
    return {"id": asset.id, "symbol": asset.symbol, "name": asset.name, "asset_type": asset.asset_type,
            "description": asset.description, "min_horizon_months": asset.min_horizon_months,
            "is_synthetic": asset.is_synthetic, "data_source": asset.data_source}


def research_for(db: Session, user: User, row: InvestorProfile, asset_id: int, as_of: date) -> dict[str, Any]:
    asset = repo.get_asset(db, asset_id)
    if asset is None:
        raise NotFoundError("Instrument not found.")
    provider = get_provider()
    records = provider.evidence(db, asset.id)
    readiness = readiness_for(db, row, as_of)
    meta = _asset_meta(asset)
    output = run_research(meta, records, readiness)
    evaluation = evaluate(asset=meta, records=records, analyst=output["analyst"], devil=output["devil"],
                          readiness=readiness, as_of=as_of)
    result: dict[str, Any] = {
        "profile_id": row.id,
        "as_of": as_of.isoformat(),
        "asset": {"id": asset.id, "symbol": asset.symbol, "name": asset.name, "asset_type": asset.asset_type,
                  "is_synthetic": asset.is_synthetic, "data_source": asset.data_source,
                  "min_horizon_months": asset.min_horizon_months},
        "analyst": output["analyst"],
        "devil": output["devil"],
        "evaluation": evaluation,
        "engine": output["engine"],
        "readiness_status": readiness["status"],
        "evidence": [
            {"evidence_key": r.key, "title": r.title, "source_type": r.source_type,
             "verification_status": r.verification_status,
             "publication_date": r.publication_date.isoformat() if r.publication_date else None,
             "period": r.period, "summary": r.summary, "metrics": dict(r.payload)}
            for r in records
        ],
        "versions": {"readiness": READINESS_RULE_VERSION, "evaluator": EVALUATOR_VERSION, "prompts": PROMPT_VERSION},
        "provider": {"id": provider.id, "is_live": provider.is_live, "attribution": provider.attribution},
    }
    stored = ResearchAnalysisRow(user_id=user.id, profile_id=row.id, asset_id=asset.id,
                                 evaluator_status=evaluation["status"], result=result)
    db.add(stored)
    db.flush()
    result["analysis_id"] = stored.id
    flag_modified(stored, "result")  # JSON mutated in place: force the UPDATE
    db.commit()
    return result


# --------------------------------------------------------------------------- simulator

def simulate_for(db: Session, user: User, row: InvestorProfile | None, body: Any, as_of: date) -> dict[str, Any]:
    asset = repo.get_asset(db, body.asset_id)
    if asset is None:
        raise NotFoundError("Instrument not found.")
    comparison: AssetSeries | None = None
    if body.compare_asset_id is not None:
        other = repo.get_asset(db, body.compare_asset_id)
        if other is None:
            raise NotFoundError("Comparison instrument not found.")
        comparison = _asset_series(db, other)
    if body.scenario_type == "COMPARISON" and comparison is None:
        raise ValidationProblem("A comparison scenario needs a second instrument (compare_asset_id).")

    initial = body.initial_amount if body.initial_amount is not None else Decimal("0")
    monthly = body.monthly_contribution if body.monthly_contribution is not None else Decimal("0")
    if body.amount_source == "PROFILE_DERIVED":
        if row is None:
            raise ValidationProblem("Profile-derived amounts need a profile.")
        readiness = readiness_for(db, row, as_of)
        if readiness["status"] == "NOT_READY":
            raise ValidationProblem(
                "No investable amount is available because readiness is NOT_READY. You can run a hypothetical scenario, "
                "which will be labelled as not financially available."
            )
        designated = D(readiness["metrics"]["designated_monthly"])
        if designated <= 0:
            raise ValidationProblem(
                "You have not designated a monthly investment amount. Add one on your profile, or run a labelled hypothetical scenario."
            )
        monthly = designated
        initial = D(readiness["metrics"]["unallocated_liquid"])
    elif body.initial_amount is None and body.monthly_contribution is None:
        raise ValidationProblem("Enter a starting amount, a monthly amount, or both for a hypothetical scenario.")

    reference_asset = _asset_series(db, asset)
    try:
        result = run_simulation(
            primary=reference_asset,
            comparison=comparison,
            scenario=body.scenario_type,
            amount_source=body.amount_source,
            initial=initial,
            monthly=monthly,
            frequency=body.contribution_frequency,
            duration_months=body.duration_months,
            evaluation=body.evaluation_date,
            market_path=body.market_path,
            cash_interest_pct=body.cash_interest_pct,
            delay_months=body.delay_months,
            seed=body.seed,
            reference=as_of,
        )
    except SimulationError as exc:
        raise ValidationProblem(str(exc)) from exc

    stored = SimulationRow(
        user_id=user.id,
        profile_id=row.id if row else None,
        asset_id=asset.id,
        scenario_type=body.scenario_type,
        amount_source=body.amount_source,
        inputs=body.model_dump(mode="json"),
        result=result,
    )
    db.add(stored)
    db.flush()
    result["simulation_id"] = stored.id
    result["engine_note"] = f"{SIMULATOR_VERSION}. {result['engine_note']}"
    flag_modified(stored, "result")  # JSON mutated in place: force the UPDATE
    db.commit()
    return result


# --------------------------------------------------------------------------- passport

def generate_passport(db: Session, user: User, row: InvestorProfile, body: Any, as_of: date) -> dict[str, Any]:
    research_row = None
    simulation_row = None
    if body.research_analysis_id is not None:
        research_row = repo.get_research(db, user.id, body.research_analysis_id)
        if research_row is None or research_row.profile_id != row.id:
            raise NotFoundError("Research analysis not found for this profile.")
    if body.simulation_id is not None:
        simulation_row = repo.get_simulation(db, user.id, body.simulation_id)
        if simulation_row is None or simulation_row.profile_id != row.id:
            raise NotFoundError("Simulation not found for this profile.")
    if research_row is not None and simulation_row is not None and research_row.asset_id != simulation_row.asset_id:
        raise ValidationProblem("The simulation was run on a different instrument from the research analysis. Re-run one for the same instrument.")

    readiness = readiness_for(db, row, as_of)
    market = None
    asset_id = research_row.asset_id if research_row is not None else None
    if asset_id is not None:
        asset = repo.get_asset(db, asset_id)
        market = market_for(db, asset, as_of) if asset else None
    timing = assess_timing(financial_from_row(row), readiness, market, as_of)

    research_snapshot = dict(research_row.result) | {"analysis_id": research_row.id} if research_row else None
    simulation_snapshot = dict(simulation_row.result) | {"simulation_id": simulation_row.id} if simulation_row else None
    skipped = None
    if simulation_row is None:
        if readiness["status"] == "NOT_READY":
            skipped = "No investment simulation was run: readiness is NOT_READY, so no investable amount exists."
        else:
            skipped = "No investment simulation was attached to this passport."

    snapshot = compose(
        profile=profile_out(row),
        readiness=readiness,
        timing=timing,
        research=research_snapshot,
        simulation=simulation_snapshot,
        simulation_skipped_reason=skipped,
        as_of=as_of,
    )
    stored = DecisionPassportRow(
        user_id=user.id,
        profile_id=row.id,
        research_analysis_id=research_row.id if research_row else None,
        simulation_id=simulation_row.id if simulation_row else None,
        schema_version=snapshot["schema_version"],
        snapshot=snapshot,
    )
    db.add(stored)
    db.flush()
    snapshot["passport_id"] = stored.id
    flag_modified(stored, "snapshot")  # JSON mutated in place: force the UPDATE
    db.commit()
    return snapshot


# --------------------------------------------------------------------------- assistant

def _serialize_chat_message(msg: Any) -> dict[str, Any]:
    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "profile_id": msg.profile_id,
        "meta": msg.meta,
        "created_at": msg.created_at.isoformat(),
    }


def assistant_history_for(db: Session, user: User) -> list[dict[str, Any]]:
    return [_serialize_chat_message(m) for m in repo.list_chat_messages(db, user.id, limit=100)]


def clear_assistant_history_for(db: Session, user: User) -> None:
    repo.clear_chat_messages(db, user.id)


def assistant_for(db: Session, user: User, profile_id: int | None, messages: list[dict[str, str]], as_of: date) -> dict[str, Any]:
    all_profiles = repo.list_profiles(db, user.id)
    row: InvestorProfile | None = None
    if profile_id is not None:
        row = get_owned_profile(db, user, profile_id)
    elif all_profiles:
        row = all_profiles[0]

    context: dict[str, Any] = {
        "user_account": {"display_name": user.display_name, "email": user.email, "is_guest": user.is_guest},
        "investor_profile": None,
        "all_profiles": [
            {"id": p.id, "display_name": p.display_name, "investment_experience": p.investment_experience}
            for p in all_profiles
        ],
        "readiness": None,
        "timing": None,
        "research": [],
        "simulations": [],
        "passports": [],
    }
    if row is not None:
        readiness = readiness_for(db, row, as_of)
        context["investor_profile"] = profile_out(row)
        context["readiness"] = readiness
        context["timing"] = assess_timing(financial_from_row(row), readiness, None, as_of)
        for item in repo.list_research(db, user.id, row.id, limit=5):
            context["research"].append({
                "id": item.id,
                "asset_name": item.result["asset"]["name"],
                "symbol": item.result["asset"].get("symbol"),
                "status": item.evaluator_status,
                "thesis": item.result.get("analyst", {}).get("thesis"),
                "counter_thesis": item.result.get("devil", {}).get("counter_thesis"),
            })
        for sim in repo.list_simulations(db, user.id, row.id, limit=5):
            metrics = sim.result["primary"]["run"]["metrics"]
            context["simulations"].append({
                "id": sim.id,
                "scenario_type": sim.scenario_type,
                "twr": metrics["time_weighted_return_pct"],
                "ending_value": metrics.get("ending_value"),
                "max_drawdown_pct": metrics.get("max_drawdown_pct"),
            })
        for pp in repo.list_passports(db, user.id, row.id)[:5]:
            context["passports"].append(passport_summary(pp))

    stored_history = repo.list_chat_messages(db, user.id, limit=30)
    latest_user_msg = messages[-1]["content"].strip()
    full_conversation = [{"role": m.role, "content": m.content} for m in stored_history]
    full_conversation.append({"role": "user", "content": latest_user_msg})

    reply = assistant_engine.answer(full_conversation, context)

    active_pid = row.id if row is not None else profile_id
    repo.add_chat_message(db, user.id, active_pid, "user", latest_user_msg, meta=None)
    repo.add_chat_message(
        db,
        user.id,
        active_pid,
        "assistant",
        reply["answer"],
        meta={
            "mode": reply["mode"],
            "provider": reply["provider"],
            "grounding": reply.get("grounding", []),
            "guardrails": reply.get("guardrails", []),
        },
    )
    db.commit()
    return reply


def passport_summary(row: DecisionPassportRow) -> dict[str, Any]:
    snap = row.snapshot
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat(),
        "status": snap["readiness"]["status"],
        "objective": snap["objective"],
        "timing_verdict_code": snap["timing"]["verdict_code"],
        "research_analysis_id": row.research_analysis_id,
        "simulation_id": row.simulation_id,
        "schema_version": row.schema_version,
    }


