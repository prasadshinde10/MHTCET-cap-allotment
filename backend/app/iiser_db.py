import os
import sqlite3
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

# Path to dedicated iiser.db
def get_iiser_db_path() -> Path:
    root_path = Path(__file__).resolve().parent.parent.parent / "iiser.db"
    if root_path.exists():
        return root_path
    app_path = Path(__file__).resolve().parent.parent / "iiser.db"
    if app_path.exists():
        return app_path
    cwd_path = Path.cwd() / "iiser.db"
    if cwd_path.exists():
        return cwd_path
    return root_path

def get_iiser_connection() -> sqlite3.Connection:
    db_path = get_iiser_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_iiser_database():
    """
    Initializes dedicated IISER database schema and indexes.
    Completely isolated from MHT CET (cutoff.db) and JoSAA (josaa.db).
    """
    conn = get_iiser_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS institutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                institute_code TEXT UNIQUE,
                institute_name TEXT NOT NULL UNIQUE,
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
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_code TEXT NOT NULL UNIQUE,
                category_name TEXT NOT NULL,
                is_pwd BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cutoff_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                academic_year INTEGER NOT NULL,
                round_no INTEGER NOT NULL,
                institute_id INTEGER NOT NULL REFERENCES institutes(id) ON DELETE CASCADE,
                program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                raw_program_name TEXT NOT NULL,
                closing_rank INTEGER NOT NULL,
                seat_pool TEXT DEFAULT 'Gender-Neutral',
                allocation_channel TEXT DEFAULT 'IAT',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (academic_year, round_no, institute_id, program_id, category_id)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS round_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                academic_year INTEGER NOT NULL,
                round_no INTEGER NOT NULL,
                notice_text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (academic_year, round_no, notice_text)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraper_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL,
                academic_year INTEGER NOT NULL,
                total_records INTEGER NOT NULL,
                total_rounds INTEGER NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Indexes for fast search & filtering
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iiser_cutoffs_year_round ON cutoff_records(academic_year, round_no);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iiser_cutoffs_institute ON cutoff_records(institute_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iiser_cutoffs_program ON cutoff_records(program_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iiser_cutoffs_category ON cutoff_records(category_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iiser_cutoffs_rank ON cutoff_records(closing_rank);")

        conn.commit()
    finally:
        conn.close()


def fetch_iiser_filter_options() -> Dict[str, Any]:
    """
    Returns available filter options from dedicated iiser.db:
    rounds, years, institutes, programs, degree_types, categories, states.
    """
    init_iiser_database()
    conn = get_iiser_connection()
    try:
        cur = conn.cursor()

        # Rounds
        cur.execute("SELECT DISTINCT round_no FROM cutoff_records ORDER BY round_no ASC")
        rounds = [r["round_no"] for r in cur.fetchall() if r["round_no"] is not None]

        # Academic Years
        cur.execute("SELECT DISTINCT academic_year FROM cutoff_records ORDER BY academic_year DESC")
        years = [r["academic_year"] for r in cur.fetchall() if r["academic_year"] is not None]

        # Institutes
        cur.execute("SELECT id, institute_code, institute_name, state FROM institutes ORDER BY institute_name ASC")
        institutes = [
            {
                "id": r["id"],
                "institute_code": r["institute_code"],
                "institute_name": r["institute_name"],
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

        # Distinct degree types
        cur.execute("SELECT DISTINCT degree_type FROM programs WHERE degree_type IS NOT NULL ORDER BY degree_type ASC")
        degree_types = [r["degree_type"] for r in cur.fetchall()]

        # Categories
        cur.execute("SELECT id, category_code, category_name, is_pwd FROM categories ORDER BY id ASC")
        categories = [
            {
                "id": r["id"],
                "category_code": r["category_code"],
                "category_name": r["category_name"],
                "is_pwd": bool(r["is_pwd"]),
            }
            for r in cur.fetchall()
        ]

        # Distinct states
        cur.execute("SELECT DISTINCT state FROM institutes WHERE state IS NOT NULL AND state != '' ORDER BY state ASC")
        states = [r["state"] for r in cur.fetchall()]

        return {
            "rounds": rounds,
            "years": years,
            "institutes": institutes,
            "programs": programs,
            "degree_types": degree_types,
            "categories": categories,
            "states": states,
        }
    finally:
        conn.close()


def query_iiser_cutoffs(
    round_no: Optional[str] = None,
    academic_year: Optional[int] = None,
    institute_id: Optional[int] = None,
    institute_name: Optional[str] = None,
    state: Optional[str] = None,
    program_id: Optional[int] = None,
    academic_program: Optional[str] = None,
    degree_type: Optional[str] = None,
    category: Optional[str] = None,
    max_rank: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "rank_asc",
) -> Dict[str, Any]:
    """
    Search and filter cutoffs from dedicated iiser.db with pagination.
    """
    init_iiser_database()
    conn = get_iiser_connection()
    try:
        cur = conn.cursor()

        where_clauses = ["1=1"]
        params: List[Any] = []

        # Round filter (single or comma-separated)
        if round_no:
            round_list = [int(r.strip()) for r in round_no.split(",") if r.strip().isdigit()]
            if round_list:
                placeholders = ",".join(["?"] * len(round_list))
                where_clauses.append(f"c.round_no IN ({placeholders})")
                params.extend(round_list)

        # Academic Year
        if academic_year:
            where_clauses.append("c.academic_year = ?")
            params.append(academic_year)

        # Institute ID
        if institute_id:
            where_clauses.append("c.institute_id = ?")
            params.append(institute_id)

        # Institute Name
        if institute_name:
            if "||" in institute_name or "," in institute_name:
                raw_names = [n.strip() for n in re.split(r"\|\||,", institute_name) if n.strip()]
                if raw_names:
                    conds = ["i.institute_name LIKE ?" for _ in raw_names]
                    where_clauses.append(f"({' OR '.join(conds)})")
                    params.extend([f"%{n}%" for n in raw_names])
            else:
                where_clauses.append("i.institute_name LIKE ?")
                params.append(f"%{institute_name.strip()}%")

        # State
        if state:
            where_clauses.append("i.state = ?")
            params.append(state.strip())

        # Program ID
        if program_id:
            where_clauses.append("c.program_id = ?")
            params.append(program_id)

        # Academic Program Name (supports single or multi-select via || or ,)
        if academic_program:
            if "||" in academic_program:
                p_names = [p.strip() for p in academic_program.split("||") if p.strip()]
                if p_names:
                    conds = ["(p.program_name LIKE ? OR c.raw_program_name LIKE ?)" for _ in p_names]
                    where_clauses.append(f"({' OR '.join(conds)})")
                    for p_item in p_names:
                        params.append(f"%{p_item}%")
                        params.append(f"%{p_item}%")
            elif "," in academic_program:
                p_names = [p.strip() for p in academic_program.split(",") if p.strip()]
                if p_names:
                    conds = ["(p.program_name LIKE ? OR c.raw_program_name LIKE ?)" for _ in p_names]
                    where_clauses.append(f"({' OR '.join(conds)})")
                    for p_item in p_names:
                        params.append(f"%{p_item}%")
                        params.append(f"%{p_item}%")
            else:
                where_clauses.append("(p.program_name LIKE ? OR c.raw_program_name LIKE ?)")
                params.append(f"%{academic_program.strip()}%")
                params.append(f"%{academic_program.strip()}%")

        # Degree Type
        if degree_type:
            where_clauses.append("p.degree_type = ?")
            params.append(degree_type.strip())

        # Category
        if category:
            if "," in category:
                cat_list = [c.strip() for c in category.split(",") if c.strip()]
                placeholders = ",".join(["?"] * len(cat_list))
                where_clauses.append(f"cat.category_code IN ({placeholders})")
                params.extend(cat_list)
            else:
                where_clauses.append("cat.category_code = ?")
                params.append(category.strip())

        # Max Rank (Student Rank chance predictor: student rank <= closing_rank)
        if max_rank is not None and max_rank > 0:
            where_clauses.append("c.closing_rank >= ?")
            params.append(max_rank)

        where_sql = " AND ".join(where_clauses)

        # Sorting
        sort_map = {
            "rank_asc": "c.closing_rank ASC, c.round_no DESC",
            "rank_desc": "c.closing_rank DESC, c.round_no DESC",
            "round_asc": "c.round_no ASC, c.closing_rank ASC",
            "round_desc": "c.round_no DESC, c.closing_rank ASC",
            "institute_asc": "i.institute_name ASC, c.round_no DESC, c.closing_rank ASC",
            "program_asc": "p.program_name ASC, c.round_no DESC, c.closing_rank ASC",
        }
        order_sql = sort_map.get(sort_by, "c.closing_rank ASC, c.round_no DESC")

        # Count total matches
        count_sql = f"""
            SELECT COUNT(*)
            FROM cutoff_records c
            JOIN institutes i ON c.institute_id = i.id
            JOIN programs p ON c.program_id = p.id
            JOIN categories cat ON c.category_id = cat.id
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
                c.round_no,
                c.raw_program_name,
                c.closing_rank,
                c.seat_pool,
                c.allocation_channel,
                i.id AS institute_id,
                i.institute_code,
                i.institute_name,
                i.state AS institute_state,
                p.id AS program_id,
                p.program_code,
                p.program_name,
                p.degree_type,
                cat.id AS category_id,
                cat.category_code,
                cat.category_name,
                cat.is_pwd
            FROM cutoff_records c
            JOIN institutes i ON c.institute_id = i.id
            JOIN programs p ON c.program_id = p.id
            JOIN categories cat ON c.category_id = cat.id
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
                "round_no": r["round_no"],
                "raw_program_name": r["raw_program_name"],
                "closing_rank": r["closing_rank"],
                "seat_pool": r["seat_pool"],
                "allocation_channel": r["allocation_channel"],
                "institute_id": r["institute_id"],
                "institute_code": r["institute_code"],
                "institute_name": r["institute_name"],
                "institute_state": r["institute_state"],
                "program_id": r["program_id"],
                "program_code": r["program_code"],
                "program_name": r["program_name"],
                "degree_type": r["degree_type"],
                "category_id": r["category_id"],
                "category_code": r["category_code"],
                "category_name": r["category_name"],
                "is_pwd": bool(r["is_pwd"]),
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


def fetch_iiser_round_notices(round_no: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Returns official round notices and program closure alerts.
    """
    init_iiser_database()
    conn = get_iiser_connection()
    try:
        cur = conn.cursor()
        if round_no:
            cur.execute("""
                SELECT id, academic_year, round_no, notice_text, created_at
                FROM round_notices
                WHERE round_no = ?
                ORDER BY round_no DESC, id ASC
            """, (round_no,))
        else:
            cur.execute("""
                SELECT id, academic_year, round_no, notice_text, created_at
                FROM round_notices
                ORDER BY round_no DESC, id ASC
            """)
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "academic_year": r["academic_year"],
                "round_no": r["round_no"],
                "notice_text": r["notice_text"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_iiser_stats() -> Dict[str, Any]:
    """
    Returns database statistics (counts of cutoffs, institutes, programs, categories, rounds, notices).
    """
    init_iiser_database()
    conn = get_iiser_connection()
    try:
        cur = conn.cursor()
        total_cutoffs = cur.execute("SELECT COUNT(*) FROM cutoff_records").fetchone()[0]
        total_institutes = cur.execute("SELECT COUNT(*) FROM institutes").fetchone()[0]
        total_programs = cur.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
        total_categories = cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        total_rounds = cur.execute("SELECT COUNT(DISTINCT round_no) FROM cutoff_records").fetchone()[0]
        total_notices = cur.execute("SELECT COUNT(*) FROM round_notices").fetchone()[0]
        
        last_meta = cur.execute("SELECT created_at FROM scraper_meta ORDER BY id DESC LIMIT 1").fetchone()
        last_scraped_at = last_meta["created_at"] if last_meta else None

        return {
            "total_cutoffs": total_cutoffs,
            "total_institutes": total_institutes,
            "total_programs": total_programs,
            "total_categories": total_categories,
            "total_rounds": total_rounds,
            "total_notices": total_notices,
            "last_scraped_at": last_scraped_at,
        }
    finally:
        conn.close()


def wipe_iiser_database() -> Dict[str, Any]:
    """
    Safely resets all records in iiser.db while keeping the schema intact.
    """
    init_iiser_database()
    conn = get_iiser_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM cutoff_records;")
        cur.execute("DELETE FROM round_notices;")
        cur.execute("DELETE FROM scraper_meta;")
        cur.execute("DELETE FROM programs;")
        cur.execute("DELETE FROM categories;")
        cur.execute("DELETE FROM institutes;")
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('cutoff_records', 'round_notices', 'scraper_meta', 'programs', 'categories', 'institutes');")
        except Exception:
            pass
        conn.commit()
        return {"success": True, "message": "IISER database wiped successfully."}
    finally:
        conn.close()
