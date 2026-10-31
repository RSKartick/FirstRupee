"""Three-Clock Timing Engine (deterministic, timing-rules-v2.0).

Clocks
- Money Clock: cash flow, reserves and the money that is actually free.
- Goal Clock: goal horizon, required monthly saving and liquidity needs.
- Market Clock: verified market context only; UNAVAILABLE / STALE / INVALID are stated explicitly.

Precedence (first matching rule decides the verdict; every rule is reported with whether it was triggered):
  R1  Missing or invalid financial inputs      -> no positive conclusion.
  R2  Negative monthly cash flow               -> cash flow first.
  R3  Emergency reserves below the floor        -> reserves first (dominates market context).
  R4  Goal inside 12 months or high liquidity   -> goal money is not risk capital.
  R5  Readiness NOT_READY                       -> deployment is not appropriate.
  R6  Readiness PREPARATION                     -> learning and research only; staged, small amounts.
  R7  Readiness READY_TO_EXPLORE                -> research permitted; never a buy instruction.
  R8  Market data missing, stale or future-dated -> stated explicitly, never filled in.
  R9  Market sentiment never overrides R1–R5, so the Market Clock cannot change the verdict code.
No market-bottom or buy-date predictions are produced.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.services.financial_engine.dates import months_until
from app.services.financial_engine.money import D, fmt_inr
from app.services.financial_engine.readiness import FinancialProfile
from app.services.financial_engine.rules import TIMING_RULE_VERSION

CAUTION = (
    "This engine does not produce buy dates, market-entry timing or market-bottom predictions. 'When' here means when your own "
    "cash flow, reserves and goal horizon can tolerate volatility. Market context is historical and descriptive only."
)


def _money_clock(p: FinancialProfile, readiness: dict[str, Any]) -> dict[str, Any]:
    m = readiness["metrics"]
    surplus = D(m["monthly_surplus"])
    coverage = D(m["emergency_coverage_months"]) if m["emergency_coverage_months"] is not None else None
    ratio = D(m["surplus_ratio"]) if m["surplus_ratio"] is not None else None
    if surplus < 0:
        status = "CRITICAL"
    elif surplus == 0 or (coverage is not None and coverage < 6) or (ratio is not None and ratio < Decimal("0.10")):
        status = "CONSTRAINED"
    else:
        status = "OK"
    headlines = {
        "CRITICAL": "Cash flow is negative - there is no money to invest.",
        "CONSTRAINED": "Money arrives, but there is little slack.",
        "OK": "Monthly cash flow leaves room after commitments.",
    }
    return {
        "name": "Money Clock",
        "status": status,
        "headline": headlines[status],
        "explanation": (
            f"Income of {fmt_inr(p.income)} less commitments of {fmt_inr(D(m['committed_outflow']))} leaves "
            f"{fmt_inr(surplus)} per month. Liquid emergency reserves of {fmt_inr(p.emergency)} and goal reserves of "
            f"{fmt_inr(p.goal_reserved)} are excluded from investable money. Investable monthly money after goal and reserve "
            f"needs is {fmt_inr(D(m['investable_monthly']))}; you designated {fmt_inr(D(m['designated_monthly']))}."
        ),
        "data": {
            "monthly_surplus": m["monthly_surplus"],
            "investable_monthly": m["investable_monthly"],
            "designated_monthly": m["designated_monthly"],
            "unallocated_liquid": m["unallocated_liquid"],
            "emergency_coverage_months": m["emergency_coverage_months"],
        },
    }


def _goal_clock(p: FinancialProfile, readiness: dict[str, Any], as_of: date) -> dict[str, Any]:
    m = readiness["metrics"]
    horizon = m["goal_horizon_months"]
    need = D(m["goal_monthly_need"]) if m["goal_monthly_need"] is not None else None
    surplus = D(m["monthly_surplus"])
    if p.goal_deadline is None:
        status = "UNAVAILABLE"
        headline = "No goal deadline - the horizon cannot be assessed."
    elif horizon is not None and horizon < 0:
        status, headline = "CRITICAL", "The goal deadline has passed; update it before any planning."
    elif horizon is not None and horizon < 12:
        status, headline = "CRITICAL", "The money is needed too soon to be risk capital."
    elif p.goal_liquidity == "HIGH" and horizon is not None and horizon < 36:
        status, headline = "CRITICAL", "High liquidity need inside three years: keep the money liquid."
    elif (horizon is not None and horizon < 36) or (need is not None and need > max(surplus, Decimal("0"))):
        status, headline = "CONSTRAINED", "The goal needs planning and funding, not market risk."
    else:
        status, headline = "OK", "The horizon is long enough to tolerate volatility, provided the deadline does not move earlier."
    target = fmt_inr(p.goal_amount) if p.goal_amount is not None else "not stated"
    return {
        "name": "Goal Clock",
        "status": status,
        "headline": headline,
        "explanation": (
            f"Goal: {p.goal_name or 'unnamed'}; target {target}; "
            + (f"{horizon} whole months from {as_of.isoformat()} to the deadline. " if horizon is not None else "no valid horizon. ")
            + (f"Remaining need after reserved money is about {fmt_inr(need)} per month. " if need is not None else "")
            + (f"Stated liquidity need: {p.goal_liquidity}. " if p.goal_liquidity else "")
        ).strip(),
        "data": {
            "goal_horizon_months": horizon,
            "goal_monthly_need": m["goal_monthly_need"],
            "goal_liquidity": p.goal_liquidity,
            "horizon_basis": m["horizon_basis"],
        },
    }


def _market_clock(market: dict[str, Any] | None) -> dict[str, Any]:
    if market is None:
        return {
            "name": "Market Clock",
            "status": "UNAVAILABLE",
            "headline": "No market series was selected.",
            "explanation": "No instrument was chosen, so no market context is used. The verdict rests on cash flow and goal horizon only.",
            "data": {},
        }
    status_map = {"OK": "OK", "STALE": "STALE", "UNAVAILABLE": "UNAVAILABLE", "FUTURE_DATA_INVALID": "INVALID"}
    status = status_map.get(market["status"], "UNAVAILABLE")
    if status == "OK":
        headline = "Historical market context is available for this instrument."
        explanation = (
            f"{market['asset_name']}: annualised volatility {market.get('annualised_volatility_pct')}% over "
            f"{market.get('observations_used')} daily observations, latest {market.get('last_observation')}. "
            f"{market.get('trailing_12m_note', '')} "
            + ("These observations are synthetic demonstration data. " if market.get("is_synthetic") else "")
            + market["disclaimer"]
        )
    elif status == "STALE":
        headline = "Market data is stale and has been withheld."
        explanation = market["note"]
    elif status == "INVALID":
        headline = "Market data contains future-dated observations."
        explanation = market["note"]
    else:
        headline = "No market data is available."
        explanation = market.get("note", "No market observations are stored.")
    return {"name": "Market Clock", "status": status, "headline": headline, "explanation": explanation, "data": {
        "status": market["status"], "last_observation": market.get("last_observation"), "age_days": market.get("age_days"),
        "annualised_volatility_pct": market.get("annualised_volatility_pct"),
        "trailing_12m_return_pct": market.get("trailing_12m_return_pct"), "is_synthetic": market.get("is_synthetic"),
        "source": market.get("source"),
    }}


def assess_timing(p: FinancialProfile, readiness: dict[str, Any], market: dict[str, Any] | None, as_of: date) -> dict[str, Any]:
    m = readiness["metrics"]
    status = readiness["status"]
    completeness = readiness["completeness"]
    surplus = D(m["monthly_surplus"])
    coverage = D(m["emergency_coverage_months"]) if m["emergency_coverage_months"] is not None else None
    money = _money_clock(p, readiness)
    goal = _goal_clock(p, readiness, as_of)
    market_clock = _market_clock(market)
    horizon = months_until(as_of, p.goal_deadline) if p.goal_deadline is not None else None

    r1 = completeness == "INCOMPLETE"
    r2 = surplus < 0
    r3 = coverage is not None and coverage < 2
    r4 = goal["status"] == "CRITICAL"
    r5 = status == "NOT_READY"
    r6 = status == "PREPARATION"
    r7 = status == "READY_TO_EXPLORE"
    r8 = market_clock["status"] in ("UNAVAILABLE", "STALE", "INVALID")

    if r1:
        code = "INPUTS_INCOMPLETE"
        verdict = (
            "Timing cannot be assessed because required inputs are missing: "
            + "; ".join(readiness["missing_information"]) + ". No positive conclusion is given."
        )
    elif r2:
        code = "CASH_FLOW_FIRST"
        verdict = "Monthly cash flow is negative. Investment deployment is not appropriate: close the monthly gap first."
    elif r3:
        code = "RESERVE_FIRST"
        verdict = "Emergency reserves cover less than 2 months of essential expenses. Market exposure is premature regardless of market conditions."
    elif r4:
        code = "GOAL_PROTECTION"
        verdict = (
            "The goal is inside the protected horizon or needs high liquidity. This money is not long-term risk capital; "
            "keep it in liquid, low-volatility holdings."
        )
    elif r5:
        code = "NOT_READY_HOLD"
        verdict = "Readiness is NOT_READY. Investment deployment is not appropriate yet. Resolve: " + (readiness["blockers"][0] if readiness["blockers"] else "the incomplete inputs") + "."
    elif r6:
        code = "EDUCATE_ONLY"
        verdict = (
            "Preparation stage: learning, comparing and simulating are appropriate. Any deployment should be small, staged and "
            "within the amount you designated. This is not a deployment signal."
        )
    else:
        code = "RESEARCH_PERMITTED"
        verdict = (
            "Your financial position permits further investment research. This is not a buy recommendation; read the Devil's "
            "Advocate evidence before any decision."
        )

    if market_clock["status"] == "OK":
        verdict += " Market context is shown for information only and does not change this verdict."
    elif r8 and market is not None:
        verdict += f" Market context is {market_clock['status'].lower()}: {market_clock['headline']}"

    precedence = [
        {"rule": "R1", "description": "Missing or invalid financial inputs produce no positive conclusion", "triggered": r1},
        {"rule": "R2", "description": "Negative monthly cash flow: cash flow first", "triggered": r2},
        {"rule": "R3", "description": "Emergency reserves below the 2-month floor dominate market context", "triggered": r3},
        {"rule": "R4", "description": "Goal inside 12 months or high liquidity: not risk capital", "triggered": r4},
        {"rule": "R5", "description": "NOT_READY never implies deployment is appropriate", "triggered": r5},
        {"rule": "R6", "description": "PREPARATION permits education and research only", "triggered": r6},
        {"rule": "R7", "description": "READY_TO_EXPLORE permits research, never an automatic buy", "triggered": r7},
        {"rule": "R8", "description": "Missing, stale or future-dated market data is stated explicitly", "triggered": r8},
        {"rule": "R9", "description": "Market sentiment never overrides capacity or goal liquidity", "triggered": True},
    ]

    return {
        "rule_version": TIMING_RULE_VERSION,
        "as_of": as_of.isoformat(),
        "verdict_code": code,
        "verdict": verdict,
        "readiness_status": status,
        "precedence": precedence,
        "clocks": {"money": money, "goal": goal, "market": market_clock},
        "caution": CAUTION,
    }
