"""
MCC NEET-UG All India Quota (AIQ) Cutoff Parser & Database Ingester
===================================================================
Dedicated parser for MCC NEET-UG All India Quota Counselling Allotment PDFs:
- MCC UG Round 1 2025.pdf (2025-2026 Round 1)
- MCC UG Round 2 2025.pdf (2025-2026 Round 2)
- MCC UG Round 3 2025.pdf (2025-2026 Round 3)
- MCC UG Round 1.pdf      (2026-2027 Round 1)
- MCC UG Round 2.pdf      (2026-2027 Round 2)
- MCC UG Round 3.pdf      (2026-2027 Round 3)

Parses allotments using multi-worker parallel execution, normalizes colleges and courses,
calculates opening/closing All India Ranks (AIR) per category and quota, and ingests
into the dedicated medical.db without touching any CET, JoSAA, IISER, or BITS data.
"""

import os
import re
import sys
import time
import argparse
import sqlite3
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

# Add project backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.medical_db import (
    get_medical_connection,
    init_medical_database,
)

STORAGE_DIR = PROJECT_ROOT / "storage" / "uploads"

# Quota mapping to clean names
QUOTA_NAME_MAP = {
    "All India": "All India Quota (AIQ)",
    "Open Seat Quota": "Open Seat Quota (AIIMS/JIPMER)",
    "Delhi University Quota": "Delhi University Quota (DU)",
    "Aligarh Muslim University (AMU) Quota": "AMU Quota",
    "Banaras Hindu University (BHU) Quota": "BHU Quota",
    "Jamia Millia Islamia": "Jamia Millia Islamia (JMI)",
    "IP University Quota": "IP University Quota (IPU)",
    "Deemed/Paid Seats Quota": "Deemed / Paid Seats Quota",
    "Employees State Insurance Scheme(ESI)": "ESIC Quota",
    "Non-Resident Indian": "NRI Quota",
    "Muslim Minority Quota": "Muslim Minority Quota",
    "Jain Minority Quota": "Jain Minority Quota",
}

# Base category normalization
def map_base_category(cat_str: str) -> str:
    if not cat_str:
        return "OPEN"
    u = cat_str.upper().strip()
    if "PWD" in u or "PH" in u or "PHYSICAL" in u:
        return "PwD / PH"
    if "OBC" in u or "BC" in u:
        return "OBC"
    if "SC" in u:
        return "SC"
    if "ST" in u:
        return "ST"
    if "EWS" in u:
        return "EWS"
    if "MINO" in u or "MUSLIM" in u or "JAIN" in u:
        return "Minority"
    if "NRI" in u:
        return "NRI / IQ"
    return "OPEN"

INDIAN_STATES = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli", "Daman and Diu", "Delhi (NCT)", "Delhi",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand",
    "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

COMMON_CITIES = [
    "New Delhi", "Delhi", "Mumbai", "Kolkata", "Chennai", "Bengaluru", "Bangalore", "Hyderabad",
    "Ahmedabad", "Pune", "Surat", "Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane",
    "Bhopal", "Visakhapatnam", "Pimpri", "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra",
    "Nashik", "Faridabad", "Meerut", "Rajkot", "Kalyan", "Varanasi", "Srinagar", "Aurangabad",
    "Dhanbad", "Amritsar", "Navi Mumbai", "Allahabad", "Prayagraj", "Ranchi", "Howrah", "Jabalpur",
    "Gwalior", "Vijayawada", "Jodhpur", "Madurai", "Raipur", "Kota", "Guwahati", "Chandigarh",
    "Solapur", "Hubli", "Mysore", "Tiruchirappalli", "Bareilly", "Aligarh", "Tiruppur", "Gurgaon",
    "Moradabad", "Jalandhar", "Bhubaneswar", "Salem", "Warangal", "Mira-Bhayandar", "Jalgaon",
    "Guntur", "Thiruvananthapuram", "Bhiwandi", "Saharanpur", "Gorakhpur", "Bikaner", "Amravati",
    "Noida", "Jamshedpur", "Bhilai", "Cuttack", "Firozabad", "Kochi", "Nellore", "Bhavnagar",
    "Dehradun", "Durgapur", "Asansol", "Rourkela", "Nanded", "Kolhapur", "Ajmer", "Akola",
    "Gulbarga", "Jamnagar", "Ujjain", "Loni", "Siliguri", "Jhansi", "Ulhasnagar", "Jammu",
    "Sangli", "Mangalore", "Erode", "Belgaum", "Kurnool", "Ambattur", "Rajahmundry", "Tirunelveli",
    "Malegaon", "Gaya", "Udaipur", "Kakinada", "Davanagere", "Kozhikode", "Maheshtala", "Rajpur",
    "Rishikesh", "Kalyani", "Puducherry", "Pondicherry", "Bilaspur", "Shimla", "Imphal", "Shillong"
]

CITY_TO_STATE = {
    "New Delhi": "Delhi", "Delhi": "Delhi", "Mumbai": "Maharashtra", "Pune": "Maharashtra",
    "Nagpur": "Maharashtra", "Chennai": "Tamil Nadu", "Kolkata": "West Bengal",
    "Bengaluru": "Karnataka", "Bangalore": "Karnataka", "Hyderabad": "Telangana",
    "Ahmedabad": "Gujarat", "Surat": "Gujarat", "Vadodara": "Gujarat", "Rajkot": "Gujarat",
    "Jaipur": "Rajasthan", "Jodhpur": "Rajasthan", "Lucknow": "Uttar Pradesh", "Varanasi": "Uttar Pradesh",
    "Chandigarh": "Chandigarh", "Bhopal": "Madhya Pradesh", "Indore": "Madhya Pradesh",
    "Bhubaneswar": "Odisha", "Rishikesh": "Uttarakhand", "Dehradun": "Uttarakhand",
    "Puducherry": "Puducherry", "Patna": "Bihar", "Ranchi": "Jharkhand", "Raipur": "Chhattisgarh"
}

def normalize_mcc_college(raw_inst: str):
    s = raw_inst.strip()
    s = re.sub(r'\(Female Seat only\s*\)', '', s, flags=re.I).strip()
    
    # State detection
    found_state = None
    for st in INDIAN_STATES:
        if re.search(r'\b' + re.escape(st) + r'\b', s, re.I):
            found_state = st.replace('Delhi (NCT)', 'Delhi')
            break
            
    # City detection
    found_city = None
    for ct in COMMON_CITIES:
        if re.search(r'\b' + re.escape(ct) + r'\b', s, re.I):
            found_city = ct
            break
            
    # Split by comma
    parts = [p.strip() for p in s.split(',') if p.strip()]
    if not parts:
        clean_name = s
    else:
        p0 = parts[0]
        if len(parts) >= 2:
            p1 = parts[1]
            is_city_or_short = any(c.lower() in p1.lower() for c in COMMON_CITIES[:30]) or len(p1) < 25
            is_address = any(word in p1.lower() for word in [
                'campus', 'road', 'marg', 'nagar', 'post', 'near', 'opp', 'sector',
                'street', 'hospital', 'gate', 'admission', 'dist', 'pin', 'at -', 'floor'
            ])
            if is_city_or_short and not is_address:
                clean_name = f"{p0}, {p1}"
            else:
                clean_name = p0
        else:
            clean_name = p0
            
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    clean_name = re.sub(r'[, -]+$', '', clean_name).strip()
    clean_name = clean_name.replace('&amp;', '&')
    
    if not found_state and found_city:
        found_state = CITY_TO_STATE.get(found_city, "All India")
    elif not found_state:
        found_state = "All India"
        
    u = s.upper()
    if "AIIMS" in u:
        ctype = "AIIMS / Central"
    elif any(k in u for k in ["JIPMER", "BHU", "AMU", "VMMC", "MAULANA AZAD", "LADY HARDINGE", "ABVIMS", "UNIVERSITY COLLEGE OF MEDICAL"]):
        ctype = "Central University"
    elif any(k in u for k in ["DEEMED", "KASTURBA", "MANIPAL", "DY PATIL", "BHARATI VIDYAPEETH", "SRM", "AMRITA", "SYMBIOSIS", "PRIVATE"]):
        ctype = "Deemed / Private"
    elif "ESI" in u or "ESIC" in u:
        ctype = "Government (ESIC)"
    else:
        ctype = "Government/Aided"
        
    slug = re.sub(r'[^A-Z0-9]', '_', clean_name.upper())
    slug = re.sub(r'_+', '_', slug).strip('_')[:30]
    college_code = f"MCC_{slug}"
    
    return clean_name, college_code, found_city, found_state, ctype


VALID_MCC_COURSES = {
    "MBBS", "BDS", "B.SC NURSING", "B.SC. NURSING", "B.SC.NURSING",
    "B.SC NURSING(FEMALE ONLY)", "BAMS", "BHMS"
}

def is_valid_mcc_course(raw_code: str) -> bool:
    if not raw_code:
        return False
    u = re.sub(r'\s+', ' ', raw_code).strip().upper()
    return u in VALID_MCC_COURSES or "MBBS" in u or "BDS" in u or "NURSING" in u

COURSE_MAP = {
    "MBBS": ("MBBS", "Bachelor of Medicine and Bachelor of Surgery", "Medical (UG)"),
    "BDS": ("BDS", "Bachelor of Dental Surgery", "Dental (UG)"),
    "B.SC NURSING": ("B.Sc. Nursing", "B.Sc. Nursing", "Nursing (UG)"),
    "B.SC. NURSING": ("B.Sc. Nursing", "B.Sc. Nursing", "Nursing (UG)"),
    "B.SC.NURSING": ("B.Sc. Nursing", "B.Sc. Nursing", "Nursing (UG)"),
    "B.SC NURSING(FEMALE ONLY)": ("B.Sc. Nursing", "B.Sc. Nursing (Female)", "Nursing (UG)"),
    "BAMS": ("BAMS", "Bachelor of Ayurvedic Medicine and Surgery", "Ayurveda (UG)"),
    "BHMS": ("BHMS", "Bachelor of Homeopathic Medicine and Surgery", "Homeopathy (UG)"),
}

def get_or_create_course(conn: sqlite3.Connection, raw_code: str, course_cache: dict) -> int:
    norm_code = re.sub(r'\s+', ' ', raw_code).strip().upper()
    if norm_code in course_cache:
        return course_cache[norm_code]
        
    meta = COURSE_MAP.get(norm_code, (norm_code, norm_code, "Medical Sciences (UG)"))
    c_code, c_name, d_type = meta
    
    cur = conn.cursor()
    cur.execute("SELECT id FROM medical_courses WHERE course_code = ?", (c_code,))
    row = cur.fetchone()
    if row:
        course_cache[norm_code] = row[0]
        return row[0]
        
    cur.execute("""
        INSERT INTO medical_courses (course_code, course_name, degree_type)
        VALUES (?, ?, ?)
    """, (c_code, c_name, d_type))
    course_cache[norm_code] = cur.lastrowid
    return cur.lastrowid


def get_or_create_college(conn: sqlite3.Connection, raw_inst: str, college_cache: dict) -> int:
    if raw_inst in college_cache:
        return college_cache[raw_inst]
        
    c_name, c_code, city, state, c_type = normalize_mcc_college(raw_inst)
    
    cur = conn.cursor()
    # Check by code
    cur.execute("SELECT id FROM medical_colleges WHERE college_code = ?", (c_code,))
    row = cur.fetchone()
    if row:
        college_cache[raw_inst] = row[0]
        return row[0]
        
    # Check by exact name
    cur.execute("SELECT id FROM medical_colleges WHERE college_name = ?", (c_name,))
    row = cur.fetchone()
    if row:
        college_cache[raw_inst] = row[0]
        return row[0]
        
    cur.execute("""
        INSERT INTO medical_colleges (college_code, college_name, college_type, city, state)
        VALUES (?, ?, ?, ?, ?)
    """, (c_code, c_name, c_type, city, state))
    college_cache[raw_inst] = cur.lastrowid
    return cur.lastrowid


# Multi-process PDF chunk extractor
def parse_pdf_chunk(args):
    pdf_path_str, round_name, start_page, end_page = args
    import fitz
    doc = fitz.open(pdf_path_str)
    records = []
    
    for pno in range(start_page, end_page):
        page = doc[pno]
        tabs = list(page.find_tables())
        if not tabs:
            continue
        rows = tabs[0].extract()
        for r in rows:
            vals = [str(x).replace('\n', ' ').strip() if x else '' for x in r]
            if not vals or not vals[0].isdigit():
                continue
                
            if round_name == "Round 1":
                if len(vals) >= 8 and vals[1].isdigit():
                    rank = int(vals[1])
                    quota, inst, course, cat = vals[2], vals[3], vals[4], vals[5]
                elif len(vals) >= 7:
                    rank = int(vals[0])
                    quota, inst, course, cat = vals[1], vals[2], vals[3], vals[4]
                else:
                    continue
                if inst and inst != '-' and course and course != '-':
                    records.append((rank, inst, course, quota, cat, "Allotted", None))
                    
            elif round_name == "Round 2":
                rank = int(vals[1]) if vals[1].isdigit() else int(vals[0])
                rem_cols = [c for c in (vals[2:] if vals[1].isdigit() else vals[1:]) if c != '']
                if len(rem_cols) < 11:
                    continue
                r1_q, r1_i, r1_c, r1_rem = rem_cols[0], rem_cols[1], rem_cols[2], rem_cols[3]
                r2_q, r2_i, r2_c, r2_cat, r2_cand_cat, r2_opt, r2_rem = rem_cols[4:11]
                records.append((rank, r2_i, r2_c, r2_q, r2_cat, r2_rem, (r1_i, r1_c, r1_q, r1_rem)))
                
            elif round_name == "Round 3":
                rank = int(vals[1]) if vals[1].isdigit() else int(vals[0])
                rem_cols = [c for c in (vals[2:] if vals[1].isdigit() else vals[1:]) if c != '']
                if len(rem_cols) < 15:
                    continue
                r1_q, r1_i, r1_c, r1_rem = rem_cols[0], rem_cols[1], rem_cols[2], rem_cols[3]
                r2_q, r2_i, r2_c, r2_rem = rem_cols[4], rem_cols[5], rem_cols[6], rem_cols[7]
                r3_q, r3_i, r3_c, r3_cat, r3_cand_cat, r3_opt, r3_rem = rem_cols[8:15]
                records.append((rank, r3_i, r3_c, r3_q, r3_cat, r3_rem, (r1_i, r1_c, r1_q, r1_rem, r2_i, r2_c, r2_q, r2_rem)))
                
    return records


def ingest_mcc_pdf(
    conn: sqlite3.Connection,
    pdf_path: Path,
    academic_year: str,
    round_name: str,
    candidate_tracker: dict,
    college_cache: dict,
    course_cache: dict,
    workers: int = 6,
    limit_pages: int = None
):
    import fitz
    print(f"\n{'='*75}")
    print(f"[*] Processing: {pdf_path.name}")
    print(f"    Academic Year: {academic_year} | Round: {round_name}")
    print(f"{'='*75}")
    
    t0 = time.time()
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    doc.close()
    
    # Start from page 1 or 2 (skipping 2-column legend tables)
    start_p = 1 if (round_name == "Round 3" and "2025" in pdf_path.name) else 2
    end_p = min(limit_pages, total_pages) if limit_pages else total_pages
    
    chunk_size = 100
    tasks = []
    for s in range(start_p, end_p, chunk_size):
        tasks.append((str(pdf_path), round_name, s, min(s + chunk_size, end_p)))
        
    print(f" -> Dispatching {len(tasks)} chunks across {workers} worker processes ({end_p - start_p} pages)...")
    with ProcessPoolExecutor(max_workers=workers) as executor:
        chunk_results = list(executor.map(parse_pdf_chunk, tasks))
        
    raw_records = [rec for sub in chunk_results for rec in sub]
    print(f" -> Extracted {len(raw_records):,} raw rows in {time.time() - t0:.2f}s.")
    
    # Resolve Allotments
    allotments = [] # (rank, inst, course, quota, cat)
    
    for rec in raw_records:
        rank = rec[0]
        
        if round_name == "Round 1":
            _, inst, course, quota, cat, _, _ = rec
            if inst and inst != '-' and course and course != '-':
                allotments.append((rank, inst, course, quota, cat))
                candidate_tracker[rank] = (inst, course, quota, cat)
                
        elif round_name == "Round 2":
            _, r2_i, r2_c, r2_q, r2_cat, r2_rem, prev = rec
            r1_i, r1_c, r1_q, r1_rem = prev
            
            if r2_i and r2_i != '-' and ('Fresh' in r2_rem or 'Upgraded' in r2_rem or 'Retained' in r2_rem):
                allotments.append((rank, r2_i, r2_c, r2_q, r2_cat))
                candidate_tracker[rank] = (r2_i, r2_c, r2_q, r2_cat)
            elif ('Did not' in r2_rem or 'No Upgradation' in r2_rem or r2_rem == 'Not Allotted.'):
                if r1_rem == 'Reported' and rank in candidate_tracker:
                    inst, course, quota, cat = candidate_tracker[rank]
                    allotments.append((rank, inst, course, quota, cat))
                elif r1_rem == 'Reported' and r1_i and r1_i != '-':
                    allotments.append((rank, r1_i, r1_c, r1_q, 'Open'))
                    candidate_tracker[rank] = (r1_i, r1_c, r1_q, 'Open')
                    
        elif round_name == "Round 3":
            _, r3_i, r3_c, r3_q, r3_cat, r3_rem, prev = rec
            r1_i, r1_c, r1_q, r1_rem, r2_i, r2_c, r2_q, r2_rem = prev
            
            if r3_i and r3_i != '-' and ('Fresh' in r3_rem or 'Upgraded' in r3_rem or 'Retained' in r3_rem):
                allotments.append((rank, r3_i, r3_c, r3_q, r3_cat))
                candidate_tracker[rank] = (r3_i, r3_c, r3_q, r3_cat)
            elif ('Did not' in r3_rem or 'No Upgradation' in r3_rem or r3_rem == 'Not Allotted.'):
                if rank in candidate_tracker:
                    inst, course, quota, cat = candidate_tracker[rank]
                    allotments.append((rank, inst, course, quota, cat))
                elif r2_rem in ('Reported', 'Retained') and r2_i and r2_i != '-':
                    allotments.append((rank, r2_i, r2_c, r2_q, 'Open'))
                    candidate_tracker[rank] = (r2_i, r2_c, r2_q, 'Open')
                elif r1_rem == 'Reported' and r1_i and r1_i != '-':
                    allotments.append((rank, r1_i, r1_c, r1_q, 'Open'))
                    candidate_tracker[rank] = (r1_i, r1_c, r1_q, 'Open')
                    
    print(f" -> Active seat allotments in {round_name}: {len(allotments):,}")
    
    # Group into cutoffs: (inst, course, quota, cat) -> list of ranks
    grouped = defaultdict(list)
    for rank, inst, course, quota, cat in allotments:
        if not is_valid_mcc_course(course):
            continue
        clean_quota = QUOTA_NAME_MAP.get(quota.strip(), quota.strip())
        norm_cat = cat.strip()
        quota_category = f"{clean_quota} - {norm_cat}"
        base_cat = map_base_category(norm_cat)
        grouped[(inst, course, quota_category, base_cat)].append(rank)
        
    print(f" -> Aggregated into {len(grouped):,} unique cutoff groups.")
    
    # Ingest into SQLite
    cur = conn.cursor()
    ingested_count = 0
    t_ingest = time.time()
    
    for (inst, course, quota_category, base_cat), ranks in grouped.items():
        college_id = get_or_create_college(conn, inst, college_cache)
        course_id = get_or_create_course(conn, course, course_cache)
        
        opening_rank = min(ranks)
        closing_rank = max(ranks)
        allotted_seats = len(ranks)
        
        cur.execute("""
            INSERT INTO medical_cutoffs (
                academic_year, round, college_id, course_id, quota_category,
                base_category, opening_rank, closing_rank, opening_score, closing_score,
                allotted_seats, exam_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, 'NEET (UG) - MCC AIQ')
            ON CONFLICT(academic_year, round, college_id, course_id, quota_category)
            DO UPDATE SET
                base_category = excluded.base_category,
                opening_rank = excluded.opening_rank,
                closing_rank = excluded.closing_rank,
                allotted_seats = excluded.allotted_seats,
                exam_name = excluded.exam_name,
                updated_at = CURRENT_TIMESTAMP;
        """, (academic_year, round_name, college_id, course_id, quota_category, base_cat, opening_rank, closing_rank, allotted_seats))
        ingested_count += 1
        
    conn.commit()
    print(f" [OK] Successfully saved {ingested_count:,} cutoffs into medical.db ({time.time() - t_ingest:.2f}s).")
    return ingested_count


def run_pipeline(workers: int = 6, limit_pages: int = None):
    print("\n" + "="*75)
    print("      MCC NEET-UG ALL INDIA QUOTA (AIQ) INGESTION PIPELINE")
    print("="*75)
    
    init_medical_database()
    conn = get_medical_connection()
    
    files_to_process = [
        # 2025-2026 Cohort
        ("MCC UG Round 1 2025.pdf", "2025-2026", "Round 1"),
        ("MCC UG Round 2 2025.pdf", "2025-2026", "Round 2"),
        ("MCC UG Round 3 2025.pdf", "2025-2026", "Round 3"),
        # 2026-2027 Cohort
        ("MCC UG Round 1.pdf",      "2026-2027", "Round 1"),
        ("MCC UG Round 2.pdf",      "2026-2027", "Round 2"),
        ("MCC UG Round 3.pdf",      "2026-2027", "Round 3"),
    ]
    
    college_cache = {}
    course_cache = {}
    total_cutoffs_ingested = 0
    t_start = time.time()
    
    # Process cohort by cohort to keep candidate tracking accurate
    cohorts = ["2025-2026", "2026-2027"]
    for cohort in cohorts:
        candidate_tracker = {}
        cohort_files = [item for item in files_to_process if item[1] == cohort]
        print(f"\n>>> Starting Cohort {cohort} ({len(cohort_files)} rounds)...")
        
        for fname, year, rname in cohort_files:
            pdf_path = STORAGE_DIR / fname
            if not pdf_path.exists():
                print(f"[!] Warning: File not found: {pdf_path}")
                continue
            count = ingest_mcc_pdf(
                conn=conn,
                pdf_path=pdf_path,
                academic_year=year,
                round_name=rname,
                candidate_tracker=candidate_tracker,
                college_cache=college_cache,
                course_cache=course_cache,
                workers=workers,
                limit_pages=limit_pages
            )
            total_cutoffs_ingested += count

    # Record metadata
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO medical_meta (source_files, total_records, status, message)
        VALUES (?, ?, 'SUCCESS', ?)
    """, (
        ", ".join([f[0] for f in files_to_process]),
        total_cutoffs_ingested,
        f"Ingested {total_cutoffs_ingested} MCC AIQ cutoff records across 6 rounds in {time.time() - t_start:.1f}s"
    ))
    conn.commit()
    conn.close()
    
    print("\n" + "="*75)
    print(f"PIPELINE COMPLETE in {time.time() - t_start:.2f}s!")
    print(f"Total MCC Cutoff Records Saved: {total_cutoffs_ingested:,}")
    print("="*75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest MCC UG All India Quota cutoffs into medical.db")
    parser.add_argument("--workers", type=int, default=6, help="Number of parallel worker processes (default: 6)")
    parser.add_argument("--limit-pages", type=int, default=None, help="Limit pages per PDF for testing")
    args = parser.parse_args()
    
    run_pipeline(workers=args.workers, limit_pages=args.limit_pages)
