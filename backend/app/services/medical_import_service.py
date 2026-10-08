"""
Medical Import and Ingestion Service
===================================
Handles uploading, auto-detection, parsing, and ingestion of Medical Cutoff PDFs
into the dedicated medical.db database. Completely isolated from CET, JoSAA, IISER, and BITS.
"""

import os
import re
import time
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import fitz

from app.medical_db import (
    get_medical_connection,
    get_medical_db_path,
    init_medical_database,
    wipe_medical_database,
    get_medical_stats,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "storage" / "uploads" / "medical"
BACKUP_DIR = PROJECT_ROOT / "storage" / "backups"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Quota mapping to clean names for MCC
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

VALID_MCC_COURSES = {
    "MBBS", "BDS", "B.SC NURSING", "B.SC. NURSING", "B.SC.NURSING",
    "B.SC NURSING(FEMALE ONLY)", "BAMS", "BHMS"
}

COURSE_MAP = {
    "MBBS": ("MBBS", "Bachelor of Medicine and Bachelor of Surgery", "Medical (UG)"),
    "BDS": ("BDS", "Bachelor of Dental Surgery", "Dental (UG)"),
    "B.SC NURSING": ("B.Sc. Nursing", "B.Sc. Nursing", "Nursing (UG)"),
    "B.SC. NURSING": ("B.Sc. Nursing", "B.Sc. Nursing", "Nursing (UG)"),
    "B.SC.NURSING": ("B.Sc. Nursing", "B.Sc. Nursing", "Nursing (UG)"),
    "B.SC NURSING(FEMALE ONLY)": ("B.Sc. Nursing", "B.Sc. Nursing (Female)", "Nursing (UG)"),
    "BAMS": ("BAMS", "Bachelor of Ayurvedic Medicine and Surgery", "Ayurveda (UG)"),
    "BHMS": ("BHMS", "Bachelor of Homeopathic Medicine and Surgery", "Homeopathy (UG)"),
    "BUMS": ("BUMS", "Bachelor of Unani Medicine and Surgery", "Unani (UG)"),
    "PT": ("BPTH", "Bachelor of Physiotherapy", "Allied Health Sciences (UG)"),
    "BPTH": ("BPTH", "Bachelor of Physiotherapy", "Allied Health Sciences (UG)"),
    "OT": ("BOTH", "Bachelor of Occupational Therapy", "Allied Health Sciences (UG)"),
    "BOTH": ("BOTH", "Bachelor of Occupational Therapy", "Allied Health Sciences (UG)"),
}

BASE_CATEGORY_MAP = {
    "OPEN": "OPEN", "OPEN (W)": "OPEN", "HOPEN": "OPEN", "HOPENW": "OPEN", "W": "OPEN",
    "OBC": "OBC", "OBC (W)": "OBC", "HOBC": "OBC", "EMOBC": "OBC", "EMOBCW": "OBC", "SOBC": "OBC",
    "EWS": "EWS", "EWS(W)": "EWS", "HEWS": "EWS", "SC": "SC", "SC (W)": "SC", "HSC": "SC",
    "ST": "ST", "ST (W)": "ST", "VJ": "VJ / NT-A", "VJA": "VJ / NT-A", "EMVJA": "VJ / NT-A",
    "NT1": "NT1 (NT-B)", "NTB": "NT1 (NT-B)", "NTB(W)": "NT1 (NT-B)", "EMNTB": "NT1 (NT-B)",
    "NT2": "NT2 (NT-C)", "NTC": "NT2 (NT-C)", "NTC(W)": "NT2 (NT-C)", "EMNTC": "NT2 (NT-C)",
    "NT3": "NT3 (NT-D)", "NTD": "NT3 (NT-D)", "NTD(W)": "NT3 (NT-D)", "EMNTD": "NT3 (NT-D)",
    "SEBC": "SEBC", "SEBC(W)": "SEBC", "HSEBC": "SEBC", "EMSEBC": "SEBC",
    "D1": "Defense", "D2": "Defense", "D3": "Defense", "DEF1": "Defense", "DEF2": "Defense", "DEF3": "Defense",
    "PH": "PwD / PH", "MKB": "MKB", "NRI": "NRI / IQ", "I.Q.": "NRI / IQ", "MINO": "Minority",
}


def map_base_category(cat_str: str) -> str:
    if not cat_str:
        return "OPEN"
    u = cat_str.upper().strip()
    if "ORPHAN" in u:
        return "Orphan"
    if any(p in u for p in ["PWD", "PH", "PHYSICAL"]):
        return "PwD / PH"
    if any(p in u for p in ["DEF", "D1", "D2", "D3"]):
        return "Defense"
    if "SEBC" in u:
        return "SEBC"
    if "OBC" in u or "BC" in u:
        return "OBC"
    if "EWS" in u:
        return "EWS"
    if "SC" in u:
        return "SC"
    if "ST" in u:
        return "ST"
    if any(p in u for p in ["VJA", "VJ", "HVJA"]):
        return "VJ / NT-A"
    if any(p in u for p in ["NT1", "NTB", "HNTB"]):
        return "NT1 (NT-B)"
    if any(p in u for p in ["NT2", "NTC", "HNTC"]):
        return "NT2 (NT-C)"
    if any(p in u for p in ["NT3", "NTD", "HNTD"]):
        return "NT3 (NT-D)"
    if "MKB" in u:
        return "MKB"
    if "MINO" in u or "MUSLIM" in u or "JAIN" in u:
        return "Minority"
    if any(p in u for p in ["NRI", "I.Q."]):
        return "NRI / IQ"
    if any(p in u for p in ["AIQ", "A"]):
        return "AIQ"
    return BASE_CATEGORY_MAP.get(u, "OPEN")


def is_valid_mcc_course(raw_code: str) -> bool:
    if not raw_code:
        return False
    u = re.sub(r'\s+', ' ', raw_code).strip().upper()
    return u in VALID_MCC_COURSES or "MBBS" in u or "BDS" in u or "NURSING" in u


def normalize_mcc_college(raw_inst: str):
    s = raw_inst.strip()
    s = re.sub(r'\(Female Seat only\s*\)', '', s, flags=re.I).strip()
    
    found_state = None
    for st in INDIAN_STATES:
        if re.search(r'\b' + re.escape(st) + r'\b', s, re.I):
            found_state = st.replace('Delhi (NCT)', 'Delhi')
            break
            
    found_city = None
    for ct in COMMON_CITIES:
        if re.search(r'\b' + re.escape(ct) + r'\b', s, re.I):
            found_city = ct
            break
            
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
    cur.execute("SELECT id FROM medical_colleges WHERE college_code = ?", (c_code,))
    row = cur.fetchone()
    if row:
        college_cache[raw_inst] = row[0]
        return row[0]
        
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


def get_or_create_state_college(conn: sqlite3.Connection, code: str, name: str, c_type: str = "Government/Aided") -> int:
    norm_code = code.lstrip('0')
    norm_name = re.sub(r'\s+', ' ', name).strip()
    norm_name = re.sub(r'\(.*?\)$', '', norm_name).strip()
    
    cur = conn.cursor()
    cur.execute("SELECT id FROM medical_colleges WHERE college_code = ?", (norm_code,))
    row = cur.fetchone()
    if row:
        return row[0]
        
    city = None
    city_matches = ["MUMBAI", "PUNE", "NAGPUR", "NASIK", "NASHIK", "THANE", "SOLAPUR", "MIRAJ", 
                    "KOLHAPUR", "AURANGABAD", "CHHATRAPATI SAMBHAJINAGAR", "JALGAON", "DHULE", 
                    "SANGLI", "SATARA", "LATUR", "NANDED", "AMRAVATI", "AKOLA", "CHANDRAPUR"]
    upper_name = norm_name.upper()
    for cm in city_matches:
        if cm in upper_name:
            city = cm.title()
            break
            
    cur.execute("""
        INSERT INTO medical_colleges (college_code, college_name, college_type, city, state)
        VALUES (?, ?, ?, ?, 'Maharashtra')
    """, (norm_code, norm_name, c_type, city))
    return cur.lastrowid


def detect_medical_pdf(pdf_path: Path) -> Dict[str, str]:
    """
    Auto-detects the format, counselling stream, round, and academic year of a medical PDF.
    """
    doc = fitz.open(str(pdf_path))
    sample_text = ""
    for pno in range(min(5, len(doc))):
        sample_text += " " + doc[pno].get_text()
    doc.close()
    
    st_upper = sample_text.upper()
    
    # 1. Check if MCC AIQ
    if any(k in st_upper for k in ["MCC", "NEET-UG COUNSELLING SEATS ALLOTMENT", "ALLOTTED QUOTA", "OPEN SEAT QUOTA", "ALL INDIA QUOTA"]):
        pdf_type = "MCC_AIQ"
        if "ROUND 3" in st_upper:
            round_name = "Round 3"
        elif "ROUND 2" in st_upper:
            round_name = "Round 2"
        else:
            round_name = "Round 1"
            
        year_match = re.search(r'202[4-7]', sample_text)
        if year_match:
            y = int(year_match.group(0))
            academic_year = f"{y}-{y+1}"
        else:
            academic_year = "2026-2027"
            
        return {
            "stream_type": "MCC_AIQ",
            "round_name": round_name,
            "academic_year": academic_year,
            "description": f"MCC NEET-UG All India Quota ({academic_year} {round_name})"
        }
        
    # 2. Check if Maharashtra State Selection List
    if "STATE COMMON ENTRANCE TEST CELL" in st_upper and "SELECTION" in st_upper:
        round_name = "Round 1"
        if "CAP-2" in st_upper or "CAP 2" in st_upper or "ROUND 2" in st_upper:
            round_name = "Round 2"
        elif "CAP-3" in st_upper or "CAP 3" in st_upper or "ROUND 3" in st_upper:
            round_name = "Round 3"
            
        year_match = re.search(r'202[4-7]', sample_text)
        y = int(year_match.group(0)) if year_match else 2026
        academic_year = f"{y}-{y+1}"
        return {
            "stream_type": "MAHA_SELECTION",
            "round_name": round_name,
            "academic_year": academic_year,
            "description": f"Maharashtra State Medical Selection List ({academic_year} {round_name})"
        }
        
    # 3. Check if Maharashtra Summary Cutoffs
    if any(k in st_upper for k in ["A :", "M :", "CUT-OFF", "CUTOFF"]):
        round_name = "Round 1"
        year_match = re.search(r'202[4-7]', sample_text)
        y = int(year_match.group(0)) if year_match else 2026
        academic_year = f"{y}-{y+1}"
        return {
            "stream_type": "MAHA_SUMMARY",
            "round_name": round_name,
            "academic_year": academic_year,
            "description": f"Maharashtra State Medical Summary Cutoff Matrix ({academic_year})"
        }
        
    return {
        "stream_type": "MCC_AIQ",
        "round_name": "Round 1",
        "academic_year": "2026-2027",
        "description": "General Medical Allotment Sheet"
    }


def parse_mcc_pdf_sync(conn: sqlite3.Connection, pdf_path: Path, academic_year: str, round_name: str) -> int:
    """
    Parses MCC NEET-UG PDF synchronously or chunked into medical.db.
    """
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    start_p = 1 if (round_name == "Round 3" and "2025" in pdf_path.name) else 2
    
    allotments = []
    college_cache = {}
    course_cache = {}
    
    for pno in range(start_p, total_pages):
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
                    allotments.append((rank, inst, course, quota, cat))
                    
            elif round_name == "Round 2":
                rank = int(vals[1]) if vals[1].isdigit() else int(vals[0])
                rem_cols = [c for c in (vals[2:] if vals[1].isdigit() else vals[1:]) if c != '']
                if len(rem_cols) < 11:
                    continue
                r1_q, r1_i, r1_c, r1_rem = rem_cols[0], rem_cols[1], rem_cols[2], rem_cols[3]
                r2_q, r2_i, r2_c, r2_cat, r2_cand_cat, r2_opt, r2_rem = rem_cols[4:11]
                
                if r2_i and r2_i != '-' and ('Fresh' in r2_rem or 'Upgraded' in r2_rem or 'Retained' in r2_rem):
                    allotments.append((rank, r2_i, r2_c, r2_q, r2_cat))
                elif ('Did not' in r2_rem or 'No Upgradation' in r2_rem or r2_rem == 'Not Allotted.'):
                    if r1_rem == 'Reported' and r1_i and r1_i != '-':
                        allotments.append((rank, r1_i, r1_c, r1_q, 'Open'))
                        
            elif round_name == "Round 3":
                rank = int(vals[1]) if vals[1].isdigit() else int(vals[0])
                rem_cols = [c for c in (vals[2:] if vals[1].isdigit() else vals[1:]) if c != '']
                if len(rem_cols) < 15:
                    continue
                r1_q, r1_i, r1_c, r1_rem = rem_cols[0], rem_cols[1], rem_cols[2], rem_cols[3]
                r2_q, r2_i, r2_c, r2_rem = rem_cols[4], rem_cols[5], rem_cols[6], rem_cols[7]
                r3_q, r3_i, r3_c, r3_cat, r3_cand_cat, r3_opt, r3_rem = rem_cols[8:15]
                
                if r3_i and r3_i != '-' and ('Fresh' in r3_rem or 'Upgraded' in r3_rem or 'Retained' in r3_rem):
                    allotments.append((rank, r3_i, r3_c, r3_q, r3_cat))
                elif ('Did not' in r3_rem or 'No Upgradation' in r3_rem or r3_rem == 'Not Allotted.'):
                    if r2_rem in ('Reported', 'Retained') and r2_i and r2_i != '-':
                        allotments.append((rank, r2_i, r2_c, r2_q, 'Open'))
                    elif r1_rem == 'Reported' and r1_i and r1_i != '-':
                        allotments.append((rank, r1_i, r1_c, r1_q, 'Open'))
                        
    doc.close()
    
    # Group into cutoffs
    grouped = defaultdict(list)
    for rank, inst, course, quota, cat in allotments:
        if not is_valid_mcc_course(course):
            continue
        clean_quota = QUOTA_NAME_MAP.get(quota.strip(), quota.strip())
        norm_cat = cat.strip()
        quota_category = f"{clean_quota} - {norm_cat}"
        base_cat = map_base_category(norm_cat)
        grouped[(inst, course, quota_category, base_cat)].append(rank)
        
    cur = conn.cursor()
    ingested_count = 0
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
    return ingested_count


def parse_maha_selection_pdf_sync(conn: sqlite3.Connection, pdf_path: Path, academic_year: str, round_name: str) -> int:
    """
    Parses Maharashtra State NEET Selection List PDF into medical.db.
    """
    doc = fitz.open(str(pdf_path))
    allotments = {}
    
    for pno in range(len(doc)):
        page_text = doc[pno].get_text()
        for line in page_text.split('\n'):
            tokens = line.split()
            if len(tokens) >= 5 and tokens[0].isdigit() and tokens[1].isdigit() and (len(tokens[2]) == 10 or tokens[2].isdigit()):
                air = int(tokens[1])
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
                    
                    prefix = code.lstrip('0')[0] if code.lstrip('0') else '1'
                    course = "MBBS"
                    if prefix == '1': course = "MBBS"
                    elif prefix == '2': course = "BDS"
                    elif prefix == '3': course = "BAMS"
                    elif prefix == '4': course = "BHMS"
                    elif prefix == '5': course = "BUMS"
                    elif prefix == '6': course = "BPTH"
                    
                    key = (code, cname, course, quota)
                    if key not in allotments:
                        allotments[key] = []
                    allotments[key].append(air)
    doc.close()
    
    cur = conn.cursor()
    ingested_count = 0
    course_cache = {}
    
    for (code, cname, course, quota), airs in allotments.items():
        if not airs:
            continue
        opening_rank = min(airs)
        closing_rank = max(airs)
        seats = len(airs)
        
        c_type = "Government/Aided"
        uname = cname.upper()
        if any(g in uname for g in ["GMC", "GOVT", "GOVERNMENT", "BJMC", "GSMC", "NAIR", "COOPER", "GRANT"]):
            c_type = "Government/Aided"
        else:
            c_type = "Private"
            
        college_id = get_or_create_state_college(conn, code, cname, c_type)
        course_id = get_or_create_course(conn, course, course_cache)
        base_cat = BASE_CATEGORY_MAP.get(quota, map_base_category(quota))
        
        cur.execute("""
            INSERT INTO medical_cutoffs (
                academic_year, round, college_id, course_id, quota_category,
                base_category, opening_rank, closing_rank, opening_score, closing_score,
                allotted_seats, exam_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, 'NEET (UG)')
            ON CONFLICT(academic_year, round, college_id, course_id, quota_category)
            DO UPDATE SET
                base_category = excluded.base_category,
                opening_rank = excluded.opening_rank,
                closing_rank = excluded.closing_rank,
                allotted_seats = excluded.allotted_seats,
                updated_at = CURRENT_TIMESTAMP;
        """, (academic_year, round_name, college_id, course_id, quota, base_cat, opening_rank, closing_rank, seats))
        ingested_count += 1
        
    conn.commit()
    return ingested_count


def sync_root_medical_db():
    """Syncs backend medical DBs to root directory."""
    try:
        c_backend = get_medical_db_path("central")
        s_backend = get_medical_db_path("state")
        if c_backend.exists():
            shutil.copy2(c_backend, PROJECT_ROOT / "medical_central.db")
        if s_backend.exists():
            shutil.copy2(s_backend, PROJECT_ROOT / "medical_state.db")
    except Exception:
        pass


def wipe_all_medical_data(counselling_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Clears data from dedicated medical_central.db and/or medical_state.db.
    """
    wipe_medical_database(counselling_type)
    sync_root_medical_db()

    target_desc = "All central and state medical"
    if counselling_type:
        c_low = counselling_type.lower()
        if c_low in ("state", "maha", "state_cet"):
            target_desc = "Maharashtra state medical"
        else:
            target_desc = "MCC central medical"

    return {
        "success": True,
        "message": f"{target_desc} cutoffs, colleges, courses, and metadata successfully cleared (100% Wipe)."
    }


def restore_verified_medical_dataset(counselling_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Restores verified medical datasets from storage/backups/ into medical_central.db and medical_state.db.
    """
    c_backup = BACKUP_DIR / "medical_central_backup.db"
    s_backup = BACKUP_DIR / "medical_state_backup.db"
    full_backup = BACKUP_DIR / "medical_backup_full_33613.db"

    # Restore Central DB
    if not counselling_type or counselling_type.lower() not in ("state", "maha", "state_cet"):
        central_db = get_medical_db_path("central")
        if c_backup.exists():
            shutil.copy2(c_backup, central_db)
        elif full_backup.exists():
            shutil.copy2(full_backup, central_db)
            conn = sqlite3.connect(str(central_db))
            conn.execute("DELETE FROM medical_cutoffs WHERE exam_name NOT LIKE '%MCC%'")
            conn.execute("DELETE FROM medical_colleges WHERE id NOT IN (SELECT DISTINCT college_id FROM medical_cutoffs)")
            conn.execute("DELETE FROM medical_courses WHERE id NOT IN (SELECT DISTINCT course_id FROM medical_cutoffs)")
            conn.commit()
            conn.close()

    # Restore State DB
    if not counselling_type or counselling_type.lower() in ("state", "maha", "state_cet"):
        state_db = get_medical_db_path("state")
        if s_backup.exists():
            shutil.copy2(s_backup, state_db)
        elif full_backup.exists():
            shutil.copy2(full_backup, state_db)
            conn = sqlite3.connect(str(state_db))
            conn.execute("DELETE FROM medical_cutoffs WHERE exam_name LIKE '%MCC%'")
            conn.execute("DELETE FROM medical_colleges WHERE id NOT IN (SELECT DISTINCT college_id FROM medical_cutoffs)")
            conn.execute("DELETE FROM medical_courses WHERE id NOT IN (SELECT DISTINCT course_id FROM medical_cutoffs)")
            conn.commit()
            conn.close()

    sync_root_medical_db()

    stats = get_medical_stats()
    return {
        "success": True,
        "message": f"Successfully restored medical datasets! Central MCC: {stats['mcc_cutoff_count']:,} cutoffs | State CET: {stats['state_cutoff_count']:,} cutoffs.",
        "cutoff_count": stats["cutoff_count"],
        "college_count": stats["college_count"],
        "course_count": stats["course_count"],
        "mcc_cutoff_count": stats["mcc_cutoff_count"],
        "state_cutoff_count": stats["state_cutoff_count"],
    }


def ingest_medical_file(
    file_path: Path,
    academic_year: Optional[str] = None,
    round_name: Optional[str] = None,
    stream_type: Optional[str] = "auto"
) -> Dict[str, Any]:
    """
    Auto-detects and ingests a medical cutoff PDF into the appropriate database (medical_central.db or medical_state.db).
    """
    detected = detect_medical_pdf(file_path)

    final_stream = stream_type if stream_type and stream_type != "auto" else detected["stream_type"]
    final_year = academic_year if academic_year and academic_year != "auto" else detected["academic_year"]
    final_round = round_name if round_name and round_name != "auto" else detected["round_name"]

    target_counselling = "state" if final_stream == "MAHA_SELECTION" else "central"
    init_medical_database(target_counselling)

    t0 = time.time()
    conn = get_medical_connection(target_counselling)
    try:
        if final_stream == "MAHA_SELECTION":
            records_created = parse_maha_selection_pdf_sync(conn, file_path, final_year, final_round)
        else:
            records_created = parse_mcc_pdf_sync(conn, file_path, final_year, final_round)

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM medical_cutoffs")
        total_cutoffs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM medical_colleges")
        total_colleges = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM medical_courses")
        total_courses = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO medical_meta (source_files, total_records, status, message)
            VALUES (?, ?, 'SUCCESS', ?)
        """, (
            file_path.name,
            records_created,
            f"Ingested {records_created} records ({final_year} {final_round}) in {time.time() - t0:.2f}s"
        ))
        conn.commit()
    finally:
        conn.close()

    sync_root_medical_db()

    target_db_name = "medical_state.db" if target_counselling == "state" else "medical_central.db"
    return {
        "success": True,
        "filename": file_path.name,
        "stream_type": final_stream,
        "target_database": target_db_name,
        "academic_year": final_year,
        "round_name": final_round,
        "records_created": records_created,
        "total_cutoffs": total_cutoffs,
        "total_colleges": total_colleges,
        "total_courses": total_courses,
        "duration_seconds": round(time.time() - t0, 2),
        "message": f"Successfully parsed {file_path.name} and ingested {records_created:,} cutoffs into {target_db_name} for {final_year} {final_round}."
    }
