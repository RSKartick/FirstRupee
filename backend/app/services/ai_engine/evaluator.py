"""Deterministic Final Evaluator (evaluator-rules-v2.0).

It checks EVERY claim from both agents against the stored evidence records and never produces a buy or sell signal.

Per-claim checks: claim type; evidence identifier exists; evidence belongs to this instrument; source verification status;
publication date present, not in the future, and within the source-type freshness limit; reporting period matches; metric
exists in the record; numeric agreement with the stored value. Claims without evidence count as UNSUPPORTED and stay in the
quality denominator. Hypotheses are labelled and excluded from evidence support.

Material risks are NOT taken from the language model. They come only from RISK_RULES applied to stored numbers, so a non-empty
LLM list can never trigger a risk status on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from app.services.financial_engine.money import D
from app.services.financial_engine.rules import EVALUATOR_VERSION

FRESHNESS_LIMIT_DAYS = {
    "ANNUAL_REPORT": 600,  # annual cycle plus publication lag
    "FUND_FACTSHEET": 540,
    "REGULATORY_FILING": 400,
    "SYNTHETIC_DOCUMENT": 900,
}
QUALITY_WEIGHT = {"SUPPORTED": 1.0, "SUPPORTED_STALE": 0.5, "SYNTHETIC_DEMONSTRATION": 0.5, "UNVERIFIED": 0.25}
SUPPORTED_STATUSES = {"SUPPORTED", "SUPPORTED_STALE", "SYNTHETIC_DEMONSTRATION"}
UNSUPPORTED_STATUSES = {"UNSUPPORTED", "INVALID_REFERENCE"}


@dataclass(frozen=True)
class EvidenceView:
    key: str
    asset_id: int
    title: str
    source_type: str
    verification_status: str
    publication_date: date | None
    period: str | None
    summary: str
    payload: dict[str, str]


@dataclass(frozen=True)
class RiskRule:
    code: str
    label: str
    metric: str
    test: Callable[[Decimal], bool]
    threshold: str


RISK_RULES: tuple[RiskRule, ...] = (
    RiskRule("HIGH_LEVERAGE", "Debt-to-equity at or above 1.0", "debtEquity", lambda v: v >= 1, "≥ 1.0"),
    RiskRule("THIN_INTEREST_COVER", "Interest coverage below 3.0x", "interestCoverage", lambda v: v < 3, "< 3.0x"),
    RiskRule("LOW_CASH_CONVERSION", "Operating cash flow below 70% of net profit", "ocfToPat", lambda v: v < Decimal("0.7"), "< 0.70"),
    RiskRule("EXPENSIVE_VALUATION", "Price-to-earnings above 35", "peRatio", lambda v: v > 35, "> 35"),
    RiskRule("HIGH_COST", "Expense ratio above 1.0% a year", "expenseRatioPct", lambda v: v > 1, "> 1.0%"),
    RiskRule("TRACKING_GAP", "Tracking difference beyond ±0.5%", "absTrackingDifferencePct", lambda v: v > Decimal("0.5"), "|x| > 0.5%"),
    RiskRule("DEEP_DRAWDOWN", "Maximum drawdown of 20% or worse", "maxDrawdownPct", lambda v: v <= -20, "≤ −20%"),
    RiskRule("PRICE_VOLATILITY", "Annualised volatility above 12%", "annualisedVolatilityPct", lambda v: v > 12, "> 12%"),
    RiskRule("LONG_DURATION", "Modified duration above 3 years", "modifiedDurationYears", lambda v: v > 3, "> 3 years"),
)


def _to_decimal(value: str) -> Decimal | None:
    try:
        return D(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def derived_metrics(payload: dict[str, str]) -> dict[str, Decimal]:
    values: dict[str, Decimal] = {}
    for key, raw in payload.items():
        number = _to_decimal(str(raw))
        if number is not None:
            values[key] = number
    if "ocfCr" in values and values.get("patCr"):
        values["ocfToPat"] = values["ocfCr"] / values["patCr"]
    if "trackingDifferencePct" in values:
        values["absTrackingDifferencePct"] = abs(values["trackingDifferencePct"])
    return values


def _agrees(claimed: Decimal, observed: Decimal) -> bool:
    tolerance = max(Decimal("0.01"), abs(observed) * Decimal("0.005"))
    return abs(claimed - observed) <= tolerance


def _freshness(record: EvidenceView, as_of: date) -> tuple[str, int | None, int]:
    limit = FRESHNESS_LIMIT_DAYS.get(record.source_type, 365)
    if record.publication_date is None:
        return "UNKNOWN", None, limit
    age = (as_of - record.publication_date).days
    if age < 0:
        return "FUTURE", age, limit
    return ("FRESH" if age <= limit else "STALE"), age, limit


def _check_claim(side: str, claim: dict[str, Any], by_key: dict[str, EvidenceView], asset_id: int, as_of: date) -> dict[str, Any]:
    claim_type = claim.get("claim_type", "FACT")
    key = claim.get("evidence_key")
    base = {
        "side": side,
        "claim": claim.get("claim", ""),
        "claim_type": claim_type,
        "evidence_key": key,
        "metric_key": claim.get("metric_key"),
        "claimed_value": claim.get("claimed_value"),
        "period": claim.get("period"),
    }
    if claim_type == "HYPOTHESIS":
        return {**base, "status": "HYPOTHESIS", "evidence_status": None, "freshness": None, "observed_value": None,
                "reasons": ["Labelled as an analytical hypothesis. It is not counted as evidence."]}
    if not key:
        return {**base, "status": "UNSUPPORTED", "evidence_status": "MISSING", "freshness": None, "observed_value": None,
                "reasons": ["Factual or qualitative claim has no evidence reference."]}
    record = by_key.get(key)
    if record is None:
        return {**base, "status": "INVALID_REFERENCE", "evidence_status": "MISSING", "freshness": None, "observed_value": None,
                "reasons": ["Evidence identifier does not exist in the dataset (possible fabrication)."]}
    if record.asset_id != asset_id:
        return {**base, "status": "INVALID_REFERENCE", "evidence_status": "MISSING", "freshness": None, "observed_value": None,
                "reasons": ["The evidence record belongs to a different instrument."]}

    freshness, age, limit = _freshness(record, as_of)
    freshness_info = {"publication_date": record.publication_date.isoformat() if record.publication_date else None,
                      "age_days": age, "limit_days": limit, "status": freshness}
    if freshness == "UNKNOWN":
        return {**base, "status": "INVALID_REFERENCE", "evidence_status": record.verification_status, "freshness": freshness_info,
                "observed_value": None, "reasons": ["The source has no publication date, so freshness cannot be verified."]}
    if freshness == "FUTURE":
        return {**base, "status": "INVALID_REFERENCE", "evidence_status": record.verification_status, "freshness": freshness_info,
                "observed_value": None, "reasons": ["The source is dated after the reference date."]}

    reasons: list[str] = []
    if claim.get("period") and record.period and claim["period"] != record.period:
        return {**base, "status": "INVALID_REFERENCE", "evidence_status": record.verification_status, "freshness": freshness_info,
                "observed_value": None, "reasons": [f"Reporting period mismatch: claim says {claim['period']}, record is {record.period}."]}

    observed: Decimal | None = None
    if claim_type == "FACT":
        metric = claim.get("metric_key")
        if not metric:
            return {**base, "status": "UNSUPPORTED", "evidence_status": record.verification_status, "freshness": freshness_info,
                    "observed_value": None, "reasons": ["Factual claim does not name a metric from the record."]}
        observed = derived_metrics(record.payload).get(metric)
        if observed is None:
            return {**base, "status": "UNSUPPORTED", "evidence_status": record.verification_status, "freshness": freshness_info,
                    "observed_value": None, "reasons": [f"Metric '{metric}' is not present in the referenced record."]}
        claimed_raw = claim.get("claimed_value")
        if claimed_raw is not None:
            claimed = _to_decimal(str(claimed_raw))
            if claimed is None:
                reasons.append("Claimed value is not a number; numeric agreement could not be checked.")
            elif not _agrees(claimed, observed):
                return {**base, "status": "CONTRADICTED", "evidence_status": "CONTRADICTED", "freshness": freshness_info,
                        "observed_value": f"{observed:.4f}",
                        "reasons": [f"Claimed {claimed_raw} but the stored record shows {observed:.4f}."]}

    if record.verification_status == "SYNTHETIC":
        status = "SYNTHETIC_DEMONSTRATION"
        reasons.append("Synthetic demonstration record: the check demonstrates the process, not independent verification.")
    elif record.verification_status == "VERIFIED" and freshness == "FRESH":
        status = "SUPPORTED"
    elif record.verification_status == "VERIFIED":
        status = "SUPPORTED_STALE"
        reasons.append(f"Source is older than its freshness limit ({age} days vs {limit}).")
    else:
        status = "UNVERIFIED"
        reasons.append("Source verification status is UNVERIFIED.")
    return {**base, "status": status, "evidence_status": record.verification_status, "freshness": freshness_info,
            "observed_value": f"{observed:.4f}" if observed is not None else None, "reasons": reasons}


def _material_risks(records: list[EvidenceView]) -> list[dict[str, Any]]:
    confirmed: list[dict[str, Any]] = []
    usable = [r for r in records if r.verification_status in ("VERIFIED", "SYNTHETIC")]
    newest_first = sorted(usable, key=lambda r: r.period or "", reverse=True)
    for rule in RISK_RULES:
        for record in newest_first:
            values = derived_metrics(record.payload)
            if rule.metric in values:
                if rule.test(values[rule.metric]):
                    confirmed.append({
                        "code": rule.code, "label": rule.label, "metric_key": rule.metric,
                        "observed_value": f"{values[rule.metric]:.4f}", "threshold": rule.threshold,
                        "evidence_key": record.key, "period": record.period,
                        "evidence_status": record.verification_status,
                        "basis": "Deterministic rule applied to the stored record",
                    })
                break  # the most recent record that contains the metric decides
    annual = sorted([r for r in usable if r.source_type == "ANNUAL_REPORT" and "opmPct" in r.payload], key=lambda r: r.period or "")
    if len(annual) >= 2:
        latest, previous = annual[-1], annual[-2]
        change = D(latest.payload["opmPct"]) - D(previous.payload["opmPct"])
        if change <= -1:
            confirmed.append({
                "code": "MARGIN_DECLINE", "label": "Operating margin fell by at least 1 percentage point",
                "metric_key": "opmPct", "observed_value": f"{change:.2f} pp", "threshold": "≤ −1.00 pp",
                "evidence_key": latest.key, "period": latest.period, "evidence_status": latest.verification_status,
                "basis": f"Change between {previous.period} and {latest.period} in stored records",
            })
    return confirmed


def _quality_label(score: int, synthetic_share: float) -> str:
    if synthetic_share >= 0.999:
        return "Demonstration only (synthetic evidence)"
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Moderate"
    if score >= 30:
        return "Weak"
    return "Unreliable"


def evaluate(
    *,
    asset: dict[str, Any],
    records: list[EvidenceView],
    analyst: dict[str, Any] | None,
    devil: dict[str, Any] | None,
    readiness: dict[str, Any],
    as_of: date,
) -> dict[str, Any]:
    by_key = {r.key: r for r in records}
    checks: list[dict[str, Any]] = []
    if analyst:
        checks += [_check_claim("ANALYST", c, by_key, asset["id"], as_of) for c in analyst.get("claims", [])]
    if devil:
        checks += [_check_claim("DEVIL_ADVOCATE", c, by_key, asset["id"], as_of) for c in devil.get("claims", [])]

    factual = [c for c in checks if c["status"] != "HYPOTHESIS"]
    total = len(factual)
    counts = {
        "total_factual_claims": total,
        "hypotheses": len(checks) - total,
        "supported": sum(c["status"] == "SUPPORTED" for c in factual),
        "supported_stale": sum(c["status"] == "SUPPORTED_STALE" for c in factual),
        "synthetic_demonstration": sum(c["status"] == "SYNTHETIC_DEMONSTRATION" for c in factual),
        "unverified": sum(c["status"] == "UNVERIFIED" for c in factual),
        "unsupported": sum(c["status"] == "UNSUPPORTED" for c in factual),
        "invalid_reference": sum(c["status"] == "INVALID_REFERENCE" for c in factual),
        "contradicted": sum(c["status"] == "CONTRADICTED" for c in factual),
    }
    weight = sum(QUALITY_WEIGHT.get(c["status"], 0.0) for c in factual)
    score = round(100 * weight / total) if total else 0
    synthetic_share = (counts["synthetic_demonstration"] / total) if total else 0.0
    quality = {
        "score": score,
        "label": _quality_label(score, synthetic_share),
        "explanation": (
            f"{counts['supported']} verified and fresh, {counts['synthetic_demonstration']} synthetic demonstration, "
            f"{counts['supported_stale']} stale, {counts['unverified']} unverified, and "
            f"{counts['unsupported'] + counts['invalid_reference']} unsupported or invalid, out of {total} factual claims. "
            f"Unsupported claims remain in the denominator and reduce the score. {counts['contradicted']} contradicted."
        ),
    }

    conflicts: list[dict[str, Any]] = []
    seen: dict[tuple[str | None, str], tuple[str, str]] = {}
    for record in sorted(records, key=lambda r: r.key):
        for metric, raw in record.payload.items():
            slot = (record.period, metric)
            if slot in seen and seen[slot][1] != str(raw) and record.period is not None:
                conflicts.append({"period": record.period, "metric_key": metric,
                                  "records": [seen[slot][0], record.key], "values": [seen[slot][1], str(raw)]})
            else:
                seen.setdefault(slot, (record.key, str(raw)))

    referenced = {c["evidence_key"] for c in checks if c.get("evidence_key")}
    synthetic_used = any(by_key[k].verification_status == "SYNTHETIC" for k in referenced if k in by_key) or bool(asset.get("is_synthetic"))
    stale_sources = [c["freshness"] | {"evidence_key": c["evidence_key"]} for c in checks
                     if c.get("freshness") and c["freshness"]["status"] == "STALE"]

    risks = _material_risks(records)
    confirmed_keys = {r["evidence_key"] for r in risks}
    unconfirmed = [c["claim"] for c in checks if c["side"] == "DEVIL_ADVOCATE" and c["status"] in SUPPORTED_STATUSES
                   and c.get("evidence_key") not in confirmed_keys and c["claim_type"] == "FACT"]

    m = readiness["metrics"]
    horizon = m.get("goal_horizon_months")
    surplus = D(m["monthly_surplus"])
    hard_constraint = readiness["status"] == "NOT_READY" or readiness["completeness"] == "INCOMPLETE" or surplus <= 0
    unsupported_share = (counts["unsupported"] + counts["invalid_reference"]) / total if total else 1.0
    usable_support = counts["supported"] + counts["supported_stale"] + counts["synthetic_demonstration"]

    if hard_constraint:
        status = "FINANCIAL_CONSTRAINTS_IDENTIFIED"
    elif horizon is not None and horizon < asset["min_horizon_months"]:
        status = "GOAL_HORIZON_MISMATCH"
    elif analyst is None or devil is None or usable_support == 0 or counts["contradicted"] > 0 or unsupported_share > 0.25:
        status = "INSUFFICIENT_EVIDENCE"
    elif risks:
        status = "MATERIAL_RISKS_IDENTIFIED"
    else:
        status = "FURTHER_RESEARCH_REQUIRED"

    missing: list[str] = list((devil or {}).get("missing_information", []))
    if counts["unsupported"] or counts["invalid_reference"]:
        missing.append(f"{counts['unsupported'] + counts['invalid_reference']} claim(s) lack valid evidence and were not relied on.")
    if conflicts:
        missing.append(f"{len(conflicts)} conflicting record value(s) found across periods; the stored values were kept unchanged.")
    if analyst is None:
        missing.append("No Research Analyst output was produced.")
    if devil is None:
        missing.append("No Devil's Advocate output was produced.")

    suitability = [
        f"Readiness is {readiness['status']} under {readiness['rule_version']}. The language model cannot change it.",
    ]
    if horizon is None:
        suitability.append("No valid goal horizon is stored, so horizon suitability could not be assessed.")
    elif horizon < asset["min_horizon_months"]:
        suitability.append(f"Your horizon ({horizon} months) is shorter than this instrument's minimum sensible horizon ({asset['min_horizon_months']} months). This is a structural mismatch, not a market view.")
    else:
        suitability.append(f"Your horizon ({horizon} months) meets this instrument's minimum sensible horizon ({asset['min_horizon_months']} months).")
    if readiness["status"] == "NOT_READY":
        suitability.append("Because readiness is NOT_READY, this analysis is educational only.")

    unresolved = []
    if not checks:
        unresolved.append("No claims were produced, so nothing could be checked against stored records.")
    if asset.get("asset_type") != "EQUITY":
        unresolved.append("Holdings and tracking behaviour are summarised from sample records and are not independently audited.")
    if asset.get("is_synthetic"):
        unresolved.append("All evidence is synthetic demonstration data. The output shows the method, not a real instrument.")

    return {
        "evaluator_version": EVALUATOR_VERSION,
        "status": status,
        "claim_checks": checks,
        "counts": counts,
        "evidence_quality": quality,
        "conflicts": conflicts,
        "data_status": {
            "synthetic_evidence_used": synthetic_used,
            "stale_sources": stale_sources,
            "reference_date": as_of.isoformat(),
        },
        "material_risks": risks,
        "unconfirmed_concerns": unconfirmed,
        "missing_data": missing,
        "suitability_notes": suitability,
        "unresolved_uncertainties": unresolved,
        "advisory_notice": (
            "This is an evidence evaluation, not a buy or sell recommendation. FirstRupee is not a regulated investment adviser, "
            "does not execute trades and does not predict markets."
        ),
    }
