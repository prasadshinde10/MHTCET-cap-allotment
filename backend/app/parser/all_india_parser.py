"""
All India CAP Cutoff PDF Parser Module.
Uses PyMuPDF visual word-coordinate parsing to reconstruct All India cutoff table records.
"""
import os
import re
from typing import List, Dict, Any, Tuple

try:
    import fitz as pymupdf
except ImportError:
    import pymupdf

COLUMN_BOUNDS = [
    ('sr_no', 40.0, 85.0),
    ('all_india_merit', 85.0, 165.0),
    ('choice_code', 165.0, 225.0),
    ('institute_name', 225.0, 515.0),
    ('course_name', 515.0, 615.0),
    ('merit_exam', 615.0, 700.0),
    ('type', 700.0, 765.0),
    ('seat_type', 765.0, 830.0)
]

TABLE_Y_MIN = 125.0
TABLE_Y_MAX = 500.0


def validate_record(rec: Dict[str, Any]) -> bool:
    if not isinstance(rec.get("sr_no"), int) or rec["sr_no"] <= 0:
        return False
    if not isinstance(rec.get("merit_rank"), int) or rec["merit_rank"] <= 0:
        return False

    percentile = rec.get("merit_score")
    if percentile is None:
        percentile = rec.get("merit_percentile")
    if not isinstance(percentile, (int, float)) or not (0.0 <= percentile <= 100.0):
        return False

    choice_code = rec.get("choice_code", "").strip()
    if not choice_code or not re.match(r'^\d{9,11}[A-Za-z]?$', choice_code):
        return False

    if not rec.get("institute_name", "").strip():
        return False
    if not rec.get("course_name", "").strip():
        return False

    return True


def parse_page_words(
    words: List[Tuple[float, float, float, float, str, int, int, int]],
    cap_round: int,
    academic_year: str,
    source_file: str,
    page_number: int
) -> List[Dict[str, Any]]:
    records = []
    data_words = [w for w in words if TABLE_Y_MIN <= w[1] <= TABLE_Y_MAX]
    if not data_words:
        return records

    sr_words = [w for w in data_words if 40.0 <= w[0] <= 85.0 and w[4].replace(',', '').isdigit()]
    sr_words.sort(key=lambda w: w[1])

    if not sr_words:
        return records

    for idx, sr_w in enumerate(sr_words):
        y_top = sr_w[1] - 4.0
        y_bottom = sr_words[idx + 1][1] - 4.0 if idx + 1 < len(sr_words) else TABLE_Y_MAX

        row_words = [w for w in data_words if y_top <= w[1] < y_bottom]

        col_texts = {}
        for cname, xmin, xmax in COLUMN_BOUNDS:
            cwords = [w for w in row_words if xmin <= w[0] < xmax]
            cwords.sort(key=lambda w: (round(w[1], 1), w[0]))
            col_texts[cname] = ' '.join(w[4] for w in cwords).strip()

        sr_no_clean = col_texts['sr_no'].replace(',', '')
        sr_no = int(sr_no_clean) if sr_no_clean.isdigit() else None

        merit_str = col_texts['all_india_merit'].replace(',', '')
        merit_rank = None
        merit_score = None

        m_match = re.search(r'(\d+)\s*\(([\d\.]+)\)', merit_str)
        if m_match:
            merit_rank = int(m_match.group(1))
            merit_score = float(m_match.group(2))
        elif merit_str.isdigit():
            merit_rank = int(merit_str)

        choice_code = col_texts['choice_code'].replace(',', '').strip()

        inst_raw = col_texts['institute_name']
        code_match = re.match(r'^(\d{5})\s*-\s*(.*)', inst_raw)
        if code_match:
            institute_code = code_match.group(1)
            institute_name = code_match.group(2).strip()
        else:
            institute_code = choice_code[:5] if len(choice_code) >= 5 else ""
            institute_name = inst_raw.strip()

        course_name = col_texts['course_name'].strip()
        merit_exam = col_texts['merit_exam'] or 'JEE (Main)'
        type_str = col_texts['type'] or 'AI to AI'
        seat_type = col_texts['seat_type'] or 'AI'

        if re.search(r'\b\d{4}\b', type_str):
            year_match = re.search(r'\b(\d{4})\b', type_str)
            if year_match:
                year_val = year_match.group(1)
                if year_val not in merit_exam:
                    merit_exam = f"{merit_exam} {year_val}".strip()
            recovered_type = None
            for vt in ['AI to AI', 'MI to AI', 'MH to AI', 'MH-AI']:
                if any(vt in w[4] for w in row_words):
                    recovered_type = vt
                    break
            type_str = recovered_type or 'AI to AI'

        rec = {
            "cap_round": cap_round,
            "academic_year": academic_year,
            "sr_no": sr_no,
            "merit_rank": merit_rank,
            "merit_score": merit_score,
            "merit_percentile": merit_score,
            "choice_code": choice_code,
            "institute_code": institute_code,
            "institute_name": institute_name,
            "course_name": course_name or "Engineering",
            "merit_exam": merit_exam,
            "type": type_str,
            "seat_type": seat_type,
            "source_file": source_file,
            "source_pdf": source_file,
            "page_number": page_number
        }

        if validate_record(rec):
            records.append(rec)

    return records


def parse_all_india_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    filename = os.path.basename(pdf_path)
    cap_round = 1
    match = re.search(r'CAP\s*(\d+)', filename, re.IGNORECASE)
    if match:
        cap_round = int(match.group(1))

    doc = pymupdf.open(pdf_path)
    all_records = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        words = page.get_text("words")
        recs = parse_page_words(words, cap_round, '2026-27', filename, page_idx + 1)
        all_records.extend(recs)
    return all_records
