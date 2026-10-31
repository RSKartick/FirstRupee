"""Research Analyst and Devil's Advocate.

Two perspectives over the same stored records. Each uses the language model when one is configured and validated, and otherwise
a rule-based analyst that writes claims only from stored numbers and the RISK_RULES thresholds. Either way the output is passed to
the deterministic evaluator. Assistant text is never allowed to become a number.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.ai_engine.evaluator import RISK_RULES, EvidenceView, derived_metrics
from app.services.ai_engine.llm import call_json
from app.services.ai_engine.prompts import ANALYST_SYSTEM, DEVIL_SYSTEM, untrusted_block
from app.services.financial_engine.money import D
from app.services.financial_engine.rules import PROMPT_VERSION


class ClaimDraft(BaseModel):
    claim: str = Field(min_length=3, max_length=600)
    claim_type: str = Field(pattern="^(FACT|QUALITATIVE|HYPOTHESIS)$")
    evidence_key: str | None = Field(default=None, max_length=120)
    metric_key: str | None = Field(default=None, max_length=60)
    claimed_value: str | None = Field(default=None, max_length=40)
    period: str | None = Field(default=None, max_length=20)


class AnalystDraft(BaseModel):
    overview: str = Field(min_length=3, max_length=2000)
    thesis: str = Field(min_length=3, max_length=2000)
    developments: list[str] = Field(default_factory=list, max_length=10)
    claims: list[ClaimDraft] = Field(default_factory=list, max_length=40)


class DevilDraft(BaseModel):
    counter_thesis: str = Field(min_length=3, max_length=2000)
    no_material_negative_finding: bool
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    claims: list[ClaimDraft] = Field(default_factory=list, max_length=40)


def _claim(text: str, key: str | None, metric: str | None = None, value: str | None = None,
           period: str | None = None, claim_type: str = "FACT") -> dict[str, Any]:
    return {"claim": text, "claim_type": claim_type, "evidence_key": key, "metric_key": metric,
            "claimed_value": value, "period": period}


def _fmt(value: Any) -> str:
    return f"{value:.2f}"


def _annual(records: list[EvidenceView]) -> list[EvidenceView]:
    rows = [r for r in records if r.source_type in ("ANNUAL_REPORT", "FUND_FACTSHEET") and r.payload]
    return sorted(rows, key=lambda r: r.period or "")


POSITIVE_CHECKS = (
    ("interestCoverage", lambda v: v >= 3, "Interest coverage is at or above 3x"),
    ("ocfToPat", lambda v: v >= D("0.8"), "Operating cash flow covers at least 80% of reported profit"),
    ("expenseRatioPct", lambda v: v <= D("0.25"), "Expense ratio is 0.25% a year or less"),
    ("absTrackingDifferencePct", lambda v: v <= D("0.5"), "Tracking difference stays within 0.5%"),
)
CONTEXT_METRICS = ("revenueCr", "opmPct", "debtEquity", "peRatio", "expenseRatioPct", "trackingDifferencePct",
                   "couponPct", "modifiedDurationYears", "annualisedVolatilityPct")


def rule_based_analyst(asset: dict[str, Any], records: list[EvidenceView]) -> dict[str, Any]:
    rows = _annual(records)
    latest = rows[-1] if rows else None
    previous = rows[-2] if len(rows) >= 2 else None
    claims: list[dict[str, Any]] = []
    developments: list[str] = []

    if latest:
        values = derived_metrics(latest.payload)
        for metric in CONTEXT_METRICS:
            if metric in values:
                claims.append(_claim(f"Recorded {metric} for {latest.period}: {_fmt(values[metric])}", latest.key, metric,
                                     f"{values[metric]:.4f}", latest.period))
        for metric, test, text in POSITIVE_CHECKS:
            if metric in values and test(values[metric]):
                claims.append(_claim(f"{text} ({latest.period}).", latest.key, metric, f"{values[metric]:.4f}", latest.period))
        if previous and "revenueCr" in values and "revenueCr" in derived_metrics(previous.payload):
            prev_values = derived_metrics(previous.payload)
            claims.append(_claim(f"Revenue of ₹{_fmt(values['revenueCr'])} crore is recorded for {latest.period}, against ₹{_fmt(prev_values['revenueCr'])} crore for {previous.period}.",
                                 latest.key, "revenueCr", f"{values['revenueCr']:.4f}", latest.period))
            if values["revenueCr"] > prev_values["revenueCr"]:
                claims.append(_claim(f"Revenue rose between {previous.period} and {latest.period}.", latest.key,
                                     "revenueCr", f"{values['revenueCr']:.4f}", latest.period))
        if previous and "opmPct" in values and "opmPct" in derived_metrics(previous.payload):
            change = values["opmPct"] - derived_metrics(previous.payload)["opmPct"]
            if change > 0:
                claims.append(_claim(f"Operating margin improved between {previous.period} and {latest.period}.", latest.key,
                                     "opmPct", f"{values['opmPct']:.4f}", latest.period))

    for doc in records:
        if doc.source_type in ("SYNTHETIC_DOCUMENT", "REGULATORY_FILING") and doc.summary:
            developments.append(doc.summary)
            claims.append(_claim(doc.summary, doc.key, claim_type="QUALITATIVE"))

    thesis_basis = (
        f"If revenue growth and operating margins hold at the levels in the stored {latest.period if latest else 'latest'} record, "
        "earnings and cash generation may continue to support the business."
        if asset.get("asset_type") == "EQUITY"
        else "If costs, tracking and liquidity characteristics stay as recorded, the instrument behaves as its documentation describes."
    )
    claims.append(_claim(thesis_basis, None, claim_type="HYPOTHESIS"))

    return {
        "overview": f"{asset['name']} ({asset['symbol']}). {asset.get('description', '')}".strip(),
        "thesis": " ".join(c["claim"] for c in claims if c["claim_type"] != "HYPOTHESIS")[:1800] or
        "The stored records contain no positive metric that meets a documented threshold.",
        "developments": developments[:6],
        "claims": claims,
    }


def rule_based_devil(asset: dict[str, Any], records: list[EvidenceView]) -> dict[str, Any]:
    rows = _annual(records)
    latest = rows[-1] if rows else None
    previous = rows[-2] if len(rows) >= 2 else None
    claims: list[dict[str, Any]] = []
    missing: list[str] = []

    if latest:
        values = derived_metrics(latest.payload)
        for rule in RISK_RULES:
            if rule.metric in values and rule.test(values[rule.metric]):
                claims.append(_claim(f"{rule.label}: recorded {_fmt(values[rule.metric])} for {latest.period}.", latest.key,
                                     rule.metric, f"{values[rule.metric]:.4f}", latest.period))
        if previous and "opmPct" in values and "opmPct" in derived_metrics(previous.payload):
            change = values["opmPct"] - derived_metrics(previous.payload)["opmPct"]
            if change <= -1:
                claims.append(_claim(f"Operating margin fell between {previous.period} and {latest.period}.", latest.key,
                                     "opmPct", f"{values['opmPct']:.4f}", latest.period))

    if asset.get("asset_type") == "EQUITY":
        missing += ["Segment-level revenue and margins are not in the stored records.",
                    "Promoter pledging, related-party transactions and auditor remarks are not in the stored records.",
                    "Quarterly results are not in the stored records."]
    else:
        missing += ["The full holdings list with weights is not in the stored records.",
                    "The exit-load schedule and tax treatment are not in the stored records."]
    if asset.get("is_synthetic"):
        missing.append("All records are synthetic demonstration data and cannot support a real investment decision.")

    negatives = [c["claim"] for c in claims]
    counter = (
        "Bear case from the stored records: " + " ".join(negatives) + " Missing information limits the assessment."
        if negatives
        else "No material negative finding is established by the stored records. That is not the same as no risk: "
        "the missing information listed above still limits a complete assessment."
    )
    return {
        "counter_thesis": counter,
        "no_material_negative_finding": not negatives,
        "missing_information": missing,
        "claims": claims,
    }


def _record_payload(records: list[EvidenceView]) -> list[dict[str, Any]]:
    return [
        {
            "evidence_key": r.key,
            "title": r.title,
            "source_type": r.source_type,
            "verification_status": r.verification_status,
            "publication_date": r.publication_date.isoformat() if r.publication_date else None,
            "period": r.period,
            "summary": r.summary,
            "metrics": {**r.payload, **{k: f"{v:.4f}" for k, v in derived_metrics(r.payload).items() if k not in r.payload}},
        }
        for r in records
    ]


def run_research(asset: dict[str, Any], records: list[EvidenceView], readiness: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    allowed_keys = [r.key for r in records]
    engine: dict[str, Any] = {
        "analyst_mode": "DETERMINISTIC_RULES",
        "devil_mode": "DETERMINISTIC_RULES",
        "provider": "none",
        "model": None,
        "prompt_version": PROMPT_VERSION,
        "errors": [],
        "allowed_evidence_keys": allowed_keys,
    }
    context = {
        "instrument": {k: asset.get(k) for k in ("name", "symbol", "asset_type", "description", "min_horizon_months", "is_synthetic", "data_source")},
        "allowed_evidence_keys": allowed_keys,
        "records": _record_payload(records),
        "investor_constraints": {
            "readiness_status": readiness["status"],
            "monthly_surplus": readiness["metrics"]["monthly_surplus"],
            "goal_horizon_months": readiness["metrics"]["goal_horizon_months"],
            "note": "Deterministic constraints. Comment on suitability only; never on whether to buy.",
        },
    }

    analyst: dict[str, Any] | None = None
    if settings.llm_enabled:
        result = call_json(ANALYST_SYSTEM, untrusted_block("evidence_records", context), AnalystDraft)
        if result.ok:
            analyst = result.data.model_dump()
            engine.update(analyst_mode="LLM", provider=result.provider, model=result.model)
        else:
            engine["errors"].append(f"Research Analyst: {result.kind} — {result.message}")
    if analyst is None:
        analyst = rule_based_analyst(asset, records)

    devil: dict[str, Any] | None = None
    if settings.llm_enabled:
        devil_context = {**context, "analyst_claims": analyst.get("claims", [])}
        result = call_json(DEVIL_SYSTEM, untrusted_block("evidence_records_and_analyst_claims", devil_context), DevilDraft)
        if result.ok:
            devil = result.data.model_dump()
            engine.update(devil_mode="LLM", provider=result.provider, model=result.model)
        else:
            engine["errors"].append(f"Devil's Advocate: {result.kind} — {result.message}")
    if devil is None:
        devil = rule_based_devil(asset, records)

    return {"analyst": analyst, "devil": devil, "engine": engine}
