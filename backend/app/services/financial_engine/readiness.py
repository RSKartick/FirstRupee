"""Deterministic Investment Readiness Engine.

Pure function of its inputs (profile + reference date). No I/O, no randomness, no LLM. The AI layer can explain the output
but can never change its classification.

Money flows are kept separate so no rupee is counted in two categories:
  * monthly surplus            = income - essentials - non-essentials - EMI - other commitments
  * goal monthly need          = (goal amount - goal reserve already held) / whole months to the goal deadline
  * emergency replenishment    = gap to 6 months of essentials / 12 months (documented assumption)
  * investable monthly         = max(0, surplus - goal need - replenishment)
  * unallocated liquid balance = liquid savings - emergency reserve - goal reserve (a stock, not a flow)
  * designated monthly amount  = the investment amount the user explicitly chose; it must not exceed investable monthly
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.services.financial_engine.dates import months_until
from app.services.financial_engine.money import D, ZERO, dstr, fmt_inr, safe_div
from app.services.financial_engine.rules import READINESS, READINESS_RULE_VERSION

REQUIRED_QUESTIONS = (
    "drawdown_reaction",
    "preferred_horizon",
    "gains_reaction",
    "loss_impact_on_expenses",
    "income_stability",
)
DRAWDOWN_SCORE = {"SELL_IMMEDIATELY": 10, "WAIT": 40, "REASSESS_THESIS": 65, "ADD_IF_THESIS_VALID": 80}
HORIZON_SCORE = {"UNDER_1_YEAR": 10, "ONE_TO_THREE_YEARS": 35, "THREE_TO_SEVEN_YEARS": 65, "OVER_SEVEN_YEARS": 85}
STABILITY_SCORE = {"VERY_STABLE": 90, "SOMEWHAT_STABLE": 60, "IRREGULAR": 25}
STATED_HORIZON_MONTHS = {"UNDER_1_YEAR": 6, "ONE_TO_THREE_YEARS": 24, "THREE_TO_SEVEN_YEARS": 60, "OVER_SEVEN_YEARS": 96}

DISCLAIMER = (
    "Rule-based educational guardrail (readiness-rules-v2.0). It is not a validated psychometric score, not a regulatory "
    "assessment and not a recommendation to buy or sell any investment. Thresholds are documented in rules.py."
)


@dataclass(frozen=True)
class DebtItem:
    debt_type: str
    outstanding: Decimal
    rate_pct: Decimal
    emi: Decimal
    remaining_months: int
    is_overdue: bool


@dataclass(frozen=True)
class FinancialProfile:
    income: Decimal
    essential: Decimal
    nonessential: Decimal
    emi: Decimal
    other: Decimal
    total_savings: Decimal
    liquid: Decimal
    emergency: Decimal
    goal_reserved: Decimal
    current_investments: Decimal
    liabilities: Decimal
    designated: Decimal
    employment_status: str
    experience: str
    goal_name: str | None
    goal_amount: Decimal | None
    goal_deadline: date | None
    goal_liquidity: str | None
    goal_importance: str | None
    questionnaire: dict[str, str] | None
    debts: tuple[DebtItem, ...] = ()
    profile_id: int | None = None


def _finding(code: str, label: str, severity: str, detail: str, **inputs: Any) -> dict[str, Any]:
    return {
        "code": code,
        "label": label,
        "severity": severity,
        "detail": detail,
        "inputs": {key: _plain_value(value) for key, value in inputs.items()},
    }


def _plain_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return dstr(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _band(score: int, low_max: int, high_min: int) -> str:
    if score < low_max:
        return "LOW"
    if score >= high_min:
        return "HIGH"
    return "MODERATE"


def risk_tolerance(questionnaire: dict[str, str] | None) -> dict[str, Any]:
    """Behavioural willingness to accept volatility. Unanswered questions produce UNKNOWN, never LOW.

    Performance-chasing (continuing to invest because prices rose) is reported as a SEPARATE behavioural indicator.
    It is deliberately not added to tolerance: investing more after gains says nothing reliable about willingness to lose.
    """
    q = questionnaire or {}
    score: int | None = None
    if all(key in q for key in ("drawdown_reaction", "preferred_horizon")):
        score = (DRAWDOWN_SCORE[q["drawdown_reaction"]] + HORIZON_SCORE[q["preferred_horizon"]]) // 2
    gains = q.get("gains_reaction")
    if gains == "INVEST_MORE_ON_GAINS":
        chasing = "ELEVATED"
    elif gains in ("KEEP_PLAN", "WITHDRAW_SOME"):
        chasing = "NOT_ELEVATED"
    else:
        chasing = "NOT_ASSESSED"
    band = "UNKNOWN" if score is None else _band(score, READINESS.tolerance_low_max, READINESS.tolerance_high_min)
    return {"score": score, "band": band, "performance_chasing": chasing}


def risk_capacity(
    p: FinancialProfile,
    *,
    coverage: Decimal | None,
    surplus_ratio: Decimal | None,
    emi_burden: Decimal | None,
    horizon_months: int | None,
    overdue: bool,
) -> dict[str, Any]:
    """Financial ability to absorb a loss. Any missing dimension makes the band UNKNOWN (never a silent LOW)."""
    q = p.questionnaire or {}
    components: dict[str, tuple[Decimal, int]] = {}
    missing: list[str] = []

    stability = q.get("income_stability")
    if stability in STABILITY_SCORE:
        components["income_stability"] = (D(STABILITY_SCORE[stability]), 20)
    else:
        missing.append("Income stability answer")
    if coverage is not None:
        components["emergency_coverage"] = (min(D(100), coverage / D(6) * D(100)), 25)
    else:
        missing.append("Emergency coverage (essential expenses must be above zero)")
    if surplus_ratio is not None:
        surplus_score = ZERO if surplus_ratio <= 0 else min(D(100), surplus_ratio / READINESS.capacity_surplus_full_ratio * D(100))
        components["monthly_surplus"] = (surplus_score, 25)
    else:
        missing.append("Monthly income")
    if emi_burden is not None:
        if overdue:
            debt_score = ZERO
        elif emi_burden <= D("0.10"):
            debt_score = D(100)
        elif emi_burden <= D("0.30"):
            debt_score = D(60)
        elif emi_burden <= D("0.45"):
            debt_score = D(25)
        else:
            debt_score = ZERO
        components["debt_burden"] = (debt_score, 15)
    if horizon_months is None:
        missing.append("Investment horizon (goal deadline or stated horizon)")
    else:
        if horizon_months >= 84:
            horizon_score = D(100)
        elif horizon_months >= 60:
            horizon_score = D(80)
        elif horizon_months >= 36:
            horizon_score = D(60)
        elif horizon_months >= 12:
            horizon_score = D(25)
        else:
            horizon_score = ZERO
        components["horizon"] = (horizon_score, 15)
    if "loss_impact_on_expenses" not in q:
        missing.append("Loss-impact answer")

    if missing:
        return {"score": None, "band": "UNKNOWN", "components": {}, "caps": [], "missing": missing}

    total_weight = sum(weight for _, weight in components.values())
    weighted = sum((score * weight for score, weight in components.values()), ZERO) / D(total_weight)
    score = int(round(weighted))

    caps: list[dict[str, Any]] = []
    if q.get("loss_impact_on_expenses") == "AFFECTS_ESSENTIALS":
        caps.append({"code": "LOSS_AFFECTS_ESSENTIALS", "cap": READINESS.cap_loss_affects_essentials,
                     "reason": "A loss of this size would affect monthly essentials."})
    if q.get("income_stability") == "IRREGULAR":
        caps.append({"code": "IRREGULAR_INCOME", "cap": READINESS.cap_irregular_income,
                     "reason": "Irregular income reduces the cushion against a loss."})
    if p.goal_liquidity == "HIGH":
        caps.append({"code": "HIGH_LIQUIDITY_GOAL", "cap": READINESS.cap_high_liquidity_goal,
                     "reason": "The goal money may be needed at short notice."})
    if coverage is not None and coverage < READINESS.emergency_floor_months:
        caps.append({"code": "COVERAGE_BELOW_FLOOR", "cap": READINESS.cap_coverage_below_floor,
                     "reason": "Emergency reserves are below the 2-month floor."})
    if surplus_ratio is not None and surplus_ratio <= 0:
        caps.append({"code": "NO_SURPLUS", "cap": READINESS.cap_no_surplus, "reason": "Monthly cash flow is not positive."})
    if overdue:
        caps.append({"code": "OVERDUE_DEBT", "cap": READINESS.cap_overdue_debt, "reason": "An existing loan is overdue."})
    for cap in caps:
        score = min(score, cap["cap"])

    return {
        "score": score,
        "band": _band(score, READINESS.capacity_low_max, READINESS.capacity_high_min),
        "components": {name: {"score": f"{value:.1f}", "weight": weight} for name, (value, weight) in components.items()},
        "caps": caps,
        "missing": [],
    }


IMPROVEMENTS: dict[str, str] = {
    "NEGATIVE_SURPLUS": "Reduce non-essential spending or EMI commitments until income covers every recorded outflow.",
    "ZERO_SURPLUS": "Create some monthly surplus, even a small one, before investing anything.",
    "THIN_SURPLUS": "Widen the monthly surplus above 10% of income so one unplanned expense does not force a withdrawal.",
    "COVERAGE_UNKNOWN": "Enter essential monthly expenses so emergency coverage can be measured.",
    "EMERGENCY_BELOW_FLOOR": "Build liquid emergency reserves to at least 2 months of essential expenses; the target is 6 months.",
    "EMERGENCY_PARTIAL": "Keep building the emergency reserve toward 6 months of essential expenses.",
    "EMI_BURDEN_HIGH": "Bring EMI payments below 45% of take-home income before taking market risk.",
    "EMI_BURDEN_ELEVATED": "Watch EMI payments: above 30% of income limits how much volatility your cash flow can absorb.",
    "OVERDUE_DEBT": "Clear overdue loan amounts before any investment decision.",
    "HIGH_INTEREST_DEBT": "Compare the cost of high-interest debt with realistic investment outcomes; repaying it is often the first step.",
    "HIGH_DEBT_LOAD": "Outstanding debt exceeds one year of income; reduce it before adding investment risk.",
    "GOAL_DATE_PASSED": "Update the goal deadline to a future date so the horizon can be assessed.",
    "GOAL_WITHIN_12_MONTHS": "Keep money needed within 12 months in liquid, low-volatility holdings, or move the goal date if realistic.",
    "GOAL_1_TO_3_YEARS": "Limit volatile exposure for money needed in 1 to 3 years.",
    "GOAL_NOT_FUNDED_BY_SURPLUS": "Lower the goal target, extend the deadline or increase monthly savings so the goal is funded from surplus.",
    "GOAL_DATE_MISSING": "Add a goal deadline so the Goal Clock can be computed.",
    "HIGH_LIQUIDITY_GOAL": "If this money may be needed at short notice, keep it out of volatile assets.",
    "TOLERANCE_CAPACITY_MISMATCH": "Build financial capacity (reserves, surplus, lower debt) before taking on volatility you cannot absorb.",
    "CAPACITY_EXCEEDS_TOLERANCE": "Use staged, small amounts; behaviour rather than ability is the constraint here.",
    "LOSS_AFFECTS_ESSENTIALS": "A loss would reach your essentials: prioritise reserves before market exposure.",
    "DESIGNATED_EXCEEDS_CAPACITY": "Reduce the designated monthly investment to the investable amount shown.",
    "INCONSISTENT_SAVINGS": "Correct the savings entries so liquid savings do not exceed total savings.",
    "RESERVES_EXCEED_LIQUID": "Reserves must be held in liquid form and cannot together exceed liquid savings.",
    "DEBT_EMI_MISMATCH": "Make the monthly EMI equal the sum of the loan EMIs listed (EMIs must not be counted twice).",
    "DEBT_TOTAL_MISMATCH": "Make existing liabilities equal the sum of the outstanding loan balances listed.",
    "RISK_QUESTIONNAIRE": "Complete the risk questionnaire so behavioural tolerance and financial capacity can be measured.",
}


def assess_readiness(p: FinancialProfile, as_of: date, profile_updated_at: str | None = None) -> dict[str, Any]:
    t = READINESS
    findings: list[dict[str, Any]] = []
    missing: list[str] = []
    limitations: list[str] = []

    income = p.income
    essential = p.essential
    nonessential = p.nonessential
    emi = p.emi
    other = p.other

    committed = essential + nonessential + emi + other
    surplus = income - committed
    surplus_ratio = safe_div(surplus, income)
    emi_burden = safe_div(emi, income)
    coverage = safe_div(p.emergency, essential)
    unallocated = p.liquid - p.emergency - p.goal_reserved
    debt_to_income = safe_div(p.liabilities, income * 12)

    q = p.questionnaire or {}

    # ---- completeness (missing inputs can never produce a positive conclusion)
    if income <= 0:
        missing.append("Monthly take-home income (must be above zero)")
    if essential <= 0:
        missing.append("Essential monthly expenses (must be above zero to measure emergency coverage)")
    if p.questionnaire is None or any(key not in q for key in REQUIRED_QUESTIONS):
        missing.append("Complete risk questionnaire (behavioural and capacity answers)")
    if p.goal_deadline is None and (p.goal_name or p.goal_amount is not None):
        missing.append("Goal deadline (needed to measure the goal horizon)")

    # ---- allocation integrity: inconsistent inputs are reported as blockers, never silently corrected
    if p.liquid > p.total_savings:
        findings.append(_finding("INCONSISTENT_SAVINGS", "Liquid savings exceed total savings", "BLOCKER",
                                 "Liquid savings cannot be larger than total savings.",
                                 liquid_savings=p.liquid, total_savings=p.total_savings))
    if p.emergency + p.goal_reserved > p.liquid:
        findings.append(_finding("RESERVES_EXCEED_LIQUID", "Reserves exceed liquid savings", "BLOCKER",
                                 "Emergency reserves plus goal reserves cannot exceed liquid savings; the same rupee would be counted twice.",
                                 emergency_reserves=p.emergency, goal_reserved=p.goal_reserved, liquid_savings=p.liquid))
    if p.debts:
        debt_emi_total = sum((d.emi for d in p.debts), ZERO)
        debt_outstanding_total = sum((d.outstanding for d in p.debts), ZERO)
        if debt_emi_total != emi:
            findings.append(_finding("DEBT_EMI_MISMATCH", "EMI does not match loan list", "BLOCKER",
                                     "Monthly EMI must equal the sum of listed loan EMIs; EMIs are never deducted twice.",
                                     monthly_emi=emi, listed_emi_total=debt_emi_total))
        if debt_outstanding_total != p.liabilities:
            findings.append(_finding("DEBT_TOTAL_MISMATCH", "Liabilities do not match loan list", "BLOCKER",
                                     "Existing liabilities must equal the sum of listed outstanding balances.",
                                     existing_liabilities=p.liabilities, listed_outstanding_total=debt_outstanding_total))
    elif p.liabilities > 0:
        limitations.append("Liabilities were entered without per-loan details, so interest rates, remaining terms and overdue status are unknown.")

    # ---- cash flow
    if surplus < 0:
        findings.append(_finding("NEGATIVE_SURPLUS", "Monthly cash flow is negative", "BLOCKER",
                                 f"Recorded outflows exceed income by {fmt_inr(-surplus)} per month.",
                                 monthly_surplus=surplus, monthly_income=income, committed_outflow=committed))
    elif surplus == 0:
        findings.append(_finding("ZERO_SURPLUS", "Zero monthly surplus", "BLOCKER",
                                 "Income exactly equals recorded commitments; there is no monthly money available to invest.",
                                 monthly_surplus=surplus))
    elif surplus_ratio is not None and surplus_ratio < t.thin_surplus_ratio:
        findings.append(_finding("THIN_SURPLUS", "Monthly surplus is thin", "WARNING",
                                 f"Only {surplus_ratio * 100:.1f}% of income remains after commitments.",
                                 monthly_surplus=surplus, surplus_ratio=surplus_ratio))
    else:
        findings.append(_finding("POSITIVE_SURPLUS", "Monthly surplus is available", "INFO",
                                 f"{fmt_inr(surplus)} per month remains after recorded commitments.",
                                 monthly_surplus=surplus))

    # ---- emergency reserve
    emergency_target = essential * t.emergency_target_months
    emergency_gap = max(ZERO, emergency_target - p.emergency)
    replenish_monthly = emergency_gap / Decimal(t.emergency_replenish_months)
    if coverage is None:
        findings.append(_finding("COVERAGE_UNKNOWN", "Emergency coverage cannot be measured", "WARNING",
                                 "Essential expenses are missing or zero, so coverage is unknown. Unknown coverage is never treated as adequate.",
                                 essential_expenses=essential))
    elif coverage < t.emergency_floor_months:
        findings.append(_finding("EMERGENCY_BELOW_FLOOR", "Emergency reserves are below the floor", "BLOCKER",
                                 f"Reserves cover {coverage:.1f} month(s) of essentials; the floor is 2 months.",
                                 emergency_reserves=p.emergency, coverage_months=coverage))
    elif coverage < t.emergency_target_months:
        findings.append(_finding("EMERGENCY_PARTIAL", "Emergency reserves are partly funded", "WARNING",
                                 f"Reserves cover {coverage:.1f} months; the target is 6 months.",
                                 emergency_reserves=p.emergency, coverage_months=coverage))
    else:
        findings.append(_finding("EMERGENCY_TARGET_MET", "Emergency reserves meet the target", "INFO",
                                 f"Reserves cover {coverage:.1f} months of essentials.",
                                 emergency_reserves=p.emergency, coverage_months=coverage))

    # ---- debt
    if emi_burden is not None:
        if emi_burden > t.emi_blocker_ratio:
            findings.append(_finding("EMI_BURDEN_HIGH", "EMI burden is very high", "BLOCKER",
                                     f"EMIs take {emi_burden * 100:.1f}% of take-home pay (blocker above 45%).",
                                     monthly_emi=emi, emi_burden=emi_burden))
        elif emi_burden > t.emi_warning_ratio:
            findings.append(_finding("EMI_BURDEN_ELEVATED", "EMI burden is elevated", "WARNING",
                                     f"EMIs take {emi_burden * 100:.1f}% of take-home pay (warning above 30%).",
                                     monthly_emi=emi, emi_burden=emi_burden))
    overdue = [d for d in p.debts if d.is_overdue]
    if overdue:
        findings.append(_finding("OVERDUE_DEBT", "A loan is overdue", "BLOCKER",
                                 f"{len(overdue)} loan(s) are marked overdue.", overdue_loans=len(overdue)))
    high_rate = [d for d in p.debts if d.outstanding > 0 and d.rate_pct > t.high_interest_pct]
    if high_rate:
        findings.append(_finding("HIGH_INTEREST_DEBT", "High-interest debt outstanding", "WARNING",
                                 "At least one loan charges more than 15% a year.",
                                 high_interest_loans=len(high_rate)))
    if debt_to_income is not None and debt_to_income > t.high_debt_to_annual_income:
        findings.append(_finding("HIGH_DEBT_LOAD", "Debt exceeds one year of income", "WARNING",
                                 "Outstanding liabilities are larger than 12 months of take-home pay.",
                                 existing_liabilities=p.liabilities, debt_to_annual_income=debt_to_income))

    # ---- goal and horizon
    horizon = months_until(as_of, p.goal_deadline) if p.goal_deadline is not None else None
    goal_remaining: Decimal | None = None
    goal_monthly: Decimal | None = None
    if p.goal_amount is not None:
        goal_remaining = max(ZERO, p.goal_amount - p.goal_reserved)
        if horizon is not None and horizon >= 0:
            goal_monthly = goal_remaining if horizon == 0 else goal_remaining / Decimal(horizon)
    investable = max(ZERO, surplus - (goal_monthly or ZERO) - replenish_monthly)

    if goal_monthly is not None and goal_monthly > max(surplus, ZERO):
        findings.append(_finding("GOAL_NOT_FUNDED_BY_SURPLUS", "Goal needs more than the surplus", "WARNING",
                                 f"The goal needs about {fmt_inr(goal_monthly)} per month; surplus is {fmt_inr(surplus)}.",
                                 goal_monthly_need=goal_monthly, monthly_surplus=surplus))
    if p.designated > investable:
        findings.append(_finding("DESIGNATED_EXCEEDS_CAPACITY", "Designated amount exceeds investable money", "WARNING",
                                 f"You designated {fmt_inr(p.designated)} per month, but only {fmt_inr(investable)} is free after goal and reserve needs.",
                                 designated_monthly=p.designated, investable_monthly=investable))
    if horizon is not None:
        if horizon < 0:
            findings.append(_finding("GOAL_DATE_PASSED", "Goal deadline has passed", "BLOCKER",
                                     "The goal deadline is in the past, so the horizon cannot be used for planning.",
                                     goal_deadline=p.goal_deadline, horizon_months=horizon))
        elif horizon < t.short_horizon_months:
            findings.append(_finding("GOAL_WITHIN_12_MONTHS", "Goal is within 12 months", "BLOCKER",
                                     "Money needed within a year is not long-term risk capital; volatile assets can fall just when it is needed.",
                                     horizon_months=horizon))
        elif horizon < t.medium_horizon_months:
            findings.append(_finding("GOAL_1_TO_3_YEARS", "Goal is 1 to 3 years away", "WARNING",
                                     "Only modest volatility fits a 1 to 3 year horizon.", horizon_months=horizon))
        else:
            findings.append(_finding("GOAL_LONG_HORIZON", "Goal horizon is 3 years or more", "INFO",
                                     "The horizon is long enough to research volatile categories seriously.",
                                     horizon_months=horizon))
    if p.goal_name and p.goal_deadline is None:
        findings.append(_finding("GOAL_DATE_MISSING", "Goal has no deadline", "WARNING",
                                 "Without a deadline the Goal Clock cannot be computed.", goal_name=p.goal_name))
    if p.goal_liquidity == "HIGH" and (horizon is None or horizon < t.medium_horizon_months):
        findings.append(_finding("HIGH_LIQUIDITY_GOAL", "Goal may be needed at short notice", "WARNING",
                                 "High liquidity needs keep money out of volatile or lock-in instruments.",
                                 goal_liquidity=p.goal_liquidity, horizon_months=horizon))

    # ---- horizon basis for capacity: goal deadline first, otherwise the stated investment horizon
    if horizon is not None:
        horizon_basis = "GOAL_DEADLINE"
        horizon_for_capacity: int | None = max(horizon, 0)
    elif q.get("preferred_horizon") in STATED_HORIZON_MONTHS:
        horizon_basis = "STATED_INVESTMENT_HORIZON"
        horizon_for_capacity = STATED_HORIZON_MONTHS[q["preferred_horizon"]]
    else:
        horizon_basis = "UNKNOWN"
        horizon_for_capacity = None

    # ---- behaviour and capacity (kept separate)
    tolerance = risk_tolerance(p.questionnaire)
    capacity = risk_capacity(
        p,
        coverage=coverage,
        surplus_ratio=surplus_ratio,
        emi_burden=emi_burden,
        horizon_months=horizon_for_capacity,
        overdue=bool(overdue),
    )
    missing.extend(item for item in capacity["missing"] if item not in missing)

    if tolerance["performance_chasing"] == "ELEVATED":
        findings.append(_finding("PERFORMANCE_CHASING_INDICATOR", "Behavioural indicator: continuing after gains", "INFO",
                                 "You said you would invest more after gains. This is a separate behavioural indicator, not a measure of risk tolerance.",
                                 gains_reaction=q.get("gains_reaction")))
    if p.questionnaire and q.get("loss_impact_on_expenses") == "AFFECTS_ESSENTIALS":
        findings.append(_finding("LOSS_AFFECTS_ESSENTIALS", "A loss would affect essentials", "WARNING",
                                 "You said a similar loss would affect monthly expenses. This is a capacity constraint, not a behavioural one.",
                                 loss_impact=q.get("loss_impact_on_expenses")))
    findings.append(_finding("RISK_TOLERANCE", f"Behavioural tolerance: {tolerance['band']}", "INFO",
                             "Derived from your drawdown reaction and preferred holding period only.",
                             risk_tolerance_score=tolerance["score"], band=tolerance["band"]))
    findings.append(_finding("RISK_CAPACITY", f"Financial capacity: {capacity['band']}", "INFO",
                             "Derived from income stability, reserves, surplus, debt burden and horizon, with hard caps.",
                             risk_capacity_score=capacity["score"], band=capacity["band"]))
    if tolerance["band"] == "HIGH" and capacity["band"] == "LOW":
        findings.append(_finding("TOLERANCE_CAPACITY_MISMATCH", "Willingness exceeds ability to absorb losses", "BLOCKER",
                                 "Comfort with volatility does not make a loss affordable. Ability to absorb losses takes precedence.",
                                 risk_tolerance_score=tolerance["score"], risk_capacity_score=capacity["score"]))
    if tolerance["band"] == "LOW" and capacity["band"] == "HIGH":
        findings.append(_finding("CAPACITY_EXCEEDS_TOLERANCE", "Capacity exceeds willingness", "WARNING",
                                 "Your finances could absorb volatility, but your stated behaviour suggests you may sell during falls.",
                                 risk_tolerance_score=tolerance["score"], risk_capacity_score=capacity["score"]))

    # ---- classification
    completeness = "INCOMPLETE" if missing else "COMPLETE"
    blockers = [f for f in findings if f["severity"] == "BLOCKER"]
    warnings = [f for f in findings if f["severity"] == "WARNING"]
    if blockers or completeness == "INCOMPLETE":
        status = "NOT_READY"
    elif warnings or (capacity["score"] is not None and capacity["score"] < t.ready_capacity_min) or (
        tolerance["score"] is not None and tolerance["score"] < t.ready_tolerance_min
    ):
        status = "PREPARATION"
    else:
        status = "READY_TO_EXPLORE"

    steps: list[str] = []
    for finding in blockers + warnings:
        advice = IMPROVEMENTS.get(finding["code"])
        if advice and advice not in steps:
            steps.append(advice)
    for item in missing:
        steps.append(f"Provide: {item}.")
    if not steps:
        steps.append("Keep your figures up to date and revisit them when income, expenses or goals change.")

    if status == "NOT_READY":
        reasons = [f["label"] for f in blockers] or ["the assessment is incomplete"]
        explanation = (
            "Investing is not appropriate yet. The main reasons are: " + "; ".join(reasons) + ". "
            "This is an arithmetic statement about liquidity and cash flow, not a judgement about you."
        )
    elif status == "PREPARATION":
        explanation = (
            "You are in the preparation stage. Learning, comparing and simulating are reasonable now; any new money should stay "
            "small, staged and liquid until the items below are addressed."
        )
    else:
        explanation = (
            "Your recorded cash flow, reserves, debt burden and horizon clear every documented guardrail. That permits further "
            "research. It is not a recommendation to buy anything: read the Devil's Advocate evidence before any decision."
        )

    investable_out = max(ZERO, investable)
    metrics_dict: dict[str, Any] = {
        "monthly_income": dstr(income),
        "essential_expenses": dstr(essential),
        "nonessential_expenses": dstr(nonessential),
        "monthly_emi": dstr(emi),
        "other_commitments": dstr(other),
        "committed_outflow": dstr(committed),
        "monthly_surplus": dstr(surplus),
        "surplus_ratio": f"{surplus_ratio:.4f}" if surplus_ratio is not None else None,
        "emi_burden": f"{emi_burden:.4f}" if emi_burden is not None else None,
        "emergency_coverage_months": f"{coverage:.2f}" if coverage is not None else None,
        "emergency_target": dstr(emergency_target),
        "emergency_gap": dstr(emergency_gap),
        "emergency_replenish_monthly": dstr(replenish_monthly),
        "goal_horizon_months": horizon,
        "goal_remaining": dstr(goal_remaining),
        "goal_monthly_need": dstr(goal_monthly),
        "investable_monthly": dstr(investable_out),
        "designated_monthly": dstr(p.designated),
        "unallocated_liquid": dstr(max(ZERO, unallocated)),
        "total_savings": dstr(p.total_savings),
        "liquid_savings": dstr(p.liquid),
        "emergency_reserves": dstr(p.emergency),
        "goal_reserved": dstr(p.goal_reserved),
        "current_investments": dstr(p.current_investments),
        "liabilities": dstr(p.liabilities),
        "debt_to_annual_income": f"{debt_to_income:.4f}" if debt_to_income is not None else None,
        "risk_tolerance_score": tolerance["score"],
        "risk_tolerance_band": tolerance["band"],
        "risk_capacity_score": capacity["score"],
        "risk_capacity_band": capacity["band"],
        "performance_chasing": tolerance["performance_chasing"],
        "horizon_basis": horizon_basis,
    }
    recommendations = build_recommendations(
        p=p,
        status=status,
        completeness=completeness,
        surplus=surplus,
        coverage=coverage,
        emergency_target=emergency_target,
        emergency_gap=emergency_gap,
        replenish_monthly=replenish_monthly,
        goal_monthly=goal_monthly,
        investable=investable_out,
        unallocated_liquid=max(ZERO, unallocated),
        horizon_for_capacity=horizon_for_capacity,
        tolerance_band=tolerance["band"],
        capacity_band=capacity["band"],
        blockers=blockers,
        warnings=warnings,
    )
    return {
        "status": status,
        "completeness": completeness,
        "rule_version": READINESS_RULE_VERSION,
        "profile_id": p.profile_id,
        "as_of": as_of.isoformat(),
        "profile_updated_at": profile_updated_at,
        "metrics": metrics_dict,
        "recommendations": recommendations,
        "capacity_detail": {
            "components": capacity["components"],
            "caps": capacity["caps"],
        },
        "findings": findings,
        "blockers": [f["label"] for f in blockers],
        "warnings": [f["label"] for f in warnings],
        "missing_information": missing,
        "limitations": limitations,
        "improvement_steps": steps,
        "explanation": explanation,
        "disclaimer": DISCLAIMER,
    }


def _pct_of(part: Decimal, whole: Decimal) -> float:
    if whole <= ZERO:
        return 0.0
    return round(float(part / whole * D(100)), 1)


def _tone_for_experience(exp: str) -> str:
    if exp == "EXPERIENCED":
        return "Advanced quantitative brief (Experienced investor mode)"
    if exp == "INTERMEDIATE":
        return "Intermediate portfolio brief (Core-satellite & risk metrics)"
    return "Beginner-friendly plain-English guide"


def _instrument_rationale(symbol: str, exp: str, status: str) -> str:
    if symbol == "NIPPON-LIQUID":
        if exp == "BEGINNER":
            return (
                "Holds 91-day government Treasury Bills and bank deposits. Your money stays safe from stock market drops "
                "and can be withdrawn in 1 working day for emergencies or near-term goals."
            )
        if exp == "INTERMEDIATE":
            return (
                "91-day maturity T-Bill and AAA money-market portfolio (0.20% TER, -0.08% max drawdown). Preserves capital "
                "for emergency reserve replenishment and short-duration liquidity buckets."
            )
        return (
            "Ultra-short duration money-market sleeve (<91d macaulay duration, 0.20% Direct TER). Eliminates duration and "
            "equity beta risk while earning repo-linked carry on liquidity reserves."
        )

    if symbol == "SETF10GILT.NS":
        if exp == "BEGINNER":
            return (
                "Backed by Government of India bonds. It cushions your portfolio when stock markets fall and pays steady "
                "government interest."
            )
        if exp == "INTERMEDIATE":
            return (
                "Sovereign 10-year constant-maturity G-Sec ETF (0.15% TER, 6.84% YTM). Acts as zero-credit-risk fixed-income "
                "ballast against equity drawdowns."
            )
        return (
            "Sovereign G-Sec duration sleeve (0.15% TER, 7.18% coupon, 6.84% YTM). Provides negative/low crisis correlation "
            "to NSE equity beta with zero default risk."
        )

    if symbol == "UTI-NIFTY50":
        if exp == "BEGINNER":
            return (
                "Automatically spreads your money across India's 50 largest companies at a tiny 0.18% yearly fee, so you "
                "do not have to guess which single stock will win."
            )
        if exp == "INTERMEDIATE":
            return (
                "Core passive large-cap anchor tracking Nifty 50 TRI (0.18% Direct TER, -0.17% tracking difference). "
                "Captures broad market equity risk premium without active manager drift."
            )
        return (
            "Core beta exposure to Nifty 50 TRI (0.18% TER, 5% turnover, -0.17% tracking error). Maximises fee efficiency "
            "for systematic monthly rupee-cost averaging."
        )

    if symbol == "NIFTYBEES.NS":
        if exp == "BEGINNER":
            return (
                "Tracks the same 50 largest Indian companies on the stock exchange with India's lowest annual fee (0.04%)."
            )
        if exp == "INTERMEDIATE":
            return (
                "Exchange-traded Nifty 50 ETF (0.04% TER, -0.05% tracking difference) for low-cost intraday index execution."
            )
        return (
            "Ultra-low-cost institutional liquidity vehicle (0.04% TER, -0.05% tracking error, Rs 36,800 Cr AUM) for "
            "precision index beta deployment."
        )

    if symbol == "PPFAS-FLEXI":
        if exp == "BEGINNER":
            return (
                "A professional fund team invests across large, mid, and small companies and holds cash when stocks look "
                "expensive. Best held for 5+ years."
            )
        if exp == "INTERMEDIATE":
            return (
                "Active flexi-cap satellite (0.63% Direct TER, 18% turnover) combining domestic multi-cap equities with "
                "valuation-driven cash buffers."
            )
        return (
            "Valuation-disciplined multi-cap active sleeve (0.63% TER, Rs 84,600 Cr AUM) providing downside capture "
            "moderation via tactical cash/TREPS allocation."
        )

    if symbol == "GOLDBEES.NS":
        if exp == "BEGINNER":
            return (
                "Digital units backed by 99.5% pure physical gold without jeweller making charges. Helps protect your "
                "purchasing power when inflation rises."
            )
        if exp == "INTERMEDIATE":
            return (
                "Physical gold bullion ETF (0.79% TER) providing a non-correlated hedge against INR depreciation and equity stress."
            )
        return (
            "Real-asset diversifier (0.79% TER, 11.8% annualised vol) with near-zero equity correlation and embedded INR/USD hedge."
        )

    if symbol == "TCS.NS":
        if exp == "BEGINNER":
            return (
                "A single profitable company with almost no debt. Only a small slice is suggested because owning one stock "
                "is always riskier than owning a 50-stock index fund."
            )
        if exp == "INTERMEDIATE":
            return (
                "High-ROCE large-cap IT franchise (0.08x D/E, 46.5x interest cover, 98% OCF/PAT) as a researched single-stock satellite."
            )
        return (
            "Quality factor single-equity satellite (24.8% OPM, 0.08x D/E, 46.5x interest cover, 98% OCF/PAT conversion, 28.9x P/E)."
        )

    return "Selected based on your readiness state, horizon, and risk capacity."


def build_recommendations(
    *,
    p: FinancialProfile,
    status: str,
    completeness: str,
    surplus: Decimal,
    coverage: Decimal | None,
    emergency_target: Decimal,
    emergency_gap: Decimal,
    replenish_monthly: Decimal,
    goal_monthly: Decimal | None,
    investable: Decimal,
    unallocated_liquid: Decimal,
    horizon_for_capacity: int | None,
    tolerance_band: str,
    capacity_band: str,
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    exp = p.experience if p.experience in ("BEGINNER", "INTERMEDIATE", "EXPERIENCED") else "BEGINNER"
    tone_label = _tone_for_experience(exp)
    pos_surplus = max(ZERO, surplus)

    # 1. Compute exact monthly rupee flow allocation
    high_rate_debts = [d for d in p.debts if d.outstanding > ZERO and d.rate_pct > READINESS.high_interest_pct]
    overdue_debts = [d for d in p.debts if d.is_overdue]

    remaining_surplus = pos_surplus
    if status == "NOT_READY":
        # Priority in NOT_READY: overdue/high-cost debt + emergency reserve floor + short-term goal reserve
        debt_accel = ZERO
        if overdue_debts or high_rate_debts:
            debt_accel = min(remaining_surplus, (pos_surplus * D("0.40")).quantize( Decimal("1") ))
            remaining_surplus -= debt_accel
        emerg_alloc = min(remaining_surplus, max(replenish_monthly, remaining_surplus * D("0.70")) if emergency_gap > ZERO else ZERO)
        remaining_surplus -= emerg_alloc
        goal_alloc = remaining_surplus
        market_deploy = ZERO
    elif status == "PREPARATION":
        debt_accel = ZERO
        if high_rate_debts:
            debt_accel = min(remaining_surplus, (pos_surplus * D("0.25")).quantize(Decimal("1")))
            remaining_surplus -= debt_accel
        emerg_alloc = min(remaining_surplus, replenish_monthly)
        remaining_surplus -= emerg_alloc
        goal_need_val = goal_monthly or ZERO
        goal_alloc = min(remaining_surplus, goal_need_val)
        remaining_surplus -= goal_alloc
        # In PREPARATION, deploy cautiously: either user's designated amount (capped at remaining_surplus) or 50% of investable
        if p.designated > ZERO:
            market_deploy = min(remaining_surplus, p.designated)
        else:
            market_deploy = (remaining_surplus * D("0.50")).quantize(Decimal("0.01"))
        # Any uninvested remainder boosts emergency or goal reserve
        leftover = remaining_surplus - market_deploy
        if emergency_gap > ZERO:
            emerg_alloc += leftover
        else:
            goal_alloc += leftover
    else:
        # READY_TO_EXPLORE
        debt_accel = ZERO
        emerg_alloc = min(remaining_surplus, replenish_monthly)
        remaining_surplus -= emerg_alloc
        goal_need_val = goal_monthly or ZERO
        goal_alloc = min(remaining_surplus, goal_need_val)
        remaining_surplus -= goal_alloc
        if p.designated > ZERO:
            market_deploy = min(remaining_surplus, p.designated)
        else:
            market_deploy = remaining_surplus
        leftover = remaining_surplus - market_deploy
        goal_alloc += leftover

    # 2. Compute lump-sum liquid savings breakdown
    if status == "NOT_READY":
        immediate_reserve_boost = unallocated_liquid
        staged_lump_sum = ZERO
        tranches_months = 0
    elif status == "PREPARATION":
        immediate_reserve_boost = min(unallocated_liquid, emergency_gap)
        staged_lump_sum = max(ZERO, unallocated_liquid - immediate_reserve_boost)
        tranches_months = 6 if staged_lump_sum > ZERO else 0
    else:
        immediate_reserve_boost = min(unallocated_liquid, emergency_gap)
        staged_lump_sum = max(ZERO, unallocated_liquid - immediate_reserve_boost)
        tranches_months = 6 if staged_lump_sum > ZERO else 0

    # 3. Determine portfolio weights and target rupee budget
    horizon_m = horizon_for_capacity if horizon_for_capacity is not None else 36
    if status == "NOT_READY":
        # Safe parking allocation for their monthly savings / reserve building
        safe_budget = pos_surplus
        weights = [
            ("NIPPON-LIQUID", "Nippon India Liquid Fund - Direct Plan - Growth", "ETF", "Emergency & Goal Safety Parking", 80, "PARK_SAFELY_UNTIL_READY"),
            ("SETF10GILT.NS", "SBI Nifty 10 yr Benchmark G-Sec ETF", "FIXED_INCOME", "Sovereign Bond Buffer", 20, "PARK_SAFELY_UNTIL_READY"),
        ]
        equity_pct, fixed_pct, gold_pct = 0, 100, 0
    elif status == "PREPARATION" or horizon_m < 36 or capacity_band == "LOW" or tolerance_band == "LOW":
        safe_budget = market_deploy if market_deploy > ZERO else pos_surplus
        weights = [
            ("NIPPON-LIQUID", "Nippon India Liquid Fund - Direct Plan - Growth", "ETF", "Liquid Stability Anchor", 45, "STAGE_CAUTIOUSLY"),
            ("SETF10GILT.NS", "SBI Nifty 10 yr Benchmark G-Sec ETF", "FIXED_INCOME", "Sovereign Fixed Income", 25, "STAGE_CAUTIOUSLY"),
            ("UTI-NIFTY50", "UTI Nifty 50 Index Fund - Direct Plan - Growth", "INDEX_FUND", "Core Large-Cap Index SIP", 20, "STAGE_CAUTIOUSLY"),
            ("GOLDBEES.NS", "Nippon India ETF Gold BeES", "GOLD", "Inflation & Currency Hedge", 10, "STAGE_CAUTIOUSLY"),
        ]
        equity_pct, fixed_pct, gold_pct = 20, 70, 10
    else:
        safe_budget = market_deploy
        if exp == "BEGINNER":
            weights = [
                ("UTI-NIFTY50", "UTI Nifty 50 Index Fund - Direct Plan - Growth", "INDEX_FUND", "Core Automated Index SIP", 50, "DEPLOY_NOW"),
                ("PPFAS-FLEXI", "Parag Parikh Flexi Cap Fund - Direct Plan - Growth", "MUTUAL_FUND", "Diversified Flexi-Cap Growth", 20, "DEPLOY_NOW"),
                ("SETF10GILT.NS", "SBI Nifty 10 yr Benchmark G-Sec ETF", "FIXED_INCOME", "Sovereign Bond Cushion", 20, "DEPLOY_NOW"),
                ("GOLDBEES.NS", "Nippon India ETF Gold BeES", "GOLD", "Gold Diversifier", 10, "DEPLOY_NOW"),
            ]
            equity_pct, fixed_pct, gold_pct = 70, 20, 10
        elif exp == "INTERMEDIATE":
            weights = [
                ("UTI-NIFTY50", "UTI Nifty 50 Index Fund - Direct Plan - Growth", "INDEX_FUND", "Core Nifty 50 Index Anchor", 40, "DEPLOY_NOW"),
                ("PPFAS-FLEXI", "Parag Parikh Flexi Cap Fund - Direct Plan - Growth", "MUTUAL_FUND", "Active Flexi-Cap Satellite", 25, "DEPLOY_NOW"),
                ("TCS.NS", "Tata Consultancy Services Ltd", "EQUITY", "Quality Large-Cap Equity Satellite", 10, "DEPLOY_NOW"),
                ("SETF10GILT.NS", "SBI Nifty 10 yr Benchmark G-Sec ETF", "FIXED_INCOME", "Sovereign Duration Ballast", 15, "DEPLOY_NOW"),
                ("GOLDBEES.NS", "Nippon India ETF Gold BeES", "GOLD", "Gold Hedge", 10, "DEPLOY_NOW"),
            ]
            equity_pct, fixed_pct, gold_pct = 75, 15, 10
        else:
            # EXPERIENCED
            weights = [
                ("NIFTYBEES.NS", "Nippon India ETF Nifty 50 BeES", "ETF", "Ultra-Low-Cost Core Index Beta (0.04% TER)", 35, "DEPLOY_NOW"),
                ("PPFAS-FLEXI", "Parag Parikh Flexi Cap Fund - Direct Plan - Growth", "MUTUAL_FUND", "Valuation-Conscious Multi-Cap Alpha", 25, "DEPLOY_NOW"),
                ("TCS.NS", "Tata Consultancy Services Ltd", "EQUITY", "High-ROCE Cash-Generative Equity Sleeve", 15, "DEPLOY_NOW"),
                ("SETF10GILT.NS", "SBI Nifty 10 yr Benchmark G-Sec ETF", "FIXED_INCOME", "10Y Sovereign G-Sec Duration Sleeve", 15, "DEPLOY_NOW"),
                ("GOLDBEES.NS", "Nippon India ETF Gold BeES", "GOLD", "Real-Asset Tail Hedge", 10, "DEPLOY_NOW"),
            ]
            equity_pct, fixed_pct, gold_pct = 75, 15, 10

    asset_allocations: list[dict[str, Any]] = []
    for sym, name, atype, role, pct_weight, act_status in weights:
        m_amt = (safe_budget * D(pct_weight) / D(100)).quantize(Decimal("0.01"))
        l_amt = (staged_lump_sum * D(pct_weight) / D(100)).quantize(Decimal("0.01"))
        asset_allocations.append({
            "symbol": sym,
            "name": name,
            "asset_type": atype,
            "role": role,
            "allocation_pct": pct_weight,
            "monthly_amount_inr": dstr(m_amt),
            "lump_sum_amount_inr": dstr(l_amt),
            "action_status": act_status,
            "rationale": _instrument_rationale(sym, exp, status),
        })

    # 4. Build experience-tailored textual headline, summary, and detailed action plan
    cov_str = f"{coverage:.1f} months" if coverage is not None else "unknown months"
    emi_pct_str = f"{(p.emi / p.income * D(100)):.1f}%" if p.income > ZERO else "0.0%"

    if status == "NOT_READY":
        blocker_text = "; ".join(f["label"] for f in blockers) if blockers else "incomplete profile inputs"
        if exp == "BEGINNER":
            headline = f"Pause stock market investing for now: protect your {fmt_inr(pos_surplus)}/month surplus in safe liquid reserves first"
            summary = (
                f"Right now, your profile is classified as NOT READY for stock market risk because of: {blocker_text}. "
                f"In plain English, your emergency safety net covers {cov_str} of essential bills (the safe minimum floor is 2 months, "
                f"and the full target is 6 months or {fmt_inr(emergency_target)}). If you put your money into stocks or equity mutual funds today "
                f"and the market drops 20% just when you need cash, you would be forced to sell at a loss. Instead, direct 100% of your "
                f"available {fmt_inr(pos_surplus)} monthly surplus into safe, penalty-free liquid instruments until your safety net and near-term goal are funded."
            )
        elif exp == "INTERMEDIATE":
            headline = f"Capital preservation phase: allocate {fmt_inr(pos_surplus)}/month to T-Bill liquid reserves before taking equity beta"
            summary = (
                f"Deterministic readiness is NOT_READY due to binding constraints ({blocker_text}). Emergency liquidity stands at {cov_str} "
                f"(shortfall of {fmt_inr(emergency_gap)} to the 6-month target of {fmt_inr(emergency_target)}), and EMI service consumes {emi_pct_str} of take-home pay. "
                f"Taking equity duration risk with zero unallocated investable surplus ({fmt_inr(investable)}/month) exposes the household balance sheet "
                f"to forced liquidation risk. Channel {fmt_inr(emerg_alloc)}/month to emergency replenishment and {fmt_inr(goal_alloc)}/month to short-duration liquid holdings."
            )
        else:
            headline = f"Balance-sheet constraint active (NOT_READY): zero equity beta until liquidity floor and short-horizon liabilities clear"
            summary = (
                f"Hard capacity blockers ({blocker_text}) cap risk capacity at {capacity_band}. With emergency coverage at {cov_str} "
                f"(target {fmt_inr(emergency_target)}, gap {fmt_inr(emergency_gap)}), debt service at {emi_pct_str} of net income, and net free investable cash flow at "
                f"{fmt_inr(investable)}/month, optimal allocation is 100% money-market/short-duration sovereign paper (0% equity beta) to eliminate sequence-of-returns "
                f"and forced-drawdown risk."
            )
    elif status == "PREPARATION":
        warn_text = "; ".join(f["label"] for f in warnings) if warnings else "moderate capacity or tolerance score"
        if exp == "BEGINNER":
            headline = f"Preparation stage: start a small, steady {fmt_inr(market_deploy)}/month plan while finishing your {fmt_inr(emergency_target)} safety net"
            summary = (
                f"You have positive cash flow ({fmt_inr(pos_surplus)} left over each month), so you do not need to sit on the sidelines completely, "
                f"but a few guardrails need attention ({warn_text}). The safest beginner approach is a two-track plan: put {fmt_inr(emerg_alloc)}/month "
                f"into your emergency reserve and {fmt_inr(goal_alloc)}/month toward your goal reserve, while starting a conservative, low-stress "
                f"investment of {fmt_inr(market_deploy)}/month ({equity_pct}% index funds, {fixed_pct}% liquid/government bonds, {gold_pct}% gold)."
            )
        elif exp == "INTERMEDIATE":
            headline = f"Staged preparation blueprint: deploy {fmt_inr(market_deploy)}/month ({equity_pct}/{fixed_pct}/{gold_pct} split) alongside reserve completion"
            summary = (
                f"Profile classifies as PREPARATION ({warn_text}). Net monthly surplus is {fmt_inr(pos_surplus)} with {cov_str} of emergency cover. "
                f"After reserving {fmt_inr(emerg_alloc)}/month for emergency target completion and {fmt_inr(goal_alloc)}/month for goal funding, "
                f"deploy {fmt_inr(market_deploy)}/month into a volatility-dampened {equity_pct}% equity / {fixed_pct}% fixed-income & liquid / {gold_pct}% gold mix."
            )
        else:
            headline = f"Transition regime (PREPARATION): {fmt_inr(market_deploy)}/month risk-budgeted deployment with {fixed_pct}% low-duration ballast"
            summary = (
                f"Readiness is in PREPARATION ({warn_text}; Tolerance: {tolerance_band}, Capacity: {capacity_band}). From {fmt_inr(pos_surplus)} monthly free cash flow, "
                f"{fmt_inr(emerg_alloc)}/month is ring-fenced for reserve amortisation (12-month target path) and {fmt_inr(goal_alloc)}/month for goal liability matching. "
                f"The remaining {fmt_inr(market_deploy)}/month is allocated {equity_pct}% passive large-cap beta / {fixed_pct}% T-bill & G-Sec / {gold_pct}% gold."
            )
    else:
        # READY_TO_EXPLORE
        if exp == "BEGINNER":
            headline = f"Ready to invest: put {fmt_inr(market_deploy)}/month to work in a simple, diversified {equity_pct}% Equity / {fixed_pct}% Bond / {gold_pct}% Gold plan"
            summary = (
                f"Great news: your emergency fund covers {cov_str} of essential expenses ({fmt_inr(p.emergency)} saved), your loan EMIs are manageable ({emi_pct_str} of income), "
                f"and your monthly surplus is {fmt_inr(pos_surplus)}. After setting aside {fmt_inr(goal_alloc)}/month for your goal reserve, you have "
                f"{fmt_inr(investable)}/month of genuinely free investable money (and you designated {fmt_inr(p.designated)}/month). "
                f"Because you selected Beginner mode, we recommend avoiding risky stock-picking and instead using low-cost index and flexi-cap funds ({equity_pct}%), "
                f"a Government of India bond ETF ({fixed_pct}%), and Gold BeES ({gold_pct}%) totalling {fmt_inr(market_deploy)}/month."
            )
        elif exp == "INTERMEDIATE":
            headline = f"Core-satellite deployment ready: {fmt_inr(market_deploy)}/month across {equity_pct}% Equity, {fixed_pct}% Sovereign G-Sec, and {gold_pct}% Gold"
            summary = (
                f"All readiness guardrails are cleared (Capacity: {capacity_band}, Tolerance: {tolerance_band}, Emergency cover: {cov_str}, Surplus: {fmt_inr(pos_surplus)}/month). "
                f"Net of goal funding ({fmt_inr(goal_alloc)}/month) and reserve maintenance ({fmt_inr(emerg_alloc)}/month), free investable capacity is {fmt_inr(investable)}/month. "
                f"The recommended {fmt_inr(market_deploy)}/month blueprint pairs a Nifty 50 index core (40%) with an active flexi-cap sleeve (25%), a quality large-cap equity satellite (10%), "
                f"10-year sovereign G-Secs (15%), and gold (10%)."
            )
        else:
            headline = f"Quantitative allocation brief (READY_TO_EXPLORE): {fmt_inr(market_deploy)}/month systematic deployment + {fmt_inr(staged_lump_sum)} staged liquidity"
            summary = (
                f"Balance-sheet and behavioural constraints clear all thresholds (Capacity: {capacity_band}, Tolerance: {tolerance_band}, Coverage: {cov_str}, "
                f"EMI/Income: {emi_pct_str}, Horizon: {horizon_m} months). Out of {fmt_inr(pos_surplus)}/month operating surplus, {fmt_inr(investable)}/month is free risk capital. "
                f"We structure a {fmt_inr(market_deploy)}/month multi-asset institutional basket: 35% Nifty 50 ETF beta (0.04% TER), 25% active flexi-cap, "
                f"15% high-ROCE quality equity factor (TCS.NS), 15% sovereign 10Y G-Sec duration (SETF10GILT.NS), and 10% Gold BeES."
            )

    textual_guidelines: list[str] = [
        f"Monthly Cash-Flow Rule: Out of your {fmt_inr(p.income)} take-home income, {fmt_inr(p.essential + p.nonessential + p.emi + p.other)} goes to expenses and EMIs, leaving {fmt_inr(pos_surplus)} monthly surplus.",
        f"Emergency & Goal Ring-Fencing: Direct {fmt_inr(emerg_alloc)}/month to emergency reserves and {fmt_inr(goal_alloc)}/month to goal reserves before taking market risk.",
        f"Monthly Market Deployment: Invest {fmt_inr(market_deploy)}/month across the {len(asset_allocations)} recommended instruments shown in the table below.",
    ]
    if staged_lump_sum > ZERO:
        textual_guidelines.append(
            f"Unallocated Lump-Sum Savings ({fmt_inr(staged_lump_sum)}): Do not invest all {fmt_inr(staged_lump_sum)} on a single day. Stage it in {tranches_months} equal monthly tranches of {fmt_inr(staged_lump_sum / D(tranches_months))} while keeping the waiting cash in Nippon India Liquid Fund."
        )
    else:
        textual_guidelines.append(
            f"Liquid Savings Protection: Your existing {fmt_inr(p.liquid)} liquid savings are already assigned to your emergency reserve ({fmt_inr(p.emergency)}) and goal reserve ({fmt_inr(p.goal_reserved)}). Do not pull from those reserves to buy volatile assets."
        )

    return {
        "experience_level": exp,
        "tone_label": tone_label,
        "readiness_status": status,
        "headline": headline,
        "summary": summary,
        "textual_guidelines": textual_guidelines,
        "category_split_pct": {
            "equity_pct": equity_pct,
            "fixed_income_and_liquid_pct": fixed_pct,
            "gold_pct": gold_pct,
        },
        "monthly_plan": {
            "monthly_income_inr": dstr(p.income),
            "committed_outflow_inr": dstr(p.essential + p.nonessential + p.emi + p.other),
            "monthly_surplus_inr": dstr(surplus),
            "emergency_topup_inr": dstr(emerg_alloc),
            "emergency_topup_pct": _pct_of(emerg_alloc, pos_surplus),
            "debt_prepayment_inr": dstr(debt_accel),
            "debt_prepayment_pct": _pct_of(debt_accel, pos_surplus),
            "goal_reserve_inr": dstr(goal_alloc),
            "goal_reserve_pct": _pct_of(goal_alloc, pos_surplus),
            "investable_capacity_inr": dstr(investable),
            "recommended_market_deployment_inr": dstr(market_deploy),
            "recommended_market_deployment_pct": _pct_of(market_deploy, pos_surplus),
        },
        "lump_sum_plan": {
            "liquid_savings_inr": dstr(p.liquid),
            "emergency_locked_inr": dstr(p.emergency),
            "goal_locked_inr": dstr(p.goal_reserved),
            "unallocated_liquid_inr": dstr(unallocated_liquid),
            "immediate_reserve_boost_inr": dstr(immediate_reserve_boost),
            "staged_market_deployment_inr": dstr(staged_lump_sum),
            "recommended_tranches_months": tranches_months,
            "monthly_tranche_inr": dstr(staged_lump_sum / D(tranches_months)) if tranches_months > 0 else "0.00",
        },
        "asset_allocations": asset_allocations,
    }


