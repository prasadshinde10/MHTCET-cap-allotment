"""
MHT-CET Web Scraper Service with Real-Time Progress Tracking.
Scrapes official MHT-CET Institute Directory and Branchwise Intake
and persists records into `institutes` and `institute_courses` SQLite tables.
"""

import time
import sqlite3
import threading
import logging
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from app.parser.institutes_data import INSTITUTES_DATA

logger = logging.getLogger(__name__)

BASE_LIST_URL = "https://fe2026.mahacet.org/StaticPages/frmInstituteList?did=1884"
SUMMARY_URL_TEMPLATE = "https://fe2026.mahacet.org/StaticPages/frmInstituteSummary.aspx?InstituteCode={code}"

scraper_state: Dict[str, Any] = {
    "is_running": False,
    "status": "IDLE",  # IDLE, RUNNING, COMPLETED, FAILED
    "current": 0,
    "total": 0,
    "progress_percent": 0,
    "current_institute": "",
    "institutes_created": 0,
    "courses_created": 0,
    "message": "Ready to scrape official MHT-CET institutes directory.",
    "error": None,
    "started_at": None,
    "completed_at": None,
}

_scraper_lock = threading.Lock()


def get_scraper_status() -> Dict[str, Any]:
    with _scraper_lock:
        return dict(scraper_state)


def init_institutes_tables(db_path: str):
    """Ensures institutes and institute_courses tables exist in SQLite database."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS institutes (
            dte_code TEXT PRIMARY KEY,
            institute_name TEXT NOT NULL,
            district TEXT,
            region TEXT,
            status TEXT,
            autonomy_status TEXT,
            minority_status TEXT,
            address TEXT,
            affiliated_university TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS institute_courses (
            choice_code TEXT PRIMARY KEY,
            dte_code TEXT NOT NULL REFERENCES institutes(dte_code),
            course_name TEXT NOT NULL,
            university TEXT,
            status TEXT,
            autonomy_status TEXT,
            minority_status TEXT,
            shift TEXT,
            accreditation TEXT,
            gender_type TEXT,
            total_intake INTEGER
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inst_district ON institutes(district);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inst_univ ON institutes(affiliated_university);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crs_dte ON institute_courses(dte_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crs_name ON institute_courses(course_name);")

    conn.commit()
    conn.close()


def fetch_institute_codes() -> List[str]:
    """Fetches list of 387 institute codes from the official MHT CET portal with fallback."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(BASE_LIST_URL, headers=headers, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            codes = []
            for a in soup.find_all("a"):
                href = a.get("href", "")
                if "InstituteCode=" in href:
                    code = href.split("InstituteCode=")[-1].strip()
                    if code and code not in codes:
                        codes.append(code)
            if codes:
                logger.info(f"Fetched {len(codes)} institute codes from live MHT-CET portal.")
                return sorted(codes)
    except Exception as e:
        logger.warning(f"Live portal fetch failed ({e}), falling back to verified master codes.")

    return sorted(list(INSTITUTES_DATA.keys()))


def scrape_institute_detail(session: requests.Session, code: str):
    """Scrapes individual institute summary page for district, header metadata, and course intake."""
    url = SUMMARY_URL_TEMPLATE.format(code=code)
    cached = INSTITUTES_DATA.get(code.zfill(5), {})

    inst_data = {
        "dte_code": code,
        "institute_name": cached.get("name", f"Institute {code}"),
        "district": cached.get("district", "Maharashtra"),
        "region": cached.get("region", ""),
        "status": cached.get("status", "Un-Aided"),
        "autonomy_status": cached.get("college_type", "Non-Autonomous"),
        "minority_status": cached.get("minority_status", "Non-Minority"),
        "address": "",
        "affiliated_university": cached.get("home_university", "")
    }
    courses_data = []

    for _ in range(2):
        try:
            res = session.get(url, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                for tr in soup.find_all("tr"):
                    cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                    if len(cells) == 2:
                        k, v = cells[0].strip(), cells[1].strip()
                        if k == "Institute Name" and v:
                            inst_data["institute_name"] = v
                        elif k == "Institute Address" and v:
                            inst_data["address"] = v
                        elif k == "Minority Status" and v:
                            inst_data["minority_status"] = v
                    elif len(cells) == 4:
                        k1, v1, k2, v2 = cells[0].strip(), cells[1].strip(), cells[2].strip(), cells[3].strip()
                        if k1 == "Region" and v1:
                            inst_data["region"] = v1
                        if k2 == "District" and v2:
                            inst_data["district"] = v2
                        if k1 == "Status" and v1:
                            inst_data["status"] = v1
                        if k2 == "Autonomy Status" and v2:
                            inst_data["autonomy_status"] = v2

                # Parse Course Intake Table
                for table in soup.find_all("table"):
                    rows = table.find_all("tr")
                    if not rows:
                        continue
                    header_text = [th.get_text(" ", strip=True) for th in rows[0].find_all(["th", "td"])]
                    if "Choice Code" in header_text or "Course Name" in header_text:
                        for r in rows[1:]:
                            cols = [td.get_text(" ", strip=True) for td in r.find_all("td")]
                            if len(cols) >= 10:
                                try:
                                    intake = int(cols[9])
                                except ValueError:
                                    intake = 0

                                courses_data.append({
                                    "choice_code": cols[0],
                                    "dte_code": code,
                                    "course_name": cols[1],
                                    "university": cols[2],
                                    "status": cols[3],
                                    "autonomy_status": cols[4],
                                    "minority_status": cols[5],
                                    "shift": cols[6],
                                    "accreditation": cols[7],
                                    "gender_type": cols[8],
                                    "total_intake": intake
                                })

                if courses_data:
                    univs = [c["university"] for c in courses_data if c["university"]]
                    if univs:
                        inst_data["affiliated_university"] = max(set(univs), key=univs.count)

                return inst_data, courses_data
        except Exception:
            time.sleep(0.5)

    return inst_data, courses_data


def _run_scraper_task(db_paths: List[str]):
    """Background task executing the scrape and updating live progress."""
    global scraper_state
    try:
        with _scraper_lock:
            scraper_state["status"] = "RUNNING"
            scraper_state["is_running"] = True
            scraper_state["progress_percent"] = 2
            scraper_state["current"] = 0
            scraper_state["error"] = None
            scraper_state["started_at"] = datetime.now(timezone.utc).isoformat()
            scraper_state["message"] = "Connecting to MHT-CET portal and fetching institute list..."

        for p in db_paths:
            init_institutes_tables(p)

        codes = fetch_institute_codes()
        total_count = len(codes)

        with _scraper_lock:
            scraper_state["total"] = total_count
            scraper_state["progress_percent"] = 5
            scraper_state["message"] = f"Found {total_count} institutes. Beginning concurrent extraction..."

        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

        all_inst_data = []
        all_courses_data = []

        completed_count = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_code = {executor.submit(scrape_institute_detail, session, code): code for code in codes}
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                completed_count += 1
                try:
                    inst, crses = future.result()
                    if inst:
                        all_inst_data.append(inst)
                    if crses:
                        all_courses_data.extend(crses)
                except Exception as err:
                    logger.warning(f"Error scraping code {code}: {err}")

                pct = int((completed_count / total_count) * 85) + 5
                inst_name = inst["institute_name"] if (inst and "institute_name" in inst) else code
                with _scraper_lock:
                    scraper_state["current"] = completed_count
                    scraper_state["progress_percent"] = pct
                    scraper_state["current_institute"] = f"{code} - {inst_name[:40]}"
                    scraper_state["message"] = f"Scraped {completed_count}/{total_count}: {code} ({inst_name[:30]})..."
                    scraper_state["institutes_created"] = len(all_inst_data)
                    scraper_state["courses_created"] = len(all_courses_data)

        # Write to databases
        with _scraper_lock:
            scraper_state["progress_percent"] = 92
            scraper_state["message"] = "Committing normalized records to SQLite database..."

        for db_path in db_paths:
            try:
                conn = sqlite3.connect(db_path, timeout=30.0)
                cursor = conn.cursor()

                for item in all_inst_data:
                    cursor.execute("""
                        INSERT OR REPLACE INTO institutes (
                            dte_code, institute_name, district, region, status, autonomy_status,
                            minority_status, address, affiliated_university
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item["dte_code"], item["institute_name"], item["district"], item["region"],
                        item["status"], item["autonomy_status"], item["minority_status"],
                        item["address"], item["affiliated_university"]
                    ))

                for crs in all_courses_data:
                    cursor.execute("""
                        INSERT OR REPLACE INTO institute_courses (
                            choice_code, dte_code, course_name, university, status,
                            autonomy_status, minority_status, shift, accreditation,
                            gender_type, total_intake
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        crs["choice_code"], crs["dte_code"], crs["course_name"], crs["university"],
                        crs["status"], crs["autonomy_status"], crs["minority_status"], crs["shift"],
                        crs["accreditation"], crs["gender_type"], crs["total_intake"]
                    ))

                conn.commit()
                conn.close()
            except Exception as dberr:
                logger.error(f"Error persisting to {db_path}: {dberr}")

        with _scraper_lock:
            scraper_state["status"] = "COMPLETED"
            scraper_state["is_running"] = False
            scraper_state["progress_percent"] = 100
            scraper_state["current"] = total_count
            scraper_state["institutes_created"] = len(all_inst_data)
            scraper_state["courses_created"] = len(all_courses_data)
            scraper_state["message"] = f"Extraction complete: {len(all_inst_data)} institutes and {len(all_courses_data)} choice intake records saved."
            scraper_state["completed_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error(f"Scraper task encountered critical failure: {e}", exc_info=True)
        with _scraper_lock:
            scraper_state["status"] = "FAILED"
            scraper_state["is_running"] = False
            scraper_state["error"] = str(e)
            scraper_state["message"] = f"Scraper failed: {e}"


def trigger_institute_scraper(db_paths: List[str]) -> Dict[str, Any]:
    """Triggers the scraper in a background thread if not already running."""
    with _scraper_lock:
        if scraper_state["is_running"]:
            return {"status": "ALREADY_RUNNING", "message": "Scraper is currently active.", **scraper_state}

    t = threading.Thread(target=_run_scraper_task, args=(db_paths,), daemon=True)
    t.start()
    return {"status": "STARTED", "message": "MHT-CET institute scraper initiated."}
