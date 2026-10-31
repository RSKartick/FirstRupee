"""Live API walk-through of the Rahul and Priya journeys against a running server.

Usage (server must be running):  python scripts/demo_journey.py http://localhost:3000
It exercises the same public endpoints as the web app, using a real session cookie and the CSRF header, and asserts the
expected deterministic results. It needs no API keys and makes no external calls.
"""

from __future__ import annotations

import sys

import httpx


def expect(condition: bool, message: str) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {message}")
    if not condition:
        raise SystemExit(f"Assertion failed: {message}")


def csrf(client: httpx.Client) -> dict[str, str]:
    token = client.get("/api/auth/me").json()["csrf_token"]
    return {"X-CSRF-Token": token}


def asset_id(client: httpx.Client, symbol: str) -> int:
    return next(a["id"] for a in client.get("/api/assets").json()["assets"] if a["symbol"] == symbol)


def rahul(client: httpx.Client) -> None:
    print("Rahul — constrained first-time saver")
    session = client.post("/api/auth/demo/rahul")
    expect(session.status_code == 201, "demo workspace created with a private session")
    pid = session.json()["profile_id"]

    readiness = client.get(f"/api/readiness/{pid}").json()["readiness"]
    expect(readiness["metrics"]["monthly_surplus"] == "4000.00", "monthly surplus is ₹4,000.00")
    expect(readiness["metrics"]["emergency_coverage_months"] == "1.00", "emergency coverage is 1.00 month")
    expect(readiness["status"] == "NOT_READY", "readiness is NOT_READY")
    expect(readiness["metrics"]["investable_monthly"] == "0.00", "no investable monthly money is invented")

    timing = client.post("/api/timing/analyze", json={"profile_id": pid}, headers=csrf(client)).json()["timing"]
    expect(timing["verdict_code"] == "RESERVE_FIRST", "three clocks: reserves come first")

    refused = client.post("/api/simulator/run", json={
        "profile_id": pid, "asset_id": asset_id(client, "UTI-NIFTY50"), "scenario_type": "STAGED_INITIAL",
        "amount_source": "PROFILE_DERIVED", "duration_months": 24,
    }, headers=csrf(client))
    expect(refused.status_code == 422, "no profile-based simulation is run for a NOT_READY profile")

    passport = client.post("/api/passport/generate", json={"profile_id": pid}, headers=csrf(client))
    expect(passport.status_code == 201, "educational passport generated without a simulation")
    expect(passport.json()["passport"]["simulation"] is None, "passport explains that no simulation was run")


def priya(client: httpx.Client) -> None:
    print("Priya — profile ready to explore")
    session = client.post("/api/auth/demo/priya")
    expect(session.status_code == 201, "demo workspace created with a private session")
    pid = session.json()["profile_id"]

    readiness = client.get(f"/api/readiness/{pid}").json()["readiness"]
    expect(readiness["status"] == "READY_TO_EXPLORE", "readiness is READY_TO_EXPLORE")
    expect(readiness["metrics"]["monthly_surplus"] == "40000.00", "monthly surplus is ₹40,000.00")
    expect(readiness["metrics"]["investable_monthly"] == "19416.67", "investable monthly after goal need is ₹19,416.67")

    tcs = asset_id(client, "TCS.NS")
    research = client.post("/api/research/analyze", json={"profile_id": pid, "asset_id": tcs}, headers=csrf(client))
    expect(research.status_code == 201, "two-sided research analysis completed")
    analysis = research.json()["analysis"]
    checks = analysis["evaluation"]["claim_checks"]
    expect(all(c["status"] != "UNSUPPORTED" for c in checks if c["claim_type"] == "FACT"), "every factual claim has evidence")
    expect(analysis["evaluation"]["data_status"]["synthetic_evidence_used"] is False, "verified evidence is used")

    simulation = client.post("/api/simulator/run", json={
        "profile_id": pid, "asset_id": tcs, "scenario_type": "STAGED_INITIAL", "amount_source": "PROFILE_DERIVED",
        "duration_months": 36,
    }, headers=csrf(client))
    expect(simulation.status_code == 201, "simulation uses the designated ₹15,000 per month")
    sim = simulation.json()["simulation"]

    passport = client.post("/api/passport/generate", json={
        "profile_id": pid, "research_analysis_id": analysis["analysis_id"], "simulation_id": sim["simulation_id"],
    }, headers=csrf(client))
    expect(passport.status_code == 201, "passport generated from matching research and simulation")
    snap = passport.json()["passport"]
    expect(snap["research"]["asset"]["symbol"] == "TCS.NS", "passport research matches the analysed instrument")
    expect(snap["simulation"]["simulation_id"] == sim["simulation_id"], "passport simulation matches the run")
    fetched = client.get(f"/api/passport/{snap['passport_id']}").json()["passport"]
    expect(fetched == snap, "stored passport is returned unchanged")


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    print(f"Demo journey against {base}")
    with httpx.Client(base_url=base, timeout=60) as client:
        expect(client.get("/api/health").json()["ok"] is True, "health endpoint reports ok")
        rahul(httpx.Client(base_url=base, timeout=60))
        priya(httpx.Client(base_url=base, timeout=60))
    print("All demo journey checks passed.")


if __name__ == "__main__":
    main()
