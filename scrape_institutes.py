#!/usr/bin/env python3
"""
Web Scraper & Full Normalization Script for MAH CET 2026 Portal.
Extracts official Institute Metadata, Affiliated Universities, Minority Status,
and Course-level Branchwise Intake details into SQLite database cutoff.db.
"""

import time
import sqlite3
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_LIST_URL = "https://fe2026.mahacet.org/StaticPages/frmInstituteList?did=1884"
SUMMARY_URL_TEMPLATE = "https://fe2026.mahacet.org/StaticPages/frmInstituteSummary.aspx?InstituteCode={code}"
DB_PATH = "cutoff.db"


def init_db(db_path: str):
    """Initializes normalized tables in SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop old tables if re-creating
    cursor.execute("DROP TABLE IF EXISTS institutes;")
    cursor.execute("DROP TABLE IF EXISTS institute_courses;")

    # 1. Master Institutes Table
    cursor.execute("""
        CREATE TABLE institutes (
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

    # 2. Course-level Branchwise Intake Table
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

    # Indexes for speed
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inst_district ON institutes(district);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inst_univ ON institutes(affiliated_university);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crs_dte ON institute_courses(dte_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crs_name ON institute_courses(course_name);")

    conn.commit()
    conn.close()


def fetch_institute_codes():
    """Fetches list of 387 institute codes from the main CET page."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    print(f"Fetching institute list from: {BASE_LIST_URL}")
    response = requests.get(BASE_LIST_URL, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    codes = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if "InstituteCode=" in href:
            code = href.split("InstituteCode=")[-1].strip()
            if code not in codes:
                codes.append(code)

    print(f"Found {len(codes)} unique institute codes on CET portal.")
    return codes


def scrape_institute_detail(session: requests.Session, code: str):
    """Scrapes individual institute summary page for district, header metadata, and course intake."""
    url = SUMMARY_URL_TEMPLATE.format(code=code)
    for attempt in range(3):
        try:
            res = session.get(url, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            inst_data = {
                "dte_code": code,
                "institute_name": "",
                "district": "",
                "region": "",
                "status": "",
                "autonomy_status": "",
                "minority_status": "",
                "address": "",
                "affiliated_university": ""
            }

            courses_data = []

            # 1. Parse Institute Header Table
            for tr in soup.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if len(cells) == 2:
                    k, v = cells[0].strip(), cells[1].strip()
                    if k == "Institute Name":
                        inst_data["institute_name"] = v
                    elif k == "Institute Address":
                        inst_data["address"] = v
                    elif k == "Minority Status":
                        inst_data["minority_status"] = v
                elif len(cells) == 4:
                    k1, v1, k2, v2 = cells[0].strip(), cells[1].strip(), cells[2].strip(), cells[3].strip()
                    if k1 == "Region":
                        inst_data["region"] = v1
                    if k2 == "District":
                        inst_data["district"] = v2
                    if k1 == "Status":
                        inst_data["status"] = v1
                    if k2 == "Autonomy Status":
                        inst_data["autonomy_status"] = v2

            # 2. Parse Course Intake Table
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                if not rows:
                    continue
                header_text = [th.get_text(" ", strip=True) for th in rows[0].find_all(["th", "td"])]
                if "Choice Code" in header_text or "Course Name" in header_text:
                    for r in rows[1:]:
                        cols = [td.get_text(" ", strip=True) for td in r.find_all("td")]
                        if len(cols) >= 10:
                            choice_code = cols[0]
                            course_name = cols[1]
                            university = cols[2]
                            c_status = cols[3]
                            c_autonomy = cols[4]
                            c_minority = cols[5]
                            shift = cols[6]
                            accreditation = cols[7]
                            gender_type = cols[8]
                            try:
                                intake = int(cols[9])
                            except ValueError:
                                intake = 0

                            courses_data.append({
                                "choice_code": choice_code,
                                "dte_code": code,
                                "course_name": course_name,
                                "university": university,
                                "status": c_status,
                                "autonomy_status": c_autonomy,
                                "minority_status": c_minority,
                                "shift": shift,
                                "accreditation": accreditation,
                                "gender_type": gender_type,
                                "total_intake": intake
                            })

            # Derive primary affiliated university for the institute
            if courses_data:
                universities = [c["university"] for c in courses_data if c["university"]]
                if universities:
                    # Pick most frequent university
                    inst_data["affiliated_university"] = max(set(universities), key=universities.count)

            return inst_data, courses_data

        except Exception as e:
            time.sleep(1)

    print(f"Warning: Failed to fetch profile for DTE Code {code} after 3 attempts.")
    return None, []


def run_scraping_and_normalization(db_path: str):
    """Orchestrates full web scraping, course intake extraction, and table normalization."""
    init_db(db_path)
    codes = fetch_institute_codes()

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    print(f"Scraping detailed profiles & branchwise intake for {len(codes)} institutes...")
    start_time = time.time()

    all_inst_data = []
    all_courses_data = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(scrape_institute_detail, session, code): code for code in codes}
        for idx, future in enumerate(as_completed(futures), start=1):
            inst, crses = future.result()
            if inst:
                all_inst_data.append(inst)
            if crses:
                all_courses_data.extend(crses)
            if idx % 50 == 0 or idx == len(codes):
                print(f"  Progress: {idx}/{len(codes)} fetched...")

    elapsed = time.time() - start_time
    print(f"Completed web scraping in {elapsed:.2f} seconds.")
    print(f"  - Parsed {len(all_inst_data)} Institute Master Records")
    print(f"  - Parsed {len(all_courses_data)} Course Intake Records")

    # Insert into database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Populate institutes table
    for item in all_inst_data:
        cursor.execute("""
            INSERT OR REPLACE INTO institutes (
                dte_code, institute_name, district, region, status, autonomy_status,
                minority_status, address, affiliated_university
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["dte_code"],
            item["institute_name"],
            item["district"],
            item["region"],
            item["status"],
            item["autonomy_status"],
            item["minority_status"],
            item["address"],
            item["affiliated_university"]
        ))

    # 2. Populate institute_courses table
    for crs in all_courses_data:
        cursor.execute("""
            INSERT OR REPLACE INTO institute_courses (
                choice_code, dte_code, course_name, university, status,
                autonomy_status, minority_status, shift, accreditation,
                gender_type, total_intake
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            crs["choice_code"],
            crs["dte_code"],
            crs["course_name"],
            crs["university"],
            crs["status"],
            crs["autonomy_status"],
            crs["minority_status"],
            crs["shift"],
            crs["accreditation"],
            crs["gender_type"],
            crs["total_intake"]
        ))

    conn.commit()

    # 3. Update cutoff_records table with scraped district, status, and autonomy
    print("Updating district, status, and autonomy in cutoff_records from web-scraped institutes table...")
    cursor.execute("""
        UPDATE cutoff_records
        SET district = (SELECT district FROM institutes WHERE institutes.dte_code = cutoff_records.college_code),
            status = (SELECT status FROM institutes WHERE institutes.dte_code = cutoff_records.college_code),
            is_autonomous = (SELECT autonomy_status FROM institutes WHERE institutes.dte_code = cutoff_records.college_code)
        WHERE EXISTS (SELECT 1 FROM institutes WHERE institutes.dte_code = cutoff_records.college_code);
    """)
    conn.commit()

    # Verification stats
    inst_count = cursor.execute("SELECT COUNT(*) FROM institutes;").fetchone()[0]
    course_count = cursor.execute("SELECT COUNT(*) FROM institute_courses;").fetchone()[0]
    total_intake_sum = cursor.execute("SELECT SUM(total_intake) FROM institute_courses;").fetchone()[0]
    distinct_districts = cursor.execute("SELECT COUNT(DISTINCT district) FROM institutes;").fetchone()[0]
    distinct_univs = cursor.execute("SELECT COUNT(DISTINCT affiliated_university) FROM institutes;").fetchone()[0]
    matched_cutoff_rows = cursor.execute("SELECT COUNT(*) FROM cutoff_records WHERE district IS NOT NULL AND district != '';").fetchone()[0]
    total_cutoff_rows = cursor.execute("SELECT COUNT(*) FROM cutoff_records;").fetchone()[0]

    print("\n" + "="*60)
    print("REFINED NORMALIZATION & SCRAPING SUMMARY")
    print("="*60)
    print(f"Total Institutes Scraped & Stored: {inst_count}")
    print(f"Total Course Choices Scraped: {course_count}")
    print(f"Total State Engineering Seat Intake: {total_intake_sum:,}")
    print(f"Unique Districts Mapped: {distinct_districts}")
    print(f"Unique Affiliated Universities Mapped: {distinct_univs}")
    print(f"Cutoff Records Updated with District & Scraped Status: {matched_cutoff_rows} / {total_cutoff_rows} ({matched_cutoff_rows/total_cutoff_rows*100:.1f}%)")
    print("="*60)

    conn.close()


if __name__ == "__main__":
    run_scraping_and_normalization(DB_PATH)
