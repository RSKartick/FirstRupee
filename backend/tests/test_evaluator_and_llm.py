"""Evidence evaluator (claim-level checks) and LLM failure handling. The model is mocked; no network calls are made."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.services.ai_engine import llm, research
from app.services.ai_engine.evaluator import EvidenceView, derived_metrics, evaluate
from app.services.ai_engine.research import AnalystDraft, run_research
from tests.factories import AS_OF, healthy, priya, rahul

ASSET = {"id": 1, "symbol": "TST-EQ", "name": "Test Foods", "asset_type": "EQUITY", "min_horizon_months": 60,
         "is_synthetic": True, "description": "Test", "data_source": "test"}


def record(key, period="FY2025", pub=date(2025, 5, 20), status="SYNTHETIC", source="ANNUAL_REPORT", asset_id=1, **payload):
    base = {"revenueCr": "2165", "opmPct": "15.3", "debtEquity": "0.58", "interestCoverage": "6.1", "ocfCr": "262",
            "patCr": "178", "peRatio": "34.6"}
    base.update(payload)
    return EvidenceView(key=key, asset_id=asset_id, title=f"Record {key}", source_type=source, verification_status=status,
                        publication_date=pub, period=period, summary="s", payload=base)


def fact(key, metric="revenueCr", value="2165", period="FY2025", text="A fact"):
    return {"claim": text, "claim_type": "FACT", "evidence_key": key, "metric_key": metric, "claimed_value": value, "period": period}


def analyst(claims):
    return {"overview": "o", "thesis": "t", "developments": [], "claims": claims}


def devil(claims=(), none_found=True, missing=()):
    return {"counter_thesis": "c", "no_material_negative_finding": none_found, "missing_information": list(missing), "claims": list(claims)}


def run_eval(records, a=None, d=None, readiness=None, asset=ASSET):
    return evaluate(asset=asset, records=records, analyst=a, devil=d if d is not None else devil(), readiness=readiness or healthy_readiness(), as_of=AS_OF)


def healthy_readiness():
    from app.services.financial_engine.readiness import assess_readiness
    return assess_readiness(healthy(), AS_OF)


def check_for(result, claim_text):
    return next(c for c in result["claim_checks"] if c["claim"] == claim_text)


def test_valid_synthetic_evidence_is_demonstrated_not_verified():
    r = run_eval([record("K1")], a=analyst([fact("K1", text="Revenue")]))
    check = check_for(r, "Revenue")
    assert check["status"] == "SYNTHETIC_DEMONSTRATION"
    assert r["data_status"]["synthetic_evidence_used"] is True
    assert r["evidence_quality"]["label"].startswith("Demonstration only")


def test_verified_fresh_evidence_is_supported():
    real_asset = {**ASSET, "is_synthetic": False}
    r = run_eval([record("K1", status="VERIFIED")], a=analyst([fact("K1", text="Revenue")]), asset=real_asset)
    assert check_for(r, "Revenue")["status"] == "SUPPORTED"
    assert r["data_status"]["synthetic_evidence_used"] is False


def test_factual_claim_without_evidence_is_unsupported_and_lowers_quality():
    claims = [fact("K1", text="Supported"), {"claim": "Unsupported statement", "claim_type": "FACT", "evidence_key": None,
                                             "metric_key": None, "claimed_value": None, "period": None}]
    r = run_eval([record("K1")], a=analyst(claims))
    assert check_for(r, "Unsupported statement")["status"] == "UNSUPPORTED"
    assert r["counts"]["unsupported"] == 1
    assert r["evidence_quality"]["score"] < 100  # unsupported claims stay in the denominator


def test_fabricated_evidence_identifier_is_invalid():
    r = run_eval([record("K1")], a=analyst([fact("MADE-UP-9", text="Invented")]))
    check = check_for(r, "Invented")
    assert check["status"] == "INVALID_REFERENCE"
    assert "does not exist" in check["reasons"][0]


def test_evidence_from_another_instrument_is_rejected():
    r = run_eval([record("K1", asset_id=99)], a=analyst([fact("K1", text="Wrong asset")]))
    assert check_for(r, "Wrong asset")["status"] == "INVALID_REFERENCE"


def test_unverified_source_is_reported_as_unverified():
    r = run_eval([record("K1", status="UNVERIFIED")], a=analyst([fact("K1", text="Unverified")]))
    assert check_for(r, "Unverified")["status"] == "UNVERIFIED"


def test_future_dated_source_is_invalid():
    r = run_eval([record("K1", pub=date(2027, 1, 1))], a=analyst([fact("K1", text="Future")]))
    assert check_for(r, "Future")["status"] == "INVALID_REFERENCE"
    assert "after the reference date" in check_for(r, "Future")["reasons"][0]


def test_missing_publication_date_is_not_treated_as_fresh():
    r = run_eval([record("K1", pub=None, status="VERIFIED")], a=analyst([fact("K1", text="Undated")]))
    check = check_for(r, "Undated")
    assert check["status"] == "INVALID_REFERENCE"
    assert "no publication date" in check["reasons"][0]


def test_stale_verified_source_is_supported_but_stale():
    r = run_eval([record("K1", pub=date(2018, 4, 1), status="VERIFIED")], a=analyst([fact("K1", text="Old")]))
    assert check_for(r, "Old")["status"] == "SUPPORTED_STALE"
    assert r["data_status"]["stale_sources"]


def test_numeric_mismatch_is_contradicted_and_blocks_sufficiency():
    r = run_eval([record("K1")], a=analyst([fact("K1", value="9000", text="Wrong number")]), d=devil())
    check = check_for(r, "Wrong number")
    assert check["status"] == "CONTRADICTED"
    assert r["status"] == "INSUFFICIENT_EVIDENCE"


def test_period_mismatch_is_invalid():
    r = run_eval([record("K1", period="FY2025")], a=analyst([fact("K1", period="FY2019", text="Period")]))
    assert check_for(r, "Period")["status"] == "INVALID_REFERENCE"


def test_narrative_claim_without_identifier_counts_as_unsupported():
    r = run_eval([record("K1")], a=analyst([{"claim": "Management is excellent", "claim_type": "QUALITATIVE",
                                             "evidence_key": None, "metric_key": None, "claimed_value": None, "period": None}]))
    assert check_for(r, "Management is excellent")["status"] == "UNSUPPORTED"


def test_hypotheses_are_labelled_and_excluded_from_support():
    r = run_eval([record("K1")], a=analyst([{"claim": "Growth may continue", "claim_type": "HYPOTHESIS", "evidence_key": None,
                                             "metric_key": None, "claimed_value": None, "period": None}]))
    assert check_for(r, "Growth may continue")["status"] == "HYPOTHESIS"
    assert r["counts"]["hypotheses"] == 1
    assert r["counts"]["total_factual_claims"] == 0


def test_llm_text_alone_cannot_create_a_material_risk():
    devil_text = devil(claims=[{"claim": "Leverage is dangerous", "claim_type": "QUALITATIVE", "evidence_key": None,
                                "metric_key": None, "claimed_value": None, "period": None}], none_found=False)
    r = run_eval([record("K1")], a=analyst([fact("K1")]), d=devil_text)
    assert r["material_risks"] == []
    assert r["status"] != "MATERIAL_RISKS_IDENTIFIED"


def test_stored_numbers_that_breach_a_rule_create_a_confirmed_material_risk():
    r = run_eval([record("K1", debtEquity="1.4", status="VERIFIED")], a=analyst([fact("K1", metric="debtEquity", value="1.4", text="Leverage")]))
    assert any(risk["code"] == "HIGH_LEVERAGE" for risk in r["material_risks"])
    assert r["status"] == "MATERIAL_RISKS_IDENTIFIED"


def test_missing_analyst_or_devil_is_insufficient():
    no_analyst = run_eval([record("K1")], a=None, d=devil())
    no_devil = evaluate(asset=ASSET, records=[record("K1")], analyst=analyst([fact("K1")]), devil=None,
                        readiness=healthy_readiness(), as_of=AS_OF)
    assert no_analyst["status"] == "INSUFFICIENT_EVIDENCE"
    assert any("No Research Analyst" in item for item in no_analyst["missing_data"])
    assert no_devil["status"] == "INSUFFICIENT_EVIDENCE"
    assert any("No Devil" in item for item in no_devil["missing_data"])


def test_conflicting_records_are_reported_not_silently_merged():
    r = run_eval([record("K1", period="FY2025"), record("K2", period="FY2025", revenueCr="2000")], a=analyst([fact("K1")]))
    assert r["conflicts"] and r["conflicts"][0]["metric_key"] == "revenueCr"


def test_financial_constraints_take_precedence_over_everything():
    from app.services.financial_engine.readiness import assess_readiness
    readiness = assess_readiness(rahul(), AS_OF)
    r = run_eval([record("K1")], a=analyst([fact("K1")]), readiness=readiness)
    assert r["status"] == "FINANCIAL_CONSTRAINTS_IDENTIFIED"


def test_goal_horizon_mismatch_is_reported():
    from app.services.financial_engine.readiness import assess_readiness
    from tests.factories import healthy as h
    from app.services.financial_engine.dates import add_months
    from decimal import Decimal
    readiness = assess_readiness(h(goal_amount=Decimal("100000"), goal_deadline=add_months(AS_OF, 30)), AS_OF)
    r = run_eval([record("K1")], a=analyst([fact("K1")]), readiness=readiness)
    assert r["status"] == "GOAL_HORIZON_MISMATCH"


def test_no_risk_and_all_supported_is_further_research():
    r = run_eval([record("K1", status="VERIFIED", pub=date(2025, 5, 20))], a=analyst([fact("K1")]))
    assert r["status"] == "FURTHER_RESEARCH_REQUIRED"


def test_derived_metrics_compute_cash_conversion():
    values = derived_metrics({"ocfCr": "150", "patCr": "200", "trackingDifferencePct": "-0.7"})
    assert float(values["ocfToPat"]) == pytest.approx(0.75)
    assert float(values["absTrackingDifferencePct"]) == pytest.approx(0.7)


# --- LLM failure paths ------------------------------------------------------

class FakeSettings:
    llm_provider = "openai-compatible"
    llm_api_key = "test-key-not-real"
    llm_base_url = "https://llm.example.test/v1"
    llm_model = "test-model"
    llm_timeout_seconds = 5.0
    llm_enabled = True


@pytest.fixture()
def fake_llm(monkeypatch):
    monkeypatch.setattr(llm, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(research, "get_settings", lambda: FakeSettings())
    original = httpx.Client

    def install(handler):
        monkeypatch.setattr(llm.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))

    return install


def completion(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@pytest.mark.parametrize("handler,expected_kind", [
    (lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("slow")), "TIMEOUT"),
    (lambda req: httpx.Response(429, json={"error": "slow down"}), "RATE_LIMIT"),
    (lambda req: httpx.Response(500, text="secret provider body sk-123"), "PROVIDER_ERROR"),
    (lambda req: completion("not json at all"), "INVALID_JSON"),
    (lambda req: completion("   "), "EMPTY_RESPONSE"),
    (lambda req: completion('{"overview": 5}'), "SCHEMA_INVALID"),
    (lambda req: httpx.Response(200, json={"unexpected": True}), "PROVIDER_ERROR"),
])
def test_llm_failures_are_classified_and_sanitised(fake_llm, handler, expected_kind):
    fake_llm(handler)
    result = llm.call_json("sys", "user", AnalystDraft)
    assert result.ok is False
    assert result.kind == expected_kind
    assert "sk-123" not in result.message and "secret" not in result.message


def test_valid_structured_llm_output_is_accepted(fake_llm):
    body = '{"overview": "A test overview.", "thesis": "A test thesis.", "developments": [], "claims": []}'
    fake_llm(lambda req: completion(body))
    result = llm.call_json("sys", "user", AnalystDraft)
    assert result.ok and result.data.overview == "A test overview."


def test_research_falls_back_to_rules_when_llm_times_out(fake_llm):
    fake_llm(lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("slow")))
    from app.services.financial_engine.readiness import assess_readiness
    out = run_research(ASSET, [record("K1", status="VERIFIED")], assess_readiness(healthy(), AS_OF))
    assert out["engine"]["analyst_mode"] == "DETERMINISTIC_RULES"
    assert any("TIMEOUT" in e for e in out["engine"]["errors"])
    assert out["analyst"]["claims"]


def test_fabricated_llm_evidence_is_caught_by_the_evaluator(fake_llm):
    body = ('{"overview": "Invented.", "thesis": "Invented thesis.", "developments": [], '
            '"claims": [{"claim": "Fabricated figure", "claim_type": "FACT", "evidence_key": "NOT-REAL-1", '
            '"metric_key": "revenueCr", "claimed_value": "99999", "period": "FY2030"}]}')
    fake_llm(lambda req: completion(body))
    from app.services.financial_engine.readiness import assess_readiness
    readiness = assess_readiness(healthy(), AS_OF)
    out = run_research(ASSET, [record("K1")], readiness)
    assert out["engine"]["analyst_mode"] == "LLM"
    evaluation = evaluate(asset=ASSET, records=[record("K1")], analyst=out["analyst"], devil=out["devil"],
                          readiness=readiness, as_of=AS_OF)
    assert check_for(evaluation, "Fabricated figure")["status"] == "INVALID_REFERENCE"
    assert evaluation["status"] == "INSUFFICIENT_EVIDENCE"


def test_priya_readiness_is_used_for_evaluation_context():
    from app.services.financial_engine.readiness import assess_readiness
    r = assess_readiness(priya(), AS_OF)
    assert r["status"] == "READY_TO_EXPLORE"
