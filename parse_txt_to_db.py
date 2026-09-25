#!/usr/bin/env python3
"""
Parser for MHT-CET Cutoff Text Files to SQLite Database.
Processes CAP 1, CAP 2, CAP 3, and CAP 4 cutoffs into cutoff.db.
Derives category & quota details while leaving district, official status,
autonomy, and university to be derived exclusively from web scraping.
"""

import sys
import re
import sqlite3
from pathlib import Path


def infer_cap_round(file_path: Path) -> int:
    """Infers CAP round number (1, 2, 3, 4) from filename."""
    name = file_path.name.upper()
    if "CAP1" in name or "CAP-1" in name or "CAP_1" in name or "ROUND1" in name or "ROUND_1" in name:
        return 1
    elif "CAP2" in name or "CAP-2" in name or "CAP_2" in name or "ROUND2" in name or "ROUND_2" in name:
        return 2
    elif "CAP3" in name or "CAP-3" in name or "CAP_3" in name or "ROUND3" in name or "ROUND_3" in name:
        return 3
    elif "CAP4" in name or "CAP-4" in name or "CAP_4" in name or "ROUND4" in name or "ROUND_4" in name:
        return 4
    else:
        # Default fallback
        match = re.search(r"CAP\s*(\d)", name)
        if match:
            return int(match.group(1))
        return 1


def parse_category_meta(category_code: str):
    """
    Parses category code (e.g., GOPENS, LOPENS, GSCS, TFWS) into seat_category:
    OPEN, SC, ST, OBC, VJ, NT1, NT2, NT3, SEBC, EWS, TFWS, PWD, DEF, ORPHAN, MI
    """
    cat = (category_code or "").upper()

    if "OPEN" in cat:
        seat_category = "OPEN"
    elif "SEBC" in cat:
        seat_category = "SEBC"
    elif "SCS" in cat or "SCH" in cat or "SCO" in cat or "SC" in cat:
        seat_category = "SC"
    elif "STS" in cat or "STH" in cat or "STO" in cat or "ST" in cat:
        seat_category = "ST"
    elif "OBC" in cat:
        seat_category = "OBC"
    elif "VJS" in cat or "VJH" in cat or "VJO" in cat or "VJ" in cat:
        seat_category = "VJ"
    elif "NT1" in cat:
        seat_category = "NT1"
    elif "NT2" in cat:
        seat_category = "NT2"
    elif "NT3" in cat:
        seat_category = "NT3"
    elif "EWS" in cat:
        seat_category = "EWS"
    elif "TFWS" in cat:
        seat_category = "TFWS"
    elif "ORPHAN" in cat:
        seat_category = "ORPHAN"
    elif cat == "MI":
        seat_category = "Minority"
    else:
        seat_category = cat

    return seat_category


def parse_reservation_level(quota_type: str, category_code: str):
    """
    Parses quota type & category suffix to determine reservation level:
    - State Level
    - Home University (HU)
    - Other Than Home University (OHU)
    - Minority (MI)
    """
    q = (quota_type or "").lower()
    cat = (category_code or "").upper()

    if "state level" in q or cat.endswith("S"):
        return "State Level"
    elif "other than home university" in q or cat.endswith("O"):
        return "Other Than Home University (OHU)"
    elif "home university" in q or cat.endswith("H"):
        return "Home University (HU)"
    elif "mi" in q or cat == "MI":
        return "Minority (MI)"
    else:
        return "State Level"


def create_database(db_path: str):
    """Creates the SQLite table schema for multi-round cutoff records."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS cutoff_records;")
    cursor.execute("""
        CREATE TABLE cutoff_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cap_round INTEGER NOT NULL,
            page_number INTEGER,
            college_code TEXT,
            college_name TEXT,
            district TEXT,
            course_code TEXT,
            course_name TEXT,
            status TEXT,
            is_autonomous TEXT,
            governance_type TEXT,
            quota_type TEXT,
            reservation_level TEXT,
            category TEXT,
            seat_category TEXT,
            stage TEXT,
            merit_rank INTEGER,
            percentile REAL
        );
    """)

    # Indexes for fast multi-round querying
    cursor.execute("CREATE INDEX idx_cap_round ON cutoff_records(cap_round);")
    cursor.execute("CREATE INDEX idx_college_code ON cutoff_records(college_code);")
    cursor.execute("CREATE INDEX idx_course_name ON cutoff_records(course_name);")
    cursor.execute("CREATE INDEX idx_district ON cutoff_records(district);")
    cursor.execute("CREATE INDEX idx_is_autonomous ON cutoff_records(is_autonomous);")
    cursor.execute("CREATE INDEX idx_status ON cutoff_records(status);")
    cursor.execute("CREATE INDEX idx_seat_category ON cutoff_records(seat_category);")
    cursor.execute("CREATE INDEX idx_reservation_level ON cutoff_records(reservation_level);")

    conn.commit()
    return conn


def parse_single_txt(txt_path: Path, cap_round: int):
    """Parses a single cutoff text file and returns structured row tuples."""
    page_regex = re.compile(r"^---\s*Page\s+(\d+)\s*---")
    college_regex = re.compile(r"^(\d{5})\s*-\s*(.+)")
    course_regex = re.compile(r"^(\d{10})\s*-\s*(.+)")
    stage_regex = re.compile(r"^\s*([I|V|X]+)\s+(\d+)")
    percentile_regex = re.compile(r"^\s*\((-?\d+\.\d+)\)\s*$")
    rank_only_regex = re.compile(r"^\s*(\d+)\s*$")

    current_page = 0
    current_college_code = None
    current_college_name = None
    current_course_code = None
    current_course_name = None
    current_status = None
    current_quota = None
    current_categories = []

    rows_to_insert = []

    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    idx = 0
    total_lines = len(lines)

    while idx < total_lines:
        line = lines[idx].strip()
        idx += 1

        if not line:
            continue

        p_match = page_regex.match(line)
        if p_match:
            current_page = int(p_match.group(1))
            continue

        col_match = college_regex.match(line)
        if col_match:
            current_college_code = col_match.group(1)
            current_college_name = col_match.group(2)
            continue

        crs_match = course_regex.match(line)
        if crs_match:
            current_course_code = crs_match.group(1)
            current_course_name = crs_match.group(2)
            current_status = None
            current_quota = None
            current_categories = []
            continue

        if line.startswith("Status:"):
            current_status = line.replace("Status:", "").strip()
            continue

        if line == "Stage":
            continue

        tokens = line.split()
        if len(tokens) >= 1 and all(re.match(r"^[A-Z0-9]+$", t) for t in tokens) and any(kw in line for kw in ["OPEN", "SC", "ST", "OBC", "EWS", "TFWS", "SEBC", "NT", "VJ", "PWD", "DEF", "ORPHAN", "MI"]):
            current_categories = tokens
            continue

        stg_match = stage_regex.match(line)
        if stg_match:
            stage_str = stg_match.group(1)
            first_rank = int(stg_match.group(2))

            ranks = [first_rank]
            percentiles = []

            if idx < total_lines:
                perc_line = lines[idx].strip()
                p_m = percentile_regex.match(perc_line)
                if p_m:
                    percentiles.append(float(p_m.group(1)))
                    idx += 1

            cat_count = len(current_categories)
            for _ in range(1, cat_count):
                if idx >= total_lines:
                    break
                r_line = lines[idx].strip()
                r_m = rank_only_regex.match(r_line)
                if r_m:
                    ranks.append(int(r_m.group(1)))
                    idx += 1
                    if idx < total_lines:
                        perc_line = lines[idx].strip()
                        p_m = percentile_regex.match(perc_line)
                        if p_m:
                            percentiles.append(float(p_m.group(1)))
                            idx += 1
                else:
                    break

            status_lower = (current_status or "").lower()
            if "government" in status_lower or "govt" in status_lower or "university department" in status_lower:
                governance_type = "Government"
            else:
                governance_type = "Private"

            for cat_idx, cat in enumerate(current_categories):
                if cat_idx < len(ranks) and cat_idx < len(percentiles):
                    seat_category = parse_category_meta(cat)
                    reservation_level = parse_reservation_level(current_quota, cat)

                    rows_to_insert.append((
                        cap_round,
                        current_page,
                        current_college_code,
                        current_college_name,
                        None, # district to be updated via web scraper
                        current_course_code,
                        current_course_name,
                        current_status,
                        None, # autonomy to be updated via web scraper
                        governance_type,
                        current_quota,
                        reservation_level,
                        cat,
                        seat_category,
                        stage_str,
                        ranks[cat_idx],
                        percentiles[cat_idx]
                    ))
            continue

        if not line.startswith("(") and not line.isdigit() and not line.startswith("---"):
            current_quota = line

    return rows_to_insert


_COL_REGEX = re.compile(r"^(\d{5})\s*-\s*(.+)")
_CRS_REGEX = re.compile(r"^(\d{10})\s*-\s*(.+)")


def _parse_pdf_page_worker(args):
    """Worker function for parallel PDF page parsing."""
    import pymupdf
    pdf_path, page_idx, cap_round = args
    doc = pymupdf.open(pdf_path)
    page = doc[page_idx]

    page_text = page.get_text()
    if "Stage" not in page_text:
        doc.close()
        return []

    tabs = page.find_tables()
    if not tabs.tables:
        doc.close()
        return []

    blocks = page.get_text("blocks")
    page_lines = []
    current_college_code = None
    current_college_name = None
    current_course_code = None
    current_course_name = None
    current_status = None

    for b in blocks:
        b_top = b[1]
        for line in b[4].splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            page_lines.append((b_top, line_str))

            if not current_college_code:
                col_match = _COL_REGEX.match(line_str)
                if col_match:
                    current_college_code = col_match.group(1)
                    current_college_name = col_match.group(2)
            if not current_course_code:
                crs_match = _CRS_REGEX.match(line_str)
                if crs_match:
                    current_course_code = crs_match.group(1)
                    current_course_name = crs_match.group(2)
            if not current_status and line_str.startswith("Status:"):
                current_status = line_str.replace("Status:", "").strip()

    status_lower = (current_status or "").lower()
    if "government" in status_lower or "govt" in status_lower or "university department" in status_lower:
        governance_type = "Government"
    else:
        governance_type = "Private"

    table_list = sorted(tabs.tables, key=lambda t: t.bbox[1])
    prev_table_bottom = 0
    rows = []

    for tab in table_list:
        tab_top = tab.bbox[1]
        tab_bottom = tab.bbox[3]

        quota_title = None
        for b_top, ls in page_lines:
            if prev_table_bottom <= b_top < tab_top:
                if (
                    ls
                    and not _COL_REGEX.match(ls)
                    and not _CRS_REGEX.match(ls)
                    and not ls.startswith("Status:")
                    and not ls.startswith("State Common")
                    and not ls.startswith("Cut Off List")
                    and not ls.startswith("Government of")
                    and not ls.startswith("Degree Courses")
                    and ls != "Stage"
                    and not ls.startswith("Legends:")
                    and not ls.startswith("Maharashtra State Seats")
                ):
                    quota_title = ls

        df = tab.extract()
        if not df or len(df) < 2:
            prev_table_bottom = tab_bottom
            continue

        header = [c.replace("\n", "").strip() if c else "" for c in df[0]]
        if not header or header[0] != "Stage":
            prev_table_bottom = tab_bottom
            continue

        categories = header[1:]

        for row in df[1:]:
            stage_str = row[0].replace("\n", "").strip()
            cell_values = row[1:]
            for cat, cell in zip(categories, cell_values):
                cell_clean = cell.strip() if cell else ""
                if not cell_clean:
                    continue
                parts = cell_clean.split("\n")
                rank_str = parts[0].strip()
                perc_str = parts[1].strip() if len(parts) >= 2 else ""
                perc_str = perc_str.replace("(", "").replace(")", "").strip()

                try:
                    rank = int(rank_str)
                    perc = float(perc_str) if perc_str else None
                    seat_category = parse_category_meta(cat)
                    reservation_level = parse_reservation_level(quota_title, cat)

                    rows.append((
                        cap_round,
                        page_idx + 1,
                        current_college_code,
                        current_college_name,
                        None,
                        current_course_code,
                        current_course_name,
                        current_status,
                        None,
                        governance_type,
                        quota_title,
                        reservation_level,
                        cat,
                        seat_category,
                        stage_str,
                        rank,
                        perc
                    ))
                except ValueError:
                    pass
        prev_table_bottom = tab_bottom

    doc.close()
    return rows


def parse_single_pdf(pdf_path: Path, cap_round: int):
    """Parses a single cutoff PDF file using parallel PyMuPDF table grid alignment."""
    import pymupdf
    from concurrent.futures import ProcessPoolExecutor

    doc = pymupdf.open(str(pdf_path))
    num_pages = len(doc)
    doc.close()

    tasks = [(str(pdf_path), p, cap_round) for p in range(num_pages)]
    rows_to_insert = []

    with ProcessPoolExecutor() as executor:
        results = executor.map(_parse_pdf_page_worker, tasks, chunksize=20)
        for res in results:
            rows_to_insert.extend(res)

    return rows_to_insert


def parse_all_cap_files(base_dir: str = ".", db_path: str = "cutoff.db"):
    """Discovers all CAP PDF (or text) files and populates multi-round cutoff.db."""
    dir_path = Path(base_dir)
    pdf_files = sorted(list(dir_path.glob("*CAP*.pdf")))

    conn = create_database(db_path)
    cursor = conn.cursor()

    total_records = 0
    round_counts = {}

    if pdf_files:
        for pdf_file in pdf_files:
            round_num = infer_cap_round(pdf_file)
            print(f"Parsing [CAP Round {round_num}] directly from PDF: {pdf_file.name}...")
            rows = parse_single_pdf(pdf_file, round_num)

            cursor.executemany("""
                INSERT INTO cutoff_records (
                    cap_round, page_number, college_code, college_name, district, course_code, course_name,
                    status, is_autonomous, governance_type, quota_type, reservation_level,
                    category, seat_category, stage, merit_rank, percentile
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            conn.commit()
            round_counts[round_num] = len(rows)
            total_records += len(rows)
            print(f"  Inserted {len(rows):,} records for CAP Round {round_num}")
    else:
        txt_files = sorted(list(dir_path.glob("*CAP*.txt")))
        if not txt_files:
            print("No CAP PDF or text files found to parse!")
            return
        for txt_file in txt_files:
            round_num = infer_cap_round(txt_file)
            print(f"Parsing [CAP Round {round_num}] from text file: {txt_file.name}...")
            rows = parse_single_txt(txt_file, round_num)

            cursor.executemany("""
                INSERT INTO cutoff_records (
                    cap_round, page_number, college_code, college_name, district, course_code, course_name,
                    status, is_autonomous, governance_type, quota_type, reservation_level,
                    category, seat_category, stage, merit_rank, percentile
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            conn.commit()
            round_counts[round_num] = len(rows)
            total_records += len(rows)
            print(f"  Inserted {len(rows):,} records for CAP Round {round_num}")

    conn.close()

    print("\n" + "="*60)
    print("MULTI-ROUND PARSING SUMMARY")
    print("="*60)
    for r, count in sorted(round_counts.items()):
        print(f"  CAP Round {r}: {count:,} records")
    print(f"Total Combined Cutoff Records Inserted: {total_records:,}")
    print("="*60)


if __name__ == "__main__":
    db_file = "cutoff.db"
    parse_all_cap_files(".", db_file)
