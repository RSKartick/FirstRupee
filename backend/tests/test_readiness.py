"""Readiness engine: calculations, classification, completeness and date handling. All tests inject the reference date."""

from datetime import date
from decimal import Decimal

from app.services.financial_engine.dates import add_months
from app.services.financial_engine.readiness import assess_readiness
from app.services.financial_engine.rules import READINESS_RULE_VERSION
from tests.factories import AS_OF, GOOD_QUESTIONNAIRE, healthy, priya, rahul


def codes(result):
    return {f["code"] for f in result["findings"]}


def run(profile, as_of=AS_OF):
    return assess_readiness(profile, as_of)


def test_positive_surplus_and_ready_baseline():
    r = run(healthy())
    assert r["metrics"]["monthly_surplus"] == "25000.00"
    assert r["status"] == "READY_TO_EXPLORE"
    assert r["completeness"] == "COMPLETE"
    assert r["rule_version"] == READINESS_RULE_VERSION


def test_zero_surplus_is_a_blocker():
    r = run(healthy(essential=Decimal("40000"), nonessential=Decimal("15000")))
    assert r["metrics"]["monthly_surplus"] == "0.00"
    assert "ZERO_SURPLUS" in codes(r)
    assert r["status"] == "NOT_READY"


def test_negative_surplus_is_a_blocker_and_never_ready():
    r = run(healthy(essential=Decimal("55000")))
    assert r["metrics"]["monthly_surplus"] == "-5000.00"
    assert "NEGATIVE_SURPLUS" in codes(r)
    assert r["status"] == "NOT_READY"
    assert r["metrics"]["investable_monthly"] == "0.00"


def test_zero_essential_expenses_make_coverage_unknown_and_incomplete():
    r = run(healthy(essential=Decimal("0")))
    assert r["metrics"]["emergency_coverage_months"] is None
    assert r["completeness"] == "INCOMPLETE"
    assert r["status"] == "NOT_READY"
    assert "COVERAGE_UNKNOWN" in codes(r)


def test_emergency_reserve_below_floor_blocks():
    r = run(healthy(emergency=Decimal("25000"), goal_reserved=Decimal("0")))
    assert r["metrics"]["emergency_coverage_months"] == "1.00"
    assert "EMERGENCY_BELOW_FLOOR" in codes(r)
    assert r["status"] == "NOT_READY"


def test_emergency_plus_goal_reserve_cannot_exceed_liquid():
    r = run(healthy(emergency=Decimal("280000"), goal_reserved=Decimal("30000"), liquid=Decimal("300000")))
    assert "RESERVES_EXCEED_LIQUID" in codes(r)
    assert r["status"] == "NOT_READY"


def test_emergency_reserve_alone_above_liquid_is_flagged():
    r = run(healthy(emergency=Decimal("350000")))
    assert "RESERVES_EXCEED_LIQUID" in codes(r)


def test_liquid_above_total_savings_is_inconsistent():
    r = run(healthy(total_savings=Decimal("200000"), liquid=Decimal("300000")))
    assert "INCONSISTENT_SAVINGS" in codes(r)
    assert r["status"] == "NOT_READY"


def test_missing_questionnaire_is_unknown_not_low():
    r = run(healthy(questionnaire=None))
    assert r["metrics"]["risk_tolerance_band"] == "UNKNOWN"
    assert r["metrics"]["risk_capacity_band"] == "UNKNOWN"
    assert r["completeness"] == "INCOMPLETE"
    assert r["status"] == "NOT_READY"


def test_existing_liabilities_without_loan_details_are_a_limitation():
    r = run(healthy(liabilities=Decimal("100000")))
    assert any("without per-loan details" in item for item in r["limitations"])
    assert r["status"] == "READY_TO_EXPLORE"


def test_high_emi_burden_blocks():
    r = run(healthy(emi=Decimal("28000"), nonessential=Decimal("0")))
    assert "EMI_BURDEN_HIGH" in codes(r)
    assert r["status"] == "NOT_READY"


def test_elevated_emi_burden_warns_without_blocking():
    r = run(healthy(emi=Decimal("25000"), nonessential=Decimal("0")))
    assert "EMI_BURDEN_ELEVATED" in codes(r)
    assert r["status"] == "PREPARATION"


def test_goal_with_name_but_no_deadline_is_incomplete():
    r = run(healthy(goal_name="Car", goal_amount=None, goal_deadline=None))
    assert "Goal deadline (needed to measure the goal horizon)" in r["missing_information"]
    assert r["status"] == "NOT_READY"


def test_past_goal_deadline_blocks():
    r = run(healthy(goal_amount=Decimal("500000"), goal_deadline=date(2026, 10, 30)))
    assert r["metrics"]["goal_horizon_months"] == -1
    assert "GOAL_DATE_PASSED" in codes(r)
    assert r["status"] == "NOT_READY"


def test_goal_one_day_before_month_end_boundary():
    r = run(healthy(goal_amount=Decimal("100000"), goal_deadline=date(2026, 11, 29)))
    assert r["metrics"]["goal_horizon_months"] == 0
    assert "GOAL_WITHIN_12_MONTHS" in codes(r)


def test_goal_on_month_end_counts_as_one_month():
    r = run(healthy(goal_amount=Decimal("100000"), goal_deadline=date(2026, 11, 30)))
    assert r["metrics"]["goal_horizon_months"] == 1


def test_leap_year_horizon_is_twelve_months():
    r = run(healthy(goal_amount=Decimal("100000"), goal_deadline=date(2025, 2, 28)), as_of=date(2024, 2, 29))
    assert r["metrics"]["goal_horizon_months"] == 12
    assert "GOAL_1_TO_3_YEARS" in codes(r) or "GOAL_LONG_HORIZON" in codes(r)


def test_injected_reference_date_is_reproducible():
    profile = healthy(goal_amount=Decimal("100000"), goal_deadline=date(2027, 10, 31))
    first = run(profile, as_of=date(2026, 10, 31))
    second = run(profile, as_of=date(2026, 10, 31))
    later = run(profile, as_of=date(2026, 12, 31))
    assert first == second
    assert first["metrics"]["goal_horizon_months"] == 12
    assert later["metrics"]["goal_horizon_months"] == 10


def test_goal_requirement_above_surplus_warns_and_prepares():
    r = run(healthy(goal_amount=Decimal("1200000"), goal_deadline=add_months(AS_OF, 36), goal_reserved=Decimal("20000")))
    assert "GOAL_NOT_FUNDED_BY_SURPLUS" in codes(r)
    assert r["metrics"]["goal_monthly_need"] == "32777.78"
    assert r["status"] == "PREPARATION"


def test_conflicting_tolerance_and_capacity_blocks():
    r = run(healthy(
        emergency=Decimal("25000"), goal_reserved=Decimal("0"),
        questionnaire={**GOOD_QUESTIONNAIRE, "drawdown_reaction": "ADD_IF_THESIS_VALID"},
    ))
    assert r["metrics"]["risk_tolerance_band"] == "HIGH"
    assert r["metrics"]["risk_capacity_band"] == "LOW"
    assert "TOLERANCE_CAPACITY_MISMATCH" in codes(r)
    assert r["status"] == "NOT_READY"


def test_performance_chasing_is_separate_from_tolerance():
    keep = run(healthy(questionnaire={**GOOD_QUESTIONNAIRE, "gains_reaction": "KEEP_PLAN"}))
    chase = run(healthy(questionnaire={**GOOD_QUESTIONNAIRE, "gains_reaction": "INVEST_MORE_ON_GAINS"}))
    assert keep["metrics"]["risk_tolerance_score"] == chase["metrics"]["risk_tolerance_score"]
    assert chase["metrics"]["performance_chasing"] == "ELEVATED"
    assert "PERFORMANCE_CHASING_INDICATOR" in codes(chase)


def test_designated_amount_above_investable_warns():
    r = run(healthy(designated=Decimal("30000")))
    assert r["metrics"]["investable_monthly"] == "25000.00"
    assert "DESIGNATED_EXCEEDS_CAPACITY" in codes(r)


def test_debt_emi_mismatch_is_a_blocker():
    from app.services.financial_engine.readiness import DebtItem
    r = run(healthy(debts=(DebtItem("CAR_LOAN", Decimal("100000"), Decimal("9"), Decimal("1000"), 60, False),),
                    liabilities=Decimal("100000")))
    assert "DEBT_EMI_MISMATCH" in codes(r)


def test_overdue_loan_blocks():
    from app.services.financial_engine.readiness import DebtItem
    r = run(healthy(debts=(DebtItem("PERSONAL_LOAN", Decimal("50000"), Decimal("12"), Decimal("5000"), 10, True),),
                    liabilities=Decimal("50000"), emi=Decimal("5000")))
    assert "OVERDUE_DEBT" in codes(r)
    assert r["status"] == "NOT_READY"


def test_demo_rahul_is_not_ready_with_liquidity_constraint():
    r = run(rahul())
    assert r["status"] == "NOT_READY"
    assert r["metrics"]["monthly_surplus"] == "4000.00"
    assert r["metrics"]["emergency_coverage_months"] == "1.00"
    assert r["metrics"]["unallocated_liquid"] == "0.00"
    assert r["metrics"]["investable_monthly"] == "0.00"
    assert {"EMERGENCY_BELOW_FLOOR", "GOAL_WITHIN_12_MONTHS"} <= codes(r)
    assert r["metrics"]["goal_horizon_months"] == 10


def test_demo_priya_is_ready_to_explore_with_investable_capacity():
    r = run(priya())
    assert r["status"] == "READY_TO_EXPLORE"
    assert r["metrics"]["monthly_surplus"] == "40000.00"
    assert r["metrics"]["emergency_coverage_months"] == "8.33"
    assert r["metrics"]["goal_monthly_need"] == "20583.33"
    assert r["metrics"]["investable_monthly"] == "19416.67"
    assert r["metrics"]["designated_monthly"] == "15000.00"
    assert r["metrics"]["risk_tolerance_band"] == "HIGH"
    assert r["metrics"]["risk_capacity_band"] == "HIGH"


def test_every_result_explains_its_next_steps_and_disclaimer():
    r = run(rahul())
    assert r["improvement_steps"]
    assert "not a recommendation" in r["disclaimer"]
    assert r["explanation"]
