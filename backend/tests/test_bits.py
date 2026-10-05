import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.bits_db import (
    get_bits_connection,
    init_bits_database,
    fetch_bits_filter_options,
    query_bits_cutoffs,
    get_bits_stats,
    wipe_bits_database,
)
from app.services.scrape_bits_official import (
    normalize_program_and_degree,
    parse_bits_html,
    save_bits_data,
    CAMPUS_METADATA,
)

client = TestClient(app)


def test_bits_program_parsing():
    samples = [
        ("B.E. Computer Science", "B.E. Computer Science", "B.E."),
        ("B.E. Chemical", "B.E. Chemical", "B.E."),
        ("B.E. Electrical & Electronics", "B.E. Electrical & Electronics", "B.E."),
        ("B.E. Electronics & Instrumentation", "B.E. Electronics & Instrumentation", "B.E."),
        ("B.E. Mechanical", "B.E. Mechanical", "B.E."),
        ("M.Sc. Biological Sciences", "M.Sc. Biological Sciences", "M.Sc."),
        ("M.Sc. Chemistry", "M.Sc. Chemistry", "M.Sc."),
        ("M.Sc. Economics", "M.Sc. Economics", "M.Sc."),
        ("M.Sc. Mathematics", "M.Sc. Mathematics", "M.Sc."),
        ("M.Sc. Physics", "M.Sc. Physics", "M.Sc."),
        ("B.Pharm.", "B.Pharm.", "B.Pharm."),
        ("B. Pharm", "B.Pharm.", "B.Pharm."),
    ]

    for raw, exp_name, exp_degree in samples:
        name, deg = normalize_program_and_degree(raw)
        assert name == exp_name
        assert deg == exp_degree


def test_mock_bits_html_parsing():
    mock_html = """
    <div id="2026-2027">
        <div class="row">
            <h4>Pilani Campus</h4>
            <table>
                <thead>
                    <tr>
                        <th>Campus</th>
                        <th>Program</th>
                        <th>Cut-off Score</th>
                        <th>Max Marks</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Pilani</td>
                        <td>B.E. Computer Science</td>
                        <td>331</td>
                        <td>390</td>
                    </tr>
                    <tr>
                        <td>Pilani</td>
                        <td>B.E. Chemical</td>
                        <td>224</td>
                        <td>390</td>
                    </tr>
                    <tr>
                        <td>Pilani</td>
                        <td>B.Pharm.</td>
                        <td>161</td>
                        <td>390</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="row">
            <h4>Goa Campus</h4>
            <table>
                <tbody>
                    <tr>
                        <td>Goa</td>
                        <td>B.E. Computer Science</td>
                        <td>298</td>
                        <td>390</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    <div id="2025-2026">
        <div class="row">
            <h4>Hyderabad Campus</h4>
            <table>
                <tbody>
                    <tr>
                        <td>Hyderabad</td>
                        <td>B.E. Computer Science</td>
                        <td>284</td>
                        <td>390</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    """
    records = parse_bits_html(mock_html, target_years=["2026-2027", "2025-2026"])
    assert len(records) == 5

    pilani_cs = next(r for r in records if r["academic_year"] == "2026-2027" and r["campus"]["code"] == "PILANI" and "Computer Science" in r["program_name"])
    assert pilani_cs["cutoff_score"] == 331
    assert pilani_cs["max_marks"] == 390
    assert pilani_cs["degree_type"] == "B.E."

    hyd_cs = next(r for r in records if r["academic_year"] == "2025-2026" and r["campus"]["code"] == "HYD")
    assert hyd_cs["cutoff_score"] == 284
    assert hyd_cs["campus"]["name"] == "Hyderabad Campus"


def test_bits_db_stats_and_filter_options():
    stats = get_bits_stats()
    assert stats["total_cutoffs"] > 0
    assert stats["total_campuses"] == 3
    assert len(stats["available_years"]) >= 2
    assert "2026-2027" in stats["available_years"]
    assert "2025-2026" in stats["available_years"]

    filters = fetch_bits_filter_options()
    assert "2026-2027" in filters["academic_years"]
    assert "2025-2026" in filters["academic_years"]
    assert len(filters["campuses"]) == 3
    assert "B.E." in filters["degree_types"]
    assert "M.Sc." in filters["degree_types"]
    assert "B.Pharm." in filters["degree_types"]


def test_bits_db_filtering():
    # Filter by Academic Year
    y26_res = query_bits_cutoffs(academic_year="2026-2027", page=1, page_size=50)
    assert y26_res["total"] > 0
    for item in y26_res["items"]:
        assert item["academic_year"] == "2026-2027"

    # Filter by Campus
    pilani_res = query_bits_cutoffs(campus_name="Pilani", page=1, page_size=50)
    assert pilani_res["total"] > 0
    for item in pilani_res["items"]:
        assert "Pilani" in item["campus_name"]

    # Filter by Degree Type
    msc_res = query_bits_cutoffs(degree_type="M.Sc.", page=1, page_size=50)
    assert msc_res["total"] > 0
    for item in msc_res["items"]:
        assert item["degree_type"] == "M.Sc."

    # Filter by Student Score (student has 300, cutoff <= 300 qualifies)
    qualifying_res = query_bits_cutoffs(student_score=300, page=1, page_size=50)
    assert qualifying_res["total"] > 0
    for item in qualifying_res["items"]:
        assert item["cutoff_score"] <= 300


def test_bits_api_endpoints():
    # 1. Filter Options
    resp = client.get("/api/bits/filter-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "academic_years" in data
    assert "campuses" in data
    assert "degree_types" in data
    assert len(data["campuses"]) == 3

    # 2. Cutoffs
    resp = client.get("/api/bits/cutoffs?academic_year=2026-2027&page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 10
    assert data["total"] > 0
    for item in data["items"]:
        assert item["academic_year"] == "2026-2027"
        assert item["max_marks"] == 390

    # 3. Stats
    resp = client.get("/api/bits/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_cutoffs"] > 0
    assert stats["total_campuses"] == 3
    assert len(stats["available_years"]) >= 2

    # 4. Scraper Status
    resp = client.get("/api/bits/scraper-status")
    assert resp.status_code == 200
    status = resp.json()
    assert "status" in status
    assert "is_running" in status

    # 5. Export CSV
    resp = client.get("/api/bits/export?academic_year=2026-2027")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "Academic Year,Campus" in resp.text


def test_bits_upsert_idempotence():
    # Calling save_bits_data again with mock items should not duplicate rows
    sample_records = [
        {
            "academic_year": "2026-2027",
            "campus": CAMPUS_METADATA["pilani"],
            "program_name": "B.E. Computer Science",
            "degree_type": "B.E.",
            "cutoff_score": 331,
            "max_marks": 390,
            "score_percentage": 84.87,
            "category": "General Merit",
            "exam_name": "BITSAT",
        }
    ]
    count1 = save_bits_data(sample_records)
    assert count1 >= 1

    # Total count in DB shouldn't increase indefinitely for the same unique (year, campus, program, category)
    stats_before = get_bits_stats()
    count2 = save_bits_data(sample_records)
    assert count2 >= 1
    stats_after = get_bits_stats()
    assert stats_after["total_cutoffs"] == stats_before["total_cutoffs"]
