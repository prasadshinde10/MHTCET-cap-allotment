"""
CSAB (Central Seat Allocation Board) Special Round Official Portal Scraper Engine
Fetches complete Opening and Closing CRL Ranks for Special Round 1 & Special Round 2:
- Target URL: https://admissions.nic.in/csabspl/Applicant/seatallotmentresult/currentorcr.aspx
Features background worker execution with thread-safe progress tracking and live status reporting.
"""

import sys
import os
import re
import io
import csv
import sqlite3
import threading
import time
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

try:
    import lxml.html
    HAS_LXML = True
except ImportError:
    HAS_LXML = False

from app.csab_db import get_csab_db_path, init_csab_db_schema
from app.services.scrape_josaa_official import OFFICIAL_HOME_STATE_MAPPING, clean_state_name

CSAB_URL = "https://admissions.nic.in/csabspl/Applicant/seatallotmentresult/currentorcr.aspx"
CSAB_ROUNDS = [1, 2]
DEFAULT_ACADEMIC_YEAR = 2026

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

# Thread-safe scraper state tracking
_csab_lock = threading.Lock()
csab_scraper_state: Dict[str, Any] = {
    "is_running": False,
    "status": "IDLE",  # "IDLE", "RUNNING", "COMPLETED", "FAILED"
    "progress_percent": 0,
    "current_round": None,
    "message": "Ready to scrape official CSAB Special Round cutoffs.",
    "records_round1": 0,
    "records_round2": 0,
    "total_records": 0,
    "total_rounds": 2,
    "completed_rounds": 0,
    "started_at": None,
    "completed_at": None,
    "error": None,
}


def get_asp_fields_fast(html_content: str) -> Dict[str, str]:
    """Ultra-fast ASP.NET viewstate field extraction using regex with lxml fallback."""
    fields = {}
    for name in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
        m = re.search(r'id=[\"\']' + name + r'[\"\']\s+value=[\"\']([^\"\']*)[\"\']', html_content)
        if not m:
            m = re.search(r'value=[\"\']([^\"\']*)[\"\']\s+id=[\"\']' + name + r'[\"\']', html_content)
        if not m:
            m = re.search(r'name=[\"\']' + name + r'[\"\']\s+value=[\"\']([^\"\']*)[\"\']', html_content)
        if m:
            fields[name] = m.group(1)

    if len(fields) < 3 and HAS_LXML:
        try:
            tree = lxml.html.fromstring(html_content)
            for name in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
                if name not in fields:
                    el = tree.xpath(f'//input[@id="{name}"]')
                    if el and el[0].get('value') is not None:
                        fields[name] = el[0].get('value')
        except Exception:
            pass
    return fields


def parse_cutoff_table_lxml(html_content: str, year: int, round_no: int) -> List[Dict[str, Any]]:
    """Fast, memory-efficient cutoff table parsing using lxml with BS4 fallback."""
    records = []
    if HAS_LXML:
        try:
            tree = lxml.html.fromstring(html_content)
            tables = tree.xpath('//table')
            target_table = None
            for t in tables:
                rows = t.xpath('.//tr')
                if len(rows) > 5:
                    target_table = t
                    break

            if target_table is not None:
                rows = target_table.xpath('.//tr')
                for tr in rows[1:]:
                    cells = [' '.join(c.text_content().split()) for c in tr.xpath('./td | ./th')]
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
                if records:
                    return records
        except Exception as e:
            print(f"[!] Warning: lxml table parsing failed, falling back to BeautifulSoup: {e}", flush=True)

    soup = BeautifulSoup(html_content, 'html.parser')
    table = None
    for t in soup.find_all('table'):
        if len(t.find_all('tr')) > 5:
            table = t
            break
    if not table:
        return []

    rows = table.find_all('tr')
    for tr in rows[1:]:
        cells = [' '.join(c.get_text(' ', strip=True).split()) for c in tr.find_all(['td', 'th'])]
        if len(cells) < 6 or not cells[0] or not cells[1]:
            continue
        records.append({
            'institute': cells[0],
            'program': cells[1],
            'quota': cells[2] if len(cells) > 2 and cells[2] else 'AI',
            'category': cells[3] if len(cells) > 3 and cells[3] else 'OPEN',
            'gender': cells[4] if len(cells) > 4 and cells[4] else 'Gender-Neutral',
            'opening_rank': cells[5] if len(cells) > 5 else '0',
            'closing_rank': cells[6] if len(cells) > 6 else '0',
            'round_no': round_no,
            'year': year
        })
    return records


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


def normalize_quota(q: str) -> str:
    s = ' '.join(q.split()).upper()
    if s in ["HS", "HOME STATE"]:
        return "HS"
    if s in ["OS", "OTHER STATE"]:
        return "OS"
    if s in ["AI", "ALL INDIA"]:
        return "AI"
    if "GOA" in s:
        return "GO"
    if "JAMMU" in s:
        return "JK"
    if "LADAKH" in s:
        return "LA"
    if s in ["AP", "ANDHRA PRADESH"]:
        return "AP"
    return s


def determine_institute_type(name: str) -> str:
    n = name.upper()
    if "NATIONAL INSTITUTE OF TECHNOLOGY" in n or "NIT " in n or "NIT," in n:
        return "NIT"
    if "INDIAN INSTITUTE OF INFORMATION TECHNOLOGY" in n or "IIIT " in n or "IIIT," in n:
        return "IIIT"
    if "INDIAN INSTITUTE OF ENGINEERING SCIENCE" in n or "IIEST" in n:
        return "IIEST"
    if ("PLANNING" in n and "ARCHITECTURE" in n) or "SPA " in n or "SPA," in n:
        return "SPA"
    return "Other-GFTI"


def scrape_csab_round(
    session: requests.Session,
    round_no: int = 1,
    year: int = DEFAULT_ACADEMIC_YEAR,
    max_retries: int = 3,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> List[Dict[str, Any]]:
    """
    Scrapes one CSAB Special Round from the official NIC portal:
    https://admissions.nic.in/csabspl/Applicant/seatallotmentresult/currentorcr.aspx
    using cascading ASP.NET PostBack simulation with auto-retry and fast lxml parsing.
    """
    for attempt in range(1, max_retries + 1):
        attempt_str = f" (Attempt {attempt}/{max_retries})" if attempt > 1 else ""
        if progress_callback:
            progress_callback(f"Connecting to CSAB portal{attempt_str}...", 0.05)
        print(f"[*] Connecting to CSAB portal for Special Round {round_no}{attempt_str}...", flush=True)

        try:
            s = requests.Session()
            r0 = s.get(CSAB_URL, headers=HEADERS, timeout=45)
            if r0.status_code != 200:
                print(f"[!] Initial CSAB GET failed: HTTP {r0.status_code}", flush=True)
                if attempt < max_retries:
                    if progress_callback:
                        progress_callback(f"CSAB portal HTTP {r0.status_code}. Retrying in {2 * attempt}s...", 0.05)
                    time.sleep(2 * attempt)
                    continue
                return []

            # Step 1: Select Round (PostBack)
            if progress_callback:
                progress_callback(f"[Step 1/5]: Selecting Special Round {round_no}...", 0.20)
            d1 = dict(get_asp_fields_fast(r0.text))
            d1['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlroundno'
            d1['__EVENTARGUMENT'] = ''
            d1['__LASTFOCUS'] = ''
            d1['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            r1 = s.post(CSAB_URL, data=d1, headers=HEADERS, timeout=60)

            # Step 2: Select InstType = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 2/5]: Selecting All Institute Types...", 0.38)
            d2 = dict(get_asp_fields_fast(r1.text))
            d2['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlInstype'
            d2['__EVENTARGUMENT'] = ''
            d2['__LASTFOCUS'] = ''
            d2['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d2['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            r2 = s.post(CSAB_URL, data=d2, headers=HEADERS, timeout=60)

            # Step 3: Select Institute = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 3/5]: Selecting All Institutes...", 0.55)
            d3 = dict(get_asp_fields_fast(r2.text))
            d3['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlInstitute'
            d3['__EVENTARGUMENT'] = ''
            d3['__LASTFOCUS'] = ''
            d3['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d3['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d3['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            r3 = s.post(CSAB_URL, data=d3, headers=HEADERS, timeout=60)

            # Step 4: Select Branch = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 4/5]: Selecting All Programs / Branches...", 0.70)
            d4 = dict(get_asp_fields_fast(r3.text))
            d4['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlBranch'
            d4['__EVENTARGUMENT'] = ''
            d4['__LASTFOCUS'] = ''
            d4['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d4['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d4['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            d4['ctl00$ContentPlaceHolder1$ddlBranch'] = 'ALL'
            r4 = s.post(CSAB_URL, data=d4, headers=HEADERS, timeout=60)

            # Step 5: Final Submit (CSAB has no ddlSeatType dropdown)
            if progress_callback:
                progress_callback(f"[Step 5/5]: Downloading complete Special Round {round_no} allotment table...", 0.82)
            d5 = dict(get_asp_fields_fast(r4.text))
            d5['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d5['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$ddlBranch'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$btnSubmit'] = 'Submit'

            r5 = s.post(CSAB_URL, data=d5, headers=HEADERS, timeout=180)

            if progress_callback:
                progress_callback(f"Fast parsing allotment records with lxml...", 0.92)

            records = parse_cutoff_table_lxml(r5.text, year=year, round_no=round_no)

            if not records:
                print(f"[!] No cutoff table found for Special Round {round_no} on attempt {attempt}", flush=True)
                if attempt < max_retries:
                    if progress_callback:
                        progress_callback(f"No records received. Retrying attempt {attempt+1}/{max_retries}...", 0.05)
                    time.sleep(3 * attempt)
                    continue
                return []

            print(f"[+] Successfully extracted {len(records)} records for CSAB Special Round {round_no}.", flush=True)
            if progress_callback:
                progress_callback(f"Extracted {len(records):,} records. Saving to database...", 0.96)
            return records
        except Exception as e:
            print(f"[!] Error in CSAB scrape for Round {round_no} (attempt {attempt}/{max_retries}): {e}", flush=True)
            if attempt < max_retries:
                if progress_callback:
                    progress_callback(f"Request failed ({type(e).__name__}). Retrying attempt {attempt+1}/{max_retries}...", 0.05)
                time.sleep(3 * attempt)
                continue
            return []
    return []


def save_records_to_db(records: List[Dict[str, Any]], db_path: Optional[Path] = None) -> int:
    if not records:
        print("[!] No records to save.", flush=True)
        return 0

    if db_path is None:
        db_path = get_csab_db_path()

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    init_csab_db_schema(conn)
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
        quota = normalize_quota(r.get("quota", "AI"))
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

            st = OFFICIAL_HOME_STATE_MAPPING.get(inst_name)
            cursor.execute("""
                INSERT INTO institutes (institute_code, institute_name, institute_type, state)
                VALUES (?, ?, ?, ?)
            """, (code, inst_name, itype, st))
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


def normalize_csab_db(db_path: Optional[Path] = None):
    """Clean up and merge duplicate entities to ensure 100% integrity."""
    if db_path is None:
        db_path = get_csab_db_path()
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    cur = conn.cursor()

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


def get_csab_scraper_status() -> Dict[str, Any]:
    with _csab_lock:
        return dict(csab_scraper_state)


def _run_full_csab_scrape_task(db_path: Optional[Path] = None):
    with _csab_lock:
        csab_scraper_state["is_running"] = True
        csab_scraper_state["status"] = "RUNNING"
        csab_scraper_state["progress_percent"] = 5
        csab_scraper_state["current_round"] = 1
        csab_scraper_state["message"] = "Initializing CSAB Special Round official scraper..."
        csab_scraper_state["records_round1"] = 0
        csab_scraper_state["records_round2"] = 0
        csab_scraper_state["total_records"] = 0
        csab_scraper_state["completed_rounds"] = 0
        csab_scraper_state["total_rounds"] = 2
        csab_scraper_state["started_at"] = datetime.now(timezone.utc).isoformat()
        csab_scraper_state["completed_at"] = None
        csab_scraper_state["error"] = None

    session = requests.Session()
    total_r1 = 0
    total_r2 = 0

    def make_progress_cb(round_no: int):
        base_pct = 10 if round_no == 1 else 50
        span = 38

        def cb(step_msg: str, fraction: float):
            sub_pct = base_pct + int(fraction * span)
            with _csab_lock:
                csab_scraper_state["current_round"] = round_no
                csab_scraper_state["message"] = f"Special Round {round_no}: {step_msg}"
                csab_scraper_state["progress_percent"] = max(csab_scraper_state["progress_percent"], sub_pct)

        return cb

    try:
        # Special Round 1
        cb1 = make_progress_cb(1)
        cb1("Connecting to portal...", 0.0)
        recs1 = scrape_csab_round(session, round_no=1, year=DEFAULT_ACADEMIC_YEAR, progress_callback=cb1)
        if recs1:
            total_r1 = save_records_to_db(recs1, db_path=db_path)

        with _csab_lock:
            csab_scraper_state["completed_rounds"] = 1
            csab_scraper_state["records_round1"] = total_r1
            csab_scraper_state["total_records"] = total_r1
            csab_scraper_state["progress_percent"] = 50
            csab_scraper_state["message"] = f"Special Round 1 complete ({total_r1:,} records). Starting Special Round 2..."

        # Special Round 2
        cb2 = make_progress_cb(2)
        cb2("Connecting to portal...", 0.0)
        recs2 = scrape_csab_round(session, round_no=2, year=DEFAULT_ACADEMIC_YEAR, progress_callback=cb2)
        if recs2:
            total_r2 = save_records_to_db(recs2, db_path=db_path)

        with _csab_lock:
            csab_scraper_state["completed_rounds"] = 2
            csab_scraper_state["records_round2"] = total_r2
            csab_scraper_state["total_records"] = total_r1 + total_r2
            csab_scraper_state["progress_percent"] = 92
            csab_scraper_state["message"] = "Normalising records and verifying integrity..."

        normalize_csab_db(db_path=db_path)

        with _csab_lock:
            csab_scraper_state["progress_percent"] = 100
            csab_scraper_state["status"] = "COMPLETED"
            csab_scraper_state["is_running"] = False
            csab_scraper_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            csab_scraper_state["message"] = (
                f"Successfully scraped & ingested both CSAB Special Rounds! "
                f"Round 1: {total_r1:,} cutoffs | Round 2: {total_r2:,} cutoffs | Total: {total_r1 + total_r2:,} cutoffs."
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        with _csab_lock:
            csab_scraper_state["status"] = "FAILED"
            csab_scraper_state["is_running"] = False
            csab_scraper_state["error"] = str(e)
            csab_scraper_state["message"] = f"Scraping failed: {str(e)}"
            csab_scraper_state["completed_at"] = datetime.now(timezone.utc).isoformat()


def start_csab_scraper_background(db_path: Optional[Path] = None) -> bool:
    with _csab_lock:
        if csab_scraper_state["is_running"]:
            return False
        csab_scraper_state["is_running"] = True
        csab_scraper_state["status"] = "RUNNING"
        csab_scraper_state["progress_percent"] = 2
        csab_scraper_state["message"] = "Starting CSAB web scraping process..."

    t = threading.Thread(target=_run_full_csab_scrape_task, args=(db_path,), daemon=True)
    t.start()
    return True
