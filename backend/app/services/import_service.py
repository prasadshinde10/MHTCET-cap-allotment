"""
Import service — handles staging-to-production commit workflow.

During commit:
1. Reads all staging_cutoffs for a batch
2. Groups by college_code → creates/finds College records
3. Groups by course_code → creates/finds Course records
4. Creates Cutoff production records with proper FKs
5. Deletes staging records
6. Updates batch status to COMMITTED
"""
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import Decimal

from app.models.college import College
from app.models.course import Course
from app.models.cutoff import Cutoff
from app.models.import_batch import ImportBatch
from app.models.cap_round import CapRound
from app.models.staging_cutoff import StagingCutoff
from app.schemas.imports import CommitResponse


class ImportService:
    def __init__(self, db: Session):
        self.db = db

    def commit_staging(self, batch_id: int) -> CommitResponse:
        """Commit staging records to production tables."""
        # 1. Get batch and validate
        batch = self.db.execute(
            select(ImportBatch).where(ImportBatch.id == batch_id)
        ).scalar_one_or_none()

        if not batch:
            raise ValueError("Batch not found")

        if batch.status not in ["COMPLETED", "COMPLETED_WITH_WARNINGS"]:
            raise ValueError(
                f"Batch is not ready for commit (current status: {batch.status})"
            )

        # Get cap_round for year
        cap_round = self.db.get(CapRound, batch.cap_round_id)
        if not cap_round:
            raise ValueError("CapRound not found for this batch")

        # 2. Get all staging records for this batch
        staging_records = self.db.execute(
            select(StagingCutoff).where(StagingCutoff.import_batch_id == batch_id)
        ).scalars().all()

        if not staging_records:
            return CommitResponse(
                records_committed=0,
                colleges_created=0,
                courses_created=0,
                message="No staging records found"
            )

        colleges_created = 0
        courses_created = 0
        records_committed = 0

        # Caches to avoid repeated DB lookups
        college_cache: Dict[str, College] = {}
        course_cache: Dict[str, Course] = {}

        # Collect cutoff objects for bulk insert
        cutoff_objects = []

        for staging in staging_records:
            # a. Find or create College
            college_code = staging.college_code
            if college_code not in college_cache:
                college, is_new = self._get_or_create_college(college_code)
                if is_new:
                    colleges_created += 1
                college_cache[college_code] = college

            college = college_cache[college_code]

            # b. Find or create Course
            course_code = staging.course_code
            if course_code not in course_cache:
                course, is_new = self._get_or_create_course(
                    college.id, course_code
                )
                if is_new:
                    courses_created += 1
                course_cache[course_code] = course

            course = course_cache[course_code]

            # c. Create Cutoff record
            cutoff = Cutoff(
                year=cap_round.year,
                cap_round_id=batch.cap_round_id,
                course_id=course.id,
                import_batch_id=batch.id,
                seat_section=staging.seat_section,
                seat_section_raw=staging.seat_section_raw,
                category_code=staging.category_code,
                gender=staging.gender,
                seat_category=staging.seat_category,
                seat_location=staging.seat_location,
                stage=staging.stage,
                merit_number=staging.merit_number,
                percentile=staging.percentile,
                source_page=staging.source_page,
                source_pdf=staging.source_pdf,
            )
            cutoff_objects.append(cutoff)
            records_committed += 1

        # Bulk add cutoffs
        self.db.bulk_save_objects(cutoff_objects)

        # 4. Delete staging records
        self.db.execute(
            StagingCutoff.__table__.delete().where(
                StagingCutoff.import_batch_id == batch_id
            )
        )

        # 5. Update batch status
        batch.status = "COMMITTED"
        batch.records_created = records_committed

        self.db.commit()

        return CommitResponse(
            records_committed=records_committed,
            colleges_created=colleges_created,
            courses_created=courses_created,
            message=f"Successfully committed {records_committed} records "
                    f"({colleges_created} new colleges, {courses_created} new courses)"
        )

    def _get_or_create_college(
        self, college_code: str
    ) -> tuple[College, bool]:
        """Find or create a College by code. Returns (college, is_new)."""
        college = self.db.execute(
            select(College).where(College.college_code == college_code)
        ).scalar_one_or_none()

        if college:
            return college, False

        # Create with code as name placeholder — admin can update later
        college = College(
            college_code=college_code,
            college_name=f"College {college_code}",
        )
        self.db.add(college)
        self.db.flush()
        return college, True

    def _get_or_create_course(
        self, college_id: int, course_code: str
    ) -> tuple[Course, bool]:
        """Find or create a Course by code under a college. Returns (course, is_new)."""
        course = self.db.execute(
            select(Course).where(
                Course.college_id == college_id,
                Course.course_code == course_code,
            )
        ).scalar_one_or_none()

        if course:
            return course, False

        # Create with code as name placeholder — admin can update later
        course = Course(
            college_id=college_id,
            course_code=course_code,
            course_name=f"Course {course_code}",
        )
        self.db.add(course)
        self.db.flush()
        return course, True
