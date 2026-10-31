"""Simulator mathematics with known inputs: look-ahead, gaps, cash-flow-neutral return/volatility/drawdown, quarterly accumulation,
delay handling, comparison rules, seeded paths and XIRR."""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pytest

from app.services.simulator.engine import (
    AssetSeries,
    SimulationError,
    build_grid,
    hypothetical_prices,
    rolling_windows,
    run_simulation,
    xirr,
)
from tests.factories import priced_series_points

REF = date(2026, 10, 31)
EVAL = date(2025, 12, 31)
START = date(2024, 1, 1)
END = date(2026, 3, 31)


def flat(price=100.0):
    return priced_series_points(START, END, lambda i, d: price)


def monthly_growth(rate):
    def fn(index, day):
        months = (day.year - START.year) * 12 + (day.month - START.month)
        return 100.0 * (1.0 + rate) ** months
    return fn


def sim(observations=None, comparison=None, **kw):
    params = dict(
        primary=AssetSeries(1, "TST-A", "Test A", True, "unit test", observations if observations is not None else flat()),
        comparison=comparison,
        scenario="LUMP_SUM",
        amount_source="USER_HYPOTHETICAL",
        initial=Decimal("100000"),
        monthly=Decimal("0"),
        frequency="MONTHLY",
        duration_months=12,
        evaluation=EVAL,
        market_path="HISTORICAL",
        cash_interest_pct=Decimal("0"),
        delay_months=0,
        seed=42,
        reference=REF,
    )
    params.update(kw)
    return run_simulation(**params)


def metrics(result):
    return result["primary"]["run"]["metrics"]


# --- market scenarios -------------------------------------------------------

def test_zero_market_return_keeps_capital_and_has_zero_return():
    m = metrics(sim())
    assert m["ending_value"] == "100000.00"
    assert m["time_weighted_return_pct"] == 0.0
    assert m["max_drawdown_pct"] == 0.0


def test_rising_market_gives_known_compound_return():
    m = metrics(sim(observations=priced_series_points(START, END, monthly_growth(0.01))))
    expected = 100000 * 1.01 ** 12
    assert abs(float(m["ending_value"]) - expected) < 1.0
    assert abs(m["time_weighted_return_pct"] - (1.01 ** 12 - 1) * 100) < 0.01
    assert m["annualised_volatility_pct"] < 0.01  # constant monthly growth has no dispersion


def test_falling_market_gives_known_loss_and_drawdown():
    m = metrics(sim(observations=priced_series_points(START, END, monthly_growth(-0.015))))
    assert abs(m["time_weighted_return_pct"] - ((1 - 0.015) ** 12 - 1) * 100) < 0.01
    assert m["max_drawdown_pct"] < -15


# --- contribution strategies ------------------------------------------------

def test_monthly_contributions_do_not_create_gains_on_flat_prices():
    result = sim(initial=Decimal("0"), monthly=Decimal("1000"), duration_months=12)
    m = metrics(result)
    assert m["total_contributions"] == "12000.00"
    assert m["ending_value"] == "12000.00"
    assert m["total_gain_loss"] == "0.00"
    assert m["time_weighted_return_pct"] == 0.0
    assert m["money_weighted_return_pct"] is not None and abs(m["money_weighted_return_pct"]) < 0.01
    assert m["annualised_volatility_pct"] == pytest.approx(0.0, abs=1e-9)
    assert m["max_drawdown_pct"] == 0.0


def test_quarterly_frequency_accumulates_cash_and_invests_on_quarter_ends():
    result = sim(initial=Decimal("0"), monthly=Decimal("1000"), frequency="QUARTERLY", duration_months=12)
    trades = result["primary"]["run"]["trades"]
    assert [round(float(t["amount"])) for t in trades] == [3000, 3000, 3000, 3000]
    assert metrics(result)["cash_held_at_end"] == "0.00"


def test_quarterly_leaves_unfinished_quarter_in_cash_and_reports_it():
    result = sim(initial=Decimal("0"), monthly=Decimal("1000"), frequency="QUARTERLY", duration_months=10)
    assert float(metrics(result)["cash_held_at_end"]) == pytest.approx(1000.0, abs=0.5)


def test_staged_initial_capital_is_deployed_in_tranches_and_sums_to_capital():
    result = sim(scenario="STAGED_INITIAL", duration_months=12)
    trades = result["primary"]["run"]["trades"]
    assert len(trades) == 12
    # Each tranche is rounded to paise on output, so allow at most 12 × ½ paisa of rounding.
    assert sum(float(t["amount"]) for t in trades) == pytest.approx(100000.0, abs=0.1)


def test_delayed_start_deploys_after_the_delay():
    result = sim(scenario="DELAYED_START", delay_months=6, duration_months=12)
    trades = result["primary"]["run"]["trades"]
    assert len(trades) == 1
    assert trades[0]["date"] > result["window"]["start"]


def test_delay_at_or_beyond_horizon_keeps_capital_in_cash_throughout():
    result = sim(scenario="DELAYED_START", delay_months=12, duration_months=12, cash_interest_pct=Decimal("3.5"))
    m = metrics(result)
    assert result["primary"]["run"]["trades"] == []
    assert abs(float(m["cash_held_at_end"]) - 103500.0) < 1.0


# --- historical integrity ---------------------------------------------------

def test_no_look_ahead_future_prices_do_not_change_the_result():
    base = priced_series_points(START, END, lambda i, d: 100.0)
    spiked = [(d, Decimal("900.0000") if d > EVAL else p) for d, p in base]
    assert metrics(sim(observations=base))["ending_value"] == metrics(sim(observations=spiked))["ending_value"]
    assert sim(observations=base)["primary"]["run"]["series"] == sim(observations=spiked)["primary"]["run"]["series"]


def test_evaluation_date_after_last_observation_is_rejected():
    short = priced_series_points(START, date(2025, 6, 30), lambda i, d: 100.0)
    with pytest.raises(SimulationError, match="after the last available price"):
        sim(observations=short, evaluation=date(2025, 12, 31))


def test_evaluation_in_the_future_relative_to_reference_is_rejected():
    with pytest.raises(SimulationError, match="cannot be in the future"):
        sim(evaluation=date(2027, 1, 1))


def test_insufficient_history_is_rejected():
    with pytest.raises(SimulationError, match="Insufficient history"):
        sim(duration_months=60)


def test_long_missing_data_gap_is_an_error_not_a_carry_forward():
    gapped = [(d, p) for d, p in flat() if not (date(2025, 3, 1) <= d <= date(2025, 4, 30))]
    with pytest.raises(SimulationError, match="Missing data"):
        build_grid(gapped, EVAL, 12, REF)


def test_comparison_requires_a_second_instrument():
    with pytest.raises(SimulationError, match="needs a second instrument"):
        sim(scenario="COMPARISON")


def test_incomplete_comparison_is_rejected():
    short_other = AssetSeries(2, "TST-B", "Test B", True, "unit test", priced_series_points(date(2025, 6, 1), END, lambda i, d: 50.0))
    with pytest.raises(SimulationError, match="Insufficient history"):
        sim(scenario="COMPARISON", comparison=short_other)


def test_comparison_uses_the_same_evaluation_date_and_capital():
    other = AssetSeries(2, "TST-B", "Test B", True, "unit test", flat(50.0))
    result = sim(scenario="COMPARISON", comparison=other)
    assert result["comparison"] is not None
    assert result["comparison"]["run"]["metrics"]["total_contributions"] == metrics(result)["total_contributions"]
    assert result["window"]["end"] == result["evaluation_date"]


def test_negative_amounts_and_bad_duration_are_rejected():
    with pytest.raises(SimulationError):
        sim(initial=Decimal("-1"))
    with pytest.raises(SimulationError):
        sim(duration_months=0)
    with pytest.raises(SimulationError):
        sim(initial=Decimal("0"), monthly=Decimal("0"))


# --- hypothetical paths -----------------------------------------------------

def test_seeded_volatile_path_is_reproducible_and_seed_sensitive():
    a = hypothetical_prices("SEEDED_GBM", 100.0, 24, seed=7)
    b = hypothetical_prices("SEEDED_GBM", 100.0, 24, seed=7)
    c = hypothetical_prices("SEEDED_GBM", 100.0, 24, seed=8)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)
    assert float(a.min()) > 0  # never a negative or zero price


def test_hypothetical_results_are_labelled_as_hypothetical():
    result = sim(market_path="SEEDED_GBM")
    assert any("hypothetical" in item.lower() for item in result["assumptions"])
    assert any("not historical" in item.lower() or "not expected" in item.lower() for item in result["limitations"])


# --- return maths ----------------------------------------------------------

def test_xirr_matches_a_known_one_year_example():
    # 365 days exactly (2025 is not a leap year), so the annualised rate is exactly 21%.
    flows = [(date(2025, 1, 1), -100.0), (date(2026, 1, 1), 121.0)]
    assert xirr(flows) == pytest.approx(0.21, abs=1e-6)


def test_xirr_returns_none_without_sign_change():
    assert xirr([(date(2024, 1, 1), -100.0)]) is None


def test_rolling_windows_are_labelled_with_method_and_count():
    series = priced_series_points(START, END, monthly_growth(0.01))
    windows = rolling_windows(series, EVAL)
    assert windows["count"] > 0
    assert "monthly anchor" in windows["method"]
    assert windows["best"]["return_pct"] >= windows["worst"]["return_pct"]


def test_time_weighted_return_equals_value_change_when_there_are_no_contributions():
    result = sim(observations=priced_series_points(START, END, monthly_growth(0.005)), duration_months=6)
    m = metrics(result)
    value_change = (float(m["ending_value"]) / 100000.0 - 1.0) * 100
    assert m["time_weighted_return_pct"] == pytest.approx(value_change, abs=0.01)
    assert result["primary"]["run"]["series"][-1]["cash"] == pytest.approx(0.0, abs=1e-6)


def test_staged_initial_mwr_dates_tranches_when_deployed():
    # With 0% cash interest and 1% monthly growth, staging 12,000 across 12 monthly tranches of 1,000
    # has the exact same market cash flows as a 0-initial, 1,000/month SIP, so their XIRRs must match.
    rising = priced_series_points(START, END, monthly_growth(0.01))
    staged_res = sim(observations=rising, scenario="STAGED_INITIAL", initial=Decimal("12000"), monthly=Decimal("0"),
                     duration_months=12, cash_interest_pct=Decimal("0"))
    sip_res = sim(observations=rising, scenario="LUMP_SUM", initial=Decimal("0"), monthly=Decimal("1000"),
                  duration_months=12, cash_interest_pct=Decimal("0"))
    assert metrics(staged_res)["money_weighted_return_pct"] == pytest.approx(
        metrics(sip_res)["money_weighted_return_pct"], abs=0.05
    )


def test_delayed_start_holds_monthly_contributions_in_cash_until_delay():
    result = sim(scenario="DELAYED_START", initial=Decimal("10000"), monthly=Decimal("1000"),
                 delay_months=6, duration_months=12, cash_interest_pct=Decimal("0"))
    trades = result["primary"]["run"]["trades"]
    # No trades may occur before month 6 (start + 6 months)
    delay_date = date(2025, 6, 30)
    assert all(date.fromisoformat(t["date"]) >= delay_date for t in trades)
