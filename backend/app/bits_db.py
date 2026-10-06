import os
import sqlite3
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

# Path to dedicated bits.db
def get_bits_db_path() -> Path:
    app_path = Path(__file__).resolve().parent.parent / "bits.db"
    if app_path.exists():
        return app_path
    root_path = Path(__file__).resolve().parent.parent.parent / "bits.db"
    if root_path.exists():
        return root_path
    cwd_path = Path.cwd() / "bits.db"
    if cwd_path.exists():
        return cwd_path
    return app_path


def get_bits_connection() -> sqlite3.Connection:
    db_path = get_bits_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_bits_database():
    """
    Initializes dedicated BITS database schema and indexes in bits.db.
    Completely isolated from MHT CET (cutoff.db), JoSAA (josaa.db), and IISER (iiser.db).
    """
    conn = get_bits_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS campuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campus_code TEXT NOT NULL UNIQUE,
                campus_name TEXT NOT NULL UNIQUE,
                location TEXT,
                state TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_code TEXT,
                program_name TEXT NOT NULL UNIQUE,
                degree_type TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cutoff_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                academic_year TEXT NOT NULL,
                campus_id INTEGER NOT NULL REFERENCES campuses(id) ON DELETE CASCADE,
                program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
                cutoff_score INTEGER NOT NULL,
                max_marks INTEGER NOT NULL DEFAULT 390,
                score_percentage REAL,
                category TEXT NOT NULL DEFAULT 'General Merit',
                exam_name TEXT NOT NULL DEFAULT 'BITSAT',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (academic_year, campus_id, program_id, category)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraper_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL,
                years_scraped TEXT NOT NULL,
                total_records INTEGER NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Indexes for fast search & filtering
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bits_cutoffs_year ON cutoff_records(academic_year);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bits_cutoffs_campus ON cutoff_records(campus_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bits_cutoffs_program ON cutoff_records(program_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bits_cutoffs_score ON cutoff_records(cutoff_score);")

        conn.commit()
    finally:
        conn.close()


def fetch_bits_filter_options() -> Dict[str, Any]:
    """
    Returns available filter options from dedicated bits.db:
    academic_years, campuses, programs, degree_types, categories.
    """
    init_bits_database()
    conn = get_bits_connection()
    try:
        cur = conn.cursor()

        # Academic Years sorted descending
        cur.execute("SELECT DISTINCT academic_year FROM cutoff_records ORDER BY academic_year DESC")
        academic_years = [r["academic_year"] for r in cur.fetchall() if r["academic_year"]]

        # Campuses
        cur.execute("SELECT id, campus_code, campus_name, location, state FROM campuses ORDER BY id ASC")
        campuses = [
            {
                "id": r["id"],
                "campus_code": r["campus_code"],
                "campus_name": r["campus_name"],
                "location": r["location"],
                "state": r["state"],
            }
            for r in cur.fetchall()
        ]

        # Programs
        cur.execute("SELECT id, program_code, program_name, degree_type FROM programs ORDER BY program_name ASC")
        programs = [
            {
                "id": r["id"],
                "program_code": r["program_code"],
                "program_name": r["program_name"],
                "degree_type": r["degree_type"],
            }
            for r in cur.fetchall()
        ]

        # Degree Types
        cur.execute("SELECT DISTINCT degree_type FROM programs WHERE degree_type IS NOT NULL ORDER BY degree_type ASC")
        degree_types = [r["degree_type"] for r in cur.fetchall()]

        # Categories
        cur.execute("SELECT DISTINCT category FROM cutoff_records WHERE category IS NOT NULL ORDER BY category ASC")
        categories = [r["category"] for r in cur.fetchall()]

        return {
            "academic_years": academic_years,
            "campuses": campuses,
            "programs": programs,
            "degree_types": degree_types,
            "categories": categories,
        }
    finally:
        conn.close()


def query_bits_cutoffs(
    academic_year: Optional[str] = None,
    campus_id: Optional[int] = None,
    campus_name: Optional[str] = None,
    program_id: Optional[int] = None,
    program_name: Optional[str] = None,
    degree_type: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    student_score: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "score_desc",
) -> Dict[str, Any]:
    """
    Search and filter cutoffs from dedicated bits.db with pagination.
    """
    init_bits_database()
    conn = get_bits_connection()
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

        # Campus ID
        if campus_id:
            where_clauses.append("c.campus_id = ?")
            params.append(campus_id)

        # Campus Name (supports single or multi-select via || or ,)
        if campus_name:
            if "||" in campus_name or "," in campus_name:
                c_names = [c.strip() for c in re.split(r"\|\||,", campus_name) if c.strip()]
                if c_names:
                    conds = ["(cmp.campus_name LIKE ? OR cmp.campus_code LIKE ?)" for _ in c_names]
                    where_clauses.append(f"({' OR '.join(conds)})")
                    for c_item in c_names:
                        params.append(f"%{c_item}%")
                        params.append(f"%{c_item}%")
            else:
                where_clauses.append("(cmp.campus_name LIKE ? OR cmp.campus_code LIKE ?)")
                params.append(f"%{campus_name.strip()}%")
                params.append(f"%{campus_name.strip()}%")

        # Program ID
        if program_id:
            where_clauses.append("c.program_id = ?")
            params.append(program_id)

        # Program Name (supports single or multi-select via || or ,)
        if program_name:
            if "||" in program_name:
                p_names = [p.strip() for p in program_name.split("||") if p.strip()]
                if p_names:
                    conds = ["p.program_name LIKE ?" for _ in p_names]
                    where_clauses.append(f"({' OR '.join(conds)})")
                    for p_item in p_names:
                        params.append(f"%{p_item}%")
            elif "," in program_name:
                p_names = [p.strip() for p in program_name.split(",") if p.strip()]
                if p_names:
                    conds = ["p.program_name LIKE ?" for _ in p_names]
                    where_clauses.append(f"({' OR '.join(conds)})")
                    for p_item in p_names:
                        params.append(f"%{p_item}%")
            else:
                where_clauses.append("p.program_name LIKE ?")
                params.append(f"%{program_name.strip()}%")

        # Degree Type
        if degree_type:
            where_clauses.append("p.degree_type = ?")
            params.append(degree_type.strip())

        # Min / Max Cutoff Score
        if min_score is not None:
            where_clauses.append("c.cutoff_score >= ?")
            params.append(min_score)

        if max_score is not None:
            where_clauses.append("c.cutoff_score <= ?")
            params.append(max_score)

        # Student Score Chance finder (student can get in if student_score >= cutoff_score)
        if student_score is not None and student_score > 0:
            where_clauses.append("c.cutoff_score <= ?")
            params.append(student_score)

        where_sql = " AND ".join(where_clauses)

        # Sorting
        sort_map = {
            "score_desc": "c.cutoff_score DESC, cmp.id ASC, p.program_name ASC",
            "score_asc": "c.cutoff_score ASC, cmp.id ASC, p.program_name ASC",
            "year_desc": "c.academic_year DESC, c.cutoff_score DESC",
            "year_asc": "c.academic_year ASC, c.cutoff_score DESC",
            "campus_asc": "cmp.campus_name ASC, c.cutoff_score DESC",
            "program_asc": "p.program_name ASC, c.cutoff_score DESC",
        }
        order_sql = sort_map.get(sort_by, "c.cutoff_score DESC, cmp.id ASC, p.program_name ASC")

        # Count total
        count_sql = f"""
            SELECT COUNT(*)
            FROM cutoff_records c
            JOIN campuses cmp ON c.campus_id = cmp.id
            JOIN programs p ON c.program_id = p.id
            WHERE {where_sql}
        """
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        # Fetch paginated items
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT 
                c.id,
                c.academic_year,
                c.cutoff_score,
                c.max_marks,
                c.score_percentage,
                c.category,
                c.exam_name,
                cmp.id AS campus_id,
                cmp.campus_code,
                cmp.campus_name,
                cmp.location AS campus_location,
                cmp.state AS campus_state,
                p.id AS program_id,
                p.program_code,
                p.program_name,
                p.degree_type
            FROM cutoff_records c
            JOIN campuses cmp ON c.campus_id = cmp.id
            JOIN programs p ON c.program_id = p.id
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
        """
        cur.execute(query_sql, params + [page_size, offset])
        rows = cur.fetchall()

        items = [
            {
                "id": r["id"],
                "academic_year": r["academic_year"],
                "cutoff_score": r["cutoff_score"],
                "max_marks": r["max_marks"],
                "score_percentage": r["score_percentage"],
                "category": r["category"],
                "exam_name": r["exam_name"],
                "campus_id": r["campus_id"],
                "campus_code": r["campus_code"],
                "campus_name": r["campus_name"],
                "campus_location": r["campus_location"],
                "campus_state": r["campus_state"],
                "program_id": r["program_id"],
                "program_code": r["program_code"],
                "program_name": r["program_name"],
                "degree_type": r["degree_type"],
            }
            for r in rows
        ]

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    finally:
        conn.close()


def get_bits_stats() -> Dict[str, Any]:
    """
    Returns database statistics (counts of cutoffs, campuses, programs, available years, and last scraped time).
    """
    init_bits_database()
    conn = get_bits_connection()
    try:
        cur = conn.cursor()
        total_cutoffs = cur.execute("SELECT COUNT(*) FROM cutoff_records").fetchone()[0]
        total_campuses = cur.execute("SELECT COUNT(*) FROM campuses").fetchone()[0]
        total_programs = cur.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
        
        cur.execute("SELECT DISTINCT academic_year FROM cutoff_records ORDER BY academic_year DESC")
        available_years = [r["academic_year"] for r in cur.fetchall() if r["academic_year"]]

        last_meta = cur.execute("SELECT created_at FROM scraper_meta ORDER BY id DESC LIMIT 1").fetchone()
        last_scraped_at = last_meta["created_at"] if last_meta else None

        return {
            "total_cutoffs": total_cutoffs,
            "total_campuses": total_campuses,
            "total_programs": total_programs,
            "available_years": available_years,
            "last_scraped_at": last_scraped_at,
        }
    finally:
        conn.close()


def wipe_bits_database() -> Dict[str, Any]:
    """
    Safely wipes all records in bits.db while preserving the schema.
    """
    init_bits_database()
    conn = get_bits_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM cutoff_records;")
        cur.execute("DELETE FROM scraper_meta;")
        cur.execute("DELETE FROM programs;")
        cur.execute("DELETE FROM campuses;")
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('cutoff_records', 'scraper_meta', 'programs', 'campuses');")
        except Exception:
            pass
        conn.commit()
        return {"success": True, "message": "BITS database wiped successfully."}
    finally:
        conn.close()
