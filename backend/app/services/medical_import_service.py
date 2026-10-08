"""
Medical Import and Ingestion Service
===================================
Handles uploading, auto-detection, parsing, and ingestion of Medical Cutoff PDFs
into the dedicated medical database (Supabase PostgreSQL in production, and SQLite locally).
Completely isolated from CET, JoSAA, IISER, and BITS.
"""

import os
import re
import time
import uuid
import shutil
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict

import threading
import fitz
from sqlalchemy import text
from app.database import engine

# Global PyMuPDF lock to prevent multi-threaded textpage / C-context corruption
FITZ_LOCK = threading.Lock()
from app.medical_db import (
    get_medical_connection,
    get_medical_db_path,
    init_medical_database,
    wipe_medical_database,
    get_medical_stats,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "storage" / "uploads" / "medical"
BACKUP_DIR = PROJECT_ROOT / "storage" / "backups"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# In-memory background task tracker for live progress telemetry
ACTIVE_MEDICAL_IMPORT_TASKS: Dict[str, Dict[str, Any]] = {}

def get_medical_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Returns task status or None if task_id not found."""
    # Prune tasks older than 1 hour
    now = time.time()
    stale_keys = [
        k for k, v in ACTIVE_MEDICAL_IMPORT_TASKS.items()
        if now - v.get("started_at", now) > 3600
    ]
    for k in stale_keys:
        ACTIVE_MEDICAL_IMPORT_TASKS.pop(k, None)

    return ACTIVE_MEDICAL_IMPORT_TASKS.get(task_id)


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
    "NURSING": ("B.Sc. Nursing", "B.Sc. Nursing", "Nursing (UG)"),
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


def clean_int(val: Any) -> Optional[int]:
    """Extracts clean integer from string or number, ignoring commas and symbols."""
    if val is None:
        return None
    cleaned = re.sub(r'[^\d]', '', str(val))
    return int(cleaned) if cleaned else None


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


def normalize_mcc_college(raw_inst: str) -> Tuple[str, str, Optional[str], str, str]:
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


def infer_maharashtra_city(name: str) -> Optional[str]:
    city_matches = [
        "MUMBAI", "PUNE", "NAGPUR", "NASIK", "NASHIK", "THANE", "SOLAPUR", "MIRAJ", 
        "KOLHAPUR", "AURANGABAD", "CHHATRAPATI SAMBHAJINAGAR", "JALGAON", "DHULE", 
        "SANGLI", "SATARA", "LATUR", "NANDED", "AMRAVATI", "AKOLA", "CHANDRAPUR", 
        "YAVATMAL", "BARAMATI", "ALIBAUG", "RATNAGIRI", "SINDHUDURG", "GONDIA"
    ]
    u = name.upper()
    for cm in city_matches:
        if cm in u:
            return cm.title()
    return None


def detect_medical_pdf(pdf_path: Path) -> Dict[str, str]:
    """
    Auto-detects format, stream type, round, and academic year of a medical cutoff PDF.
    """
    sample_text = ""
    with FITZ_LOCK:
        doc = fitz.open(str(pdf_path))
        try:
            for pno in range(min(5, len(doc))):
                sample_text += " " + doc[pno].get_text()
        finally:
            doc.close()

    st_upper = sample_text.upper()

    # 1. Check if MCC AIQ
    if any(k in st_upper for k in ["MCC", "NEET-UG COUNSELLING SEATS ALLOTMENT", "ALLOTTED QUOTA", "OPEN SEAT QUOTA", "ALL INDIA QUOTA"]):
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

    # 3. Check if Maharashtra Summary Cutoff Matrix
    if any(k in st_upper for k in ["QUOTAWISE LIST", "A :", "M :", "CUT-OFF", "CUTOFF"]):
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


# ==============================================================================
# PARSING ROUTINE 1: Maharashtra Summary Cutoff Matrix (Quotawise F/L Matrix)
# ==============================================================================
def parse_maha_summary_pdf(
    pdf_path: Path,
    academic_year: str,
    round_name: str,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """
    Parses Maharashtra Summary Matrix PDF where each page displays columns SC F, SC L, etc.
    Extracts opening/closing ranks from 'A :' line and marks from 'M :' line.
    """
    with FITZ_LOCK:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
    records = []

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

    try:
        for pno in range(total_pages):
            with FITZ_LOCK:
                page = doc[pno]
                text_content = page.get_text()
            lines = text_content.split('\n')

            if progress_callback:
                progress_callback(pno + 1, total_pages, f"Parsing Summary Matrix page {pno + 1} of {total_pages}...", len(records))

            # Detect Course & Type
            for l in lines[:6]:
                if 'Quotawise List' in l or 'quotawise' in l.lower():
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

            course_meta = COURSE_MAP.get(current_course, (current_course, current_course, "Medical Sciences (UG)"))

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
                        college_code = m_code.group(1).lstrip('0')
                        college_name = m_code.group(2).strip()
                    else:
                        college_code = ""
                        college_name = prefix

                    if college_code:
                        college_name = re.sub(r'\(.*?\)$', '', college_name).strip()
                        city = infer_maharashtra_city(college_name)

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

                        for cat, vals in cat_records.items():
                            o_rank = vals['open_rank']
                            c_rank = vals['close_rank']
                            o_score = vals['open_score']
                            c_score = vals['close_score']

                            if o_rank or c_rank or o_score or c_score:
                                base_cat = BASE_CATEGORY_MAP.get(cat, cat)
                                records.append({
                                    "college_code": college_code,
                                    "college_name": college_name,
                                    "college_type": current_college_type,
                                    "city": city,
                                    "state": "Maharashtra",
                                    "course_code": course_meta[0],
                                    "course_name": course_meta[1],
                                    "degree_type": course_meta[2],
                                    "academic_year": academic_year,
                                    "round": round_name,
                                    "quota_category": cat,
                                    "base_category": base_cat,
                                    "opening_rank": o_rank or c_rank,
                                    "closing_rank": c_rank or o_rank,
                                    "opening_score": o_score or c_score,
                                    "closing_score": c_score or o_score,
                                    "allotted_seats": 1,
                                    "exam_name": "NEET (UG)",
                                    "counselling_type": "state",
                                })
                i += 1
    finally:
        with FITZ_LOCK:
            doc.close()
    return records


# ==============================================================================
# PARSING ROUTINE 2: Maharashtra State Selection List (Individual Allotments)
# ==============================================================================
def parse_maha_selection_pdf(
    pdf_path: Path,
    academic_year: str,
    round_name: str,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """
    Parses Maharashtra State NEET Selection List PDF into cutoffs grouped by college and quota.
    """
    with FITZ_LOCK:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
    allotments = defaultdict(list)
    college_names = {}

    try:
        for pno in range(total_pages):
            with FITZ_LOCK:
                page = doc[pno]
                page_text = page.get_text()

        if progress_callback:
            progress_callback(pno + 1, total_pages, f"Reading candidates on page {pno + 1} of {total_pages}...", len(allotments))

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

                    code = m.group(2).strip().lstrip('0')
                    cname = m.group(3).strip()
                    college_names[code] = cname

                    prefix = code[0] if code else '1'
                    course = "MBBS"
                    if prefix == '1': course = "MBBS"
                    elif prefix == '2': course = "BDS"
                    elif prefix == '3': course = "BAMS"
                    elif prefix == '4': course = "BHMS"
                    elif prefix == '5': course = "BUMS"
                    elif prefix == '6': course = "BPTH"

                    key = (code, course, quota)
                    allotments[key].append(air)

    finally:
        with FITZ_LOCK:
            doc.close()

    records = []
    for (code, course, quota), airs in allotments.items():
        if not airs:
            continue
        cname = college_names.get(code, f"College {code}")
        cname_clean = re.sub(r'\(.*?\)$', '', cname).strip()
        cname_clean = re.sub(r'\s+', ' ', cname_clean)

        uname = cname_clean.upper()
        if any(g in uname for g in ["GMC", "GOVT", "GOVERNMENT", "BJMC", "GSMC", "NAIR", "COOPER", "GRANT"]):
            c_type = "Government/Aided"
        else:
            c_type = "Private"

        city = infer_maharashtra_city(cname_clean)
        course_meta = COURSE_MAP.get(course, (course, course, "Medical Sciences (UG)"))
        base_cat = map_base_category(quota)

        records.append({
            "college_code": code,
            "college_name": cname_clean,
            "college_type": c_type,
            "city": city,
            "state": "Maharashtra",
            "course_code": course_meta[0],
            "course_name": course_meta[1],
            "degree_type": course_meta[2],
            "academic_year": academic_year,
            "round": round_name,
            "quota_category": quota,
            "base_category": base_cat,
            "opening_rank": min(airs),
            "closing_rank": max(airs),
            "opening_score": None,
            "closing_score": None,
            "allotted_seats": len(airs),
            "exam_name": "NEET (UG)",
            "counselling_type": "state",
        })

    return records


# ==============================================================================
# PARSING ROUTINE 3: MCC NEET-UG All India Quota PDF
# ==============================================================================
def parse_mcc_pdf(
    pdf_path: Path,
    academic_year: str,
    round_name: str,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """
    Parses MCC AIQ NEET-UG PDFs (Round 1, Round 2, Round 3) into normalized records.
    """
    with FITZ_LOCK:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
    start_p = 1 if (round_name == "Round 3" and "2025" in pdf_path.name) else 2
    allotments = []

    try:
        for pno in range(start_p, total_pages):
            with FITZ_LOCK:
                page = doc[pno]
            if progress_callback:
                progress_callback(pno + 1, total_pages, f"Extracting MCC records from page {pno + 1} of {total_pages}...", len(allotments))

            rows = []
            try:
                with FITZ_LOCK:
                    tabs = list(page.find_tables())
                    if tabs:
                        rows = tabs[0].extract()
            except Exception as table_err:
                logger.debug(f"find_tables note on page {pno}: {table_err}")
                rows = []

            page_allotments = []
            if rows:
                for r in rows:
                    vals = [str(x).replace('\n', ' ').strip() if x else '' for x in r]
                    if not vals or not vals[0].isdigit():
                        continue

                    if round_name == "Round 1":
                        if len(vals) >= 8 and vals[1].isdigit():
                            rank = int(vals[1])
                            quota, inst, course, cat = vals[2], vals[3], vals[4], vals[5]
                        elif len(vals) >= 7 and vals[0].isdigit():
                            rank = int(vals[0])
                            quota, inst, course, cat = vals[1], vals[2], vals[3], vals[4]
                        else:
                            continue
                        if inst and inst != '-' and course and course != '-':
                            page_allotments.append((rank, inst, course, quota, cat))

                    elif round_name == "Round 2":
                        rank = int(vals[1]) if vals[1].isdigit() else int(vals[0])
                        rem_cols = [c for c in (vals[2:] if vals[1].isdigit() else vals[1:]) if c != '']
                        if len(rem_cols) >= 11:
                            r1_q, r1_i, r1_c, r1_rem = rem_cols[0], rem_cols[1], rem_cols[2], rem_cols[3]
                            r2_q, r2_i, r2_c, r2_cat, r2_cand_cat, r2_opt, r2_rem = rem_cols[4:11]

                            if r2_i and r2_i != '-' and ('Fresh' in r2_rem or 'Upgraded' in r2_rem or 'Retained' in r2_rem):
                                page_allotments.append((rank, r2_i, r2_c, r2_q, r2_cat))
                            elif ('Did not' in r2_rem or 'No Upgradation' in r2_rem or r2_rem == 'Not Allotted.'):
                                if r1_rem == 'Reported' and r1_i and r1_i != '-':
                                    page_allotments.append((rank, r1_i, r1_c, r1_q, 'Open'))

                    elif round_name == "Round 3":
                        rank = int(vals[1]) if vals[1].isdigit() else int(vals[0])
                        rem_cols = [c for c in (vals[2:] if vals[1].isdigit() else vals[1:]) if c != '']
                        if len(rem_cols) >= 15:
                            r1_q, r1_i, r1_c, r1_rem = rem_cols[0], rem_cols[1], rem_cols[2], rem_cols[3]
                            r2_q, r2_i, r2_c, r2_rem = rem_cols[4], rem_cols[5], rem_cols[6], rem_cols[7]
                            r3_q, r3_i, r3_c, r3_cat, r3_cand_cat, r3_opt, r3_rem = rem_cols[8:15]

                            if r3_i and r3_i != '-' and ('Fresh' in r3_rem or 'Upgraded' in r3_rem or 'Retained' in r3_rem):
                                page_allotments.append((rank, r3_i, r3_c, r3_q, r3_cat))
                            elif ('Did not' in r3_rem or 'No Upgradation' in r3_rem or r3_rem == 'Not Allotted.'):
                                if r2_rem in ('Reported', 'Retained') and r2_i and r2_i != '-':
                                    page_allotments.append((rank, r2_i, r2_c, r2_q, 'Open'))
                                elif r1_rem == 'Reported' and r1_i and r1_i != '-':
                                    page_allotments.append((rank, r1_i, r1_c, r1_q, 'Open'))

            # Fallback to text line parser if find_tables produced no allotments
            if not page_allotments:
                try:
                    with FITZ_LOCK:
                        p_text = page.get_text()
                    lines = [l.strip() for l in p_text.split('\n') if l.strip()]
                    i = 0
                    while i < len(lines):
                        if lines[i].isdigit() and i + 5 < len(lines) and lines[i+1].isdigit():
                            rank = int(lines[i+1])
                            quota = lines[i+2]
                            inst = lines[i+3]
                            course = lines[i+4]
                            cat = lines[i+5]
                            if inst and inst != '-' and course and course != '-':
                                page_allotments.append((rank, inst, course, quota, cat))
                            i += 6
                            while i < len(lines) and not (lines[i].isdigit() and i + 1 < len(lines) and lines[i+1].isdigit()):
                                i += 1
                        else:
                            i += 1
                except Exception as text_err:
                    logger.debug(f"text fallback note on MCC page {pno}: {text_err}")

            allotments.extend(page_allotments)

    finally:
        with FITZ_LOCK:
            doc.close()

    grouped = defaultdict(list)
    for rank, inst, course, quota, cat in allotments:
        if not is_valid_mcc_course(course):
            continue
        clean_quota = QUOTA_NAME_MAP.get(quota.strip(), quota.strip())
        norm_cat = cat.strip()
        quota_category = f"{clean_quota} - {norm_cat}"
        base_cat = map_base_category(norm_cat)
        grouped[(inst, course, quota_category, base_cat)].append(rank)

    records = []
    for (inst, course, quota_category, base_cat), ranks in grouped.items():
        cname, ccode, city, st, ctype = normalize_mcc_college(inst)
        norm_course = re.sub(r'\s+', ' ', course).strip().upper()
        course_meta = COURSE_MAP.get(norm_course, (norm_course, norm_course, "Medical Sciences (UG)"))

        records.append({
            "college_code": ccode,
            "college_name": cname,
            "college_type": ctype,
            "city": city,
            "state": st,
            "course_code": course_meta[0],
            "course_name": course_meta[1],
            "degree_type": course_meta[2],
            "academic_year": academic_year,
            "round": round_name,
            "quota_category": quota_category,
            "base_category": base_cat,
            "opening_rank": min(ranks),
            "closing_rank": max(ranks),
            "opening_score": None,
            "closing_score": None,
            "allotted_seats": len(ranks),
            "exam_name": "NEET (UG) - MCC AIQ",
            "counselling_type": "central",
        })

    return records


# ==============================================================================
# DUAL DATABASE INGESTION: PostgreSQL (Supabase) + Local SQLite
# ==============================================================================
def save_medical_records(records: List[Dict[str, Any]], counselling_type: str, progress_callback=None) -> int:
    """
    Saves parsed cutoff records into Supabase PostgreSQL (if active) and SQLite simultaneously.
    """
    if not records:
        return 0

    init_medical_database(counselling_type)

    if progress_callback:
        progress_callback(None, None, f"Upserting {len(records):,} cutoffs into database...", len(records))

    # 1. PostgreSQL (Supabase) Ingestion if dialect is postgresql
    if engine.dialect.name == "postgresql":
        logger.info(f"[Medical Import] Ingesting {len(records):,} records into Supabase PostgreSQL...")
        
        # Deduplicate and upsert colleges
        colleges_to_insert = {}
        for r in records:
            code = r["college_code"]
            if code not in colleges_to_insert:
                colleges_to_insert[code] = {
                    "code": code,
                    "name": r["college_name"],
                    "ctype": r.get("college_type") or "Government/Aided",
                    "city": r.get("city"),
                    "state": r.get("state") or ("Maharashtra" if r["counselling_type"] == "state" else "All India")
                }

        courses_to_insert = {}
        for r in records:
            code = r["course_code"]
            if code not in courses_to_insert:
                courses_to_insert[code] = {
                    "code": code,
                    "name": r["course_name"],
                    "dtype": r.get("degree_type") or "Medical (UG)"
                }

        with engine.begin() as conn:
            # Colleges
            col_map = {}
            for code, c_data in colleges_to_insert.items():
                res = conn.execute(
                    text("""
                        INSERT INTO medical_colleges (college_code, college_name, college_type, city, state)
                        VALUES (:code, :name, :ctype, :city, :state)
                        ON CONFLICT (college_code) DO UPDATE SET
                            college_name = EXCLUDED.college_name,
                            college_type = COALESCE(EXCLUDED.college_type, medical_colleges.college_type),
                            city = COALESCE(EXCLUDED.city, medical_colleges.city)
                        RETURNING id;
                    """),
                    c_data
                )
                col_map[code] = res.scalar()

            # Courses
            crs_map = {}
            for code, crs_data in courses_to_insert.items():
                res = conn.execute(
                    text("""
                        INSERT INTO medical_courses (course_code, course_name, degree_type)
                        VALUES (:code, :name, :dtype)
                        ON CONFLICT (course_code) DO UPDATE SET
                            course_name = EXCLUDED.course_name
                        RETURNING id;
                    """),
                    crs_data
                )
                crs_map[code] = res.scalar()

            # Cutoffs in batches of 500
            cutoff_rows = []
            for r in records:
                c_id = col_map.get(r["college_code"])
                crs_id = crs_map.get(r["course_code"])
                if not c_id or not crs_id:
                    continue
                cutoff_rows.append({
                    "academic_year": r["academic_year"],
                    "round": r["round"],
                    "college_id": c_id,
                    "course_id": crs_id,
                    "quota_category": r["quota_category"],
                    "base_category": r["base_category"],
                    "opening_rank": r.get("opening_rank"),
                    "closing_rank": r.get("closing_rank"),
                    "opening_score": r.get("opening_score"),
                    "closing_score": r.get("closing_score"),
                    "allotted_seats": r.get("allotted_seats", 1),
                    "exam_name": r.get("exam_name", "NEET (UG)"),
                    "counselling_type": r.get("counselling_type", counselling_type),
                })

            chunk_size = 500
            for i in range(0, len(cutoff_rows), chunk_size):
                chunk = cutoff_rows[i:i + chunk_size]
                conn.execute(
                    text("""
                        INSERT INTO medical_cutoffs (
                            academic_year, round, college_id, course_id, quota_category,
                            base_category, opening_rank, closing_rank, opening_score, closing_score,
                            allotted_seats, exam_name, counselling_type
                        )
                        VALUES (
                            :academic_year, :round, :college_id, :course_id, :quota_category,
                            :base_category, :opening_rank, :closing_rank, :opening_score, :closing_score,
                            :allotted_seats, :exam_name, :counselling_type
                        )
                        ON CONFLICT (academic_year, round, college_id, course_id, quota_category)
                        DO UPDATE SET
                            base_category = EXCLUDED.base_category,
                            opening_rank = EXCLUDED.opening_rank,
                            closing_rank = EXCLUDED.closing_rank,
                            opening_score = EXCLUDED.opening_score,
                            closing_score = EXCLUDED.closing_score,
                            allotted_seats = EXCLUDED.allotted_seats,
                            exam_name = EXCLUDED.exam_name,
                            counselling_type = EXCLUDED.counselling_type,
                            updated_at = CURRENT_TIMESTAMP;
                    """),
                    chunk
                )

    # 2. SQLite Ingestion (dedicated medical_central.db or medical_state.db)
    conn_sqlite = get_medical_connection(counselling_type)
    try:
        cur = conn_sqlite.cursor()
        
        # Colleges
        for r in records:
            cur.execute("""
                INSERT INTO medical_colleges (college_code, college_name, college_type, city, state)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (college_code) DO UPDATE SET college_name = excluded.college_name;
            """, (
                r["college_code"],
                r["college_name"],
                r.get("college_type", "Government/Aided"),
                r.get("city"),
                r.get("state", "Maharashtra")
            ))

        cur.execute("SELECT college_code, id FROM medical_colleges")
        s_col_map = {row[0]: row[1] for row in cur.fetchall()}

        # Courses
        for r in records:
            cur.execute("""
                INSERT INTO medical_courses (course_code, course_name, degree_type)
                VALUES (?, ?, ?)
                ON CONFLICT (course_code) DO UPDATE SET course_name = excluded.course_name;
            """, (
                r["course_code"],
                r["course_name"],
                r.get("degree_type", "Medical (UG)")
            ))

        cur.execute("SELECT course_code, id FROM medical_courses")
        s_crs_map = {row[0]: row[1] for row in cur.fetchall()}

        # Cutoffs
        for r in records:
            sc_id = s_col_map.get(r["college_code"])
            scrs_id = s_crs_map.get(r["course_code"])
            if not sc_id or not scrs_id:
                continue

            cur.execute("""
                INSERT INTO medical_cutoffs (
                    academic_year, round, college_id, course_id, quota_category,
                    base_category, opening_rank, closing_rank, opening_score, closing_score,
                    allotted_seats, exam_name, counselling_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (academic_year, round, college_id, course_id, quota_category)
                DO UPDATE SET
                    base_category = excluded.base_category,
                    opening_rank = excluded.opening_rank,
                    closing_rank = excluded.closing_rank,
                    opening_score = excluded.opening_score,
                    closing_score = excluded.closing_score,
                    allotted_seats = excluded.allotted_seats,
                    exam_name = excluded.exam_name,
                    counselling_type = excluded.counselling_type,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                r["academic_year"],
                r["round"],
                sc_id,
                scrs_id,
                r["quota_category"],
                r["base_category"],
                r.get("opening_rank"),
                r.get("closing_rank"),
                r.get("opening_score"),
                r.get("closing_score"),
                r.get("allotted_seats", 1),
                r.get("exam_name", "NEET (UG)"),
                r.get("counselling_type", counselling_type)
            ))
        conn_sqlite.commit()
    finally:
        conn_sqlite.close()

    sync_root_medical_db()
    return len(records)


# ==============================================================================
# BACKGROUND TASK RUNNER: Updates live telemetry at each step
# ==============================================================================
def run_medical_import_task(
    task_id: str,
    file_path: Path,
    academic_year: Optional[str] = None,
    round_name: Optional[str] = None,
    stream_type: Optional[str] = "auto"
):
    """
    Runs asynchronous medical PDF extraction and ingestion with live progress updates.
    """
    task = ACTIVE_MEDICAL_IMPORT_TASKS.get(task_id)
    if not task:
        task = {
            "task_id": task_id,
            "filename": file_path.name,
            "status": "PROCESSING",
            "progress_percent": 0,
            "current_page": 0,
            "total_pages": 0,
            "records_created": 0,
            "current_action": "Initializing PDF parsing...",
            "started_at": time.time(),
            "finished_at": None,
            "error": None,
            "result": None,
        }
        ACTIVE_MEDICAL_IMPORT_TASKS[task_id] = task

    t0 = time.time()
    try:
        task["current_action"] = "Inspecting PDF format and structure..."
        task["status"] = "PROCESSING"
        task["progress_percent"] = 5

        detected = detect_medical_pdf(file_path)

        final_stream = stream_type if stream_type and stream_type != "auto" else detected["stream_type"]
        final_year = academic_year if academic_year and academic_year != "auto" else detected["academic_year"]
        final_round = round_name if round_name and round_name != "auto" else detected["round_name"]

        is_state = final_stream in ("MAHA_SELECTION", "MAHA_SUMMARY") or "state" in (stream_type or "").lower()
        target_counselling = "state" if is_state else "central"

        task["stream_type"] = final_stream
        task["academic_year"] = final_year
        task["round_name"] = final_round
        task["current_action"] = f"Detected {final_stream} format ({final_year} {final_round}). Parsing pages..."

        def progress_cb(cur_page, tot_pages, action_text, records_count=0):
            if tot_pages:
                task["total_pages"] = tot_pages
            if cur_page:
                task["current_page"] = cur_page
                # 5% to 85% is page parsing
                pct = int(5 + (cur_page / tot_pages) * 80)
                task["progress_percent"] = min(85, max(5, pct))
            if action_text:
                task["current_action"] = action_text
            task["records_created"] = records_count

        # Execute extraction based on detected format
        if final_stream == "MAHA_SUMMARY":
            records = parse_maha_summary_pdf(file_path, final_year, final_round, progress_callback=progress_cb)
        elif final_stream == "MAHA_SELECTION":
            records = parse_maha_selection_pdf(file_path, final_year, final_round, progress_callback=progress_cb)
        else:
            records = parse_mcc_pdf(file_path, final_year, final_round, progress_callback=progress_cb)

        task["records_created"] = len(records)
        task["progress_percent"] = 88
        task["current_action"] = f"Extracted {len(records):,} cutoffs. Ingesting into database..."

        records_created = save_medical_records(records, target_counselling, progress_callback=progress_cb)

        stats = get_medical_stats()
        duration = round(time.time() - t0, 2)
        target_db_name = "PostgreSQL (Supabase) + medical_state.db" if target_counselling == "state" else "PostgreSQL (Supabase) + medical_central.db"

        result = {
            "success": True,
            "filename": file_path.name,
            "stream_type": final_stream,
            "target_database": target_db_name,
            "academic_year": final_year,
            "round_name": final_round,
            "records_created": records_created,
            "total_cutoffs": stats.get("cutoff_count", 0),
            "total_colleges": stats.get("college_count", 0),
            "total_courses": stats.get("course_count", 0),
            "duration_seconds": duration,
            "message": f"Successfully parsed {file_path.name} and ingested {records_created:,} cutoffs into database for {final_year} {final_round}."
        }

        task["status"] = "COMPLETED"
        task["progress_percent"] = 100
        task["current_action"] = f"Completed in {duration}s! {records_created:,} records ingested."
        task["finished_at"] = time.time()
        task["result"] = result
        logger.info(f"[Medical Task {task_id}] COMPLETED: {result['message']}")

    except Exception as e:
        logger.exception(f"[Medical Task {task_id}] FAILED: {str(e)}")
        task["status"] = "FAILED"
        task["error"] = str(e)
        task["finished_at"] = time.time()
        task["current_action"] = f"Parsing failed: {str(e)}"


def ingest_medical_file(
    file_path: Path,
    academic_year: Optional[str] = None,
    round_name: Optional[str] = None,
    stream_type: Optional[str] = "auto"
) -> Dict[str, Any]:
    """
    Synchronous fallback for ingesting medical cutoff files.
    """
    task_id = f"sync_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    run_medical_import_task(task_id, file_path, academic_year, round_name, stream_type)
    task = ACTIVE_MEDICAL_IMPORT_TASKS.get(task_id, {})
    if task.get("status") == "FAILED":
        raise RuntimeError(task.get("error", "Medical PDF parsing failed"))
    return task.get("result", {})


def sync_root_medical_db():
    """Syncs backend medical DBs to root directory if available."""
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
    Clears data from dedicated medical database (PostgreSQL and SQLite).
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
    Restores verified medical datasets from storage/backups/ into PostgreSQL and SQLite.
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

    # Also restore into PostgreSQL if engine is PostgreSQL
    if engine.dialect.name == "postgresql":
        from app.medical_db import auto_seed_medical_database_if_empty, wipe_medical_database
        wipe_medical_database(counselling_type)
        auto_seed_medical_database_if_empty()

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
