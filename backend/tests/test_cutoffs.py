import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.cutoff import Cutoff

client = TestClient(app)


def test_cutoffs_endpoint_route_alias():
    # Both /api/cutoffs and /api/cutoffs/ should resolve without 404 or 307
    r1 = client.get("/api/cutoffs?page=1&page_size=5")
    assert r1.status_code == 200
    assert "items" in r1.json()

    r2 = client.get("/api/cutoffs/?page=1&page_size=5")
    assert r2.status_code == 200
    assert "items" in r2.json()


def test_mht_cet_state_engineering_cutoff_search():
    # Applied filter: category OPEN (LOPEN, GOPEN), STATE quota, max_percentile 80, year 2026
    resp = client.get(
        "/api/cutoffs?page=1&page_size=20&year=2026&category_code=LOPEN,GOPEN&quota_group=STATE&max_percentile=80"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 10000, f"Expected thousands of cutoffs, got {data['total']}"
    assert len(data["items"]) == 20
    for item in data["items"]:
        assert item["percentile"] <= 80.0
        assert item["seat_section"] != "All India Seats (AI)"
        assert any(item["category_code"].startswith(prefix) for prefix in ["GOPEN", "LOPEN"])


def test_cutoffs_export_unauthenticated():
    resp = client.get(
        "/api/cutoffs/export?year=2026&category_code=LOPEN,GOPEN&quota_group=STATE&max_percentile=80"
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "Percentile" in resp.text


def test_cutoffs_mutation_requires_auth():
    # PUT and DELETE should be blocked for unauthenticated users
    r_put = client.put("/api/cutoffs/1", json={"merit_number": 999})
    assert r_put.status_code == 401

    r_del = client.delete("/api/cutoffs/1")
    assert r_del.status_code == 401
