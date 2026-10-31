"""Unit and API integration tests for Indian Government & Statutory Schemes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.schemes import (
    SCHEMES,
    calculate_scheme_growth,
    evaluate_profile_fit,
    get_all_schemes,
    get_scheme_by_id,
)


def test_schemes_catalog_integrity():
    assert len(SCHEMES) == 10
    ids = {s.id for s in SCHEMES}
    assert "ppf" in ids
    assert "nps_tier1" in ids
    assert "ssy" in ids
    assert "scss" in ids
    assert "pomis" in ids
    assert "nsc" in ids
    assert "mssc" in ids
    assert "sgb" in ids
    assert "epf" in ids
    assert "apy" in ids

    for s in SCHEMES:
        assert s.interest_rate_pct > 0
        assert s.name
        assert s.authority
        assert s.tax_treatment in ("EEE", "EET", "TAXABLE_INTEREST", "CAPITAL_GAINS_EXEMPT")


def test_ppf_calculation_matches_sovereign_compounding():
    calc = calculate_scheme_growth(
        scheme_id="ppf",
        monthly_deposit=10000,
        lump_sum=0,
        horizon_years=15,
        tax_bracket_pct=30.0,
    )
    assert calc["horizon_years"] == 15
    assert calc["total_principal_deposited"] == 1800000.0  # 10k * 12 * 15
    assert calc["gross_maturity_amount"] > 3000000.0  # PPF 15Y accumulates > 31L
    assert calc["taxable_interest_liability"] == 0.0  # EEE: tax-free interest
    assert calc["total_tax_saved_over_horizon"] == 540000.0  # 1.2L * 30% * 15


def test_nps_tax_saving_includes_80ccd_1b():
    calc = calculate_scheme_growth(
        scheme_id="nps_tier1",
        monthly_deposit=15000,
        horizon_years=20,
        tax_bracket_pct=30.0,
    )
    assert calc["tax_saved_annual"] == 60000.0  # (1.5L 80C + 50k 80CCD(1B)) * 30%
    assert calc["gross_maturity_amount"] > calc["total_principal_deposited"]


def test_profile_fit_evaluation_ranks_sensibly():
    profile = {
        "monthly_surplus": 60000,
        "goal_horizon_months": 180,  # 15 years
        "goal_name": "Child Higher Education",
        "investment_experience": "BEGINNER",
    }
    evals = evaluate_profile_fit(profile)
    assert len(evals) == 10
    top_scheme_ids = [e["scheme"]["id"] for e in evals[:3]]
    # PPF or SSY should rank at the top for child education with 15-year horizon
    assert "ssy" in top_scheme_ids or "ppf" in top_scheme_ids


def test_schemes_api_endpoints():
    app = create_app()
    client = TestClient(app)

    # 1. List schemes
    resp = client.get("/api/schemes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert data["count"] == 10

    # 2. Filter category
    resp_tax = client.get("/api/schemes?category=TAX_SAVING_AND_WEALTH")
    assert resp_tax.status_code == 200
    assert resp_tax.json()["count"] >= 2

    # 3. Get single scheme
    resp_ppf = client.get("/api/schemes/ppf")
    assert resp_ppf.status_code == 200
    assert resp_ppf.json()["scheme"]["short_name"] == "PPF"

    # 4. Calculate
    resp_calc = client.post("/api/schemes/calculate", json={
        "scheme_id": "ppf",
        "monthly_deposit": 12500,
        "horizon_years": 15,
        "tax_bracket_pct": 30.0,
    })
    assert resp_calc.status_code == 200
    assert resp_calc.json()["calculation"]["gross_maturity_amount"] > 3500000.0
