from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main


def test_startup_without_seed_makes_no_market_data_http_calls(monkeypatch, app, base_client):
    monkeypatch.delenv("SEED_ON_STARTUP", raising=False)
    urls: list[str] = []

    class GuardedHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, url, *args, **kwargs):
            urls.append(str(url))
            raise AssertionError("startup attempted an outbound market-data request")

    monkeypatch.setattr(main, "seed_catalog", lambda *_args, **_kwargs: pytest.fail("startup unexpectedly seeded"))
    client = TestClient(app)
    monkeypatch.setattr(httpx, "Client", GuardedHttpClient)

    with client:
        response = client.get("/api/assets")

    assert response.status_code == 200
    assert any(asset["symbol"] == "TCS.NS" for asset in response.json()["assets"])
    assert not any("query1.finance.yahoo.com" in url or "api.mfapi.in" in url for url in urls)
    assert urls == []
