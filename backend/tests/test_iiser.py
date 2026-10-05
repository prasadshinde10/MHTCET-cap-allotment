import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.iiser_db import (
    get_iiser_connection,
    init_iiser_database,
    fetch_iiser_filter_options,
    query_iiser_cutoffs,
    get_iiser_stats,
    fetch_iiser_round_notices,
)
from app.services.scrape_iiser_official import (
    parse_program_and_institute,
    parse_iiser_html,
    IISER_CAMPUSES,
)

client = TestClient(app)


def test_program_and_institute_decomposition():
    raw_samples = [
        ("BS-MS IISER Berhampur", "IISER Berhampur", "BS-MS (Dual Degree)", "BS-MS", "Odisha"),
        ("BS-MS IISER Pune", "IISER Pune", "BS-MS (Dual Degree)", "BS-MS", "Maharashtra"),
        ("BS-MS (Computational and Data Sciences) IISER Kolkata", "IISER Kolkata", "BS-MS (Computational and Data Sciences)", "BS-MS", "West Bengal"),
        ("B.Tech. Chemical Engineering IISER Bhopal", "IISER Bhopal", "B.Tech. Chemical Engineering", "B.Tech", "Madhya Pradesh"),
        ("B.Tech. Data Science and Engineering IISER Bhopal", "IISER Bhopal", "B.Tech. Data Science and Engineering", "B.Tech", "Madhya Pradesh"),
        ("BS (Economic Sciences) IISER Bhopal", "IISER Bhopal", "BS (Economic Sciences)", "BS", "Madhya Pradesh"),
        ("BS (Economic and Statistical Sciences) IISER Tirupati", "IISER Tirupati", "BS (Economic and Statistical Sciences)", "BS", "Andhra Pradesh"),
    ]

    for raw, exp_inst, exp_prog, exp_deg, exp_state in raw_samples:
        inst_meta, prog_meta = parse_program_and_institute(raw)
        assert inst_meta["name"] == exp_inst
        assert inst_meta["state"] == exp_state
        assert prog_meta["name"] == exp_prog
        assert prog_meta["degree_type"] == exp_deg


def test_mock_html_parsing():
    mock_html = """
    <div class="container">
        <h4>Round 1: Closing Ranks</h4>
        <div class="admission-important-notice">
            <ul>
                <li>Program closure notice for Round 1</li>
            </ul>
        </div>
        <table class="table">
            <thead>
                <tr><th colspan="12">Closing Ranks</th></tr>
                <tr><th>Academic Program</th><th colspan="2">UR</th></tr>
                <tr><th>UR</th><th>UR-PwD</th><th>EWS</th><th>EWS PwD</th><th>OBC-NCL</th><th>OBC-NCL PwD</th><th>SC</th><th>SC PwD</th><th>ST</th><th>ST PwD</th><th>KM</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>BS-MS IISER Pune</td>
                    <td>263</td>
                    <td>5454</td>
                    <td>2128</td>
                    <td>--</td>
                    <td>1524</td>
                    <td>--</td>
                    <td>5080</td>
                    <td>--</td>
                    <td>7353</td>
                    <td>--</td>
                    <td>4019</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    records, notices = parse_iiser_html(mock_html, default_year=2024)
    assert len(records) > 0
    assert len(notices) == 1
    assert notices[0]["notice_text"] == "Program closure notice for Round 1"

    ur_rec = next(r for r in records if r["category_code"] == "UR")
    assert ur_rec["closing_rank"] == 263
    assert ur_rec["round_no"] == 1
    assert ur_rec["institute"]["name"] == "IISER Pune"


def test_iiser_stats_and_filter_options():
    stats = get_iiser_stats()
    assert stats["total_cutoffs"] > 0
    assert stats["total_institutes"] == 7
    assert stats["total_rounds"] >= 1

    filters = fetch_iiser_filter_options()
    assert len(filters["rounds"]) >= 1
    assert len(filters["institutes"]) == 7
    assert "BS-MS" in filters["degree_types"]


def test_query_iiser_cutoffs_filtering():
    # Filter by institute
    pune_res = query_iiser_cutoffs(institute_name="Pune", page=1, page_size=20)
    assert pune_res["total"] > 0
    for item in pune_res["items"]:
        assert "Pune" in item["institute_name"]

    # Filter by round
    r1_res = query_iiser_cutoffs(round_no="1", page=1, page_size=20)
    assert r1_res["total"] > 0
    for item in r1_res["items"]:
        assert item["round_no"] == 1

    # Filter by chance (student rank <= closing_rank)
    chance_res = query_iiser_cutoffs(max_rank=1000, page=1, page_size=20)
    assert chance_res["total"] > 0
    for item in chance_res["items"]:
        assert item["closing_rank"] >= 1000


def test_iiser_api_endpoints():
    # 1. Filter options
    resp = client.get("/api/iiser/filter-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "rounds" in data
    assert "institutes" in data
    assert len(data["institutes"]) == 7

    # 2. Cutoffs
    resp = client.get("/api/iiser/cutoffs?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 5
    assert data["total"] > 0

    # 3. Stats
    resp = client.get("/api/iiser/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_cutoffs"] > 0
    assert stats["total_institutes"] == 7

    # 4. Notices
    resp = client.get("/api/iiser/notices")
    assert resp.status_code == 200
    notices = resp.json()
    assert isinstance(notices, list)

    # 5. Export CSV
    resp = client.get("/api/iiser/export?round_no=1")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Closing Rank" in resp.text
