"""
PDF Import Orchestrator for MHT-CET CAP cutoff PDFs.

This is the main module that coordinates the full PDF → staging pipeline.
It processes pages sequentially, maintaining parser state across pages,
and handles the VERTICAL layout of the actual PDFs.

Processing flow for each page:
1. Skip page headers (Dir, State Common Entrance Test Cell, etc.)
2. Detect college header → update state
3. Detect course header → update state
4. Skip status line
5. Detect seat section → update state, reset categories
6. Collect category codes (one per line) into a list
7. When stage line is detected, start cutoff block parsing
8. Parse merit/percentile pairs mapped to categories in order
9. On "Stage" end marker, flush records
10. On new section/course/college, flush and reset as appropriate
"""
from dataclasses import dataclass, field
from typing import Any
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import hashlib
import logging

from app.parser.pdf_loader import PDFLoader
from app.parser.state_machine import ParserState
from app.parser.college_parser import CollegeParser
from app.parser.course_parser import CourseParser
from app.parser.section_parser import SectionParser
from app.parser.category_parser import CategoryParser
from app.parser.cutoff_parser import CutoffBlockParser
from app.parser.normalizer import CategoryNormalizer
from app.parser.validator import RecordValidator
from app.parser.patterns import (
    PAGE_HEADER_PATTERNS,
    STATUS_PATTERN,
    STATUS_LINE_PATTERN,
    LEGEND_PATTERN,
    STAGE_LABEL_PATTERN,
    STAGE_PATTERN,
    MERIT_NUMBER_PATTERN,
    PERCENTILE_PATTERN,
    PAGE_NUMBER_PATTERN,
)
from app.models.staging_cutoff import StagingCutoff
from app.models.import_log import ImportLog
from app.models.parser_error import ParserError
from app.models.import_batch import ImportBatch
from app.models.college import College
from app.models.course import Course

logger = logging.getLogger(__name__)


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
    error_details: list[dict[str, Any]] = field(default_factory=list)


class PDFImporter:
    """
    Main PDF import orchestrator.

    Processes an MHT-CET CAP cutoff PDF page-by-page, extracting
    structured cutoff data and inserting into staging tables.
    """

    # Parser phases within a section
    PHASE_EXPECTING_CATEGORIES = "EXPECTING_CATEGORIES"
    PHASE_IN_CUTOFF_BLOCK = "IN_CUTOFF_BLOCK"
    PHASE_IDLE = "IDLE"

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

        self.state = ParserState()
        self.normalizer = CategoryNormalizer()
        self.staging_buffer: list[dict[str, Any]] = []
        self.batch_size = 500
        self.result = ImportResult()

        self._phase = self.PHASE_IDLE
        self._collecting_categories: list[str] = []
        self._cutoff_block: CutoffBlockParser | None = None
        self.colleges_map: dict[str, str] = {}
        self.courses_map: dict[str, tuple[str, str]] = {}

    def process(self) -> ImportResult:
        """Main entry point — process the full PDF."""
        self._log("INFO", f"Starting import of {self.file_path}", 0)

        with PDFLoader(self.file_path) as loader:
            page_count = loader.get_page_count()
            self._log("INFO", f"PDF has {page_count} pages", 0)

            for page_num in range(1, page_count + 1):
                self.state.page_number = page_num
                text = loader.get_page_text(page_num)

                try:
                    self._process_page(page_num, text)
                except Exception as e:
                    logger.error(f"Error processing page {page_num}: {e}")
                    self._record_error(
                        page_num, "PAGE_PROCESSING_ERROR", "ERROR",
                        text[:500] if text else "",
                        f"Unexpected error processing page: {str(e)}",
                    )
                    self.result.errors += 1

                # Batch insert periodically
                if len(self.staging_buffer) >= self.batch_size:
                    self._flush_staging_buffer()

                self.result.pages_processed = page_num

                # Progress logging every 100 pages
                if page_num % 100 == 0:
                    self._log("INFO", f"Processed {page_num}/{page_count} pages, {self.result.records_created} records", page_num)

                # Update import batch progress
                self._update_batch_progress(page_num, page_count)

            # Final flush
            if self.staging_buffer:
                self._flush_staging_buffer()

        # Sync discovered college and course names
        self._sync_colleges_and_courses()

        self.result.colleges_found = len(self.state.colleges_found)
        self.result.courses_found = len(self.state.courses_found)

        self._log(
            "INFO",
            f"Import complete: {self.result.pages_processed} pages, "
            f"{self.result.records_created} records, "
            f"{self.result.errors} errors, "
            f"{self.result.warnings} warnings",
            0,
        )

        return self.result

    def _sync_colleges_and_courses(self):
        """Create or update College and Course metadata from extracted names."""
        try:
            for code, name in self.colleges_map.items():
                college = self.db.query(College).filter(College.college_code == code).first()
                if college:
                    if name and (college.college_name.startswith("College ") or not college.college_name):
                        college.college_name = name
                else:
                    college = College(college_code=code, college_name=name or f"College {code}")
                    self.db.add(college)
            self.db.flush()

            for course_code, (course_name, college_code) in self.courses_map.items():
                if not college_code:
                    continue
                college = self.db.query(College).filter(College.college_code == college_code).first()
                if college:
                    course = self.db.query(Course).filter(Course.college_id == college.id, Course.course_code == course_code).first()
                    if course:
                        if course_name and (course.course_name.startswith("Course ") or not course.course_name):
                            course.course_name = course_name
                    else:
                        course = Course(college_id=college.id, course_code=course_code, course_name=course_name or f"Course {course_code}")
                        self.db.add(course)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error syncing colleges and courses: {e}")

    def _process_page(self, page_number: int, text: str):
        """Process a single page of the PDF."""
        if not text or not text.strip():
            return

        lines = text.split('\n')

        for line in lines:
            self._process_line(line, page_number)

    def _process_line(self, line: str, page_number: int):
        """Process a single line, updating parser state and extracting records."""
        raw_line = line
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            return

        # Skip page headers
        for pattern in PAGE_HEADER_PATTERNS:
            if pattern.match(stripped):
                return

        # Skip status lines
        if STATUS_PATTERN.match(stripped):
            return
        if STATUS_LINE_PATTERN.match(stripped):
            return

        # Skip legend
        if LEGEND_PATTERN.match(stripped):
            return

        # Skip standalone page numbers at the bottom
        if PAGE_NUMBER_PATTERN.match(stripped) and len(stripped) <= 4:
            # Might be a page number, but also could be a merit number.
            # Only skip if we're not in a cutoff block
            if self._phase != self.PHASE_IN_CUTOFF_BLOCK:
                return

        # Check for "Stage" end marker — this ends a cutoff block
        if STAGE_LABEL_PATTERN.match(line):
            if self._cutoff_block:
                self._cutoff_block.feed_line(line)
                self._flush_cutoff_block(page_number)
            self._phase = self.PHASE_IDLE
            return

        # Check for college header
        college_match = CollegeParser.parse_line(stripped)
        if college_match:
            self._flush_cutoff_block(page_number)
            self.state.set_college(college_match[0], college_match[1])
            self.colleges_map[college_match[0]] = college_match[1]
            self._phase = self.PHASE_IDLE
            self._collecting_categories = []
            return

        # Check for course header
        course_match = CourseParser.parse_line(stripped)
        if course_match:
            self._flush_cutoff_block(page_number)
            self.state.set_course(course_match[0], course_match[1])
            self.courses_map[course_match[0]] = (course_match[1], self.state.current_college_code or "")
            self._phase = self.PHASE_IDLE
            self._collecting_categories = []
            return

        # Check for seat section
        section_match = SectionParser.parse_line(stripped)
        if section_match:
            self._flush_cutoff_block(page_number)
            self.state.set_section(section_match[0], section_match[1])
            self._phase = self.PHASE_EXPECTING_CATEGORIES
            self._collecting_categories = []
            return

        # If we're expecting categories, try to collect them
        if self._phase == self.PHASE_EXPECTING_CATEGORIES:
            cat_code = CategoryParser.parse_line(stripped)
            if cat_code:
                self._collecting_categories.append(cat_code)
                return
            else:
                # Not a category code — might be a stage line starting cutoff data
                if self._collecting_categories:
                    self.state.set_categories(self._collecting_categories)
                    self._start_cutoff_block()

        # If we're in a cutoff block, feed lines to the block parser
        if self._phase == self.PHASE_IN_CUTOFF_BLOCK and self._cutoff_block:
            # Check if this line starts a new section/course/college
            # (which would mean the "Stage" end marker was missing)
            stage_match = STAGE_PATTERN.match(line)
            merit_match = MERIT_NUMBER_PATTERN.match(stripped)
            perc_match = PERCENTILE_PATTERN.match(stripped)

            if stage_match or merit_match or perc_match:
                self._cutoff_block.feed_line(line)
                return

            # If line doesn't match cutoff data, the block might be over
            # Try to see if it's a new section or category
            cat_code = CategoryParser.parse_line(stripped)
            if cat_code:
                # New categories starting — flush current block
                self._flush_cutoff_block(page_number)
                self._phase = self.PHASE_EXPECTING_CATEGORIES
                self._collecting_categories = [cat_code]
                return

            section_re_match = SectionParser.parse_line(stripped)
            if section_re_match:
                self._flush_cutoff_block(page_number)
                self.state.set_section(section_re_match[0], section_re_match[1])
                self._phase = self.PHASE_EXPECTING_CATEGORIES
                self._collecting_categories = []
                return

        # If we were collecting categories and hit a stage line, start cutoff block
        if self._phase == self.PHASE_EXPECTING_CATEGORIES:
            stage_match = STAGE_PATTERN.match(line)
            if stage_match and self._collecting_categories:
                self.state.set_categories(self._collecting_categories)
                self._start_cutoff_block()
                self._cutoff_block.feed_line(line)
                return

    def _start_cutoff_block(self):
        """Initialize a new cutoff block parser."""
        self._cutoff_block = CutoffBlockParser(
            categories=list(self.state.current_categories)
        )
        self._phase = self.PHASE_IN_CUTOFF_BLOCK

    def _flush_cutoff_block(self, page_number: int):
        """Flush the current cutoff block, creating staging records."""
        if not self._cutoff_block:
            return

        records = self._cutoff_block.get_records()

        for rec in records:
            if not self.state.current_college_code or not self.state.current_course_code:
                self._record_error(
                    page_number, "MISSING_CONTEXT", "WARNING",
                    f"{rec.category_code} {rec.stage} {rec.merit_number}",
                    "Cutoff record found without college/course context",
                )
                self.result.warnings += 1
                continue

            # Normalize category
            norm = self.normalizer.normalize(rec.category_code)

            record_dict = {
                "import_batch_id": self.batch_id,
                "cap_round_id": self.cap_round_id,
                "year": self.year,
                "college_code": self.state.current_college_code,
                "course_code": self.state.current_course_code,
                "seat_section": self.state.current_seat_section or "UNKNOWN",
                "seat_section_raw": self.state.current_seat_section_raw,
                "category_code": rec.category_code,
                "gender": norm.get("gender"),
                "seat_category": norm.get("seat_category"),
                "seat_location": norm.get("seat_location"),
                "stage": rec.stage,
                "merit_number": rec.merit_number,
                "percentile": rec.percentile,
                "source_page": page_number,
                "source_pdf": self.file_path,
            }

            # Validate
            is_valid, errors = RecordValidator.validate_cutoff(record_dict)
            if is_valid:
                self.staging_buffer.append(record_dict)
                self.result.records_created += 1
            else:
                self._record_error(
                    page_number, "VALIDATION_ERROR", "WARNING",
                    f"{rec.category_code} {rec.stage} {rec.merit_number} ({rec.percentile})",
                    f"Validation errors: {', '.join(errors)}",
                )
                self.result.records_rejected += 1
                self.result.warnings += 1

        self._cutoff_block = None

    def _flush_staging_buffer(self):
        """Batch insert staging records into the database."""
        if not self.staging_buffer:
            return

        try:
            staging_objects = []
            for rec in self.staging_buffer:
                staging_obj = StagingCutoff(
                    import_batch_id=rec["import_batch_id"],
                    cap_round_id=rec["cap_round_id"],
                    year=rec["year"],
                    college_code=rec.get("college_code", ""),
                    course_code=rec.get("course_code", ""),
                    seat_section=rec["seat_section"],
                    seat_section_raw=rec.get("seat_section_raw"),
                    category_code=rec["category_code"],
                    gender=rec.get("gender"),
                    seat_category=rec.get("seat_category"),
                    seat_location=rec.get("seat_location"),
                    stage=rec["stage"],
                    merit_number=rec.get("merit_number"),
                    percentile=rec.get("percentile"),
                    source_page=rec.get("source_page"),
                    source_pdf=rec.get("source_pdf"),
                    validation_status="VALID",
                )
                staging_objects.append(staging_obj)

            self.db.bulk_save_objects(staging_objects)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error flushing staging buffer: {e}")
            self.db.rollback()
            self.result.errors += 1
            self._record_error(
                self.state.page_number, "DB_INSERT_ERROR", "ERROR",
                "", f"Failed to insert batch of {len(self.staging_buffer)} records: {str(e)}",
            )

        self.staging_buffer.clear()

    def _log(self, level: str, message: str, page_number: int, context: dict | None = None):
        """Create an import log record."""
        try:
            log = ImportLog(
                import_batch_id=self.batch_id,
                level=level,
                message=message,
                page_number=page_number if page_number > 0 else None,
                context=context,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to write import log: {e}")

    def _record_error(
        self, page: int, error_type: str, severity: str,
        raw_text: str, message: str, context: dict | None = None,
    ):
        """Create a parser error record."""
        err_detail = {
            "page": page,
            "error_type": error_type,
            "severity": severity,
            "raw_text": raw_text[:1000] if raw_text else "",
            "message": message,
        }
        self.result.error_details.append(err_detail)

        try:
            error = ParserError(
                import_batch_id=self.batch_id,
                source_page=page,
                error_type=error_type,
                severity=severity,
                raw_text=raw_text[:2000] if raw_text else None,
                error_message=message,
                college_code=self.state.current_college_code,
                course_code=self.state.current_course_code,
                status="OPEN",
                context=context or self.state.to_context_dict(),
            )
            self.db.add(error)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to write parser error: {e}")

    def _update_batch_progress(self, current_page: int, total_pages: int):
        """Update the import batch with current progress."""
        try:
            batch = self.db.query(ImportBatch).filter(ImportBatch.id == self.batch_id).first()
            if batch:
                batch.pages_processed = current_page
                batch.records_created = self.result.records_created
                batch.records_rejected = self.result.records_rejected
                batch.warning_count = self.result.warnings
                batch.error_count = self.result.errors
                self.db.commit()
        except Exception:
            pass  # Non-critical — don't fail the import for progress updates
