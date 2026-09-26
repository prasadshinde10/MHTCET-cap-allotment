"""
Production PDF Importer for MHT-CET CAP Cutoff Datasets.
Integrates PyMuPDF table grid alignment parser directly into the backend framework.
"""
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
from pathlib import Path
import re
import logging

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from app.models.cutoff import Cutoff
from app.models.college import College
from app.models.course import Course
from app.models.cap_round import CapRound
from app.models.import_batch import ImportBatch
from app.models.import_log import ImportLog

logger = logging.getLogger(__name__)

_COL_REGEX = re.compile(r"^(\d{5})\s*-\s*(.+)")
_CRS_REGEX = re.compile(r"^(\d{9,11}[A-Z]?)\s*-\s*(.+)")


@dataclass
class ImportResult:
    """Result of a PDF import operation."""
    pages_processed: int = 0
    records_created: int = 0
    records_rejected: int = 0
    colleges_found: int = 0
    courses_found: int = 0
    warnings: int = 0
    errors: int = 0
    error_details: List[Dict[str, Any]] = field(default_factory=list)


def parse_category_meta(category_code: str) -> str:
    """Parses category code into seat_category."""
    cat = (category_code or "").upper()
    if "OPEN" in cat:
        return "OPEN"
    elif "SEBC" in cat:
        return "SEBC"
    elif any(s in cat for s in ["SCS", "SCH", "SCO", "SC"]):
        return "SC"
    elif any(s in cat for s in ["STS", "STH", "STO", "ST"]):
        return "ST"
    elif "OBC" in cat:
        return "OBC"
    elif any(s in cat for s in ["VJS", "VJH", "VJO", "VJ"]):
        return "VJ"
    elif "NT1" in cat:
        return "NT1"
    elif "NT2" in cat:
        return "NT2"
    elif "NT3" in cat:
        return "NT3"
    elif "EWS" in cat:
        return "EWS"
    elif "TFWS" in cat:
        return "TFWS"
    elif "ORPHAN" in cat:
        return "ORPHAN"
    elif cat == "MI":
        return "Minority"
    return cat


def parse_reservation_level(quota_type: Optional[str], category_code: str) -> str:
    """Parses quota type & category suffix to determine reservation level."""
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
    return "State Level"


def extract_district(college_name: str) -> str:
    """Extracts known district or city from college name."""
    districts = [
        "Mumbai", "Pune", "Nagpur", "Nashik", "Amravati", "Aurangabad", "Chhatrapati Sambhajinagar",
        "Kolhapur", "Solapur", "Thane", "Navi Mumbai", "Sangli", "Satara", "Ahmednagar",
        "Jalgaon", "Dhule", "Nanded", "Latur", "Akola", "Buldhana", "Yavatmal", "Wardha",
        "Chandrapur", "Bhandara", "Gondia", "Gadchiroli", "Parbhani", "Jalna", "Beed",
        "Osmanabad", "Dharashiv", "Ratnagiri", "Sindhudurg", "Raigad", "Palghar", "Nandurbar"
    ]
    name_clean = college_name.replace(",", " ").replace("-", " ")
    for d in districts:
        if re.search(r"\b" + re.escape(d) + r"\b", name_clean, re.IGNORECASE):
            return d
    return "Maharashtra"


class PDFImporter:
    """
    Production PDF Importer.
    Orchestrates ingestion of CAP Round PDFs into backend database tables.
    """

    def __init__(
        self,
        db_session: Session,
        import_batch_id: int,
        file_path: str,
        year: int,
        round_number: int,
        cap_round_id: int,
    ):
        self.db = db_session
        self.batch_id = import_batch_id
        self.file_path = file_path
        self.year = year
        self.round_number = round_number
        self.cap_round_id = cap_round_id

    def process(self) -> ImportResult:
        """Processes the PDF file and inserts cutoff records into the database."""
        logger.info(f"Processing batch {self.batch_id} for file {self.file_path}")
        result = ImportResult()

        pdf_path = Path(self.file_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found at: {self.file_path}")

        doc = fitz.open(str(pdf_path))
        num_pages = len(doc)
        result.pages_processed = num_pages

        # Pre-cache existing colleges and courses to minimize DB queries
        college_cache: Dict[str, College] = {}
        for col in self.db.execute(select(College)).scalars().all():
            college_cache[col.college_code] = col

        course_cache: Dict[tuple, Course] = {}
        for crs in self.db.execute(select(Course)).scalars().all():
            course_cache[(crs.college_id, crs.course_code)] = crs

        new_cutoffs: List[Cutoff] = []
        new_colleges_count = 0
        new_courses_count = 0

        for page_idx in range(num_pages):
            page = doc[page_idx]
            page_text = page.get_text()
            if "Stage" not in page_text:
                continue

            tabs = page.find_tables()
            if not tabs.tables:
                continue

            blocks = page.get_text("blocks")
            page_lines = []
            for b in blocks:
                b_top = b[1]
                for line in b[4].splitlines():
                    line_str = line.strip()
                    if line_str:
                        page_lines.append((b_top, line_str))

            table_list = sorted(tabs.tables, key=lambda t: t.bbox[1])
            prev_table_bottom = 0

            for tab in table_list:
                tab_top = tab.bbox[1]
                tab_bottom = tab.bbox[3]

                current_college_code, current_college_name = None, None
                current_course_code, current_course_name = None, None
                current_status = None
                quota_title = None

                for b_top, ls in page_lines:
                    if b_top < tab_top:
                        col_match = _COL_REGEX.match(ls)
                        if col_match:
                            current_college_code, current_college_name = col_match.group(1), col_match.group(2).strip()
                        crs_match = _CRS_REGEX.match(ls)
                        if crs_match:
                            current_course_code, current_course_name = crs_match.group(1), crs_match.group(2).strip()
                        if ls.startswith("Status:"):
                            st_val = ls.replace("Status:", "").strip()
                            if st_val:
                                current_status = st_val

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

                if not current_college_code or not current_course_code:
                    prev_table_bottom = tab_bottom
                    continue

                status_lower = f"{current_college_name or ''} {current_status or ''}".lower()
                if "government" in status_lower or "govt" in status_lower or "university department" in status_lower:
                    governance_type = "Government"
                else:
                    governance_type = "Private"

                # Ensure College exists in DB
                if current_college_code not in college_cache:
                    district = extract_district(current_college_name)
                    col_obj = College(
                        college_code=current_college_code,
                        college_name=current_college_name,
                        city=district,
                        district=district,
                        college_type="Autonomous" if "autonomous" in status_lower else "Non-Autonomous",
                        funding_type=governance_type,
                        minority_status="Minority" if "minority" in status_lower else "Non-Minority",
                        status="Active"
                    )
                    self.db.add(col_obj)
                    self.db.flush()
                    college_cache[current_college_code] = col_obj
                    new_colleges_count += 1
                col_obj = college_cache[current_college_code]

                # Ensure Course exists in DB
                course_key = (col_obj.id, current_course_code)
                if course_key not in course_cache:
                    crs_obj = Course(
                        college_id=col_obj.id,
                        course_code=current_course_code,
                        course_name=current_course_name or "Engineering Course"
                    )
                    self.db.add(crs_obj)
                    self.db.flush()
                    course_cache[course_key] = crs_obj
                    new_courses_count += 1
                crs_obj = course_cache[course_key]

                df = tab.extract()
                if not df or len(df) < 2:
                    prev_table_bottom = tab_bottom
                    continue

                header = [c.replace("\n", "").strip() if c else "" for c in df[0]]
                is_cutoff_table = False
                if header:
                    if header[0] == "Stage":
                        is_cutoff_table = True
                    elif len(header) > 1 and any(cat in (header[1] or "") for cat in ["OPEN", "SC", "ST", "OBC", "VJ", "NT", "EWS", "TFWS", "SEBC"]):
                        is_cutoff_table = True

                if not is_cutoff_table:
                    prev_table_bottom = tab_bottom
                    continue

                categories = header[1:]

                for row in df[1:]:
                    stage_str = row[0].replace("\n", "").strip() if row[0] else "Stage-I"
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

                            gender = "Ladies" if cat.upper().startswith("L") else "General"

                            cutoff_entry = Cutoff(
                                year=self.year,
                                cap_round_id=self.cap_round_id,
                                course_id=crs_obj.id,
                                import_batch_id=self.batch_id,
                                seat_section=quota_title or reservation_level or "State Level",
                                seat_section_raw=quota_title,
                                category_code=cat,
                                gender=gender,
                                seat_category=seat_category,
                                seat_location=reservation_level,
                                stage=stage_str,
                                merit_number=rank,
                                percentile=perc,
                                source_page=page_idx + 1,
                                source_pdf=pdf_path.name
                            )
                            new_cutoffs.append(cutoff_entry)

                            # Batch commit in chunks of 2,000 for high performance and low memory
                            if len(new_cutoffs) >= 2000:
                                self.db.bulk_save_objects(new_cutoffs)
                                self.db.commit()
                                result.records_created += len(new_cutoffs)
                                new_cutoffs = []

                        except (ValueError, TypeError):
                            result.warnings += 1

                prev_table_bottom = tab_bottom

        # Commit remaining records
        if new_cutoffs:
            self.db.bulk_save_objects(new_cutoffs)
            self.db.commit()
            result.records_created += len(new_cutoffs)

        doc.close()

        result.colleges_found = len(college_cache)
        result.courses_found = len(course_cache)

        # Update CapRound metadata
        cap_round = self.db.get(CapRound, self.cap_round_id)
        if cap_round:
            cap_round.total_records = (cap_round.total_records or 0) + result.records_created
            cap_round.total_pages = num_pages
            cap_round.processing_status = "COMPLETED"
            self.db.commit()

        # Update Batch status
        batch = self.db.get(ImportBatch, self.batch_id)
        if batch:
            batch.status = "COMPLETED"
            batch.pages_processed = result.pages_processed
            batch.records_created = result.records_created
            batch.warning_count = result.warnings
            batch.error_count = result.errors
            batch.completed_at = datetime.now(timezone.utc)
            self.db.commit()

        logger.info(
            f"Batch {self.batch_id} complete: {result.records_created} records created across {result.pages_processed} pages."
        )
        return result
