"""
JoSAA Official Portal Scraper
Fetches complete Opening and Closing Ranks (Rounds 1 to 5)
Directly from official JoSAA portal:
https://josaa.admissions.nic.in/applicant/seatallotmentresult/currentorcr.aspx
"""

import sys
import os
import re
import sqlite3
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Any

BASE_URL = "https://josaa.admissions.nic.in/applicant/seatallotmentresult/currentorcr.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

def get_db_path() -> Path:
    root_path = Path(__file__).resolve().parent.parent.parent / "josaa.db"
    return root_path

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
    if "INDIAN INSTITUTE OF TECHNOLOGY" in n or "IIT " in n or "IIT," in n:
        return "IIT"
    if "NATIONAL INSTITUTE OF TECHNOLOGY" in n or "NIT " in n or "NIT," in n:
        return "NIT"
    if "INDIAN INSTITUTE OF INFORMATION TECHNOLOGY" in n or "IIIT " in n or "IIIT," in n:
        return "IIIT"
    return "Other-GFTI"

def scrape_round(session: requests.Session, round_no: int = 1, year: int = 2024) -> List[Dict[str, Any]]:
    print(f"[*] Connecting to JoSAA portal for Round {round_no}...")
    try:
        r = session.get(BASE_URL, headers=HEADERS, timeout=25)
    except Exception as e:
        print(f"[!] Network error connecting to JoSAA portal: {e}")
        return []

    if r.status_code != 200:
        print(f"[!] Failed to load base page: HTTP {r.status_code}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    
    viewstate = soup.find("input", {"id": "__VIEWSTATE"})
    eventvalidation = soup.find("input", {"id": "__EVENTVALIDATION"})
    viewstategenerator = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})

    if not viewstate:
        print("[!] Could not locate ASP.NET __VIEWSTATE on page.")
        return []

    form_data = {
        "__VIEWSTATE": viewstate.get("value", ""),
        "__EVENTVALIDATION": eventvalidation.get("value", "") if eventvalidation else "",
        "__VIEWSTATEGENERATOR": viewstategenerator.get("value", "") if viewstategenerator else "",
        "ctl00$ContentPlaceHolder1$ddlroundno": str(round_no),
        "ctl00$ContentPlaceHolder1$ddlInstype": "ALL",
        "ctl00$ContentPlaceHolder1$ddlInstitute": "ALL",
        "ctl00$ContentPlaceHolder1$ddlBranch": "ALL",
        "ctl00$ContentPlaceHolder1$ddlSeatType": "ALL",
        "ctl00$ContentPlaceHolder1$btnSubmit": "Submit"
    }

    print(f"[*] Querying Round {round_no} (All Institutes & Branches)...")
    try:
        post_res = session.post(BASE_URL, data=form_data, headers=HEADERS, timeout=60)
    except Exception as e:
        print(f"[!] POST request timed out or failed: {e}")
        return []

    if post_res.status_code != 200:
        print(f"[!] Server returned status {post_res.status_code}")
        return []

    post_soup = BeautifulSoup(post_res.text, "html.parser")
    
    table = None
    for t in post_soup.find_all("table"):
        if len(t.find_all("tr")) > 5:
            table = t
            break

    if not table:
        print(f"[!] No cutoff table found for Round {round_no}. (The portal may be undergoing maintenance or requires session refresh)")
        return []

    rows = table.find_all("tr")
    print(f"[+] Found table with {len(rows)} rows.")

    records = []
    for tr in rows[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 6:
            continue
        
        records.append({
            "institute": cells[0],
            "program": cells[1],
            "quota": cells[2] if len(cells) > 2 else "AI",
            "category": cells[3] if len(cells) > 3 else "OPEN",
            "gender": cells[4] if len(cells) > 4 else "Gender-Neutral",
            "opening_rank": cells[5] if len(cells) > 5 else "0",
            "closing_rank": cells[6] if len(cells) > 6 else "0",
            "round_no": round_no,
            "year": year
        })

    print(f"[+] Successfully extracted {len(records)} records for Round {round_no}.")
    return records

def save_records_to_db(records: List[Dict[str, Any]]):
    if not records:
        print("[!] No records to save.")
        return 0

    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    saved_count = 0
    for r in records:
        inst_name = r["institute"].strip()
        inst_type = determine_institute_type(inst_name)
        
        cursor.execute("SELECT id FROM institutes WHERE institute_name = ?", (inst_name,))
        row = cursor.fetchone()
        if not row:
            code = re.sub(r"[^A-Za-z0-9]", "", inst_name)[:10].upper()
            cursor.execute("""
                INSERT INTO institutes (institute_code, institute_name, institute_type)
                VALUES (?, ?, ?)
            """, (code, inst_name, inst_type))
            inst_id = cursor.lastrowid
        else:
            inst_id = row[0]

        prog_name = r["program"].strip()
        deg = parse_degree_type(prog_name)
        cursor.execute("SELECT id FROM programs WHERE program_name = ?", (prog_name,))
        p_row = cursor.fetchone()
        if not p_row:
            cursor.execute("INSERT INTO programs (program_name, degree_type) VALUES (?, ?)", (prog_name, deg))
            prog_id = cursor.lastrowid
        else:
            prog_id = p_row[0]

        cat_code = r["category"].strip()
        cursor.execute("SELECT id FROM categories WHERE category_code = ?", (cat_code,))
        c_row = cursor.fetchone()
        if not c_row:
            cursor.execute("INSERT INTO categories (category_code, category_name) VALUES (?, ?)", (cat_code, cat_code))
            cat_id = cursor.lastrowid
        else:
            cat_id = c_row[0]

        open_rk, open_p = parse_rank(r["opening_rank"])
        close_rk, close_p = parse_rank(r["closing_rank"])
        is_prep = open_p or close_p
        quota = r["quota"].strip().upper()
        gender = r["gender"].strip()
        round_no = int(r["round_no"])
        year = int(r["year"])

        cursor.execute("""
            INSERT OR REPLACE INTO cutoff_records (
                academic_year, round_no, institute_id, program_id, category_id,
                quota, gender, opening_rank, closing_rank, is_preparatory
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (year, round_no, inst_id, prog_id, cat_id, quota, gender, open_rk, close_rk, is_prep))
        saved_count += 1

    conn.commit()
    conn.close()
    print(f"[+] Successfully committed {saved_count} cutoff records into {db_path.name}.")
    return saved_count

def run_scraper(rounds: List[int] = None, year: int = 2024):
    if rounds is None:
        rounds = [1, 2, 3, 4, 5]

    session = requests.Session()
    total = 0
    for r in rounds:
        recs = scrape_round(session, round_no=r, year=year)
        if recs:
            c = save_records_to_db(recs)
            total += c

    print(f"\n========================================================")
    print(f" Scraping complete! Total cutoffs saved: {total}")
    print(f"========================================================")
    return total

if __name__ == "__main__":
    r_arg = [int(sys.argv[1])] if len(sys.argv) > 1 else [1, 2, 3, 4, 5]
    run_scraper(rounds=r_arg)
