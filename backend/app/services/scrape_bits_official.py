import re
import ssl
import time
import logging
import threading
import requests
import urllib.request
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from bs4 import BeautifulSoup
from pathlib import Path

from app.bits_db import get_bits_connection, init_bits_database

logger = logging.getLogger("bits_scraper")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(asctime)s] [BITS-SCRAPER] %(levelname)s: %(message)s"))
    logger.addHandler(ch)

DEFAULT_BITS_URL = "https://admissions.bits-pilani.ac.in/FD/BITSAT_cutOffs.html"
TARGET_YEARS = ["2026-2027", "2025-2026"]

CAMPUS_METADATA = {
    "pilani": {
        "code": "PILANI",
        "name": "Pilani Campus",
        "location": "Pilani, Rajasthan",
        "state": "Rajasthan",
    },
    "k k birla goa": {
        "code": "GOA",
        "name": "K.K. Birla Goa Campus",
        "location": "Zuarinagar, Goa",
        "state": "Goa",
    },
    "goa": {
        "code": "GOA",
        "name": "K.K. Birla Goa Campus",
        "location": "Zuarinagar, Goa",
        "state": "Goa",
    },
    "hyderabad": {
        "code": "HYD",
        "name": "Hyderabad Campus",
        "location": "Jawahar Nagar, Hyderabad",
        "state": "Telangana",
    },
}

# Thread-safe global scraper telemetry state
_scraper_lock = threading.Lock()
_scraper_state: Dict[str, Any] = {
    "is_running": False,
    "status": "IDLE",  # IDLE, RUNNING, COMPLETED, FAILED
    "progress_percent": 0,
    "message": "Ready to scrape official BITSAT cutoff data.",
    "records_count": 0,
    "years_count": 0,
    "started_at": None,
    "completed_at": None,
    "error": None,
}


def get_bits_scraper_status() -> Dict[str, Any]:
    with _scraper_lock:
        return dict(_scraper_state)


def _update_scraper_state(**kwargs):
    with _scraper_lock:
        _scraper_state.update(kwargs)


def fetch_bits_html(url: str = DEFAULT_BITS_URL) -> str:
    """
    Fetches raw HTML from official BITSAT cutoffs page.
    Uses requests with fallback to urllib, handling SSL flexibly.
    """
    logger.info(f"Connecting to official BITS Pilani cutoff page at {url}...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # Primary attempt: requests
    try:
        resp = requests.get(url, headers=headers, timeout=25, verify=False)
        if resp.status_code == 200 and len(resp.text) > 1000:
            return resp.text
    except Exception as exc:
        logger.warning(f"Requests fetch failed ({exc}), falling back to urllib...")

    # Secondary attempt: urllib with unverified context
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def normalize_program_and_degree(raw_prog: str) -> Tuple[str, str]:
    """
    Normalizes program name and extracts degree type.
    """
    p = raw_prog.strip()
    # Normalize B.Pharm naming
    if p.lower().startswith("b. pharm") or p.lower().startswith("b.pharm"):
        p = "B.Pharm."
        deg = "B.Pharm."
    elif p.startswith("B.E."):
        deg = "B.E."
    elif p.startswith("M.Sc."):
        deg = "M.Sc."
    else:
        deg = "Integrated First Degree"
    return p, deg


def parse_bits_html(html_content: str, target_years: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Parses HTML content from BITSAT cutoff page for the specified academic years.
    Handles both modern 4-cell table structures and legacy nested structures.
    """
    if target_years is None:
        target_years = list(TARGET_YEARS)

    soup = BeautifulSoup(html_content, "html.parser")
    all_records: List[Dict[str, Any]] = []

    for yr in target_years:
        div = soup.find("div", id=yr)
        if not div:
            logger.warning(f"No div found with id='{yr}' on BITSAT page.")
            continue

        current_campus_key = "pilani"
        tables = div.find_all("table")

        for table in tables:
            for tr in table.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                if not cells:
                    continue

                # 4-cell row format: [Campus, Program, Cut-off Score, Max Marks]
                if len(cells) >= 4 and cells[2].isdigit() and cells[3].isdigit():
                    campus_str = cells[0].lower().strip()
                    raw_program = cells[1].strip()
                    score = int(cells[2])
                    max_marks = int(cells[3])

                    # Match campus
                    campus_info = None
                    for k, meta in CAMPUS_METADATA.items():
                        if k in campus_str:
                            campus_info = meta
                            break
                    if not campus_info:
                        campus_info = CAMPUS_METADATA["pilani"]

                    prog_name, degree_type = normalize_program_and_degree(raw_program)
                    pct = round((score / max_marks) * 100, 2) if max_marks > 0 else None

                    all_records.append({
                        "academic_year": yr,
                        "campus": campus_info,
                        "program_name": prog_name,
                        "degree_type": degree_type,
                        "cutoff_score": score,
                        "max_marks": max_marks,
                        "score_percentage": pct,
                        "category": "General Merit",
                        "exam_name": "BITSAT",
                    })

                # 3-cell format: [Program, Cut-off Score, Max Marks] where Campus was declared in header
                elif len(cells) >= 3 and cells[1].isdigit() and cells[2].isdigit():
                    raw_program = cells[0].strip()
                    score = int(cells[1])
                    max_marks = int(cells[2])

                    campus_info = CAMPUS_METADATA.get(current_campus_key, CAMPUS_METADATA["pilani"])
                    prog_name, degree_type = normalize_program_and_degree(raw_program)
                    pct = round((score / max_marks) * 100, 2) if max_marks > 0 else None

                    all_records.append({
                        "academic_year": yr,
                        "campus": campus_info,
                        "program_name": prog_name,
                        "degree_type": degree_type,
                        "cutoff_score": score,
                        "max_marks": max_marks,
                        "score_percentage": pct,
                        "category": "General Merit",
                        "exam_name": "BITSAT",
                    })

                else:
                    # Header row check to switch current campus
                    row_lower = " ".join(cells).lower()
                    for k in CAMPUS_METADATA:
                        if k in row_lower:
                            current_campus_key = k
                            break

    logger.info(f"Parsed {len(all_records)} BITSAT cutoff records across years: {target_years}.")
    return all_records


def save_bits_data(records: List[Dict[str, Any]], source_url: str = DEFAULT_BITS_URL) -> int:
    """
    Saves parsed BITSAT records into dedicated bits.db database.
    Uses duplicate prevention / upsert semantics within a single transaction.
    """
    init_bits_database()
    conn = get_bits_connection()
    try:
        cur = conn.cursor()

        # Cache known IDs
        campus_cache: Dict[str, int] = {}
        cur.execute("SELECT id, campus_code FROM campuses")
        for row in cur.fetchall():
            campus_cache[row["campus_code"]] = row["id"]

        prog_cache: Dict[str, int] = {}
        cur.execute("SELECT id, program_name FROM programs")
        for row in cur.fetchall():
            prog_cache[row["program_name"]] = row["id"]

        inserted_count = 0
        years_seen = set()

        for rec in records:
            c_meta = rec["campus"]
            c_code = c_meta["code"]

            if c_code not in campus_cache:
                cur.execute("""
                    INSERT INTO campuses (campus_code, campus_name, location, state)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(campus_code) DO UPDATE SET 
                        campus_name = excluded.campus_name,
                        location = excluded.location,
                        state = excluded.state,
                        updated_at = CURRENT_TIMESTAMP
                """, (c_code, c_meta["name"], c_meta.get("location"), c_meta.get("state")))
                cur.execute("SELECT id FROM campuses WHERE campus_code = ?", (c_code,))
                campus_id = cur.fetchone()[0]
                campus_cache[c_code] = campus_id
            else:
                campus_id = campus_cache[c_code]

            p_name = rec["program_name"]
            deg_type = rec["degree_type"]

            if p_name not in prog_cache:
                cur.execute("""
                    INSERT INTO programs (program_name, degree_type)
                    VALUES (?, ?)
                    ON CONFLICT(program_name) DO UPDATE SET 
                        degree_type = excluded.degree_type,
                        updated_at = CURRENT_TIMESTAMP
                """, (p_name, deg_type))
                cur.execute("SELECT id FROM programs WHERE program_name = ?", (p_name,))
                prog_id = cur.fetchone()[0]
                prog_cache[p_name] = prog_id
            else:
                prog_id = prog_cache[p_name]

            year = rec["academic_year"]
            years_seen.add(year)

            cur.execute("""
                INSERT INTO cutoff_records (
                    academic_year, campus_id, program_id, cutoff_score,
                    max_marks, score_percentage, category, exam_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(academic_year, campus_id, program_id, category) DO UPDATE SET 
                    cutoff_score = excluded.cutoff_score,
                    max_marks = excluded.max_marks,
                    score_percentage = excluded.score_percentage,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                year,
                campus_id,
                prog_id,
                rec["cutoff_score"],
                rec["max_marks"],
                rec.get("score_percentage"),
                rec.get("category", "General Merit"),
                rec.get("exam_name", "BITSAT"),
            ))
            inserted_count += 1

        # Audit scraper run
        cur.execute("""
            INSERT INTO scraper_meta (source_url, years_scraped, total_records, status, message)
            VALUES (?, ?, ?, 'SUCCESS', ?)
        """, (
            source_url,
            ", ".join(sorted(years_seen)),
            inserted_count,
            f"Successfully scraped {inserted_count} BITSAT cutoffs for years: {', '.join(sorted(years_seen))}."
        ))

        conn.commit()
        logger.info(f"Database sync complete! Upserted {inserted_count} BITSAT cutoff records.")
        return inserted_count
    finally:
        conn.close()


def run_bits_scraper(url: str = DEFAULT_BITS_URL, target_years: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Executes the full BITSAT scraper pipeline synchronously.
    """
    if target_years is None:
        target_years = list(TARGET_YEARS)

    start_time = datetime.now()
    _update_scraper_state(
        is_running=True,
        status="RUNNING",
        progress_percent=15,
        message=f"Fetching official BITSAT cutoffs from {url}...",
        started_at=start_time.isoformat(),
        error=None,
    )

    try:
        # Step 1: Fetch HTML
        html = fetch_bits_html(url)
        _update_scraper_state(
            progress_percent=45,
            message=f"Fetched {len(html)} bytes. Parsing cutoffs for years: {', '.join(target_years)}...",
        )

        # Step 2: Parse
        records = parse_bits_html(html, target_years=target_years)
        if not records:
            raise ValueError(f"No cutoff records found for years {target_years} on BITS page.")

        _update_scraper_state(
            progress_percent=75,
            message=f"Parsed {len(records)} cutoffs. Saving into dedicated bits.db...",
        )

        # Step 3: Save to bits.db
        saved_count = save_bits_data(records, source_url=url)
        end_time = datetime.now()

        result = {
            "success": True,
            "message": f"Successfully scraped and stored {saved_count} BITSAT cutoffs across {len(target_years)} years.",
            "records_count": saved_count,
            "years": target_years,
            "years_count": len(target_years),
            "url": url,
            "duration_seconds": round((end_time - start_time).total_seconds(), 2),
        }

        _update_scraper_state(
            is_running=False,
            status="COMPLETED",
            progress_percent=100,
            records_count=saved_count,
            years_count=len(target_years),
            completed_at=end_time.isoformat(),
            message=result["message"],
        )
        return result

    except Exception as exc:
        err_msg = str(exc)
        logger.error(f"BITSAT Scraper failed: {err_msg}", exc_info=True)
        _update_scraper_state(
            is_running=False,
            status="FAILED",
            progress_percent=0,
            error=err_msg,
            message=f"Scraping failed: {err_msg}",
            completed_at=datetime.now().isoformat(),
        )
        return {
            "success": False,
            "error": err_msg,
            "message": f"Scraping failed: {err_msg}",
        }


def start_bits_scraper_background(url: str = DEFAULT_BITS_URL, target_years: Optional[List[str]] = None) -> bool:
    """
    Triggers the scraper in a background thread if not currently running.
    """
    with _scraper_lock:
        if _scraper_state["is_running"]:
            return False
        _scraper_state["is_running"] = True
        _scraper_state["status"] = "RUNNING"
        _scraper_state["progress_percent"] = 5
        _scraper_state["message"] = "Initializing background BITSAT scraper..."
        _scraper_state["started_at"] = datetime.now().isoformat()
        _scraper_state["error"] = None

    def worker():
        run_bits_scraper(url=url, target_years=target_years)

    thread = threading.Thread(target=worker, daemon=True, name="bits-scraper-worker")
    thread.start()
    return True


if __name__ == "__main__":
    res = run_bits_scraper()
    print("Scraper Execution Result:", res)
