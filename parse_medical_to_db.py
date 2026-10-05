import os
import re
import sys
import time
import sqlite3
from pathlib import Path

# Add project backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.medical_db import (
    get_medical_connection,
    init_medical_database,
)

PDF_FOLDER = Path(r"C:\Users\HP\Desktop\cap allotment portal\medical_data")

COURSE_MAP = {
    "MBBS": ("MBBS", "Bachelor of Medicine and Bachelor of Surgery", "Medical (UG)"),
    "BDS": ("BDS", "Bachelor of Dental Surgery", "Dental (UG)"),
    "BAMS": ("BAMS", "Bachelor of Ayurvedic Medicine and Surgery", "Ayurveda (UG)"),
    "BHMS": ("BHMS", "Bachelor of Homeopathic Medicine and Surgery", "Homeopathy (UG)"),
    "BUMS": ("BUMS", "Bachelor of Unani Medicine and Surgery", "Unani (UG)"),
    "PT": ("BPTH", "Bachelor of Physiotherapy", "Allied Health Sciences (UG)"),
    "BPTH": ("BPTH", "Bachelor of Physiotherapy", "Allied Health Sciences (UG)"),
    "OT": ("BOTH", "Bachelor of Occupational Therapy", "Allied Health Sciences (UG)"),
    "BOTH": ("BOTH", "Bachelor of Occupational Therapy", "Allied Health Sciences (UG)"),
    "NURSING": ("B.Sc. Nursing", "B.Sc. Nursing", "Nursing (UG)"),
}

BASE_CATEGORY_MAP = {
    "OPEN": "OPEN",
    "OPEN (W)": "OPEN",
    "HOPEN": "OPEN",
    "HOPENW": "OPEN",
    "W": "OPEN",
    "OBC": "OBC",
    "OBC (W)": "OBC",
    "HOBC": "OBC",
    "EMOBC": "OBC",
    "EMOBCW": "OBC",
    "SOBC": "OBC",
    "EWS": "EWS",
    "EWS(W)": "EWS",
    "HEWS": "EWS",
    "SC": "SC",
    "SC (W)": "SC",
    "HSC": "SC",
    "ST": "ST",
    "ST (W)": "ST",
    "VJ": "VJ / NT-A",
    "VJA": "VJ / NT-A",
    "EMVJA": "VJ / NT-A",
    "NT1": "NT1 (NT-B)",
    "NTB": "NT1 (NT-B)",
    "NTB(W)": "NT1 (NT-B)",
    "EMNTB": "NT1 (NT-B)",
    "NT2": "NT2 (NT-C)",
    "NTC": "NT2 (NT-C)",
    "NTC(W)": "NT2 (NT-C)",
    "EMNTC": "NT2 (NT-C)",
    "EMNTCW": "NT2 (NT-C)",
    "NT3": "NT3 (NT-D)",
    "NTD": "NT3 (NT-D)",
    "NTD(W)": "NT3 (NT-D)",
    "EMNTD": "NT3 (NT-D)",
    "EMNTDW": "NT3 (NT-D)",
    "HNTD": "NT3 (NT-D)",
    "SEBC": "SEBC",
    "SEBC(W)": "SEBC",
    "HSEBC": "SEBC",
    "EMSEBC": "SEBC",
    "EMSEBCW": "SEBC",
    "D1": "Defense",
    "D2": "Defense",
    "D3": "Defense",
    "DEF1": "Defense",
    "DEF2": "Defense",
    "DEF3": "Defense",
    "PH": "PwD / PH",
    "MKB": "MKB",
    "NRI": "NRI / IQ",
    "I.Q.": "NRI / IQ",
    "MINO": "Minority",
}

def clean_int(val):
    if not val:
        return None
    cleaned = re.sub(r'[^\d]', '', str(val))
    return int(cleaned) if cleaned else None

def get_or_create_college(conn, code, name, college_type="Government/Aided"):
    norm_code = code.lstrip('0')
    norm_name = re.sub(r'\s+', ' ', name).strip()
    norm_name = re.sub(r'\(.*?\)$', '', norm_name).strip()
    
    cur = conn.cursor()
    cur.execute("SELECT id, college_name, college_type FROM medical_colleges WHERE college_code = ?", (norm_code,))
    row = cur.fetchone()
    if row:
        return row[0]
    
    # Infer city from name
    city = None
    city_matches = ["MUMBAI", "PUNE", "NAGPUR", "NASIK", "NASHIK", "THANE", "SOLAPUR", "MIRAJ", 
                    "KOLHAPUR", "AURANGABAD", "CHHATRAPATI SAMBHAJINAGAR", "JALGAON", "DHULE", 
                    "SANGLI", "SATARA", "LATUR", "NANDED", "AMRAVATI", "AKOLA", "CHANDRAPUR", 
                    "YAVATMAL", "BARAMATI", "ALIBAUG", "RATNAGIRI", "SINDHUDURG", "GONDIA"]
    upper_name = norm_name.upper()
    for cm in city_matches:
        if cm in upper_name:
            city = cm.title()
            break
            
    cur.execute("""
        INSERT INTO medical_colleges (college_code, college_name, college_type, city)
        VALUES (?, ?, ?, ?)
    """, (norm_code, norm_name, college_type, city))
    return cur.lastrowid

def get_or_create_course(conn, raw_code):
    norm_code = raw_code.replace('.', '').strip().upper()
    meta = COURSE_MAP.get(norm_code, (norm_code, norm_code, "Medical Sciences (UG)"))
    c_code, c_name, d_type = meta
    
    cur = conn.cursor()
    cur.execute("SELECT id FROM medical_courses WHERE course_code = ?", (c_code,))
    row = cur.fetchone()
    if row:
        return row[0]
        
    cur.execute("""
        INSERT INTO medical_courses (course_code, course_name, degree_type)
        VALUES (?, ?, ?)
    """, (c_code, c_name, d_type))
    return cur.lastrowid


def parse_and_insert_summary_pdf(conn, pdf_path, academic_year, round_name="Summary Cutoff"):
    import fitz
    print(f"\n[*] Ingesting Summary Cutoffs: {pdf_path.name} ({academic_year})...")
    doc = fitz.open(str(pdf_path))
    
    cols_info = [
        ('SC', 'F'), ('SC', 'L'),
        ('ST', 'F'), ('ST', 'L'),
        ('VJ', 'F'), ('VJ', 'L'),
        ('NT1', 'F'), ('NT1', 'L'),
        ('NT2', 'F'), ('NT2', 'L'),
        ('NT3', 'F'), ('NT3', 'L'),
        ('OBC', 'F'), ('OBC', 'L'),
        ('SEBC', 'F'), ('SEBC', 'L'),
        ('EWS', 'F'), ('EWS', 'L'),
        ('OPEN', 'F'), ('OPEN', 'L'),
        ('D1', 'L'),
        ('D2', 'L'),
        ('D3', 'L'),
        ('PH', 'L'),
        ('MKB', 'L'),
        ('NRI', 'L'),
    ]
    
    current_course = 'MBBS'
    current_college_type = 'Government/Aided'
    total_inserted = 0
    
    for pno in range(len(doc)):
        page = doc[pno]
        text = page.get_text()
        lines = text.split('\n')
        
        # Detect Course & Type
        for l in lines[:6]:
            if 'Quotawise List' in l:
                course_match = re.search(r'In\s+([A-Za-z\.]+)\s+(GOVERNMENT/AIDED|PRIVATE)', l, re.IGNORECASE)
                if course_match:
                    raw_c = course_match.group(1).replace('.', '').upper()
                    current_course = raw_c
                    raw_t = course_match.group(2).upper()
                    current_college_type = 'Government/Aided' if 'GOV' in raw_t else 'Private'
                break
        
        # Find F/L line
        fl_line = None
        fl_idx = -1
        for idx, l in enumerate(lines[:10]):
            if 'F' in l and 'L' in l and len(re.findall(r'[FL]', l)) >= 10:
                fl_line = l
                fl_idx = idx
                break
        
        if not fl_line:
            continue
            
        fl_matches = list(re.finditer(r'[FL]', fl_line))
        centers = [m.start() for m in fl_matches]
        boundaries = [31]
        for i in range(len(centers) - 1):
            boundaries.append((centers[i] + centers[i+1]) // 2)
        boundaries.append(300)
        
        course_id = get_or_create_course(conn, current_course)
        
        i = fl_idx + 1
        while i < len(lines):
            line = lines[i]
            if 'A :' in line:
                a_line = line
                m_line = ''
                if i + 1 < len(lines) and 'M :' in lines[i+1]:
                    m_line = lines[i+1]
                
                prefix = a_line[:a_line.find('A :')].strip()
                m_code = re.search(r'(?:^\d+\s+)?(\d{4,5})\s+(.+)$', prefix)
                if m_code:
                    college_code = m_code.group(1)
                    college_name = m_code.group(2).strip()
                else:
                    college_code = ""
                    college_name = prefix
                    
                if college_code:
                    college_id = get_or_create_college(conn, college_code, college_name, current_college_type)
                    
                    # Group F and L for each category
                    cat_records = {}
                    for c_idx in range(min(len(cols_info), len(boundaries) - 1)):
                        cat, fl = cols_info[c_idx]
                        st = boundaries[c_idx]
                        en = boundaries[c_idx+1]
                        a_val = clean_int(a_line[st:en]) if st < len(a_line) else None
                        m_val = clean_int(m_line[st:en]) if st < len(m_line) else None
                        
                        if cat not in cat_records:
                            cat_records[cat] = {'open_rank': None, 'close_rank': None, 'open_score': None, 'close_score': None}
                        if fl == 'F':
                            cat_records[cat]['open_rank'] = a_val
                            cat_records[cat]['open_score'] = m_val
                        elif fl == 'L':
                            cat_records[cat]['close_rank'] = a_val
                            cat_records[cat]['close_score'] = m_val
                    
                    # Insert into DB
                    for cat, vals in cat_records.items():
                        o_rank = vals['open_rank']
                        c_rank = vals['close_rank']
                        o_score = vals['open_score']
                        c_score = vals['close_score']
                        
                        # Only insert if there's any valid rank/score
                        if o_rank or c_rank or o_score or c_score:
                            base_cat = BASE_CATEGORY_MAP.get(cat, cat)
                            cur = conn.cursor()
                            cur.execute("""
                                INSERT OR REPLACE INTO medical_cutoffs
                                (academic_year, round, college_id, course_id, quota_category, base_category,
                                 opening_rank, closing_rank, opening_score, closing_score, allotted_seats)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (academic_year, round_name, college_id, course_id, cat, base_cat,
                                  o_rank or c_rank, c_rank or o_rank, o_score or c_score, c_score or o_score, 1))
                            total_inserted += 1
            i += 1
            
    conn.commit()
    print(f"  [+] Inserted/Updated {total_inserted} cutoffs for {academic_year}.")


def parse_and_insert_selection_pdf(conn, pdf_path, academic_year, round_name):
    import fitz
    print(f"\n[*] Ingesting Selection List: {pdf_path.name} ({academic_year} {round_name})...")
    doc = fitz.open(str(pdf_path))
    
    # We will accumulate candidate allotments by:
    # (college_code, college_name, course_code, quota) -> list of AIRs
    allotments = {}
    
    for pno in range(len(doc)):
        page_text = doc[pno].get_text()
        for line in page_text.split('\n'):
            tokens = line.split()
            if len(tokens) >= 5 and tokens[0].isdigit() and tokens[1].isdigit() and (len(tokens[2]) == 10 or tokens[2].isdigit()):
                air = int(tokens[1])
                # Find Quota and College Code/Name
                m = re.search(r'([A-Za-z0-9\(\)\.\s]+)\s+(\d{4,5}):([^(\n]+)', line)
                if m:
                    raw_quota = m.group(1).strip()
                    raw_quota = re.sub(r'\(EM[DR]\)', '', raw_quota).strip()
                    q_tokens = raw_quota.split()
                    
                    if not q_tokens:
                        quota = "OPEN"
                    elif q_tokens[-1] == "(W)" and len(q_tokens) >= 2:
                        quota = f"{q_tokens[-2]} (W)"
                    else:
                        quota = q_tokens[-1]
                        
                    code = m.group(2).strip()
                    cname = m.group(3).strip()
                    
                    # Determine course from prefix
                    prefix = code.lstrip('0')[0] if code.lstrip('0') else '1'
                    course = "MBBS"
                    if prefix == '1':
                        course = "MBBS"
                    elif prefix == '2':
                        course = "BDS"
                    elif prefix == '3':
                        course = "BAMS"
                    elif prefix == '4':
                        course = "BHMS"
                    elif prefix == '5':
                        course = "BUMS"
                    elif prefix == '6':
                        course = "BPTH"
                    
                    key = (code, cname, course, quota)
                    if key not in allotments:
                        allotments[key] = []
                    allotments[key].append(air)
                    
    print(f"  [>] Parsed {sum(len(v) for v in allotments.values())} candidates across {len(allotments)} college-quota combinations.")
    
    total_inserted = 0
    cur = conn.cursor()
    for (code, cname, course, quota), airs in allotments.items():
        if not airs:
            continue
        opening_rank = min(airs)
        closing_rank = max(airs)
        seats = len(airs)
        
        # College type inference
        c_type = "Government/Aided"
        uname = cname.upper()
        if any(g in uname for g in ["GMC", "GOVT", "GOVERNMENT", "BJMC", "GSMC", "NAIR", "COOPER", "GRANT"]):
            c_type = "Government/Aided"
        else:
            c_type = "Private"
            
        college_id = get_or_create_college(conn, code, cname, c_type)
        course_id = get_or_create_course(conn, course)
        base_cat = BASE_CATEGORY_MAP.get(quota, "OPEN")
        if quota.startswith("OPEN"):
            base_cat = "OPEN"
        elif quota.startswith("OBC"):
            base_cat = "OBC"
        elif quota.startswith("SC"):
            base_cat = "SC"
        elif quota.startswith("ST"):
            base_cat = "ST"
        elif quota.startswith("EWS"):
            base_cat = "EWS"
        elif quota.startswith("SEBC"):
            base_cat = "SEBC"
        elif quota.startswith("DEF"):
            base_cat = "Defense"
            
        cur.execute("""
            INSERT OR REPLACE INTO medical_cutoffs
            (academic_year, round, college_id, course_id, quota_category, base_category,
             opening_rank, closing_rank, opening_score, closing_score, allotted_seats)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
        """, (academic_year, round_name, college_id, course_id, quota, base_cat, opening_rank, closing_rank, seats))
        total_inserted += 1
        
    conn.commit()
    print(f"  [+] Inserted/Updated {total_inserted} cutoffs for {academic_year} {round_name}.")


def main():
    print("==========================================================")
    print("    Maharashtra NEET Medical Cutoff Database Ingestion     ")
    print("==========================================================")
    t0 = time.time()
    init_medical_database()
    conn = get_medical_connection()
    
    try:
        # 1. Ingest 2024-25 Summary
        f24 = PDF_FOLDER / "2024-25 cut off.pdf"
        if f24.exists():
            parse_and_insert_summary_pdf(conn, f24, "2024-2025", "Round 1")
            
        # 2. Ingest 2025-26 Summary
        f25 = PDF_FOLDER / "2025-26 cut off.pdf"
        if f25.exists():
            parse_and_insert_summary_pdf(conn, f25, "2025-2026", "Round 1")
            
        # 3. Ingest 2026-2027 R1 MBBS BDS
        f26_r1 = PDF_FOLDER / "2026-2027 R1 MBBS BDS.pdf"
        if f26_r1.exists():
            parse_and_insert_selection_pdf(conn, f26_r1, "2026-2027", "Round 1")

        # 4. Ingest 2026-2027 R2 MBBS BDS
        f26_r2 = PDF_FOLDER / "2026-2027 R2 MBBS BDS.pdf"
        if f26_r2.exists():
            parse_and_insert_selection_pdf(conn, f26_r2, "2026-2027", "Round 2")

        # 5. Ingest 2026-2027 R1 BAMS BHMS BDS
        f26_ayush = PDF_FOLDER / "2026-2027 R1 BAMS BHMS BDS.pdf"
        if f26_ayush.exists():
            parse_and_insert_selection_pdf(conn, f26_ayush, "2026-2027", "Round 1")
            
        # Record metadata
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM medical_cutoffs")
        c_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM medical_colleges")
        col_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM medical_courses")
        crs_count = cur.fetchone()[0]
        
        cur.execute("""
            INSERT INTO medical_meta (source_files, total_records, status, message)
            VALUES (?, ?, 'SUCCESS', ?)
        """, (
            "2024-25 cut off.pdf, 2025-26 cut off.pdf, 2026-2027 R1 MBBS BDS.pdf, 2026-2027 R2 MBBS BDS.pdf, 2026-2027 R1 BAMS BHMS BDS.pdf",
            c_count,
            f"Successfully populated {c_count} cutoffs across {col_count} colleges and {crs_count} courses."
        ))
        conn.commit()
        
        print("\n" + "="*58)
        print(f"DATABASE INGESTION COMPLETED IN {round(time.time() - t0, 2)} SECONDS!")
        print(f"Total Colleges: {col_count}")
        print(f"Total Courses:  {crs_count}")
        print(f"Total Cutoffs:  {c_count}")
        print("="*58)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
