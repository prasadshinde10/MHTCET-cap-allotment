import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.medical_db import (
    get_medical_connection,
    fetch_medical_filter_options,
    query_medical_cutoffs,
    get_medical_stats,
)

client = TestClient(app)


def test_medical_db_connection_and_stats():
    conn = get_medical_connection()
    assert conn is not None
    conn.close()

    stats = get_medical_stats()
    assert stats["cutoff_count"] > 0
    assert stats["college_count"] > 0
    assert stats["course_count"] > 0
    assert "2026-2027" in stats["years"]
    assert "MBBS" in stats["courses_breakdown"]


def test_medical_filter_options():
    options = fetch_medical_filter_options()
    assert len(options["academic_years"]) >= 3
    assert len(options["colleges"]) > 0
    assert len(options["courses"]) >= 5
    assert "Government/Aided" in options["college_types"]
    assert "OPEN" in options["categories"]


def test_medical_cutoffs_query_basic():
    res = query_medical_cutoffs(page=1, page_size=10)
    assert res["total"] > 0
    assert len(res["items"]) <= 10
    item = res["items"][0]
    assert "college_name" in item
    assert "course_code" in item
    assert "quota_category" in item
    assert "closing_rank" in item


def test_medical_cutoffs_query_with_filters():
    # Filter for MBBS and Government
    res = query_medical_cutoffs(
        course_name="MBBS",
        college_type="Government/Aided",
        page=1,
        page_size=20,
    )
    assert res["total"] > 0
    for itm in res["items"]:
        assert itm["course_code"] == "MBBS"
        assert itm["college_type"] == "Government/Aided"


def test_medical_student_rank_predictor():
    res = query_medical_cutoffs(
        course_name="MBBS",
        student_rank=10000,
        page=1,
        page_size=10,
    )
    assert res["total"] > 0
    for itm in res["items"]:
        if itm["chance"]:
            assert itm["chance"] in ["High", "Medium", "Borderline", "Low"]


def test_medical_api_endpoints():
    # 1. Filter options
    resp = client.get("/api/medical/filter-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "academic_years" in data
    assert "colleges" in data

    # 2. Cutoffs search
    resp2 = client.get("/api/medical/cutoffs?course_name=BDS&page=1&page_size=10")
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["total"] > 0

    # 3. Stats
    resp3 = client.get("/api/medical/stats")
    assert resp3.status_code == 200
    d3 = resp3.json()
    assert d3["cutoff_count"] > 0

    # 4. CSV Export
    resp4 = client.get("/api/medical/export?course_name=MBBS")
    assert resp4.status_code == 200
    assert "attachment" in resp4.headers.get("content-disposition", "")
    assert "Academic Year" in resp4.text
