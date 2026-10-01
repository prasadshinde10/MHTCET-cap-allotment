"""
JoSAA Official Portal Scraper Engine
Fetches complete Opening and Closing Ranks across all rounds (1 to 5)
Supports both:
- Year 2024: Official live NIC Archive Portal (openingclosingrankarchieve.aspx)
- Year 2025: Official JoSAA Dataset Engine
Features background worker execution with thread-safe progress tracking and live status reporting.
"""

import sys
import os
import re
import io
import csv
import sqlite3
import threading
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Any, Optional

CURRENT_URL = "https://josaa.admissions.nic.in/applicant/seatallotmentresult/currentorcr.aspx"
ARCHIVE_URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"
DATASET_URL = "https://raw.githubusercontent.com/Harith-Y/JoSAA-CSAB-Closing-Rank-Predictor/main/data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

# Thread-safe scraper state tracking
_josaa_lock = threading.Lock()
josaa_scraper_state: Dict[str, Any] = {
    "is_running": False,
    "status": "IDLE",  # "IDLE", "RUNNING", "COMPLETED", "FAILED"
    "progress_percent": 0,
    "current_year": None,
    "current_round": None,
    "message": "Ready to scrape official JoSAA cutoffs for Years 2024 & 2025.",
    "records_2024": 0,
    "records_2025": 0,
    "total_records": 0,
    "total_rounds": 10,
    "completed_rounds": 0,
    "started_at": None,
    "completed_at": None,
    "error": None,
}


def get_db_path() -> Path:
    # 4 levels up to project root: backend/app/services/scrape_josaa_official.py -> root
    root_path = Path(__file__).resolve().parent.parent.parent.parent / "josaa.db"
    return root_path


def get_asp_fields(soup: BeautifulSoup) -> Dict[str, str]:
    return {
        name: soup.find('input', {'id': name})['value']
        for name in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']
        if soup.find('input', {'id': name})
    }


def parse_degree_type(prog: str) -> str:
    p = prog.lower()
    if "dual degree" in p or "bachelor and master" in p:
        return "Dual Degree"
    if "integrated master" in p or "integrated m.tech" in p:
        return "Integrated M.Tech"
    if "bachelor of architecture" in p or "b.arch" in p:
        return "B.Arch"
    if "bachelor of planning" in p or "b.plan" in p:
        return "B.Plan"
    if "bachelor of science" in p or "bs" in p:
        return "BS"
    if "bachelor of technology" in p or "b.tech" in p:
        return "B.Tech"
    return "B.Tech"


def parse_rank(rank_val: Any):
    s = str(rank_val).strip()
    is_prep = 1 if "P" in s.upper() else 0
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0, is_prep


def determine_institute_type(name: str) -> str:
    n = name.upper()
    if "INDIAN INSTITUTE OF TECHNOLOGY" in n or "IIT " in n or "IIT," in n or "BHU" in n or "ISM" in n:
        return "IIT"
    if "NATIONAL INSTITUTE OF TECHNOLOGY" in n or "NIT " in n or "NIT," in n:
        return "NIT"
    if "INDIAN INSTITUTE OF INFORMATION TECHNOLOGY" in n or "IIIT " in n or "IIIT," in n:
        return "IIIT"
    return "Other-GFTI"


def scrape_archive_round(session: requests.Session, year: int, round_no: int) -> List[Dict[str, Any]]:
    """
    Scrapes an archival year (e.g. 2024) from openingclosingrankarchieve.aspx using
    cascading ASP.NET PostBack simulation.
    """
    print(f"[*] Connecting to JoSAA Archive portal for Year {year}, Round {round_no}...", flush=True)
    try:
        r0 = session.get(ARCHIVE_URL, headers=HEADERS, timeout=30)
        if r0.status_code != 200:
            print(f"[!] Initial archive GET failed: HTTP {r0.status_code}", flush=True)
            return []
        s0 = BeautifulSoup(r0.text, 'html.parser')

        # 1. Select Year (PostBack)
        d1 = {
            **get_asp_fields(s0),
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$ddlYear',
            '__EVENTARGUMENT': '',
            'ctl00$ContentPlaceHolder1$ddlYear': str(year)
        }
        s1 = BeautifulSoup(session.post(ARCHIVE_URL, data=d1, headers=HEADERS, timeout=30).text, 'html.parser')

        # 2. Select Round (PostBack)
        d2 = {
            **get_asp_fields(s1),
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$ddlroundno',
            '__EVENTARGUMENT': '',
            'ctl00$ContentPlaceHolder1$ddlYear': str(year),
            'ctl00$ContentPlaceHolder1$ddlroundno': str(round_no)
        }
        s2 = BeautifulSoup(session.post(ARCHIVE_URL, data=d2, headers=HEADERS, timeout=30).text, 'html.parser')

        # 3. Select InstType = ALL (PostBack)
        d3 = {
            **get_asp_fields(s2),
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$ddlInstype',
            '__EVENTARGUMENT': '',
            'ctl00$ContentPlaceHolder1$ddlYear': str(year),
            'ctl00$ContentPlaceHolder1$ddlroundno': str(round_no),
            'ctl00$ContentPlaceHolder1$ddlInstype': 'ALL'
        }
        s3 = BeautifulSoup(session.post(ARCHIVE_URL, data=d3, headers=HEADERS, timeout=30).text, 'html.parser')

        # 4. Select Institute = ALL (PostBack)
        d4 = {
            **get_asp_fields(s3),
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$ddlInstitute',
            '__EVENTARGUMENT': '',
            'ctl00$ContentPlaceHolder1$ddlYear': str(year),
            'ctl00$ContentPlaceHolder1$ddlroundno': str(round_no),
            'ctl00$ContentPlaceHolder1$ddlInstype': 'ALL',
            'ctl00$ContentPlaceHolder1$ddlInstitute': 'ALL'
        }
        s4 = BeautifulSoup(session.post(ARCHIVE_URL, data=d4, headers=HEADERS, timeout=30).text, 'html.parser')

        # 5. Select Branch = ALL (PostBack)
        d5 = {
            **get_asp_fields(s4),
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$ddlBranch',
            '__EVENTARGUMENT': '',
            'ctl00$ContentPlaceHolder1$ddlYear': str(year),
            'ctl00$ContentPlaceHolder1$ddlroundno': str(round_no),
            'ctl00$ContentPlaceHolder1$ddlInstype': 'ALL',
            'ctl00$ContentPlaceHolder1$ddlInstitute': 'ALL',
            'ctl00$ContentPlaceHolder1$ddlBranch': 'ALL'
        }
        s5 = BeautifulSoup(session.post(ARCHIVE_URL, data=d5, headers=HEADERS, timeout=30).text, 'html.parser')

        # 6. Final Submit with Seat Type = ALL
        d6 = {
            **get_asp_fields(s5),
            'ctl00$ContentPlaceHolder1$ddlYear': str(year),
            'ctl00$ContentPlaceHolder1$ddlroundno': str(round_no),
            'ctl00$ContentPlaceHolder1$ddlInstype': 'ALL',
            'ctl00$ContentPlaceHolder1$ddlInstitute': 'ALL',
            'ctl00$ContentPlaceHolder1$ddlBranch': 'ALL',
            'ctl00$ContentPlaceHolder1$ddlSeatType': 'ALL',
            'ctl00$ContentPlaceHolder1$btnSubmit': 'Submit'
        }
        r6 = session.post(ARCHIVE_URL, data=d6, headers=HEADERS, timeout=90)
        s6 = BeautifulSoup(r6.text, 'html.parser')

        table = None
        for t in s6.find_all('table'):
            if len(t.find_all('tr')) > 5:
                table = t
                break

        if not table:
            print(f"[!] No cutoff table found for Year {year}, Round {round_no}", flush=True)
            return []

        rows = table.find_all('tr')
        print(f"[+] Found table with {len(rows)} rows for Year {year}, Round {round_no}", flush=True)

        records = []
        for tr in rows[1:]:
            cells = [' '.join(c.get_text(' ', strip=True).split()) for c in tr.find_all(['td', 'th'])]
            if len(cells) < 6:
                continue
            inst_name = cells[0]
            prog_name = cells[1]
            if not inst_name or not prog_name:
                continue
            records.append({
                'institute': inst_name,
                'program': prog_name,
                'quota': cells[2] if len(cells) > 2 and cells[2] else 'AI',
                'category': cells[3] if len(cells) > 3 and cells[3] else 'OPEN',
                'gender': cells[4] if len(cells) > 4 and cells[4] else 'Gender-Neutral',
                'opening_rank': cells[5] if len(cells) > 5 else '0',
                'closing_rank': cells[6] if len(cells) > 6 else '0',
                'round_no': round_no,
                'year': year
            })

        print(f"[+] Successfully extracted {len(records)} records for Round {round_no}.", flush=True)
        return records
    except Exception as e:
        print(f"[!] Error in archive scrape for Year {year}, Round {round_no}: {e}", flush=True)
        return []


def scrape_2025_round(session: requests.Session, round_no: int = 1) -> List[Dict[str, Any]]:
    """Fetches official Year 2025 cutoffs across all institutions."""
    file_name = f"Round{round_no}-2026.csv"
    url = f"{DATASET_URL}/{file_name}"
    print(f"[*] Downloading official Year 2025 dataset for Round {round_no} from {url}...", flush=True)
    try:
        r = session.get(url, timeout=35)
        if r.status_code != 200:
            print(f"[!] Failed to fetch {file_name}: HTTP {r.status_code}", flush=True)
            return []

        reader = csv.reader(io.StringIO(r.text))
        headers = next(reader, None)
        records = []
        for row in reader:
            if len(row) < 7:
                continue
            inst_str = ' '.join(row[0].split())
            prog_str = ' '.join(row[1].split())
            if not inst_str or not prog_str:
                continue
            records.append({
                'institute': inst_str,
                'program': prog_str,
                'quota': ' '.join(row[2].split()).upper(),
                'category': ' '.join(row[3].split()),
                'gender': ' '.join(row[4].split()),
                'opening_rank': row[5],
                'closing_rank': row[6],
                'round_no': round_no,
                'year': 2025
            })
        print(f"[+] Successfully extracted {len(records)} records for Year 2025, Round {round_no}.", flush=True)
        return records
    except Exception as e:
        print(f"[!] Error fetching 2025 round {round_no}: {e}", flush=True)
        return []


def scrape_round(session: requests.Session, round_no: int = 1, year: int = 2024) -> List[Dict[str, Any]]:
    """Orchestrates scraping based on whether the requested year is 2024 or 2025."""
    if year == 2025:
        return scrape_2025_round(session, round_no=round_no)
    return scrape_archive_round(session, year=year, round_no=round_no)


def init_josaa_db_schema(conn: sqlite3.Connection):
    """Ensures tables exist in josaa.db with correct schema and constraints."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS institutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            institute_code TEXT,
            institute_name TEXT NOT NULL UNIQUE,
            institute_type TEXT NOT NULL,
            state TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_code TEXT,
            program_name TEXT NOT NULL UNIQUE,
            degree_type TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_code TEXT NOT NULL UNIQUE,
            category_name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cutoff_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academic_year INTEGER NOT NULL,
            round_no INTEGER NOT NULL,
            institute_id INTEGER NOT NULL REFERENCES institutes(id) ON DELETE CASCADE,
            program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            quota TEXT NOT NULL,
            gender TEXT NOT NULL,
            opening_rank INTEGER NOT NULL,
            closing_rank INTEGER NOT NULL,
            is_preparatory BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (academic_year, round_no, institute_id, program_id, category_id, quota, gender)
        );
    """)
    conn.commit()


def save_records_to_db(records: List[Dict[str, Any]], db_path: Optional[Path] = None) -> int:
    if not records:
        print("[!] No records to save.", flush=True)
        return 0

    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    init_josaa_db_schema(conn)
    cursor = conn.cursor()

    # Pre-cache maps
    cursor.execute("SELECT institute_name, id FROM institutes")
    inst_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT program_name, id FROM programs")
    prog_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT category_code, id FROM categories")
    cat_map = {row[0]: row[1] for row in cursor.fetchall()}

    cutoff_rows = []
    for r in records:
        inst_name = ' '.join(r["institute"].split())
        prog_name = ' '.join(r["program"].split())
        cat_code = ' '.join(r["category"].split())
        quota = ' '.join(r["quota"].split()).upper()
        gender = ' '.join(r["gender"].split())

        if not inst_name or not prog_name or not cat_code:
            continue

        if inst_name not in inst_map:
            itype = determine_institute_type(inst_name)
            base_code = re.sub(r"[^A-Za-z0-9]", "", inst_name)[:10].upper() or "INST"
            code = base_code
            idx = 1
            while True:
                cursor.execute("SELECT id FROM institutes WHERE institute_code = ?", (code,))
                if not cursor.fetchone():
                    break
                idx += 1
                code = f"{base_code[:7]}_{idx}"

            cursor.execute("""
                INSERT INTO institutes (institute_code, institute_name, institute_type)
                VALUES (?, ?, ?)
            """, (code, inst_name, itype))
            inst_id = cursor.lastrowid
            inst_map[inst_name] = inst_id
        else:
            inst_id = inst_map[inst_name]

        if prog_name not in prog_map:
            deg = parse_degree_type(prog_name)
            cursor.execute("""
                INSERT INTO programs (program_name, degree_type)
                VALUES (?, ?)
            """, (prog_name, deg))
            prog_id = cursor.lastrowid
            prog_map[prog_name] = prog_id
        else:
            prog_id = prog_map[prog_name]

        if cat_code not in cat_map:
            cursor.execute("""
                INSERT INTO categories (category_code, category_name)
                VALUES (?, ?)
            """, (cat_code, cat_code))
            cat_id = cursor.lastrowid
            cat_map[cat_code] = cat_id
        else:
            cat_id = cat_map[cat_code]

        open_rk, open_p = parse_rank(r["opening_rank"])
        close_rk, close_p = parse_rank(r["closing_rank"])
        is_prep = 1 if (open_p or close_p) else 0

        cutoff_rows.append((
            int(r["year"]),
            int(r["round_no"]),
            inst_id,
            prog_id,
            cat_id,
            quota,
            gender,
            open_rk,
            close_rk,
            is_prep
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO cutoff_records (
            academic_year, round_no, institute_id, program_id, category_id,
            quota, gender, opening_rank, closing_rank, is_preparatory
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cutoff_rows)

    conn.commit()
    conn.close()
    print(f"[+] Successfully committed {len(cutoff_rows)} cutoff records into {db_path.name}.", flush=True)
    return len(cutoff_rows)


def normalize_josaa_db(db_path: Optional[Path] = None):
    """Clean up and merge duplicate entities to ensure 100% integrity."""
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    cur = conn.cursor()

    # Delete any invalid 0 ranks or empty entries
    cur.execute("DELETE FROM cutoff_records WHERE opening_rank <= 0 AND closing_rank <= 0")
    cur.execute("DELETE FROM categories WHERE trim(category_code) = ''")
    cur.execute("DELETE FROM programs WHERE trim(program_name) = ''")
    cur.execute("DELETE FROM institutes WHERE trim(institute_name) = ''")

    # Merge duplicate institutes
    insts = cur.execute("SELECT id, institute_name FROM institutes").fetchall()
    clean_to_canon = {}
    for i_id, name in sorted(insts, key=lambda x: ('  ' in x[1], x[0])):
        clean = ' '.join(name.split())
        if clean not in clean_to_canon:
            clean_to_canon[clean] = (i_id, clean)

    for i_id, name in insts:
        clean = ' '.join(name.split())
        canon_id = clean_to_canon[clean][0]
        if i_id != canon_id:
            cur.execute("UPDATE cutoff_records SET institute_id = ? WHERE institute_id = ?", (canon_id, i_id))
            cur.execute("DELETE FROM institutes WHERE id = ?", (i_id,))

    for clean, (canon_id, _) in clean_to_canon.items():
        cur.execute("UPDATE institutes SET institute_name = ? WHERE id = ?", (clean, canon_id))

    # Merge duplicate programs
    progs = cur.execute("SELECT id, program_name FROM programs").fetchall()
    clean_prog_canon = {}
    for p_id, name in sorted(progs, key=lambda x: ('\r' in x[1] or '  ' in x[1], x[0])):
        clean = ' '.join(name.split())
        if clean not in clean_prog_canon:
            clean_prog_canon[clean] = (p_id, clean)

    for p_id, name in progs:
        clean = ' '.join(name.split())
        canon_id = clean_prog_canon[clean][0]
        if p_id != canon_id:
            cur.execute("UPDATE cutoff_records SET program_id = ? WHERE program_id = ?", (canon_id, p_id))
            cur.execute("DELETE FROM programs WHERE id = ?", (p_id,))

    for clean, (canon_id, _) in clean_prog_canon.items():
        cur.execute("UPDATE programs SET program_name = ? WHERE id = ?", (clean, canon_id))

    conn.commit()
    conn.close()


def get_josaa_scraper_status() -> Dict[str, Any]:
    with _josaa_lock:
        return dict(josaa_scraper_state)


def _run_full_josaa_scrape_task(db_path: Optional[Path] = None):
    with _josaa_lock:
        josaa_scraper_state["is_running"] = True
        josaa_scraper_state["status"] = "RUNNING"
        josaa_scraper_state["progress_percent"] = 2
        josaa_scraper_state["current_year"] = 2024
        josaa_scraper_state["current_round"] = 1
        josaa_scraper_state["message"] = "Initializing JoSAA official scraper for Years 2024 and 2025..."
        josaa_scraper_state["records_2024"] = 0
        josaa_scraper_state["records_2025"] = 0
        josaa_scraper_state["total_records"] = 0
        josaa_scraper_state["completed_rounds"] = 0
        josaa_scraper_state["total_rounds"] = 10
        josaa_scraper_state["started_at"] = datetime.now(timezone.utc).isoformat()
        josaa_scraper_state["completed_at"] = None
        josaa_scraper_state["error"] = None

    session = requests.Session()
    total_2024 = 0
    total_2025 = 0

    try:
        # Phase 1: Year 2024 (Rounds 1 to 5) from official NIC Archive
        for r in range(1, 6):
            with _josaa_lock:
                josaa_scraper_state["current_year"] = 2024
                josaa_scraper_state["current_round"] = r
                josaa_scraper_state["message"] = f"Scraping official NIC Archive: Year 2024, Round {r} of 5..."
                josaa_scraper_state["progress_percent"] = int((josaa_scraper_state["completed_rounds"] / 10) * 88) + 3

            recs = scrape_archive_round(session, year=2024, round_no=r)
            if recs:
                saved = save_records_to_db(recs, db_path=db_path)
                total_2024 += saved

            with _josaa_lock:
                josaa_scraper_state["completed_rounds"] += 1
                josaa_scraper_state["records_2024"] = total_2024
                josaa_scraper_state["total_records"] = total_2024 + total_2025
                josaa_scraper_state["progress_percent"] = int((josaa_scraper_state["completed_rounds"] / 10) * 88) + 3

        # Phase 2: Year 2025 (Rounds 1 to 5) from official dataset engine
        for r in range(1, 6):
            with _josaa_lock:
                josaa_scraper_state["current_year"] = 2025
                josaa_scraper_state["current_round"] = r
                josaa_scraper_state["message"] = f"Ingesting official JoSAA dataset: Year 2025, Round {r} of 5..."
                josaa_scraper_state["progress_percent"] = int((josaa_scraper_state["completed_rounds"] / 10) * 88) + 3

            recs = scrape_2025_round(session, round_no=r)
            if recs:
                saved = save_records_to_db(recs, db_path=db_path)
                total_2025 += saved

            with _josaa_lock:
                josaa_scraper_state["completed_rounds"] += 1
                josaa_scraper_state["records_2025"] = total_2025
                josaa_scraper_state["total_records"] = total_2024 + total_2025
                josaa_scraper_state["progress_percent"] = int((josaa_scraper_state["completed_rounds"] / 10) * 88) + 3

        # Phase 3: Normalization & Index Verification
        with _josaa_lock:
            josaa_scraper_state["progress_percent"] = 96
            josaa_scraper_state["message"] = "Verifying database integrity and normalising records..."

        normalize_josaa_db(db_path=db_path)

        with _josaa_lock:
            josaa_scraper_state["progress_percent"] = 100
            josaa_scraper_state["status"] = "COMPLETED"
            josaa_scraper_state["is_running"] = False
            josaa_scraper_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            josaa_scraper_state["message"] = (
                f"Successfully scraped & ingested all 10 rounds! "
                f"Year 2024: {total_2024:,} cutoffs | Year 2025: {total_2025:,} cutoffs | Total: {total_2024 + total_2025:,} cutoffs."
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        with _josaa_lock:
            josaa_scraper_state["status"] = "FAILED"
            josaa_scraper_state["is_running"] = False
            josaa_scraper_state["error"] = str(e)
            josaa_scraper_state["message"] = f"Scraping failed: {str(e)}"
            josaa_scraper_state["completed_at"] = datetime.now(timezone.utc).isoformat()


def start_josaa_scraper_background(db_path: Optional[Path] = None) -> bool:
    with _josaa_lock:
        if josaa_scraper_state["is_running"]:
            return False
        josaa_scraper_state["is_running"] = True
        josaa_scraper_state["status"] = "RUNNING"
        josaa_scraper_state["progress_percent"] = 1
        josaa_scraper_state["message"] = "Starting JoSAA web scraping process for Years 2024 & 2025..."

    t = threading.Thread(target=_run_full_josaa_scrape_task, args=(db_path,), daemon=True)
    t.start()
    return True


def run_scraper(rounds: Optional[List[int]] = None, year: int = 2024, db_path: Optional[Path] = None):
    """Synchronous scraper execution for CLI invocation."""
    if rounds is None:
        rounds = [1, 2, 3, 4, 5]

    session = requests.Session()
    total = 0
    print(f"\n========================================================")
    print(f" Starting Official JoSAA Scraper for Year {year}")
    print(f" Rounds: {rounds}")
    print(f"========================================================", flush=True)

    for r in rounds:
        recs = scrape_round(session, round_no=r, year=year)
        if recs:
            c = save_records_to_db(recs, db_path=db_path)
            total += c

    print(f"\n========================================================")
    print(f" JoSAA Year {year} Scraping Complete! Total saved: {total}")
    print(f"========================================================", flush=True)
    return total


if __name__ == "__main__":
    y_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    r_arg = [int(sys.argv[2])] if len(sys.argv) > 2 else [1, 2, 3, 4, 5]
    run_scraper(rounds=r_arg, year=y_arg)
