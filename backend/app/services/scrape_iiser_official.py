import re
import ssl
import time
import urllib.request
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from bs4 import BeautifulSoup
from pathlib import Path

from app.iiser_db import get_iiser_connection, init_iiser_database

logger = logging.getLogger("iiser_scraper")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(asctime)s] [IISER-SCRAPER] %(levelname)s: %(message)s"))
    logger.addHandler(ch)

DEFAULT_IISER_URL = "https://www.iiseradmission.in/pages/closing_ranks.html"

# Known IISER campuses metadata
IISER_CAMPUSES = {
    "berhampur": {"code": "IISER-BPR", "name": "IISER Berhampur", "state": "Odisha"},
    "bhopal": {"code": "IISER-BHO", "name": "IISER Bhopal", "state": "Madhya Pradesh"},
    "kolkata": {"code": "IISER-KOL", "name": "IISER Kolkata", "state": "West Bengal"},
    "mohali": {"code": "IISER-MOH", "name": "IISER Mohali", "state": "Punjab"},
    "pune": {"code": "IISER-PUN", "name": "IISER Pune", "state": "Maharashtra"},
    "thiruvananthapuram": {"code": "IISER-TVM", "name": "IISER Thiruvananthapuram", "state": "Kerala"},
    "tirupati": {"code": "IISER-TIR", "name": "IISER Tirupati", "state": "Andhra Pradesh"},
}

CATEGORY_NAMES = {
    "UR": ("Unreserved (General)", False),
    "UR-PwD": ("Unreserved PwD", True),
    "EWS": ("Economically Weaker Section (EWS)", False),
    "EWS PwD": ("EWS PwD", True),
    "OBC-NCL": ("Other Backward Classes Non-Creamy Layer", False),
    "OBC-NCL PwD": ("OBC-NCL PwD", True),
    "SC": ("Scheduled Caste (SC)", False),
    "SC PwD": ("SC PwD", True),
    "ST": ("Scheduled Tribe (ST)", False),
    "ST PwD": ("ST PwD", True),
    "KM": ("Kashmiri Migrant", False),
}

# Thread-safe global scraper telemetry state
_scraper_lock = threading.Lock()
_scraper_state: Dict[str, Any] = {
    "is_running": False,
    "status": "IDLE",  # IDLE, RUNNING, COMPLETED, FAILED
    "progress_percent": 0,
    "current_round": None,
    "message": "Ready to scrape official IISER cutoff data.",
    "records_count": 0,
    "total_rounds": 0,
    "started_at": None,
    "completed_at": None,
    "error": None,
}


def get_iiser_scraper_status() -> Dict[str, Any]:
    with _scraper_lock:
        return dict(_scraper_state)


def _update_scraper_state(**kwargs):
    with _scraper_lock:
        _scraper_state.update(kwargs)


def fetch_official_html(url: str = DEFAULT_IISER_URL) -> str:
    """
    Fetches raw HTML from the official IISER closing ranks page.
    Handles SSL verification issues gracefully.
    """
    logger.info(f"Connecting to official IISER closing ranks portal at {url}...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)

    # First attempt with standard SSL
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.read().decode("utf-8")
    except Exception as exc:
        logger.warning(f"Standard SSL verification failed ({exc}). Retrying with unverified context...")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            return response.read().decode("utf-8")


def parse_program_and_institute(raw_text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parses a raw program string (e.g. 'BS-MS IISER Berhampur' or 
    'B.Tech. Data Science and Engineering IISER Bhopal') into:
    - Institute metadata: {code, name, state}
    - Program metadata: {name, degree_type}
    """
    cleaned = raw_text.strip()

    # Search for IISER <City>
    match = re.search(r"(IISER\s+[A-Za-z]+)", cleaned, re.IGNORECASE)
    if match:
        matched_inst = match.group(1).strip()
        city = matched_inst.split()[-1].lower()
        if city in IISER_CAMPUSES:
            inst_meta = dict(IISER_CAMPUSES[city])
        else:
            inst_meta = {
                "code": f"IISER-{city.upper()[:3]}",
                "name": matched_inst,
                "state": "India"
            }
        
        # Remaining portion is the program name
        prog_part = cleaned.replace(matched_inst, "").strip()
        # Clean trailing/leading hyphens or brackets
        prog_part = re.sub(r"^\s*-\s*", "", prog_part).strip()
        if not prog_part or prog_part == "BS-MS":
            prog_part = "BS-MS (Dual Degree)"
    else:
        # Fallback if pattern deviates
        inst_meta = {
            "code": "IISER-GEN",
            "name": "IISER System",
            "state": "India"
        }
        prog_part = cleaned

    # Determine degree type
    p_lower = prog_part.lower()
    if "b.tech" in p_lower:
        degree = "B.Tech"
    elif "bs-ms" in p_lower or "bs-ms" in raw_text.lower():
        degree = "BS-MS"
    elif p_lower.startswith("bs") or "bs (" in p_lower:
        degree = "BS"
    else:
        degree = "BS-MS"

    prog_meta = {
        "name": prog_part,
        "degree_type": degree
    }

    return inst_meta, prog_meta


def parse_iiser_html(html_content: str, default_year: int = 2024) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parses HTML content from IISER closing ranks page.
    Extracts all cutoff records and important round notices dynamically.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table")

    if not tables:
        raise ValueError("No closing rank tables found on the IISER webpage.")

    logger.info(f"Found {len(tables)} potential cutoff tables in HTML.")

    all_records: List[Dict[str, Any]] = []
    all_notices: List[Dict[str, Any]] = []

    # Default category order from the standard IISER layout
    fallback_categories = [
        "UR", "UR-PwD", "EWS", "EWS PwD", "OBC-NCL",
        "OBC-NCL PwD", "SC", "SC PwD", "ST", "ST PwD", "KM"
    ]

    for table_idx, table in enumerate(tables):
        # 1. Determine round number from previous h4 or the table thead
        parent = table.find_parent("div", class_="container") or table.parent
        prev_h4 = parent.find("h4") if parent else None
        if not prev_h4:
            prev_h4 = table.find_previous("h4")

        round_no = None
        if prev_h4:
            h4_text = prev_h4.get_text(strip=True)
            r_match = re.search(r"Round\s*(\d+)", h4_text, re.IGNORECASE)
            if r_match:
                round_no = int(r_match.group(1))

        if round_no is None:
            # Fallback: check inside thead
            thead_text = table.find("thead").get_text() if table.find("thead") else ""
            words_to_num = {
                "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10
            }
            for word, num in words_to_num.items():
                if word in thead_text.lower():
                    round_no = num
                    break

        if round_no is None:
            round_no = len(tables) - table_idx
            logger.warning(f"Could not extract round name for table {table_idx + 1}, using fallback: Round {round_no}")

        # 2. Extract Important Updates / Round Notices
        notice_div = parent.find("div", class_=re.compile(r"admission-important-notice")) if parent else None
        if not notice_div:
            notice_div = table.find_previous("div", class_=re.compile(r"admission-important-notice"))

        if notice_div:
            li_tags = notice_div.find_all("li")
            for li in li_tags:
                txt = li.get_text(" ", strip=True)
                if txt and not txt.startswith("<!--"):
                    all_notices.append({
                        "academic_year": default_year,
                        "round_no": round_no,
                        "notice_text": txt,
                    })
            if not li_tags:
                p_tag = notice_div.find("p")
                if p_tag:
                    txt = p_tag.get_text(" ", strip=True)
                    if txt:
                        all_notices.append({
                            "academic_year": default_year,
                            "round_no": round_no,
                            "notice_text": txt,
                        })

        # 3. Parse headers to detect category columns dynamically
        thead = table.find("thead")
        categories_for_table = list(fallback_categories)
        if thead:
            tr_rows = thead.find_all("tr")
            if len(tr_rows) >= 3:
                # Row 2 contains individual category headers (UR, UR-PwD, ...)
                sub_ths = [th.get_text(strip=True) for th in tr_rows[2].find_all("th")]
                # Add KM if KM is in row 1
                if "KM" not in sub_ths and any("KM" in th.get_text(strip=True) for th in tr_rows[1].find_all("th")):
                    sub_ths.append("KM")
                if len(sub_ths) == 11:
                    categories_for_table = sub_ths

        # 4. Parse rows
        tbody = table.find("tbody")
        if not tbody:
            continue

        for tr in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) < 2:
                continue

            raw_prog = cells[0]
            inst_meta, prog_meta = parse_program_and_institute(raw_prog)

            rank_cells = cells[1:]
            for cat_idx, val in enumerate(rank_cells):
                if cat_idx >= len(categories_for_table):
                    break
                cat_code = categories_for_table[cat_idx]

                # Sanitize rank
                cleaned_val = re.sub(r"[^\d]", "", val)
                if cleaned_val:
                    rank_num = int(cleaned_val)
                    if rank_num > 0:
                        all_records.append({
                            "academic_year": default_year,
                            "round_no": round_no,
                            "raw_program_name": raw_prog,
                            "institute": inst_meta,
                            "program": prog_meta,
                            "category_code": cat_code,
                            "closing_rank": rank_num,
                            "seat_pool": "Gender-Neutral",
                            "allocation_channel": "IAT",
                        })

    logger.info(f"Successfully extracted {len(all_records)} cutoff records across {len(tables)} rounds.")
    logger.info(f"Extracted {len(all_notices)} official round notices.")
    return all_records, all_notices


def save_iiser_data(records: List[Dict[str, Any]], notices: List[Dict[str, Any]], source_url: str = DEFAULT_IISER_URL) -> int:
    """
    Saves parsed IISER records and notices into dedicated iiser.db.
    Uses upsert semantics (duplicate prevention) inside a single transaction.
    """
    init_iiser_database()
    conn = get_iiser_connection()
    try:
        cur = conn.cursor()

        # Cache known IDs
        inst_cache: Dict[str, int] = {}
        cur.execute("SELECT id, institute_name FROM institutes")
        for row in cur.fetchall():
            inst_cache[row["institute_name"]] = row["id"]

        prog_cache: Dict[str, int] = {}
        cur.execute("SELECT id, program_name FROM programs")
        for row in cur.fetchall():
            prog_cache[row["program_name"]] = row["id"]

        cat_cache: Dict[str, int] = {}
        cur.execute("SELECT id, category_code FROM categories")
        for row in cur.fetchall():
            cat_cache[row["category_code"]] = row["id"]

        # Ensure categories exist
        for cat_code, (cat_name, is_pwd) in CATEGORY_NAMES.items():
            if cat_code not in cat_cache:
                cur.execute("""
                    INSERT INTO categories (category_code, category_name, is_pwd)
                    VALUES (?, ?, ?)
                    ON CONFLICT(category_code) DO UPDATE SET 
                        category_name = excluded.category_name,
                        is_pwd = excluded.is_pwd,
                        updated_at = CURRENT_TIMESTAMP
                """, (cat_code, cat_name, 1 if is_pwd else 0))
                cat_cache[cat_code] = cur.lastrowid

        # Insert records
        inserted_count = 0
        rounds_seen = set()
        years_seen = set()

        for rec in records:
            inst_info = rec["institute"]
            inst_name = inst_info["name"]
            if inst_name not in inst_cache:
                cur.execute("""
                    INSERT INTO institutes (institute_code, institute_name, state)
                    VALUES (?, ?, ?)
                    ON CONFLICT(institute_name) DO UPDATE SET 
                        institute_code = excluded.institute_code,
                        state = excluded.state,
                        updated_at = CURRENT_TIMESTAMP
                """, (inst_info.get("code"), inst_name, inst_info.get("state")))
                cur.execute("SELECT id FROM institutes WHERE institute_name = ?", (inst_name,))
                inst_id = cur.fetchone()[0]
                inst_cache[inst_name] = inst_id
            else:
                inst_id = inst_cache[inst_name]

            prog_info = rec["program"]
            prog_name = prog_info["name"]
            if prog_name not in prog_cache:
                cur.execute("""
                    INSERT INTO programs (program_name, degree_type)
                    VALUES (?, ?)
                    ON CONFLICT(program_name) DO UPDATE SET 
                        degree_type = excluded.degree_type,
                        updated_at = CURRENT_TIMESTAMP
                """, (prog_name, prog_info.get("degree_type", "BS-MS")))
                cur.execute("SELECT id FROM programs WHERE program_name = ?", (prog_name,))
                prog_id = cur.fetchone()[0]
                prog_cache[prog_name] = prog_id
            else:
                prog_id = prog_cache[prog_name]

            cat_code = rec["category_code"]
            if cat_code not in cat_cache:
                cat_name, is_pwd = CATEGORY_NAMES.get(cat_code, (cat_code, "PwD" in cat_code))
                cur.execute("""
                    INSERT INTO categories (category_code, category_name, is_pwd)
                    VALUES (?, ?, ?)
                    ON CONFLICT(category_code) DO UPDATE SET 
                        category_name = excluded.category_name,
                        updated_at = CURRENT_TIMESTAMP
                """, (cat_code, cat_name, 1 if is_pwd else 0))
                cur.execute("SELECT id FROM categories WHERE category_code = ?", (cat_code,))
                cat_id = cur.fetchone()[0]
                cat_cache[cat_code] = cat_id
            else:
                cat_id = cat_cache[cat_code]

            # Upsert cutoff record
            year = rec["academic_year"]
            r_no = rec["round_no"]
            years_seen.add(year)
            rounds_seen.add(r_no)

            cur.execute("""
                INSERT INTO cutoff_records (
                    academic_year, round_no, institute_id, program_id, category_id,
                    raw_program_name, closing_rank, seat_pool, allocation_channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(academic_year, round_no, institute_id, program_id, category_id) DO UPDATE SET 
                    closing_rank = excluded.closing_rank,
                    raw_program_name = excluded.raw_program_name,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                year,
                r_no,
                inst_id,
                prog_id,
                cat_id,
                rec["raw_program_name"],
                rec["closing_rank"],
                rec.get("seat_pool", "Gender-Neutral"),
                rec.get("allocation_channel", "IAT"),
            ))
            inserted_count += 1

        # Insert round notices
        for n in notices:
            cur.execute("""
                INSERT OR IGNORE INTO round_notices (academic_year, round_no, notice_text)
                VALUES (?, ?, ?)
            """, (n["academic_year"], n["round_no"], n["notice_text"]))

        # Log scraper metadata
        academic_year = max(years_seen) if years_seen else 2024
        cur.execute("""
            INSERT INTO scraper_meta (source_url, academic_year, total_records, total_rounds, status, message)
            VALUES (?, ?, ?, ?, 'SUCCESS', ?)
        """, (
            source_url,
            academic_year,
            inserted_count,
            len(rounds_seen),
            f"Successfully scraped {inserted_count} cutoffs across {len(rounds_seen)} rounds."
        ))

        conn.commit()
        logger.info(f"Database sync complete! Upserted {inserted_count} cutoff records.")
        return inserted_count
    finally:
        conn.close()


def run_iiser_scraper(url: str = DEFAULT_IISER_URL, default_year: int = 2024) -> Dict[str, Any]:
    """
    Executes the full scraper pipeline synchronously:
    1. Fetches official HTML from website
    2. Parses closing ranks and notices
    3. Saves data in dedicated iiser.db
    """
    start_time = datetime.now()
    _update_scraper_state(
        is_running=True,
        status="RUNNING",
        progress_percent=10,
        message=f"Fetching official closing ranks from {url}...",
        started_at=start_time.isoformat(),
        error=None,
    )

    try:
        # Step 1: Fetch
        html = fetch_official_html(url)
        _update_scraper_state(
            progress_percent=40,
            message=f"Fetched {len(html)} bytes. Parsing HTML tables...",
        )

        # Step 2: Parse
        records, notices = parse_iiser_html(html, default_year=default_year)
        total_rounds = len(set(r["round_no"] for r in records))
        _update_scraper_state(
            progress_percent=70,
            total_rounds=total_rounds,
            message=f"Parsed {len(records)} cutoffs across {total_rounds} rounds. Saving to iiser.db...",
        )

        # Step 3: Save to database
        saved_count = save_iiser_data(records, notices, source_url=url)
        end_time = datetime.now()

        result = {
            "success": True,
            "message": f"Successfully scraped and stored {saved_count} cutoff records across {total_rounds} rounds.",
            "records_count": saved_count,
            "notices_count": len(notices),
            "total_rounds": total_rounds,
            "url": url,
            "duration_seconds": round((end_time - start_time).total_seconds(), 2),
        }

        _update_scraper_state(
            is_running=False,
            status="COMPLETED",
            progress_percent=100,
            records_count=saved_count,
            total_rounds=total_rounds,
            completed_at=end_time.isoformat(),
            message=result["message"],
        )
        return result

    except Exception as exc:
        err_msg = str(exc)
        logger.error(f"IISER Scraper failed: {err_msg}", exc_info=True)
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


def start_iiser_scraper_background(url: str = DEFAULT_IISER_URL, default_year: int = 2024) -> bool:
    """
    Triggers the scraper in a background thread if not already running.
    """
    with _scraper_lock:
        if _scraper_state["is_running"]:
            return False
        _scraper_state["is_running"] = True
        _scraper_state["status"] = "RUNNING"
        _scraper_state["progress_percent"] = 5
        _scraper_state["message"] = "Initializing background scraper..."
        _scraper_state["started_at"] = datetime.now().isoformat()
        _scraper_state["error"] = None

    def worker():
        run_iiser_scraper(url=url, default_year=default_year)

    thread = threading.Thread(target=worker, daemon=True, name="iiser-scraper-worker")
    thread.start()
    return True


if __name__ == "__main__":
    res = run_iiser_scraper()
    print("Scraper Execution Result:", res)
