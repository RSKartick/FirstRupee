from __future__ import annotations

from app.api.routes import catalog
from app.data_sources import demo_catalog


def test_live_benchmark_cache_header_and_public_response(monkeypatch, new_client):
    calls: list[float] = []

    def live_quotes(*, timeout: float):
        calls.append(timeout)
        return [{"symbol": "^NSEI", "is_live": True, "source": "Yahoo Finance Live (NSE/BSE)"}]

    monkeypatch.setattr(catalog, "fetch_live_benchmarks", live_quotes)
    response = new_client.get("/api/assets/benchmarks")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, s-maxage=60, stale-while-revalidate=240"
    assert "set-cookie" not in response.headers
    assert calls == [2.0]
    assert set(response.json()) == {"benchmarks", "provider"}


def test_fallback_benchmarks_keep_provenance_and_short_cache(monkeypatch, new_client):
    class OfflineClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            raise RuntimeError("market data provider unavailable")

    monkeypatch.setattr(demo_catalog.httpx, "Client", OfflineClient)
    quotes = demo_catalog.fetch_live_benchmarks(timeout=2.0)
    assert quotes
    assert all(quote["is_live"] is False for quote in quotes)
    assert all(quote["source"] == "NSE/BSE Cached Reference Snapshot" for quote in quotes)

    monkeypatch.setattr(catalog, "fetch_live_benchmarks", lambda *, timeout: quotes)
    response = new_client.get("/api/assets/benchmarks")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, s-maxage=15"
    assert "set-cookie" not in response.headers
