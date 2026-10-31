"""Three-Clock Timing Engine: every precedence branch, market-data states and the rule that market context never overrides finance."""

from datetime import date, timedelta
from decimal import Decimal

from app.services.financial_engine.market import market_snapshot
from app.services.financial_engine.readiness import assess_readiness
from app.services.financial_engine.timing import assess_timing
from app.services.financial_engine.dates import add_months
from app.services.financial_engine.rules import TIMING_RULE_VERSION
from tests.factories import AS_OF, healthy, priya, rahul


def timing(profile, market=None, as_of=AS_OF):
    readiness = assess_readiness(profile, as_of)
    return assess_timing(profile, readiness, market, as_of)


def rising_market(as_of=AS_OF, days=500, age=0, synthetic=True):
    end = as_of - timedelta(days=age)
    points = []
    for i in range(days):
        d = end - timedelta(days=days - i)
        points.append((d, Decimal(f"{100 * (1.0004 ** i):.4f}")))
    return market_snapshot(points, as_of, asset_name="Test index", is_synthetic=synthetic, source="test")


def test_rule_version_is_recorded():
    assert timing(healthy())["rule_version"] == TIMING_RULE_VERSION


def test_not_ready_never_returns_a_deployment_positive_verdict():
    holding_codes = {"INPUTS_INCOMPLETE", "CASH_FLOW_FIRST", "RESERVE_FIRST", "GOAL_PROTECTION", "NOT_READY_HOLD"}
    for profile in (rahul(), healthy(essential=Decimal("55000")), healthy(questionnaire=None)):
        result = timing(profile, market=rising_market())
        assert result["readiness_status"] == "NOT_READY"
        assert result["verdict_code"] in holding_codes
        text = result["verdict"].lower()
        assert "permits further" not in text and "preparation stage" not in text


def test_negative_cash_flow_takes_precedence_over_reserve_and_goal():
    result = timing(healthy(essential=Decimal("55000"), emergency=Decimal("25000"), goal_reserved=Decimal("0")))
    assert result["verdict_code"] == "CASH_FLOW_FIRST"
    assert result["clocks"]["money"]["status"] == "CRITICAL"


def test_insufficient_reserve_dominates_attractive_market_data():
    result = timing(rahul(), market=rising_market())
    assert result["verdict_code"] == "RESERVE_FIRST"
    assert result["clocks"]["market"]["status"] == "OK"


def test_goal_within_twelve_months_is_protected_when_reserves_are_fine():
    profile = healthy(goal_amount=Decimal("100000"), goal_deadline=add_months(AS_OF, 8), goal_liquidity="MEDIUM")
    result = timing(profile)
    assert result["verdict_code"] == "GOAL_PROTECTION"
    assert result["clocks"]["goal"]["status"] == "CRITICAL"


def test_high_liquidity_inside_three_years_is_goal_protection():
    profile = healthy(goal_amount=Decimal("100000"), goal_deadline=add_months(AS_OF, 24), goal_liquidity="HIGH")
    result = timing(profile)
    assert result["verdict_code"] == "GOAL_PROTECTION"


def test_expired_goal_is_critical_and_holds_deployment():
    profile = healthy(goal_amount=Decimal("100000"), goal_deadline=date(2026, 10, 30))
    result = timing(profile)
    assert result["clocks"]["goal"]["status"] == "CRITICAL"
    assert result["verdict_code"] == "GOAL_PROTECTION"


def test_missing_goal_horizon_is_unavailable_and_incomplete_when_named():
    no_goal = timing(healthy())
    assert no_goal["clocks"]["goal"]["status"] == "UNAVAILABLE"
    named = timing(healthy(goal_name="Car", goal_amount=None, goal_deadline=None))
    assert named["verdict_code"] == "INPUTS_INCOMPLETE"
    assert "No positive conclusion" in named["verdict"]


def test_preparation_permits_education_only():
    result = timing(healthy(emergency=Decimal("90000"), goal_reserved=Decimal("0")))
    assert result["readiness_status"] == "PREPARATION"
    assert result["verdict_code"] == "EDUCATE_ONLY"
    assert "not a deployment signal" in result["verdict"]


def test_ready_to_explore_permits_research_not_a_buy():
    result = timing(priya())
    assert result["verdict_code"] == "RESEARCH_PERMITTED"
    assert "not a buy recommendation" in result["verdict"]


def test_missing_market_data_is_stated_explicitly():
    result = timing(priya(), market=None)
    assert result["clocks"]["market"]["status"] == "UNAVAILABLE"
    assert "No market series was selected" in result["clocks"]["market"]["headline"]


def test_future_dated_market_data_is_invalid():
    points = [(AS_OF + timedelta(days=3), Decimal("101")), (AS_OF - timedelta(days=1), Decimal("100"))]
    market = market_snapshot(points, AS_OF, asset_name="Test", is_synthetic=True, source="test")
    result = timing(priya(), market=market)
    assert market["status"] == "FUTURE_DATA_INVALID"
    assert result["clocks"]["market"]["status"] == "INVALID"


def test_stale_market_data_is_withheld():
    market = rising_market(age=100)
    result = timing(priya(), market=market)
    assert market["status"] == "STALE"
    assert result["clocks"]["market"]["status"] == "STALE"
    assert "annualised_volatility_pct" not in market or market.get("annualised_volatility_pct") is None


def test_synthetic_market_context_is_labelled_as_synthetic():
    result = timing(priya(), market=rising_market(synthetic=True))
    assert "synthetic" in result["clocks"]["market"]["explanation"].lower()
    assert result["clocks"]["market"]["data"]["is_synthetic"] is True


def test_short_history_has_no_trailing_twelve_month_return():
    market = rising_market(days=200)
    assert market["trailing_12m_return_pct"] is None


def test_market_sentiment_never_changes_the_verdict_code():
    bearish = timing(priya(), market=rising_market())
    neutral = timing(priya(), market=None)
    assert bearish["verdict_code"] == neutral["verdict_code"] == "RESEARCH_PERMITTED"
    rule9 = [p for p in bearish["precedence"] if p["rule"] == "R9"][0]
    assert rule9["triggered"] is True


def test_no_buy_date_or_bottom_predictions_are_generated():
    text = timing(priya(), market=rising_market())["verdict"].lower()
    for forbidden in ("buy on", "bottom", "entry point", "guaranteed"):
        assert forbidden not in text
