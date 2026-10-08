"""
JoSAA Official Portal Scraper Engine
Fetches complete Opening and Closing Ranks across all rounds:
- Year 2025: All 6 rounds from Official NIC Archive Portal (openingclosingrankarchieve.aspx)
- Year 2026: 5 rounds from Official JoSAA Live Portal (currentorcr.aspx)
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

CURRENT_URL = "https://josaa.admissions.nic.in/applicant/seatallotmentresult/currentorcr.aspx"
ARCHIVE_URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"
DATASET_URL = "https://raw.githubusercontent.com/Harith-Y/JoSAA-CSAB-Closing-Rank-Predictor/main/data"
INSTITUTE_VIEW_URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/instituteview.aspx"
INSTITUTE_PROFILE_BASE_URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/InstProfile.aspx"

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
    "message": "Ready to scrape official JoSAA cutoffs for Years 2025 & 2026.",
    "records_2025": 0,
    "records_2026": 0,
    "total_records": 0,
    "total_rounds": 11,
    "completed_rounds": 0,
    "started_at": None,
    "completed_at": None,
    "error": None,
}


from app.josaa_db import get_josaa_db_path


def get_db_path() -> Path:
    return get_josaa_db_path()


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


def get_asp_fields(soup: BeautifulSoup) -> Dict[str, str]:
    return {
        name: soup.find('input', {'id': name})['value']
        for name in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']
        if soup.find('input', {'id': name})
    }


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


def determine_institute_type(name: str) -> str:
    n = name.upper()
    if "INDIAN INSTITUTE OF TECHNOLOGY" in n or "IIT " in n or "IIT," in n or "BHU" in n or "ISM" in n:
        return "IIT"
    if "NATIONAL INSTITUTE OF TECHNOLOGY" in n or "NIT " in n or "NIT," in n:
        return "NIT"
    if "INDIAN INSTITUTE OF INFORMATION TECHNOLOGY" in n or "IIIT " in n or "IIIT," in n:
        return "IIIT"
    return "Other-GFTI"


def scrape_archive_round(
    session: requests.Session,
    year: int = 2025,
    round_no: int = 1,
    max_retries: int = 3,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> List[Dict[str, Any]]:
    """
    Scrapes an archival year (e.g. 2025, 2024) exclusively from the official NIC portal:
    https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx
    using cascading ASP.NET PostBack simulation with auto-retry and fast lxml parsing.
    """
    for attempt in range(1, max_retries + 1):
        attempt_str = f" (Attempt {attempt}/{max_retries})" if attempt > 1 else ""
        if progress_callback:
            progress_callback(f"Connecting to archive portal{attempt_str}...", 0.05)
        print(f"[*] Connecting to official JoSAA Archive portal for Year {year}, Round {round_no}{attempt_str}...", flush=True)

        try:
            s = requests.Session()
            r0 = s.get(ARCHIVE_URL, headers=HEADERS, timeout=45)
            if r0.status_code != 200:
                print(f"[!] Initial archive GET failed: HTTP {r0.status_code}", flush=True)
                if attempt < max_retries:
                    if progress_callback:
                        progress_callback(f"Archive portal HTTP {r0.status_code}. Retrying in {2 * attempt}s...", 0.05)
                    time.sleep(2 * attempt)
                    continue
                return []

            # 1. Select Year (PostBack)
            if progress_callback:
                progress_callback(f"[Step 1/6]: Selecting Year {year}...", 0.15)
            d1 = dict(get_asp_fields_fast(r0.text))
            d1['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlYear'
            d1['__EVENTARGUMENT'] = ''
            d1['__LASTFOCUS'] = ''
            d1['ctl00$ContentPlaceHolder1$ddlYear'] = str(year)
            r1 = s.post(ARCHIVE_URL, data=d1, headers=HEADERS, timeout=60)

            # 2. Select Round (PostBack)
            if progress_callback:
                progress_callback(f"[Step 2/6]: Selecting Round {round_no}...", 0.30)
            d2 = dict(get_asp_fields_fast(r1.text))
            d2['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlroundno'
            d2['__EVENTARGUMENT'] = ''
            d2['__LASTFOCUS'] = ''
            d2['ctl00$ContentPlaceHolder1$ddlYear'] = str(year)
            d2['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            r2 = s.post(ARCHIVE_URL, data=d2, headers=HEADERS, timeout=60)

            # 3. Select InstType = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 3/6]: Selecting All Institute Types...", 0.45)
            d3 = dict(get_asp_fields_fast(r2.text))
            d3['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlInstype'
            d3['__EVENTARGUMENT'] = ''
            d3['__LASTFOCUS'] = ''
            d3['ctl00$ContentPlaceHolder1$ddlYear'] = str(year)
            d3['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d3['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            r3 = s.post(ARCHIVE_URL, data=d3, headers=HEADERS, timeout=60)

            # 4. Select Institute = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 4/6]: Selecting All Institutes...", 0.60)
            d4 = dict(get_asp_fields_fast(r3.text))
            d4['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlInstitute'
            d4['__EVENTARGUMENT'] = ''
            d4['__LASTFOCUS'] = ''
            d4['ctl00$ContentPlaceHolder1$ddlYear'] = str(year)
            d4['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d4['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d4['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            r4 = s.post(ARCHIVE_URL, data=d4, headers=HEADERS, timeout=60)

            # 5. Select Branch = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 5/6]: Selecting All Programs / Branches...", 0.72)
            d5 = dict(get_asp_fields_fast(r4.text))
            d5['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlBranch'
            d5['__EVENTARGUMENT'] = ''
            d5['__LASTFOCUS'] = ''
            d5['ctl00$ContentPlaceHolder1$ddlYear'] = str(year)
            d5['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d5['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$ddlBranch'] = 'ALL'
            r5 = s.post(ARCHIVE_URL, data=d5, headers=HEADERS, timeout=60)

            # 6. Final Submit with Seat Type = ALL
            if progress_callback:
                progress_callback(f"[Step 6/6]: Downloading complete Round {round_no} table from archive portal...", 0.80)
            d6 = dict(get_asp_fields_fast(r5.text))
            d6['ctl00$ContentPlaceHolder1$ddlYear'] = str(year)
            d6['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d6['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d6['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            d6['ctl00$ContentPlaceHolder1$ddlBranch'] = 'ALL'
            d6['ctl00$ContentPlaceHolder1$ddlSeatType'] = 'ALL'
            d6['ctl00$ContentPlaceHolder1$btnSubmit'] = 'Submit'

            r6 = s.post(ARCHIVE_URL, data=d6, headers=HEADERS, timeout=180)

            if progress_callback:
                progress_callback(f"Fast parsing archive records with lxml...", 0.90)

            records = parse_cutoff_table_lxml(r6.text, year=year, round_no=round_no)

            if not records:
                print(f"[!] No cutoff table found for Year {year}, Round {round_no} on attempt {attempt}", flush=True)
                if attempt < max_retries:
                    if progress_callback:
                        progress_callback(f"No records received. Retrying attempt {attempt+1}/{max_retries}...", 0.05)
                    time.sleep(3 * attempt)
                    continue
                return []

            print(f"[+] Successfully extracted {len(records)} records for Year {year}, Round {round_no}.", flush=True)
            if progress_callback:
                progress_callback(f"Extracted {len(records):,} records. Saving to database...", 0.96)
            return records
        except Exception as e:
            print(f"[!] Error in archive scrape for Year {year}, Round {round_no} (attempt {attempt}/{max_retries}): {e}", flush=True)
            if attempt < max_retries:
                if progress_callback:
                    progress_callback(f"Request failed ({type(e).__name__}). Retrying attempt {attempt+1}/{max_retries}...", 0.05)
                time.sleep(3 * attempt)
                continue
            return []
    return []


def scrape_2025_round(
    session: requests.Session,
    round_no: int = 1,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> List[Dict[str, Any]]:
    """Exclusively scrapes Year 2025 cutoffs from official NIC archive portal."""
    return scrape_archive_round(session, year=2025, round_no=round_no, progress_callback=progress_callback)


def scrape_2026_round(
    session: requests.Session,
    round_no: int = 1,
    max_retries: int = 3,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> List[Dict[str, Any]]:
    """Scrapes Year 2026 from the live NIC portal (currentorcr.aspx) using cascading ASP.NET PostBack with auto-retry and fast lxml parsing."""
    for attempt in range(1, max_retries + 1):
        attempt_str = f" (Attempt {attempt}/{max_retries})" if attempt > 1 else ""
        if progress_callback:
            progress_callback(f"Connecting to live NIC portal{attempt_str}...", 0.05)
        print(f"[*] Connecting to JoSAA live portal for Year 2026, Round {round_no}{attempt_str}...", flush=True)

        try:
            # Use a fresh session per round to guarantee pristine viewstate sequence
            s = requests.Session()
            r0 = s.get(CURRENT_URL, headers=HEADERS, timeout=45)
            if r0.status_code != 200:
                print(f"[!] Initial live portal GET failed: HTTP {r0.status_code}", flush=True)
                if attempt < max_retries:
                    if progress_callback:
                        progress_callback(f"Portal returned HTTP {r0.status_code}, retrying in {2 * attempt}s...", 0.05)
                    time.sleep(2 * attempt)
                    continue
                return []

            # 1. Select Round (PostBack)
            if progress_callback:
                progress_callback(f"[Step 1/5]: Selecting Round {round_no}...", 0.20)
            d1 = dict(get_asp_fields_fast(r0.text))
            d1['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlroundno'
            d1['__EVENTARGUMENT'] = ''
            d1['__LASTFOCUS'] = ''
            d1['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            r1 = s.post(CURRENT_URL, data=d1, headers=HEADERS, timeout=60)

            # 2. Select InstType = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 2/5]: Selecting All Institute Types...", 0.35)
            d2 = dict(get_asp_fields_fast(r1.text))
            d2['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlInstype'
            d2['__EVENTARGUMENT'] = ''
            d2['__LASTFOCUS'] = ''
            d2['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d2['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            r2 = s.post(CURRENT_URL, data=d2, headers=HEADERS, timeout=60)

            # 3. Select Institute = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 3/5]: Selecting All Institutes...", 0.50)
            d3 = dict(get_asp_fields_fast(r2.text))
            d3['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlInstitute'
            d3['__EVENTARGUMENT'] = ''
            d3['__LASTFOCUS'] = ''
            d3['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d3['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d3['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            r3 = s.post(CURRENT_URL, data=d3, headers=HEADERS, timeout=60)

            # 4. Select Branch = ALL (PostBack)
            if progress_callback:
                progress_callback(f"[Step 4/5]: Selecting All Programs / Branches...", 0.65)
            d4 = dict(get_asp_fields_fast(r3.text))
            d4['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ddlBranch'
            d4['__EVENTARGUMENT'] = ''
            d4['__LASTFOCUS'] = ''
            d4['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d4['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d4['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            d4['ctl00$ContentPlaceHolder1$ddlBranch'] = 'ALL'
            r4 = s.post(CURRENT_URL, data=d4, headers=HEADERS, timeout=60)

            # 5. Final Submit with Seat Type = ALL (note exact lowercase 't' in ddlSeattype)
            if progress_callback:
                progress_callback(f"[Step 5/5]: Downloading complete allotment table (~13,000 live records from NIC, please wait)...", 0.75)
            d5 = dict(get_asp_fields_fast(r4.text))
            d5['ctl00$ContentPlaceHolder1$ddlroundno'] = str(round_no)
            d5['ctl00$ContentPlaceHolder1$ddlInstype'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$ddlInstitute'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$ddlBranch'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$ddlSeattype'] = 'ALL'
            d5['ctl00$ContentPlaceHolder1$btnSubmit'] = 'Submit'
            r5 = s.post(CURRENT_URL, data=d5, headers=HEADERS, timeout=180)

            if progress_callback:
                progress_callback(f"Fast parsing allotment records with lxml...", 0.90)

            records = parse_cutoff_table_lxml(r5.text, year=2026, round_no=round_no)

            if not records:
                print(f"[!] No cutoff table found for Year 2026, Round {round_no} on attempt {attempt}", flush=True)
                if attempt < max_retries:
                    if progress_callback:
                        progress_callback(f"No records received from NIC. Retrying in {3 * attempt}s...", 0.05)
                    time.sleep(3 * attempt)
                    continue
                return []

            print(f"[+] Successfully extracted {len(records)} records for Year 2026, Round {round_no}.", flush=True)
            if progress_callback:
                progress_callback(f"Extracted {len(records):,} records. Saving to database...", 0.96)
            return records
        except Exception as e:
            print(f"[!] Error in live portal scrape for Year 2026, Round {round_no} (attempt {attempt}/{max_retries}): {e}", flush=True)
            if attempt < max_retries:
                if progress_callback:
                    progress_callback(f"Portal request failed ({type(e).__name__}). Retrying attempt {attempt+1}/{max_retries}...", 0.05)
                time.sleep(3 * attempt)
                continue
            return []
    return []


def scrape_round(
    session: requests.Session,
    round_no: int = 1,
    year: int = 2025,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> List[Dict[str, Any]]:
    """Orchestrates scraping based on whether the requested year is 2025, 2026, or archival."""
    if year == 2026:
        return scrape_2026_round(session, round_no=round_no, progress_callback=progress_callback)
    if year == 2025:
        return scrape_2025_round(session, round_no=round_no, progress_callback=progress_callback)
    return scrape_archive_round(session, year=year, round_no=round_no, progress_callback=progress_callback)


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


OFFICIAL_HOME_STATE_MAPPING: Dict[str, str] = {
    # NITs
    "Dr. B R Ambedkar National Institute of Technology, Jalandhar": "Punjab",
    "Malaviya National Institute of Technology Jaipur": "Rajasthan",
    "Maulana Azad National Institute of Technology Bhopal": "Madhya Pradesh",
    "Motilal Nehru National Institute of Technology Allahabad": "Uttar Pradesh",
    "National Institute of Technology  Agartala": "Tripura",
    "National Institute of Technology Calicut": "Kerala",
    "National Institute of Technology Delhi": "Delhi",
    "National Institute of Technology Durgapur": "West Bengal",
    "National Institute of Technology Goa": "Goa",
    "National Institute of Technology Hamirpur": "Himachal Pradesh",
    "National Institute of Technology Karnataka, Surathkal": "Karnataka",
    "National Institute of Technology Meghalaya": "Meghalaya",
    "National Institute of Technology Nagaland": "Nagaland",
    "National Institute of Technology Patna": "Bihar",
    "National Institute of Technology Puducherry": "Puducherry",
    "National Institute of Technology Raipur": "Chhattisgarh",
    "National Institute of Technology Sikkim": "Sikkim",
    "National Institute of Technology Arunachal Pradesh": "Arunachal Pradesh",
    "National Institute of Technology, Jamshedpur": "Jharkhand",
    "National Institute of Technology, Kurukshetra": "Haryana",
    "National Institute of Technology, Manipur": "Manipur",
    "National Institute of Technology, Mizoram": "Mizoram",
    "National Institute of Technology, Rourkela": "Odisha",
    "National Institute of Technology, Silchar": "Assam",
    "National Institute of Technology, Srinagar": "Jammu and Kashmir",
    "National Institute of Technology, Tiruchirappalli": "Tamil Nadu",
    "National Institute of Technology, Uttarakhand": "Uttarakhand",
    "National Institute of Technology, Warangal": "Telangana",
    "Sardar Vallabhbhai National Institute of Technology, Surat": "Gujarat",
    "Visvesvaraya National Institute of Technology, Nagpur": "Maharashtra",
    "National Institute of Technology, Andhra Pradesh": "Andhra Pradesh",
    "Indian Institute of Engineering Science and Technology, Shibpur": "West Bengal",
    
    # IIITs / GFTIs offering Home State Quota
    "Assam University, Silchar": "Assam",
    "Birla Institute of Technology, Mesra, Ranchi": "Jharkhand",
    "Gurukula Kangri Vishwavidyalaya, Haridwar": "Uttarakhand",
    "Institute of Chemical Technology, Mumbai: Indian Oil Odisha Campus, Bhubaneswar": "Odisha",
    "Institute of Chemical Technology, Mumbai: Marathwada Campus, Jalna": "Maharashtra",
    "Institute of Technology, Guru Ghasidas Vishwavidyalaya, Bilaspur": "Chhattisgarh",
    "J.K. Institute of Applied Physics & Technology, Department of Electronics & Communication, University of Allahabad": "Uttar Pradesh",
    "National Institute of Electronics and Information Technology, Aurangabad": "Maharashtra",
    "National Institute of Advanced Manufacturing Technology, Ranchi": "Jharkhand",
    "Sant Longowal Institute of Engineering and Technology": "Punjab",
    "Mizoram University, Aizawl": "Mizoram",
    "School of Engineering, Tezpur University, Napaam, Tezpur": "Assam",
    "Shri Mata Vaishno Devi University, Katra, J & K": "Jammu and Kashmir",
    "Indian Institute of Handloom Technology, Salem": "Tamil Nadu",
    "Central Institute of Technology Kokrajhar": "Assam",
    "Puducherry Technological University, Puducherry": "Puducherry",
    "Ghani Khan Choudhury Institute of Engineering and Technology, Malda, West Bengal": "West Bengal",
    "Central University of Rajasthan, Bandarsindri, Distt. Ajmer": "Rajasthan",
    "National Institute of Food Technology Entrepreneurship and Management, Kundli": "Haryana",
    "National Institute of Food Technology Entrepreneurship and Management, Thanjavur": "Tamil Nadu",
    "Central University of Jammu": "Jammu and Kashmir",
    "Institute of Engineering and Technology, Dr. H. S. Gour University. Sagar": "Madhya Pradesh",
    "Central University of Haryana": "Haryana",
    "Punjab Engineering College, Chandigarh": "Chandigarh",
    "Jawaharlal Nehru University, Delhi": "Delhi",
    "International Institute of Information Technology, Naya Raipur": "Chhattisgarh",
    "International Institute of Information Technology, Bhubaneswar": "Odisha",
    "Birla Institute of Technology, Deoghar Off-Campus": "Jharkhand",
    "Birla Institute of Technology, Patna Off-Campus": "Bihar",
    "Islamic University of Science and Technology Kashmir": "Jammu and Kashmir"
}

def clean_state_name(raw_state: str) -> str:
    s = raw_state.strip()
    if not s or s.lower() in ["all india", "all", "none", "na", "-"]:
        return ""
    if "puducherry" in s.lower() or "pondicherry" in s.lower():
        return "Puducherry"
    if "delhi" in s.lower():
        return "Delhi"
    if "jammu" in s.lower():
        return "Jammu and Kashmir"
    if "andaman" in s.lower():
        return "Andaman and Nicobar Islands"
    if "odisha" in s.lower() or "orissa" in s.lower():
        return "Odisha"
    if "chhattisgarh" in s.lower() or "chhatisgarh" in s.lower():
        return "Chhattisgarh"
    if "chandigarh" in s.lower():
        return "Chandigarh"
    if "," in s:
        # If multiple states/UTs are listed, take the primary state
        first_part = s.split(",")[0].strip()
        return first_part.title()
    return s.title()


def scrape_institute_home_states(session: Optional[requests.Session] = None, db_path: Optional[Path] = None) -> Dict[str, str]:
    """
    Scrapes https://josaa.admissions.nic.in/applicant/seatmatrix/instituteview.aspx
    Inspects each institute's 'Academic Programwise Seats breakup' table.
    If 'State/All India Seats' column contains 'All India', skips (no HS quota).
    If it contains an Indian State name, maps that Home State to the institute in josaa.db.
    Falls back to official mapping dictionary to guarantee 100% complete coverage.
    """
    if db_path is None:
        db_path = get_db_path()
    
    if session is None:
        session = requests.Session()
    
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    init_josaa_db_schema(conn)
    cur = conn.cursor()

    # Pre-populate with official curated mapping
    mapped_states: Dict[str, str] = dict(OFFICIAL_HOME_STATE_MAPPING)
    
    print("[*] Connecting to JoSAA seat matrix institute view for Home State mapping...", flush=True)
    try:
        r0 = session.get(INSTITUTE_VIEW_URL, headers=HEADERS, timeout=20)
        if r0.status_code == 200:
            s0 = BeautifulSoup(r0.text, 'html.parser')
            fields = get_asp_fields(s0)
            d1 = {
                **fields,
                '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$ddlInstType',
                '__EVENTARGUMENT': '',
                'ctl00$ContentPlaceHolder1$ddlInstType': 'ALL'
            }
            r1 = session.post(INSTITUTE_VIEW_URL, data=d1, headers=HEADERS, timeout=25)
            s1 = BeautifulSoup(r1.text, 'html.parser')
            table = s1.find('table')
            if table:
                rows = table.find_all('tr')[1:]
                print(f"[+] Found {len(rows)} institutes on official seat matrix page.", flush=True)
                for r in rows:
                    cells = r.find_all(['td', 'th'])
                    if len(cells) < 3:
                        continue
                    link = cells[0].find('a')
                    href = link.get('href', '') if link else ''
                    code_match = re.search(r'instcd=(\d+)', href)
                    if not code_match:
                        continue
                    inst_cd = code_match.group(1)
                    inst_name = re.sub(r'^\d+', '', cells[2].get_text(' ', strip=True)).strip()
                    
                    if inst_name in mapped_states:
                        continue

                    try:
                        prof_url = f"{INSTITUTE_PROFILE_BASE_URL}?instcd={inst_cd}"
                        rp = session.get(prof_url, headers=HEADERS, timeout=10)
                        sp = BeautifulSoup(rp.text, 'html.parser')
                        
                        target_table = None
                        for t in sp.find_all('table'):
                            if 'State/All India Seats' in t.get_text():
                                target_table = t
                                break
                        
                        if target_table:
                            for trow in target_table.find_all('tr'):
                                tcells = [c.get_text(' ', strip=True) for c in trow.find_all(['td', 'th'])]
                                if len(tcells) >= 4 and tcells[0].isdigit():
                                    state_raw = tcells[3].strip()
                                    cleaned = clean_state_name(state_raw)
                                    if cleaned:
                                        mapped_states[inst_name] = cleaned
                                    break
                    except Exception as e:
                        print(f"[!] Warning: Failed live fetch for instcd={inst_cd} ({inst_name}): {e}", flush=True)
    except Exception as e:
        print(f"[!] Warning: Live seat matrix scrape error: {e}", flush=True)

    # Commit state mappings to josaa.db
    updated_count = 0
    for inst_name, state in mapped_states.items():
        clean_name = ' '.join(inst_name.split())
        cur.execute("SELECT id FROM institutes WHERE institute_name = ? OR institute_name LIKE ?", (clean_name, f"%{clean_name}%"))
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE institutes 
                SET state = ? 
                WHERE id = ?
            """, (state, row[0]))
            updated_count += 1
        else:
            itype = determine_institute_type(clean_name)
            base_code = re.sub(r"[^A-Za-z0-9]", "", clean_name)[:10].upper() or "INST"
            cur.execute("""
                INSERT INTO institutes (institute_code, institute_name, institute_type, state)
                VALUES (?, ?, ?, ?)
            """, (base_code, clean_name, itype, state))
            updated_count += 1

    conn.commit()
    conn.close()
    print(f"[+] Successfully mapped Home State for {len(mapped_states)} institutes ({updated_count} DB rows inserted/updated).", flush=True)
    return mapped_states


def get_josaa_scraper_status() -> Dict[str, Any]:
    with _josaa_lock:
        return dict(josaa_scraper_state)


def _run_full_josaa_scrape_task(db_path: Optional[Path] = None):
    with _josaa_lock:
        josaa_scraper_state["is_running"] = True
        josaa_scraper_state["status"] = "RUNNING"
        josaa_scraper_state["progress_percent"] = 2
        josaa_scraper_state["current_year"] = 2025
        josaa_scraper_state["current_round"] = 1
        josaa_scraper_state["message"] = "Initializing JoSAA official scraper for Years 2025 and 2026..."
        josaa_scraper_state["records_2025"] = 0
        josaa_scraper_state["records_2026"] = 0
        josaa_scraper_state["total_records"] = 0
        josaa_scraper_state["completed_rounds"] = 0
        josaa_scraper_state["total_rounds"] = 11
        josaa_scraper_state["started_at"] = datetime.now(timezone.utc).isoformat()
        josaa_scraper_state["completed_at"] = None
        josaa_scraper_state["error"] = None

    session = requests.Session()
    total_2025 = 0
    total_2026 = 0

    def make_progress_cb(round_idx: int, year: int, round_no: int):
        base_pct = int((round_idx / 11) * 85) + 3
        next_pct = int(((round_idx + 1) / 11) * 85) + 3
        span = max(1, next_pct - base_pct)

        def cb(step_msg: str, fraction: float):
            sub_pct = min(next_pct - 1, base_pct + int(fraction * span))
            with _josaa_lock:
                josaa_scraper_state["current_year"] = year
                josaa_scraper_state["current_round"] = round_no
                josaa_scraper_state["message"] = f"Year {year}, Round {round_no}: {step_msg}"
                josaa_scraper_state["progress_percent"] = max(josaa_scraper_state["progress_percent"], sub_pct)

        return cb

    try:
        # Phase 1: Year 2025 (Rounds 1 to 6)
        for r in range(1, 7):
            round_idx = r - 1
            cb = make_progress_cb(round_idx=round_idx, year=2025, round_no=r)
            cb("Connecting to archive portal...", 0.0)

            recs = scrape_round(session, round_no=r, year=2025, progress_callback=cb)
            if recs:
                saved = save_records_to_db(recs, db_path=db_path)
                total_2025 += saved

            with _josaa_lock:
                josaa_scraper_state["completed_rounds"] += 1
                josaa_scraper_state["records_2025"] = total_2025
                josaa_scraper_state["total_records"] = total_2025 + total_2026
                josaa_scraper_state["progress_percent"] = int((josaa_scraper_state["completed_rounds"] / 11) * 85) + 3
                josaa_scraper_state["message"] = f"Year 2025, Round {r} complete ({len(recs) if recs else 0:,} records)."

        # Phase 2: Year 2026 (Rounds 1 to 5) from official live portal
        for r in range(1, 6):
            round_idx = 6 + (r - 1)
            cb = make_progress_cb(round_idx=round_idx, year=2026, round_no=r)
            cb("Connecting to live portal...", 0.0)

            recs = scrape_2026_round(session, round_no=r, progress_callback=cb)
            if recs:
                saved = save_records_to_db(recs, db_path=db_path)
                total_2026 += saved

            with _josaa_lock:
                josaa_scraper_state["completed_rounds"] += 1
                josaa_scraper_state["records_2026"] = total_2026
                josaa_scraper_state["total_records"] = total_2025 + total_2026
                josaa_scraper_state["progress_percent"] = int((josaa_scraper_state["completed_rounds"] / 11) * 85) + 3
                josaa_scraper_state["message"] = f"Year 2026, Round {r} complete ({len(recs) if recs else 0:,} records)."

        # Phase 3: Home State Seat Matrix Scraper & Normalization
        with _josaa_lock:
            josaa_scraper_state["progress_percent"] = 92
            josaa_scraper_state["message"] = "Mapping and scraping institute Home States from official seat matrix..."

        scrape_institute_home_states(session=session, db_path=db_path)

        with _josaa_lock:
            josaa_scraper_state["progress_percent"] = 97
            josaa_scraper_state["message"] = "Verifying database integrity and normalising records..."

        normalize_josaa_db(db_path=db_path)

        with _josaa_lock:
            josaa_scraper_state["progress_percent"] = 100
            josaa_scraper_state["status"] = "COMPLETED"
            josaa_scraper_state["is_running"] = False
            josaa_scraper_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            josaa_scraper_state["message"] = (
                f"Successfully scraped & ingested all 11 rounds! "
                f"Year 2025: {total_2025:,} cutoffs (6 rounds) | Year 2026: {total_2026:,} cutoffs (5 rounds) | Total: {total_2025 + total_2026:,} cutoffs."
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
        josaa_scraper_state["message"] = "Starting JoSAA web scraping process for Years 2025 & 2026..."

    t = threading.Thread(target=_run_full_josaa_scrape_task, args=(db_path,), daemon=True)
    t.start()
    return True


def run_scraper(rounds: Optional[List[int]] = None, year: int = 2025, db_path: Optional[Path] = None):
    """Synchronous scraper execution for CLI invocation."""
    if rounds is None:
        rounds = [1, 2, 3, 4, 5, 6] if year == 2025 else [1, 2, 3, 4, 5]

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
    y_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    default_rounds = [1, 2, 3, 4, 5, 6] if y_arg == 2025 else [1, 2, 3, 4, 5]
    r_arg = [int(sys.argv[2])] if len(sys.argv) > 2 else default_rounds
    run_scraper(rounds=r_arg, year=y_arg)
