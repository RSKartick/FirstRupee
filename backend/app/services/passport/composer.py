"""Decision Passport composition. The result is a snapshot: every number, claim, version and data timestamp used is copied in,
so the passport can be read later without recomputation and remains valid after rules change."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.services.financial_engine.rules import PASSPORT_SCHEMA_VERSION

PASSPORT_DISCLAIMER = (
    "Educational decision-support snapshot generated from the inputs recorded at the time. It is not investment advice, not a "
    "recommendation to buy or sell, and not a forecast. FirstRupee is not a regulated investment adviser and does not execute trades. "
    "Synthetic demonstration data is labelled wherever it is used. A commercial deployment requires separate review of applicable "
    "SEBI requirements, data licences and privacy obligations."
)


def _review_conditions(readiness: dict[str, Any], research: dict[str, Any] | None) -> tuple[list[dict[str, str]], list[str]]:
    conditions: list[dict[str, str]] = []
    depends: list[str] = []
    if research:
        for check in research["evaluation"]["claim_checks"]:
            if check["side"] == "ANALYST" and check["claim_type"] == "FACT" and check.get("metric_key") and check.get("claimed_value"):
                period = check.get("period") or "the recorded period"
                depends.append(f"{check['metric_key']} stays near {check['claimed_value']} ({period}) in verified newer data")
                conditions.append({
                    "condition": f"Verified newer data shows {check['metric_key']} materially below {check['claimed_value']} recorded for {period}.",
                    "trigger": f"Next verified record for {check['evidence_key']} or a later period.",
                    "severity": "THESIS_BREAKING",
                })
        for risk in research["evaluation"]["material_risks"]:
            conditions.append({
                "condition": f"'{risk['label']}' is confirmed by verified data (currently {risk['observed_value']}, {risk['period']}).",
                "trigger": "Any update to the referenced record.",
                "severity": "HIGH",
            })
    m = readiness["metrics"]
    if m.get("emergency_coverage_months") is not None:
        conditions.append({"condition": "Emergency reserve coverage falls below 6 months of essential expenses.",
                           "trigger": "Any change to income, expenses or reserves.", "severity": "CONSTRAINT"})
    if m.get("goal_horizon_months") is not None:
        conditions.append({"condition": "The goal deadline moves inside 36 months or the liquidity need rises.",
                           "trigger": "Change to goal date or liquidity setting.", "severity": "CONSTRAINT"})
    conditions.append({"condition": f"Readiness changes from {readiness['status']} under a new rule set or new inputs.",
                       "trigger": "Re-run readiness after any material change.", "severity": "CONSTRAINT"})
    return conditions, depends


def compose(
    *,
    profile: dict[str, Any],
    readiness: dict[str, Any],
    timing: dict[str, Any],
    research: dict[str, Any] | None,
    simulation: dict[str, Any] | None,
    simulation_skipped_reason: str | None,
    as_of: date,
) -> dict[str, Any]:
    review_conditions, depends = _review_conditions(readiness, research)
    evidence_refs: list[dict[str, Any]] = []
    if research:
        used = {c.get("evidence_key") for c in research["evaluation"]["claim_checks"] if c.get("evidence_key")}
        for record in research["evidence"]:
            if record["evidence_key"] in used:
                evidence_refs.append({
                    "evidence_key": record["evidence_key"],
                    "title": record["title"],
                    "source_type": record["source_type"],
                    "verification_status": record["verification_status"],
                    "publication_date": record["publication_date"],
                    "period": record["period"],
                    "claims": [c["claim"] for c in research["evaluation"]["claim_checks"] if c.get("evidence_key") == record["evidence_key"]],
                })

    stale = research["evaluation"]["data_status"]["stale_sources"] if research else []
    missing = list(readiness["missing_information"]) + list(readiness["limitations"])
    if research:
        missing += research["evaluation"]["missing_data"]
    if simulation:
        missing += [item for item in simulation["limitations"] if "excluded" in item.lower() or "not" in item.lower()]
    if simulation_skipped_reason:
        missing.append(simulation_skipped_reason)

    assumptions = [
        f"Reference date for every calculation: {as_of.isoformat()}. Readiness and timing were computed with this date.",
        f"Readiness rule set {readiness['rule_version']}; timing rule set {timing['rule_version']}.",
        "Emergency reserves and goal-reserved money are excluded from investable money; no rupee is counted twice.",
        "Market context is historical and descriptive only; it does not predict returns or timing.",
    ]
    if research:
        engine = research["engine"]
        assumptions.append(
            f"Research: analyst mode {engine['analyst_mode']}, devil's advocate mode {engine['devil_mode']}, "
            f"prompt set {engine['prompt_version']}; the deterministic evaluator checked every claim."
        )
    if simulation:
        assumptions += simulation["assumptions"]

    synthetic_used = bool(research and research["evaluation"]["data_status"]["synthetic_evidence_used"]) or bool(
        simulation and simulation["data_period"]["is_synthetic"]
    )
    data_status = {
        "synthetic_data_used": synthetic_used,
        "synthetic_notice": "Synthetic demonstration data is in use. It demonstrates the method and is not independent verification." if synthetic_used else None,
        "stale_sources": stale,
        "market_context": timing["clocks"]["market"]["status"],
        "as_of": as_of.isoformat(),
    }

    return {
        "schema_version": PASSPORT_SCHEMA_VERSION,
        "reference_date": as_of.isoformat(),
        "versions": {
            "passport": PASSPORT_SCHEMA_VERSION,
            "readiness": readiness["rule_version"],
            "timing": timing["rule_version"],
            "simulator": simulation["engine_version"] if simulation else None,
            "evaluator": research["evaluation"]["evaluator_version"] if research else None,
            "prompts": research["engine"]["prompt_version"] if research else None,
        },
        "investor_profile": profile,
        "objective": (
            f"{profile['goal_name']} — target {profile['goal_amount']}" if profile.get("goal_name") and profile.get("goal_amount")
            else (profile["goal_name"] or "No goal recorded")
        ),
        "horizon": {
            "months": readiness["metrics"]["goal_horizon_months"],
            "basis": readiness["metrics"]["horizon_basis"],
        },
        "readiness": readiness,
        "timing": timing,
        "research": None if research is None else {
            "analysis_id": research.get("analysis_id"),
            "asset": research["asset"],
            "analyst_thesis": research["analyst"]["thesis"],
            "counter_thesis": research["devil"]["counter_thesis"],
            "no_material_negative_finding": research["devil"]["no_material_negative_finding"],
            "evaluator_status": research["evaluation"]["status"],
            "evidence_quality": research["evaluation"]["evidence_quality"],
            "material_risks": research["evaluation"]["material_risks"],
            "unconfirmed_concerns": research["evaluation"]["unconfirmed_concerns"],
            "suitability_notes": research["evaluation"]["suitability_notes"],
            "claim_counts": research["evaluation"]["counts"],
        },
        "simulation": None if simulation is None else {
            "simulation_id": simulation.get("simulation_id"),
            "scenario_type": simulation["scenario_type"],
            "amount_source": simulation["amount_source"],
            "financially_available": simulation["financially_available"],
            "market_path": simulation["market_path"],
            "window": simulation["window"],
            "inputs": simulation["inputs"],
            "primary_metrics": simulation["primary"]["run"]["metrics"],
            "labels": simulation["labels"],
            "data_period": simulation["data_period"],
        },
        "simulation_skipped_reason": simulation_skipped_reason,
        "evidence_references": evidence_refs,
        "data_status": data_status,
        "missing_information": missing,
        "assumptions": assumptions,
        "review_conditions": review_conditions,
        "thesis_expiry": {
            "statement": (
                "This thesis expires when verified future information contradicts a dependency listed below. "
                "A contradiction is a reason to reassess, not to hold on."
            ),
            "depends_on": depends or ["No metric-based dependency was extracted; the qualitative reasoning above is the dependency."],
            "review_by": (as_of + timedelta(days=365)).isoformat(),
        },
        "disclaimer": PASSPORT_DISCLAIMER,
    }
