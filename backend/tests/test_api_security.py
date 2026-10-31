"""Authentication, owner scoping, cross-record association and CSRF protection, through the real HTTP API."""

from __future__ import annotations

from tests.helpers import csrf, profile_payload, register


def test_unauthenticated_requests_are_rejected(new_client):
    assert new_client.get("/api/profile").status_code == 401
    assert new_client.get("/api/profile/1").status_code == 401
    assert new_client.get("/api/auth/me").json() == {"user": None, "csrf_token": None}


def test_invalid_session_cookie_is_rejected(new_client):
    new_client.cookies.set("fr_session", "not-a-real-token")
    assert new_client.get("/api/profile").status_code == 401


def test_user_cannot_read_update_or_delete_another_users_profile(new_client, app):
    from fastapi.testclient import TestClient

    a = TestClient(app)
    b = TestClient(app)
    register(a, "alice@example.test")
    register(b, "bob@example.test")
    created = a.post("/api/profile", json=profile_payload(), headers=csrf(a))
    assert created.status_code == 201
    pid = created.json()["profile"]["id"]

    assert b.get(f"/api/profile/{pid}").status_code == 404
    assert b.put(f"/api/profile/{pid}", json=profile_payload(display_name="Hijacked"), headers=csrf(b)).status_code == 404
    assert b.delete(f"/api/profile/{pid}", headers=csrf(b)).status_code == 404
    assert b.get(f"/api/readiness/{pid}").status_code == 404
    assert a.get(f"/api/profile/{pid}").json()["profile"]["display_name"] == "Tester"  # unchanged


def test_user_cannot_run_research_or_simulation_for_another_users_profile(app):
    from fastapi.testclient import TestClient

    a, b = TestClient(app), TestClient(app)
    register(a, "carol@example.test")
    register(b, "dan@example.test")
    pid = a.post("/api/profile", json=profile_payload(), headers=csrf(a)).json()["profile"]["id"]
    assets = a.get("/api/assets").json()["assets"]
    asset_id = assets[0]["id"]

    assert b.post("/api/research/analyze", json={"profile_id": pid, "asset_id": asset_id}, headers=csrf(b)).status_code == 404
    assert b.post("/api/simulator/run", json={"profile_id": pid, "asset_id": asset_id, "scenario_type": "LUMP_SUM",
                                              "initial_amount": "1000", "duration_months": 12}, headers=csrf(b)).status_code == 404
    assert b.post("/api/timing/analyze", json={"profile_id": pid}, headers=csrf(b)).status_code == 404
    assert b.get(f"/api/passport/profile/{pid}").status_code == 404


def test_user_cannot_read_another_users_research_simulation_or_passport(app):
    from fastapi.testclient import TestClient

    a, b = TestClient(app), TestClient(app)
    register(a, "erin@example.test")
    register(b, "frank@example.test")
    pid = a.post("/api/profile", json=profile_payload(), headers=csrf(a)).json()["profile"]["id"]
    asset_id = a.get("/api/assets").json()["assets"][0]["id"]
    research = a.post("/api/research/analyze", json={"profile_id": pid, "asset_id": asset_id}, headers=csrf(a))
    assert research.status_code == 201
    rid = research.json()["analysis"]["analysis_id"]
    sim = a.post("/api/simulator/run", json={"profile_id": pid, "asset_id": asset_id, "scenario_type": "LUMP_SUM",
                                             "initial_amount": "1000", "duration_months": 12,
                                             "evaluation_date": "2025-12-31"}, headers=csrf(a))
    sid = sim.json()["simulation"]["simulation_id"]
    passport = a.post("/api/passport/generate", json={"profile_id": pid, "research_analysis_id": rid}, headers=csrf(a))
    assert passport.status_code == 201
    xid = passport.json()["passport"]["passport_id"]

    assert b.get(f"/api/research/{rid}").status_code == 404
    assert b.get(f"/api/simulator/{sid}").status_code == 404
    assert b.get(f"/api/passport/{xid}").status_code == 404


def test_cross_profile_association_is_rejected_for_passports(app):
    from fastapi.testclient import TestClient

    client = TestClient(app)
    register(client, "gina@example.test")
    first = client.post("/api/profile", json=profile_payload(display_name="First"), headers=csrf(client)).json()["profile"]["id"]
    second = client.post("/api/profile", json=profile_payload(display_name="Second"), headers=csrf(client)).json()["profile"]["id"]
    asset_id = client.get("/api/assets").json()["assets"][0]["id"]
    rid = client.post("/api/research/analyze", json={"profile_id": first, "asset_id": asset_id},
                      headers=csrf(client)).json()["analysis"]["analysis_id"]

    response = client.post("/api/passport/generate", json={"profile_id": second, "research_analysis_id": rid}, headers=csrf(client))
    assert response.status_code == 404


def test_passport_rejects_simulation_on_a_different_instrument(app):
    from fastapi.testclient import TestClient

    client = TestClient(app)
    register(client, "hal@example.test")
    pid = client.post("/api/profile", json=profile_payload(), headers=csrf(client)).json()["profile"]["id"]
    catalogue = client.get("/api/assets").json()["assets"]
    asset_a, asset_b = catalogue[0]["id"], catalogue[1]["id"]
    rid = client.post("/api/research/analyze", json={"profile_id": pid, "asset_id": asset_a},
                      headers=csrf(client)).json()["analysis"]["analysis_id"]
    sid = client.post("/api/simulator/run", json={"profile_id": pid, "asset_id": asset_b, "scenario_type": "LUMP_SUM",
                                                  "initial_amount": "1000", "duration_months": 12,
                                                  "evaluation_date": "2025-12-31"}, headers=csrf(client)).json()["simulation"]["simulation_id"]
    response = client.post("/api/passport/generate", json={"profile_id": pid, "research_analysis_id": rid,
                                                           "simulation_id": sid}, headers=csrf(client))
    assert response.status_code == 422
    assert "different instrument" in response.json()["detail"]


def test_csrf_is_required_for_state_changing_requests(app):
    from fastapi.testclient import TestClient

    client = TestClient(app)
    register(client, "ivy@example.test")
    assert client.post("/api/profile", json=profile_payload()).status_code == 403
    assert client.post("/api/profile", json=profile_payload(), headers={"X-CSRF-Token": "forged"}).status_code == 403
    assert client.post("/api/profile", json=profile_payload(), headers=csrf(client)).status_code == 201


def test_logout_invalidates_the_session(app):
    from fastapi.testclient import TestClient

    client = TestClient(app)
    register(client, "jay@example.test")
    assert client.get("/api/profile").status_code == 200
    assert client.post("/api/auth/logout", headers=csrf(client)).status_code == 200
    assert client.get("/api/profile").status_code == 401


def test_session_cookie_is_httponly_and_samesite(app):
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post("/api/auth/register", json={"email": "kim@example.test", "password": "a-long-password-1",
                                                       "display_name": "Kim"})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_password_hashing_uses_argon2id_and_login_rejects_wrong_password(app):
    from fastapi.testclient import TestClient
    from app.models.tables import User
    from app.db.session import SessionLocal
    from sqlalchemy import select

    client = TestClient(app)
    register(client, "leo@example.test", password="correct-horse-battery")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "leo@example.test"))
        assert user.password_hash.startswith("$argon2id$")
    assert client.post("/api/auth/login", json={"email": "leo@example.test", "password": "wrong-password-1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "leo@example.test", "password": "correct-horse-battery"}).status_code == 200


def test_error_responses_do_not_expose_internals(app):
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/api/profile/999999")
    assert response.status_code == 401
    body = response.text.lower()
    assert "traceback" not in body and "sqlalchemy" not in body
