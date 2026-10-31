from __future__ import annotations

from app.api.routes import catalog


def test_asset_key_listing_matches_full_listing_without_observation_summary(monkeypatch, new_client):
    full = new_client.get("/api/assets")
    assert full.status_code == 200
    expected = [(item["id"], item["symbol"]) for item in full.json()["assets"]]

    monkeypatch.setattr(catalog, "_summaries", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("lightweight asset listing queried observation summaries")
    ))
    light = new_client.get("/api/assets?fields=id%2Csymbol")

    assert light.status_code == 200
    assets = light.json()["assets"]
    assert [(item["id"], item["symbol"]) for item in assets] == expected
    assert all(set(item) == {"id", "symbol"} for item in assets)
