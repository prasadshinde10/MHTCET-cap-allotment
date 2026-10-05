import os
import sqlite3
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

# Path to dedicated medical.db at project root (completely isolated from cutoff.db, josaa.db, iiser.db, bits.db)
def get_medical_db_path() -> Path:
    root_path = Path(__file__).resolve().parent.parent.parent / "medical.db"
    return root_path

def get_medical_connection() -> sqlite3.Connection:
    db_path = get_medical_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_medical_database():
    """
    Initializes dedicated Medical database schema and indexes.
    Completely isolated from MHT CET, JoSAA, IISER, and BITS.
    """
    conn = get_medical_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_colleges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                college_code TEXT NOT NULL UNIQUE,
                college_name TEXT NOT NULL,
                college_type TEXT DEFAULT 'Government/Aided',
                city TEXT,
                state TEXT DEFAULT 'Maharashtra',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT NOT NULL UNIQUE,
                course_name TEXT NOT NULL,
                degree_type TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_cutoffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                academic_year TEXT NOT NULL,
                round TEXT NOT NULL DEFAULT 'Round 1',
                college_id INTEGER NOT NULL REFERENCES medical_colleges(id) ON DELETE CASCADE,
                course_id INTEGER NOT NULL REFERENCES medical_courses(id) ON DELETE CASCADE,
                quota_category TEXT NOT NULL,
                base_category TEXT NOT NULL DEFAULT 'OPEN',
                opening_rank INTEGER,
                closing_rank INTEGER,
                opening_score INTEGER,
                closing_score INTEGER,
                allotted_seats INTEGER DEFAULT 0,
                exam_name TEXT NOT NULL DEFAULT 'NEET (UG)',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (academic_year, round, college_id, course_id, quota_category)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_files TEXT NOT NULL,
                total_records INTEGER NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Indexes for ultra-fast query performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_med_cutoffs_year ON medical_cutoffs(academic_year);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_med_cutoffs_round ON medical_cutoffs(round);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_med_cutoffs_college ON medical_cutoffs(college_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_med_cutoffs_course ON medical_cutoffs(course_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_med_cutoffs_category ON medical_cutoffs(base_category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_med_cutoffs_quota ON medical_cutoffs(quota_category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_med_cutoffs_closing_rank ON medical_cutoffs(closing_rank);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_med_cutoffs_closing_score ON medical_cutoffs(closing_score);")

        conn.commit()
    finally:
        conn.close()


def fetch_medical_filter_options() -> Dict[str, Any]:
    """
    Returns available filter options from dedicated medical.db:
    academic_years, rounds, colleges, courses, college_types, categories, quotas.
    """
    init_medical_database()
    conn = get_medical_connection()
    try:
        cur = conn.cursor()

        # Academic Years sorted descending
        cur.execute("SELECT DISTINCT academic_year FROM medical_cutoffs ORDER BY academic_year DESC")
        academic_years = [r["academic_year"] for r in cur.fetchall() if r["academic_year"]]

        # Rounds
        cur.execute("SELECT DISTINCT round FROM medical_cutoffs ORDER BY round ASC")
        rounds = [r["round"] for r in cur.fetchall() if r["round"]]

        # Colleges
        cur.execute("""
            SELECT id, college_code, college_name, college_type, city, state 
            FROM medical_colleges 
            ORDER BY college_name ASC
        """)
        colleges = [
            {
                "id": r["id"],
                "college_code": r["college_code"],
                "college_name": r["college_name"],
                "college_type": r["college_type"],
                "city": r["city"],
                "state": r["state"],
            }
            for r in cur.fetchall()
        ]

        # Courses
        cur.execute("""
            SELECT id, course_code, course_name, degree_type 
            FROM medical_courses 
            ORDER BY id ASC
        """)
        courses = [
            {
                "id": r["id"],
                "course_code": r["course_code"],
                "course_name": r["course_name"],
                "degree_type": r["degree_type"],
            }
            for r in cur.fetchall()
        ]

        # College Types
        cur.execute("SELECT DISTINCT college_type FROM medical_colleges WHERE college_type IS NOT NULL ORDER BY college_type ASC")
        college_types = [r["college_type"] for r in cur.fetchall()]

        # Base Categories
        cur.execute("SELECT DISTINCT base_category FROM medical_cutoffs WHERE base_category IS NOT NULL ORDER BY base_category ASC")
        categories = [r["base_category"] for r in cur.fetchall()]

        # Quotas
        cur.execute("SELECT DISTINCT quota_category FROM medical_cutoffs WHERE quota_category IS NOT NULL ORDER BY quota_category ASC")
        quotas = [r["quota_category"] for r in cur.fetchall()]

        return {
            "academic_years": academic_years,
            "rounds": rounds,
            "colleges": colleges,
            "courses": courses,
            "college_types": college_types,
            "categories": categories,
            "quotas": quotas,
        }
    finally:
        conn.close()


def query_medical_cutoffs(
    academic_year: Optional[str] = None,
    round_name: Optional[str] = None,
    college_id: Optional[int] = None,
    college_name: Optional[str] = None,
    course_id: Optional[int] = None,
    course_name: Optional[str] = None,
    college_type: Optional[str] = None,
    category: Optional[str] = None,
    quota: Optional[str] = None,
    student_rank: Optional[int] = None,
    student_score: Optional[int] = None,
    min_rank: Optional[int] = None,
    max_rank: Optional[int] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "rank_asc",
) -> Dict[str, Any]:
    """
    Search and filter cutoffs from dedicated medical.db with pagination and student chance calculation.
    """
    init_medical_database()
    conn = get_medical_connection()
    try:
        cur = conn.cursor()

        where_clauses = ["1=1"]
        params: List[Any] = []

        # Academic Year filter (single or comma-separated)
        if academic_year:
            if "," in academic_year:
                y_list = [y.strip() for y in academic_year.split(",") if y.strip()]
                placeholders = ",".join(["?"] * len(y_list))
                where_clauses.append(f"c.academic_year IN ({placeholders})")
                params.extend(y_list)
            else:
                where_clauses.append("c.academic_year = ?")
                params.append(academic_year.strip())

        # Round filter
        if round_name:
            if "," in round_name:
                r_list = [r.strip() for r in round_name.split(",") if r.strip()]
                placeholders = ",".join(["?"] * len(r_list))
                where_clauses.append(f"c.round IN ({placeholders})")
                params.extend(r_list)
            else:
                where_clauses.append("c.round = ?")
                params.append(round_name.strip())

        # College ID
        if college_id:
            where_clauses.append("c.college_id = ?")
            params.append(college_id)

        # College Name/Code query (supports multi-select via || or ,)
        if college_name:
            if "||" in college_name or "," in college_name:
                c_names = [c.strip() for c in re.split(r"\|\||,", college_name) if c.strip()]
                if c_names:
                    conds = ["(col.college_name LIKE ? OR col.college_code LIKE ?)" for _ in c_names]
                    where_clauses.append(f"({' OR '.join(conds)})")
                    for c_item in c_names:
                        params.append(f"%{c_item}%")
                        params.append(f"%{c_item}%")
            else:
                where_clauses.append("(col.college_name LIKE ? OR col.college_code LIKE ?)")
                params.append(f"%{college_name.strip()}%")
                params.append(f"%{college_name.strip()}%")

        # Course ID
        if course_id:
            where_clauses.append("c.course_id = ?")
            params.append(course_id)

        # Course Name/Code query (supports multi-select via || or ,)
        if course_name:
            if "||" in course_name or "," in course_name:
                cr_names = [cr.strip() for cr in re.split(r"\|\||,", course_name) if cr.strip()]
                if cr_names:
                    conds = ["(crs.course_name LIKE ? OR crs.course_code LIKE ?)" for _ in cr_names]
                    where_clauses.append(f"({' OR '.join(conds)})")
                    for cr_item in cr_names:
                        params.append(f"%{cr_item}%")
                        params.append(f"%{cr_item}%")
            else:
                where_clauses.append("(crs.course_name LIKE ? OR crs.course_code LIKE ?)")
                params.append(f"%{course_name.strip()}%")
                params.append(f"%{course_name.strip()}%")

        # College Type
        if college_type:
            if "||" in college_type or "," in college_type:
                t_list = [t.strip() for t in re.split(r"\|\||,", college_type) if t.strip()]
                placeholders = ",".join(["?"] * len(t_list))
                where_clauses.append(f"col.college_type IN ({placeholders})")
                params.extend(t_list)
            else:
                where_clauses.append("col.college_type = ?")
                params.append(college_type.strip())

        # Base Category
        if category:
            if "||" in category or "," in category:
                cat_list = [cat.strip() for cat in re.split(r"\|\||,", category) if cat.strip()]
                placeholders = ",".join(["?"] * len(cat_list))
                where_clauses.append(f"c.base_category IN ({placeholders})")
                params.extend(cat_list)
            else:
                where_clauses.append("c.base_category = ?")
                params.append(category.strip())

        # Quota Category
        if quota:
            if "||" in quota or "," in quota:
                q_list = [q.strip() for q in re.split(r"\|\||,", quota) if q.strip()]
                placeholders = ",".join(["?"] * len(q_list))
                where_clauses.append(f"c.quota_category IN ({placeholders})")
                params.extend(q_list)
            else:
                where_clauses.append("c.quota_category = ?")
                params.append(quota.strip())

        # Rank ranges
        if min_rank is not None:
            where_clauses.append("c.closing_rank >= ?")
            params.append(min_rank)
        if max_rank is not None:
            where_clauses.append("c.closing_rank <= ?")
            params.append(max_rank)

        # Score ranges
        if min_score is not None:
            where_clauses.append("c.closing_score >= ?")
            params.append(min_score)
        if max_score is not None:
            where_clauses.append("c.closing_score <= ?")
            params.append(max_score)

        # Student NEET AIR filter: show options where candidate's rank <= closing rank * 1.15 (eligible or near cut)
        if student_rank is not None:
            where_clauses.append("(c.closing_rank IS NOT NULL AND c.closing_rank >= ?)")
            params.append(int(student_rank * 0.90)) # Show reachable colleges

        # Student NEET Score filter: show options where candidate score >= closing score
        if student_score is not None:
            where_clauses.append("(c.closing_score IS NULL OR c.closing_score <= ?)")
            params.append(student_score)

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM medical_cutoffs c
            JOIN medical_colleges col ON c.college_id = col.id
            JOIN medical_courses crs ON c.course_id = crs.id
            WHERE {where_sql}
        """
        cur.execute(count_sql, params)
        total = cur.fetchone()["total"]

        # Sort Order
        order_map = {
            "rank_asc": "c.closing_rank ASC NULLS LAST, col.college_name ASC",
            "rank_desc": "c.closing_rank DESC NULLS LAST, col.college_name ASC",
            "score_desc": "c.closing_score DESC NULLS LAST, c.closing_rank ASC NULLS LAST",
            "score_asc": "c.closing_score ASC NULLS LAST, c.closing_rank ASC NULLS LAST",
            "year_desc": "c.academic_year DESC, c.round ASC, c.closing_rank ASC NULLS LAST",
            "year_asc": "c.academic_year ASC, c.round ASC, c.closing_rank ASC NULLS LAST",
            "college_asc": "col.college_name ASC, c.academic_year DESC",
            "course_asc": "crs.course_name ASC, c.closing_rank ASC NULLS LAST",
        }
        order_by_sql = order_map.get(sort_by, "c.closing_rank ASC NULLS LAST, col.college_name ASC")

        # Pagination
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT 
                c.id,
                c.academic_year,
                c.round,
                c.quota_category,
                c.base_category,
                c.opening_rank,
                c.closing_rank,
                c.opening_score,
                c.closing_score,
                c.allotted_seats,
                c.exam_name,
                col.id AS college_id,
                col.college_code,
                col.college_name,
                col.college_type,
                col.city,
                col.state,
                crs.id AS course_id,
                crs.course_code,
                crs.course_name,
                crs.degree_type
            FROM medical_cutoffs c
            JOIN medical_colleges col ON c.college_id = col.id
            JOIN medical_courses crs ON c.course_id = crs.id
            WHERE {where_sql}
            ORDER BY {order_by_sql}
            LIMIT ? OFFSET ?
        """
        cur.execute(query_sql, params + [page_size, offset])
        rows = cur.fetchall()

        items = []
        for r in rows:
            c_rank = r["closing_rank"]
            c_score = r["closing_score"]
            
            # Chance estimation based on rank or score
            chance = None
            if student_rank is not None and c_rank is not None:
                if student_rank <= c_rank * 0.85:
                    chance = "High"
                elif student_rank <= c_rank:
                    chance = "Medium"
                elif student_rank <= c_rank * 1.10:
                    chance = "Borderline"
                else:
                    chance = "Low"
            elif student_score is not None and c_score is not None:
                diff = student_score - c_score
                if diff >= 20:
                    chance = "High"
                elif diff >= 0:
                    chance = "Medium"
                elif diff >= -15:
                    chance = "Borderline"
                else:
                    chance = "Low"

            items.append({
                "id": r["id"],
                "academic_year": r["academic_year"],
                "round": r["round"],
                "quota_category": r["quota_category"],
                "base_category": r["base_category"],
                "opening_rank": r["opening_rank"],
                "closing_rank": r["closing_rank"],
                "opening_score": r["opening_score"],
                "closing_score": r["closing_score"],
                "allotted_seats": r["allotted_seats"],
                "exam_name": r["exam_name"],
                "chance": chance,
                "college_id": r["college_id"],
                "college_code": r["college_code"],
                "college_name": r["college_name"],
                "college_type": r["college_type"],
                "city": r["city"],
                "state": r["state"],
                "course_id": r["course_id"],
                "course_code": r["course_code"],
                "course_name": r["course_name"],
                "degree_type": r["degree_type"],
            })

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    finally:
        conn.close()


def get_medical_stats() -> Dict[str, Any]:
    """
    Returns counts of cutoffs, colleges, courses, available years, and breakdown.
    """
    init_medical_database()
    conn = get_medical_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS total FROM medical_cutoffs")
        cutoff_count = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM medical_colleges")
        college_count = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM medical_courses")
        course_count = cur.fetchone()["total"]

        cur.execute("SELECT DISTINCT academic_year FROM medical_cutoffs ORDER BY academic_year DESC")
        years = [r["academic_year"] for r in cur.fetchall()]

        cur.execute("""
            SELECT college_type, COUNT(*) as count 
            FROM medical_colleges 
            GROUP BY college_type
        """)
        college_types = {r["college_type"]: r["count"] for r in cur.fetchall()}

        cur.execute("""
            SELECT crs.course_code, COUNT(c.id) as count 
            FROM medical_courses crs
            LEFT JOIN medical_cutoffs c ON c.course_id = crs.id
            GROUP BY crs.course_code
        """)
        courses_breakdown = {r["course_code"]: r["count"] for r in cur.fetchall()}

        return {
            "cutoff_count": cutoff_count,
            "college_count": college_count,
            "course_count": course_count,
            "years": years,
            "college_types": college_types,
            "courses_breakdown": courses_breakdown,
        }
    finally:
        conn.close()


def wipe_medical_database():
    """
    Safely resets medical database.
    """
    conn = get_medical_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM medical_cutoffs;")
        cur.execute("DELETE FROM medical_colleges;")
        cur.execute("DELETE FROM medical_courses;")
        cur.execute("DELETE FROM medical_meta;")
        conn.commit()
    finally:
        conn.close()
