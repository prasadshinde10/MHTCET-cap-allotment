"""
Production PDF Importer for MHT-CET CAP Cutoff Datasets.
Integrates PyMuPDF table grid alignment parser directly into the backend framework.
"""
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
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
from app.parser.institutes_data import INSTITUTES_DATA

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
    Supports both Maharashtra State Seats (grid format) and All India Seats (table coordinate format).
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

    @staticmethod
    def is_all_india_pdf(doc: fitz.Document, filename: str = "") -> bool:
        """Detects if the PDF is an All India Cutoff list rather than Maharashtra State list."""
        fn = filename.lower()
        if "ai_cutoff" in fn or "all_india" in fn or "allindia" in fn:
            return True
        for i in range(min(3, len(doc))):
            txt = doc[i].get_text()
            if "All India Seats" in txt or "All India Merit" in txt:
                return True
        return False

    def _sync_all_india_raw_table(self, records: List[Dict[str, Any]]):
        """Syncs parsed records to the all_india_cutoff_records table."""
        if not records:
            return
        try:
            from sqlalchemy import text
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS all_india_cutoff_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cap_round INTEGER NOT NULL,
                    academic_year TEXT,
                    sr_no INTEGER,
                    merit_rank INTEGER NOT NULL,
                    merit_percentile REAL NOT NULL,
                    choice_code TEXT NOT NULL,
                    college_code TEXT NOT NULL,
                    college_name TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    merit_exam TEXT,
                    type TEXT,
                    seat_type TEXT,
                    source_pdf TEXT,
                    page_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            for r in records:
                self.db.execute(text("""
                    INSERT INTO all_india_cutoff_records (
                        cap_round, academic_year, sr_no, merit_rank, merit_percentile,
                        choice_code, college_code, college_name, course_name,
                        merit_exam, type, seat_type, source_pdf, page_number
                    ) VALUES (
                        :cap_round, :academic_year, :sr_no, :merit_rank, :merit_percentile,
                        :choice_code, :college_code, :college_name, :course_name,
                        :merit_exam, :type, :seat_type, :source_pdf, :page_number
                    )
                """), {
                    "cap_round": r["cap_round"],
                    "academic_year": r["academic_year"],
                    "sr_no": r["sr_no"],
                    "merit_rank": r["merit_rank"],
                    "merit_percentile": r["merit_percentile"],
                    "choice_code": r["choice_code"],
                    "college_code": r["institute_code"],
                    "college_name": r["institute_name"],
                    "course_name": r["course_name"],
                    "merit_exam": r.get("merit_exam"),
                    "type": r.get("type"),
                    "seat_type": r.get("seat_type"),
                    "source_pdf": r.get("source_pdf"),
                    "page_number": r.get("page_number")
                })
            self.db.commit()
        except Exception as e:
            logger.warning(f"Could not sync all_india_cutoff_records table: {e}")

    def _process_all_india(
        self,
        doc: fitz.Document,
        pdf_path: Path,
        result: ImportResult,
        college_cache: Dict[str, College],
        course_cache: Dict[tuple, Course]
    ) -> ImportResult:
        """Parses and ingests All India cutoff PDFs using coordinate bounds extraction."""
        from app.parser.all_india_parser import parse_page_words

        num_pages = len(doc)
        result.pages_processed = num_pages

        new_cutoffs: List[Cutoff] = []
        raw_ai_records: List[Dict[str, Any]] = []
        acad_year = f"{self.year}-{str(self.year + 1)[-2:]}"

        for page_idx in range(num_pages):
            page = doc[page_idx]
            words = page.get_text("words")
            if not words:
                continue

            page_recs = parse_page_words(
                words=words,
                cap_round=self.round_number,
                academic_year=acad_year,
                source_file=pdf_path.name,
                page_number=page_idx + 1
            )

            for rec in page_recs:
                inst_code = str(rec.get("institute_code", "")).strip()
                inst_name = rec.get("institute_name", "").strip()
                choice_code = str(rec.get("choice_code", "")).strip()
                course_name = rec.get("course_name", "").strip() or "Engineering Course"

                if not inst_code or not choice_code:
                    continue

                # 1. Resolve College (enrich from verified INSTITUTES_DATA master dictionary)
                if inst_code not in college_cache:
                    inst_meta = INSTITUTES_DATA.get(inst_code.zfill(5))
                    status_lower = inst_name.lower()
                    if inst_meta:
                        col_district = inst_meta.get("district") or extract_district(inst_name)
                        col_type = inst_meta.get("college_type") or ("Autonomous" if "autonomous" in status_lower else "Non-Autonomous")
                        col_funding = inst_meta.get("funding_type") or ("Government" if any(k in status_lower for k in ["government", "govt", "university department"]) else "Private")
                        col_minority = inst_meta.get("minority_status") or ("Minority" if "minority" in status_lower else "Non-Minority")
                        col_univ = inst_meta.get("home_university") or ""
                        col_name = inst_meta.get("name") or inst_name
                    else:
                        col_district = extract_district(inst_name)
                        col_type = "Autonomous" if "autonomous" in status_lower else "Non-Autonomous"
                        col_funding = "Government" if any(k in status_lower for k in ["government", "govt", "university department"]) else "Private"
                        col_minority = "Minority" if "minority" in status_lower else "Non-Minority"
                        col_univ = ""
                        col_name = inst_name

                    col_obj = College(
                        college_code=inst_code,
                        college_name=col_name,
                        city=col_district,
                        district=col_district,
                        college_type=col_type,
                        funding_type=col_funding,
                        minority_status=col_minority,
                        home_university=col_univ,
                        status="Active"
                    )
                    self.db.add(col_obj)
                    self.db.flush()
                    college_cache[inst_code] = col_obj

                col_obj = college_cache[inst_code]

                # 2. Resolve Course
                course_key = (col_obj.id, choice_code)
                if course_key not in course_cache:
                    crs_obj = Course(
                        college_id=col_obj.id,
                        course_code=choice_code,
                        course_name=course_name
                    )
                    self.db.add(crs_obj)
                    self.db.flush()
                    course_cache[course_key] = crs_obj

                crs_obj = course_cache[course_key]

                # 3. Create Cutoff record
                cutoff_entry = Cutoff(
                    year=self.year,
                    cap_round_id=self.cap_round_id,
                    course_id=crs_obj.id,
                    import_batch_id=self.batch_id,
                    seat_section="All India Seats (AI)",
                    seat_section_raw=rec.get("seat_type") or "AI",
                    category_code="AI",
                    gender="General",
                    seat_category=rec.get("seat_type") or "AI",
                    seat_location="All India",
                    stage="AI",
                    merit_number=rec.get("merit_rank"),
                    percentile=rec.get("merit_percentile"),
                    source_page=rec.get("page_number", page_idx + 1),
                    source_pdf=pdf_path.name
                )
                new_cutoffs.append(cutoff_entry)
                raw_ai_records.append(rec)

                if len(new_cutoffs) >= 2000:
                    self.db.bulk_save_objects(new_cutoffs)
                    self.db.commit()
                    result.records_created += len(new_cutoffs)
                    new_cutoffs = []

        if new_cutoffs:
            self.db.bulk_save_objects(new_cutoffs)
            self.db.commit()
            result.records_created += len(new_cutoffs)

        # Sync raw table
        self._sync_all_india_raw_table(raw_ai_records)
        doc.close()

        result.colleges_found = len(college_cache)
        result.courses_found = len(course_cache)

        # Update CapRound metadata
        cap_round = self.db.get(CapRound, self.cap_round_id)
        if cap_round:
            total_for_round = self.db.query(func.count(Cutoff.id)).filter(Cutoff.cap_round_id == self.cap_round_id).scalar() or 0
            cap_round.total_records = total_for_round
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
            f"All India Batch {self.batch_id} complete: {result.records_created} records created across {result.pages_processed} pages."
        )
        return result

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

        # Route to All India ingestion if document is All India Cutoff PDF
        if self.is_all_india_pdf(doc, pdf_path.name):
            logger.info(f"Detected All India Cutoff PDF for batch {self.batch_id}. Invoking All India extractor.")
            return self._process_all_india(doc, pdf_path, result, college_cache, course_cache)

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

                for idx_line, (b_top, ls) in enumerate(page_lines):
                    if b_top < tab_top:
                        col_match = _COL_REGEX.match(ls)
                        if col_match:
                            current_college_code, current_college_name = col_match.group(1), col_match.group(2).strip()
                        crs_match = _CRS_REGEX.match(ls)
                        if crs_match:
                            current_course_code, current_course_name = crs_match.group(1), crs_match.group(2).strip()
                        if ls.startswith("Status:"):
                            st_val = ls.replace("Status:", "").strip()
                            if not st_val and idx_line + 1 < len(page_lines):
                                next_top, next_ls = page_lines[idx_line + 1]
                                if next_top < tab_top and not next_ls.startswith("Stage"):
                                    st_val = next_ls
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
                    inst_meta = INSTITUTES_DATA.get(str(current_college_code).zfill(5))
                    if inst_meta:
                        col_district = inst_meta.get("district") or "Maharashtra"
                        col_type = inst_meta.get("college_type") or ("Autonomous" if "autonomous" in status_lower else "Non-Autonomous")
                        col_funding = inst_meta.get("funding_type") or governance_type
                        col_minority = inst_meta.get("minority_status") or ("Minority" if "minority" in status_lower else "Non-Minority")
                        col_univ = inst_meta.get("home_university") or ""
                        col_name = inst_meta.get("name") or current_college_name
                    else:
                        col_district = extract_district(current_college_name)
                        col_type = "Autonomous" if "autonomous" in status_lower else "Non-Autonomous"
                        col_funding = governance_type
                        col_minority = "Minority" if "minority" in status_lower else "Non-Minority"
                        col_univ = ""
                        col_name = current_college_name

                    col_obj = College(
                        college_code=current_college_code,
                        college_name=col_name,
                        city=col_district,
                        district=col_district,
                        college_type=col_type,
                        funding_type=col_funding,
                        minority_status=col_minority,
                        home_university=col_univ,
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
