"""End-to-end API journeys for the two fictional demonstration investors, using a real SQLite database and migrations."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import csrf


def _asset_id(client, symbol):
    return next(a["id"] for a in client.get("/api/assets").json()["assets"] if a["symbol"] == symbol)


def test_catalogue_is_verified_and_public(new_client):
    body = new_client.get("/api/assets").json()
    assert len(body["assets"]) == 8
    assert all(not a["is_synthetic"] for a in body["assets"])
    history = new_client.get(f"/api/assets/{body['assets'][0]['id']}/history?interval=monthly&from=2024-01-01&to=2024-12-31")
    assert history.status_code == 200
    assert history.json()["is_synthetic"] is False
    assert len(history.json()["points"]) == 12


def test_history_rejects_inverted_and_future_ranges(new_client):
    asset_id = new_client.get("/api/assets").json()["assets"][0]["id"]
    assert new_client.get(f"/api/assets/{asset_id}/history?from=2025-01-01&to=2024-01-01").status_code == 422
    assert new_client.get(f"/api/assets/{asset_id}/history?to=2030-01-01").status_code == 422


def test_rahul_journey_is_constrained_and_never_simulates_invented_money(app):
    client = TestClient(app)
    response = client.post("/api/auth/demo/rahul")
    assert response.status_code == 201
    pid = response.json()["profile_id"]

    readiness = client.get(f"/api/readiness/{pid}").json()["readiness"]
    assert readiness["status"] == "NOT_READY"
    assert readiness["metrics"]["monthly_surplus"] == "4000.00"
    assert readiness["metrics"]["emergency_coverage_months"] == "1.00"
    assert readiness["metrics"]["investable_monthly"] == "0.00"
    assert readiness["metrics"]["unallocated_liquid"] == "0.00"
    assert readiness["metrics"]["goal_horizon_months"] == 10
    assert readiness["recommendations"]["readiness_status"] == "NOT_READY"
    assert readiness["recommendations"]["asset_allocations"]

    timing = client.post("/api/timing/analyze", json={"profile_id": pid}, headers=csrf(client)).json()["timing"]
    assert timing["verdict_code"] == "RESERVE_FIRST"
    assert timing["clocks"]["goal"]["status"] == "CRITICAL"

    refused = client.post("/api/simulator/run", json={
        "profile_id": pid, "asset_id": _asset_id(client, "UTI-NIFTY50"), "scenario_type": "STAGED_INITIAL",
        "amount_source": "PROFILE_DERIVED", "duration_months": 24,
    }, headers=csrf(client))
    assert refused.status_code == 422
    assert "NOT_READY" in refused.json()["detail"]

    hypothetical = client.post("/api/simulator/run", json={
        "profile_id": pid, "asset_id": _asset_id(client, "UTI-NIFTY50"), "scenario_type": "LUMP_SUM",
        "amount_source": "USER_HYPOTHETICAL", "initial_amount": "10000", "duration_months": 12,
        "evaluation_date": "2025-12-31",
    }, headers=csrf(client))
    assert hypothetical.status_code == 201
    assert hypothetical.json()["simulation"]["financially_available"] is False

    research = client.post("/api/research/analyze", json={
        "profile_id": pid, "asset_id": _asset_id(client, "TATAPOWER.NS")}, headers=csrf(client))
    assert research.status_code == 201
    assert research.json()["analysis"]["evaluation"]["status"] == "FINANCIAL_CONSTRAINTS_IDENTIFIED"

    passport = client.post("/api/passport/generate", json={"profile_id": pid}, headers=csrf(client))
    assert passport.status_code == 201
    snap = passport.json()["passport"]
    assert snap["simulation"] is None
    assert "NOT_READY" in snap["simulation_skipped_reason"]
    assert snap["readiness"]["status"] == "NOT_READY"
    fetched = client.get(f"/api/passport/{snap['passport_id']}").json()["passport"]
    assert fetched == snap


def test_priya_journey_explores_with_traceable_evidence_and_matching_passport(app):
    client = TestClient(app)
    pid = client.post("/api/auth/demo/priya").json()["profile_id"]

    readiness = client.get(f"/api/readiness/{pid}").json()["readiness"]
    assert readiness["status"] == "READY_TO_EXPLORE"
    assert readiness["metrics"]["monthly_surplus"] == "40000.00"
    assert readiness["metrics"]["investable_monthly"] == "19416.67"
    assert readiness["metrics"]["designated_monthly"] == "15000.00"
    assert readiness["recommendations"]["readiness_status"] == "READY_TO_EXPLORE"
    assert readiness["recommendations"]["monthly_plan"]["recommended_market_deployment_inr"] == "15000.00"

    tcs = _asset_id(client, "TCS.NS")
    tatapower = _asset_id(client, "TATAPOWER.NS")
    rec_m = client.post("/api/research/analyze", json={"profile_id": pid, "asset_id": tcs}, headers=csrf(client)).json()["analysis"]
    rec_s = client.post("/api/research/analyze", json={"profile_id": pid, "asset_id": tatapower}, headers=csrf(client)).json()["analysis"]

    assert rec_m["evaluation"]["status"] == "FURTHER_RESEARCH_REQUIRED"
    assert rec_s["evaluation"]["status"] == "MATERIAL_RISKS_IDENTIFIED"
    for analysis in (rec_m, rec_s):
        for check in analysis["evaluation"]["claim_checks"]:
            if check["claim_type"] == "HYPOTHESIS":
                assert check["status"] == "HYPOTHESIS"
            elif check["evidence_key"]:
                assert check["status"] != "UNSUPPORTED"
        assert analysis["evaluation"]["data_status"]["synthetic_evidence_used"] is False
        assert analysis["analyst"]["claims"]
        assert analysis["devil"]["counter_thesis"]

    sim = client.post("/api/simulator/run", json={
        "profile_id": pid, "asset_id": tcs, "scenario_type": "STAGED_INITIAL",
        "amount_source": "PROFILE_DERIVED", "duration_months": 36, "contribution_frequency": "MONTHLY",
    }, headers=csrf(client))
    assert sim.status_code == 201, sim.text
    simulation = sim.json()["simulation"]
    assert simulation["financially_available"] is True
    assert simulation["inputs"]["monthly_contribution"] == "15000.00"
    assert len(simulation["primary"]["run"]["contributions"]) == 36

    cross = client.post("/api/passport/generate", json={
        "profile_id": pid, "research_analysis_id": rec_s["analysis_id"], "simulation_id": simulation["simulation_id"],
    }, headers=csrf(client))
    assert cross.status_code == 422

    passport = client.post("/api/passport/generate", json={
        "profile_id": pid, "research_analysis_id": rec_m["analysis_id"], "simulation_id": simulation["simulation_id"],
    }, headers=csrf(client))
    assert passport.status_code == 201, passport.text
    snap = passport.json()["passport"]
    assert snap["readiness"]["status"] == "READY_TO_EXPLORE"
    assert snap["research"]["asset"]["symbol"] == "TCS.NS"
    assert snap["research"]["evaluator_status"] == rec_m["evaluation"]["status"]
    assert snap["simulation"]["simulation_id"] == simulation["simulation_id"]
    assert snap["simulation"]["financially_available"] is True
    assert snap["data_status"]["synthetic_data_used"] is False
    assert snap["thesis_expiry"]["depends_on"]
    assert snap["review_conditions"]
    assert all(ref["verification_status"] == "VERIFIED" for ref in snap["evidence_references"])

    listing = client.get(f"/api/passport/profile/{pid}").json()["passports"]
    assert any(p["id"] == snap["passport_id"] for p in listing)

    answer = client.post("/api/assistant/chat", json={"profile_id": pid, "messages": [
        {"role": "user", "content": "Am I ready to invest?"}]}, headers=csrf(client)).json()
    assert "READY_TO_EXPLORE" in answer["answer"]
    assert answer["mode"] == "DETERMINISTIC"


def test_profile_crud_validates_cross_field_money_rules(new_client):
    from tests.helpers import profile_payload, register

    register(new_client, "crud@example.test")
    bad = profile_payload(emergency_reserves="280000.00", goal_reserved_amount="30000.00")
    response = new_client.post("/api/profile", json=bad, headers=csrf(new_client))
    assert response.status_code == 422
    assert "same rupee" in str(response.json()["errors"])

    past = profile_payload(goal_name="Trip", goal_amount="50000.00", goal_deadline="2020-01-01")
    assert new_client.post("/api/profile", json=past, headers=csrf(new_client)).status_code == 422

    created = new_client.post("/api/profile", json=profile_payload(), headers=csrf(new_client))
    pid = created.json()["profile"]["id"]
    updated = new_client.put(f"/api/profile/{pid}", json=profile_payload(display_name="Renamed"), headers=csrf(new_client))
    assert updated.status_code == 200
    assert updated.json()["profile"]["display_name"] == "Renamed"
    assert new_client.delete(f"/api/profile/{pid}", headers=csrf(new_client)).status_code == 204
    assert new_client.get(f"/api/profile/{pid}").status_code == 404


def test_health_reports_engine_versions_and_no_secrets(new_client):
    body = new_client.get("/api/health").json()
    assert body["ok"] is True
    assert body["language_model"]["enabled"] is False
    assert body["market_data"]["is_live"] is True
    assert "readiness" in body["rule_versions"]
    assert "key" not in str(body).lower()
