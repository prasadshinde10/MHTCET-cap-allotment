import os
import sqlite3
import re
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy import text
from app.database import engine
from app.models.base import Base

logger = logging.getLogger(__name__)

# Paths to dedicated medical databases (separate for Central MCC and State CET Cell)
def get_medical_db_path(counselling_type: Optional[str] = None) -> Path:
    c_low = (counselling_type or "").lower().strip()
    is_state = c_low in ("state", "maha", "state_cet", "maharashtra")
    db_filename = "medical_state.db" if is_state else "medical_central.db"

    # 1. Current working directory
    cwd_p = Path.cwd() / db_filename
    if cwd_p.exists():
        return cwd_p
    # 2. backend directory if run from project root
    backend_p = Path.cwd() / "backend" / db_filename
    if backend_p.exists():
        return backend_p
    # 3. App directory
    app_p = Path(__file__).resolve().parent.parent / db_filename
    if app_p.exists():
        return app_p
    # 4. Project root directory
    root_p = Path(__file__).resolve().parent.parent.parent / db_filename
    if root_p.exists():
        return root_p

    return app_p


def get_medical_connection(counselling_type: Optional[str] = None) -> sqlite3.Connection:
    db_path = get_medical_db_path(counselling_type)
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def _init_single_sqlite_db(conn: sqlite3.Connection):
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
                counselling_type TEXT DEFAULT 'state',
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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                stream_type TEXT DEFAULT 'auto',
                academic_year TEXT,
                round_name TEXT,
                total_pages INTEGER DEFAULT 0,
                pages_processed INTEGER DEFAULT 0,
                records_created INTEGER DEFAULT 0,
                status TEXT DEFAULT 'PROCESSING',
                current_action TEXT,
                progress_percent INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0.0,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Indexes
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


def init_medical_database(counselling_type: Optional[str] = None):
    """
    Initializes dedicated Medical database schema and indexes for Central and/or State DBs.
    Supports both Supabase PostgreSQL and local SQLite.
    """
    if engine.dialect.name == "postgresql":
        Base.metadata.create_all(bind=engine)
    else:
        if counselling_type:
            _init_single_sqlite_db(get_medical_connection(counselling_type))
        else:
            _init_single_sqlite_db(get_medical_connection("central"))
            _init_single_sqlite_db(get_medical_connection("state"))


def auto_seed_medical_database_if_empty():
    """
    Auto-seeds Supabase PostgreSQL database on startup if medical_cutoffs table is empty.
    Reads verified cutoffs from bundled medical_central.db and medical_state.db.
    """
    init_medical_database()

    # Only needed when connected to PostgreSQL (e.g. Supabase on Render)
    if engine.dialect.name != "postgresql":
        return

    try:
        with engine.connect() as conn:
            existing_count = conn.execute(text("SELECT COUNT(id) FROM medical_cutoffs")).scalar()
            if existing_count and existing_count > 0:
                logger.info(f"[Medical] PostgreSQL database already seeded ({existing_count:,} cutoffs present).")
                return

        logger.info("[Medical] PostgreSQL medical_cutoffs table is empty. Seeding verified datasets...")
        p_c = get_medical_db_path("central")
        p_s = get_medical_db_path("state")

        col_map = {}
        crs_map = {}
        total_seeded = 0

        with engine.begin() as conn:
            for p, ctype in [(p_c, "central"), (p_s, "state")]:
                if not p.exists():
                    logger.warning(f"[Medical] Seed file not found: {p}")
                    continue

                src = sqlite3.connect(str(p))
                src.row_factory = sqlite3.Row
                scur = src.cursor()

                # Colleges
                scur.execute("SELECT * FROM medical_colleges")
                for r in scur.fetchall():
                    code = r["college_code"]
                    if code not in col_map:
                        res = conn.execute(
                            text("""
                                INSERT INTO medical_colleges (college_code, college_name, college_type, city, state)
                                VALUES (:code, :name, :ctype, :city, :st)
                                ON CONFLICT (college_code) DO UPDATE SET college_name = EXCLUDED.college_name
                                RETURNING id
                            """),
                            {"code": code, "name": r["college_name"], "ctype": r["college_type"], "city": r["city"], "st": r["state"]}
                        )
                        col_map[code] = res.scalar()

                # Courses
                scur.execute("SELECT * FROM medical_courses")
                for r in scur.fetchall():
                    code = r["course_code"]
                    if code not in crs_map:
                        res = conn.execute(
                            text("""
                                INSERT INTO medical_courses (course_code, course_name, degree_type)
                                VALUES (:code, :name, :dtype)
                                ON CONFLICT (course_code) DO UPDATE SET course_name = EXCLUDED.course_name
                                RETURNING id
                            """),
                            {"code": code, "name": r["course_name"], "dtype": r["degree_type"]}
                        )
                        crs_map[code] = res.scalar()

                # Map IDs
                scur.execute("SELECT id, college_code FROM medical_colleges")
                src_col_to_code = {r["id"]: r["college_code"] for r in scur.fetchall()}
                scur.execute("SELECT id, course_code FROM medical_courses")
                src_crs_to_code = {r["id"]: r["course_code"] for r in scur.fetchall()}

                # Cutoffs
                scur.execute("SELECT * FROM medical_cutoffs")
                batch = []
                for r in scur.fetchall():
                    col_code = src_col_to_code.get(r["college_id"])
                    crs_code = src_crs_to_code.get(r["course_id"])
                    if not col_code or not crs_code or col_code not in col_map or crs_code not in crs_map:
                        continue

                    batch.append({
                        "academic_year": r["academic_year"],
                        "round": r["round"],
                        "college_id": col_map[col_code],
                        "course_id": crs_map[crs_code],
                        "quota_category": r["quota_category"],
                        "base_category": r["base_category"],
                        "opening_rank": r["opening_rank"],
                        "closing_rank": r["closing_rank"],
                        "opening_score": r["opening_score"],
                        "closing_score": r["closing_score"],
                        "allotted_seats": r["allotted_seats"],
                        "exam_name": r["exam_name"],
                        "counselling_type": ctype,
                    })

                    if len(batch) >= 2000:
                        conn.execute(text("""
                            INSERT INTO medical_cutoffs (
                                academic_year, round, college_id, course_id, quota_category,
                                base_category, opening_rank, closing_rank, opening_score, closing_score,
                                allotted_seats, exam_name, counselling_type
                            ) VALUES (
                                :academic_year, :round, :college_id, :course_id, :quota_category,
                                :base_category, :opening_rank, :closing_rank, :opening_score, :closing_score,
                                :allotted_seats, :exam_name, :counselling_type
                            )
                            ON CONFLICT (academic_year, round, college_id, course_id, quota_category)
                            DO UPDATE SET
                                closing_rank = EXCLUDED.closing_rank,
                                opening_rank = EXCLUDED.opening_rank
                        """), batch)
                        total_seeded += len(batch)
                        batch = []

                if batch:
                    conn.execute(text("""
                        INSERT INTO medical_cutoffs (
                            academic_year, round, college_id, course_id, quota_category,
                            base_category, opening_rank, closing_rank, opening_score, closing_score,
                            allotted_seats, exam_name, counselling_type
                        ) VALUES (
                            :academic_year, :round, :college_id, :course_id, :quota_category,
                            :base_category, :opening_rank, :closing_rank, :opening_score, :closing_score,
                            :allotted_seats, :exam_name, :counselling_type
                        )
                        ON CONFLICT (academic_year, round, college_id, course_id, quota_category)
                        DO UPDATE SET
                            closing_rank = EXCLUDED.closing_rank,
                            opening_rank = EXCLUDED.opening_rank
                    """), batch)
                    total_seeded += len(batch)

                src.close()

        logger.info(f"[Medical] Successfully auto-seeded {total_seeded:,} medical cutoffs into Supabase PostgreSQL!")
    except Exception as e:
        logger.error(f"[Medical] Error during auto-seeding: {e}", exc_info=True)


def fetch_medical_filter_options(counselling_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns available filter options from Supabase PostgreSQL (production) or local SQLite:
    academic_years, rounds, colleges, courses, college_types, categories, quotas, states, cities.
    """
    init_medical_database(counselling_type)

    is_pg = engine.dialect.name == "postgresql"

    # WHERE condition for Central vs State
    c_low = (counselling_type or "").lower().strip()
    is_central = c_low in ("central", "mcc", "aiq")
    is_state = c_low in ("state", "maha", "state_cet", "maharashtra")

    if is_pg:
        # Query Supabase PostgreSQL
        with engine.connect() as conn:
            where_cond = "1=1"
            if is_central:
                where_cond = "(c.exam_name LIKE '%MCC%' OR c.counselling_type = 'central')"
            elif is_state:
                where_cond = "(c.exam_name NOT LIKE '%MCC%' AND c.counselling_type != 'central')"

            academic_years = [
                r[0] for r in conn.execute(text(f"SELECT DISTINCT c.academic_year FROM medical_cutoffs c WHERE {where_cond} AND c.academic_year IS NOT NULL ORDER BY c.academic_year DESC")).fetchall()
            ]
            rounds = [
                r[0] for r in conn.execute(text(f"SELECT DISTINCT c.round FROM medical_cutoffs c WHERE {where_cond} AND c.round IS NOT NULL ORDER BY c.round ASC")).fetchall()
            ]
            colleges = [
                {
                    "id": r[0],
                    "college_code": r[1],
                    "college_name": r[2],
                    "college_type": r[3],
                    "city": r[4],
                    "state": r[5],
                }
                for r in conn.execute(text(f"""
                    SELECT DISTINCT col.id, col.college_code, col.college_name, col.college_type, col.city, col.state
                    FROM medical_colleges col
                    JOIN medical_cutoffs c ON c.college_id = col.id
                    WHERE {where_cond}
                    ORDER BY col.college_name ASC
                """)).fetchall()
            ]
            courses = [
                {
                    "id": r[0],
                    "course_code": r[1],
                    "course_name": r[2],
                    "degree_type": r[3],
                }
                for r in conn.execute(text(f"""
                    SELECT DISTINCT crs.id, crs.course_code, crs.course_name, crs.degree_type
                    FROM medical_courses crs
                    JOIN medical_cutoffs c ON c.course_id = crs.id
                    WHERE {where_cond}
                    ORDER BY crs.id ASC
                """)).fetchall()
            ]
            college_types = [
                r[0] for r in conn.execute(text(f"""
                    SELECT DISTINCT col.college_type
                    FROM medical_colleges col
                    JOIN medical_cutoffs c ON c.college_id = col.id
                    WHERE {where_cond} AND col.college_type IS NOT NULL
                    ORDER BY col.college_type ASC
                """)).fetchall()
            ]
            categories = [
                r[0] for r in conn.execute(text(f"SELECT DISTINCT c.base_category FROM medical_cutoffs c WHERE {where_cond} AND c.base_category IS NOT NULL ORDER BY c.base_category ASC")).fetchall()
            ]
            quotas = [
                r[0] for r in conn.execute(text(f"SELECT DISTINCT c.quota_category FROM medical_cutoffs c WHERE {where_cond} AND c.quota_category IS NOT NULL ORDER BY c.quota_category ASC")).fetchall()
            ]
            states = [
                r[0] for r in conn.execute(text(f"""
                    SELECT DISTINCT col.state
                    FROM medical_colleges col
                    JOIN medical_cutoffs c ON c.college_id = col.id
                    WHERE {where_cond} AND col.state IS NOT NULL AND col.state != ''
                    ORDER BY col.state ASC
                """)).fetchall()
            ]
            cities = [
                r[0] for r in conn.execute(text(f"""
                    SELECT DISTINCT col.city
                    FROM medical_colleges col
                    JOIN medical_cutoffs c ON c.college_id = col.id
                    WHERE {where_cond} AND col.city IS NOT NULL AND col.city != ''
                    ORDER BY col.city ASC
                """)).fetchall()
            ]

            return {
                "academic_years": academic_years,
                "rounds": rounds,
                "colleges": colleges,
                "courses": courses,
                "college_types": college_types,
                "categories": categories,
                "quotas": quotas,
                "states": states,
                "cities": cities,
            }

    # SQLite Fallback (Local Development)
    conn = get_medical_connection(counselling_type)
    try:
        cur = conn.cursor()
        where_cond = "1=1"
        if is_central:
            where_cond = "c.exam_name LIKE '%MCC%'"
        elif is_state:
            where_cond = "c.exam_name NOT LIKE '%MCC%'"

        cur.execute(f"SELECT DISTINCT c.academic_year FROM medical_cutoffs c WHERE {where_cond} AND c.academic_year IS NOT NULL ORDER BY c.academic_year DESC")
        academic_years = [r["academic_year"] for r in cur.fetchall() if r["academic_year"]]

        cur.execute(f"SELECT DISTINCT c.round FROM medical_cutoffs c WHERE {where_cond} AND c.round IS NOT NULL ORDER BY c.round ASC")
        rounds = [r["round"] for r in cur.fetchall() if r["round"]]

        cur.execute(f"""
            SELECT DISTINCT col.id, col.college_code, col.college_name, col.college_type, col.city, col.state 
            FROM medical_colleges col
            JOIN medical_cutoffs c ON c.college_id = col.id
            WHERE {where_cond}
            ORDER BY col.college_name ASC
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

        cur.execute(f"""
            SELECT DISTINCT crs.id, crs.course_code, crs.course_name, crs.degree_type 
            FROM medical_courses crs
            JOIN medical_cutoffs c ON c.course_id = crs.id
            WHERE {where_cond}
            ORDER BY crs.id ASC
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

        cur.execute(f"""
            SELECT DISTINCT col.college_type 
            FROM medical_colleges col
            JOIN medical_cutoffs c ON c.college_id = col.id
            WHERE {where_cond} AND col.college_type IS NOT NULL 
            ORDER BY col.college_type ASC
        """)
        college_types = [r["college_type"] for r in cur.fetchall()]

        cur.execute(f"SELECT DISTINCT c.base_category FROM medical_cutoffs c WHERE {where_cond} AND c.base_category IS NOT NULL ORDER BY c.base_category ASC")
        categories = [r["base_category"] for r in cur.fetchall()]

        cur.execute(f"SELECT DISTINCT c.quota_category FROM medical_cutoffs c WHERE {where_cond} AND c.quota_category IS NOT NULL ORDER BY c.quota_category ASC")
        quotas = [r["quota_category"] for r in cur.fetchall()]

        cur.execute(f"""
            SELECT DISTINCT col.state 
            FROM medical_colleges col
            JOIN medical_cutoffs c ON c.college_id = col.id
            WHERE {where_cond} AND col.state IS NOT NULL AND col.state != ''
            ORDER BY col.state ASC
        """)
        states = [r["state"] for r in cur.fetchall()]

        cur.execute(f"""
            SELECT DISTINCT col.city 
            FROM medical_colleges col
            JOIN medical_cutoffs c ON c.college_id = col.id
            WHERE {where_cond} AND col.city IS NOT NULL AND col.city != ''
            ORDER BY col.city ASC
        """)
        cities = [r["city"] for r in cur.fetchall()]

        return {
            "academic_years": academic_years,
            "rounds": rounds,
            "colleges": colleges,
            "courses": courses,
            "college_types": college_types,
            "categories": categories,
            "quotas": quotas,
            "states": states,
            "cities": cities,
        }
    finally:
        conn.close()


def query_medical_cutoffs(
    counselling_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    round_name: Optional[str] = None,
    college_id: Optional[int] = None,
    college_name: Optional[str] = None,
    course_id: Optional[int] = None,
    course_name: Optional[str] = None,
    college_type: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    quota: Optional[str] = None,
    gender: Optional[str] = None,
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
    Search and filter cutoffs from Supabase PostgreSQL (production) or SQLite (local)
    with pagination and student chance calculation.
    """
    init_medical_database(counselling_type)

    is_pg = engine.dialect.name == "postgresql"

    where_clauses = ["1=1"]
    params: Dict[str, Any] = {}
    sqlite_params: List[Any] = []

    # Counselling Type filter: central (MCC) vs state (Maharashtra)
    if counselling_type:
        c_low = counselling_type.lower()
        if c_low in ("central", "mcc", "aiq"):
            where_clauses.append("(c.exam_name LIKE '%MCC%' OR c.counselling_type = 'central')")
        elif c_low in ("state", "maha", "state_cet"):
            where_clauses.append("(c.exam_name NOT LIKE '%MCC%' AND c.counselling_type != 'central')")

    # State filter
    if state:
        if "||" in state or "," in state:
            st_list = [s.strip() for s in re.split(r"\|\||,", state) if s.strip()]
            if is_pg:
                where_clauses.append("col.state = ANY(:st_list)")
                params["st_list"] = st_list
            else:
                placeholders = ",".join(["?"] * len(st_list))
                where_clauses.append(f"col.state IN ({placeholders})")
                sqlite_params.extend(st_list)
        else:
            if is_pg:
                where_clauses.append("col.state = :state")
                params["state"] = state.strip()
            else:
                where_clauses.append("col.state = ?")
                sqlite_params.append(state.strip())

    # City filter
    if city:
        if "||" in city or "," in city:
            ct_list = [c.strip() for c in re.split(r"\|\||,", city) if c.strip()]
            if is_pg:
                where_clauses.append("col.city = ANY(:ct_list)")
                params["ct_list"] = ct_list
            else:
                placeholders = ",".join(["?"] * len(ct_list))
                where_clauses.append(f"col.city IN ({placeholders})")
                sqlite_params.extend(ct_list)
        else:
            if is_pg:
                where_clauses.append("col.city = :city")
                params["city"] = city.strip()
            else:
                where_clauses.append("col.city = ?")
                sqlite_params.append(city.strip())

    # Academic Year filter
    if academic_year:
        if "," in academic_year:
            y_list = [y.strip() for y in academic_year.split(",") if y.strip()]
            if is_pg:
                where_clauses.append("c.academic_year = ANY(:y_list)")
                params["y_list"] = y_list
            else:
                placeholders = ",".join(["?"] * len(y_list))
                where_clauses.append(f"c.academic_year IN ({placeholders})")
                sqlite_params.extend(y_list)
        else:
            if is_pg:
                where_clauses.append("c.academic_year = :year")
                params["year"] = academic_year.strip()
            else:
                where_clauses.append("c.academic_year = ?")
                sqlite_params.append(academic_year.strip())

    # Round filter
    if round_name:
        if "," in round_name:
            r_list = [r.strip() for r in round_name.split(",") if r.strip()]
            if is_pg:
                where_clauses.append("c.round = ANY(:r_list)")
                params["r_list"] = r_list
            else:
                placeholders = ",".join(["?"] * len(r_list))
                where_clauses.append(f"c.round IN ({placeholders})")
                sqlite_params.extend(r_list)
        else:
            if is_pg:
                where_clauses.append("c.round = :round")
                params["round"] = round_name.strip()
            else:
                where_clauses.append("c.round = ?")
                sqlite_params.append(round_name.strip())

    # College ID
    if college_id:
        if is_pg:
            where_clauses.append("c.college_id = :college_id")
            params["college_id"] = college_id
        else:
            where_clauses.append("c.college_id = ?")
            sqlite_params.append(college_id)

    # College Name/Code query
    if college_name:
        c_names = [c.strip() for c in re.split(r"\|\||,", college_name) if c.strip()]
        if c_names:
            if is_pg:
                conds = []
                for idx, c_item in enumerate(c_names):
                    key = f"col_name_{idx}"
                    conds.append(f"(col.college_name ILIKE :{key} OR col.college_code ILIKE :{key})")
                    params[key] = f"%{c_item}%"
                where_clauses.append(f"({' OR '.join(conds)})")
            else:
                conds = ["(col.college_name LIKE ? OR col.college_code LIKE ?)" for _ in c_names]
                where_clauses.append(f"({' OR '.join(conds)})")
                for c_item in c_names:
                    sqlite_params.append(f"%{c_item}%")
                    sqlite_params.append(f"%{c_item}%")

    # Course ID
    if course_id:
        if is_pg:
            where_clauses.append("c.course_id = :course_id")
            params["course_id"] = course_id
        else:
            where_clauses.append("c.course_id = ?")
            sqlite_params.append(course_id)

    # Course Name query
    if course_name:
        cr_names = [cr.strip() for cr in re.split(r"\|\||,", course_name) if cr.strip()]
        if cr_names:
            if is_pg:
                conds = []
                for idx, cr_item in enumerate(cr_names):
                    key = f"crs_name_{idx}"
                    conds.append(f"(crs.course_name ILIKE :{key} OR crs.course_code ILIKE :{key})")
                    params[key] = f"%{cr_item}%"
                where_clauses.append(f"({' OR '.join(conds)})")
            else:
                conds = ["(crs.course_name LIKE ? OR crs.course_code LIKE ?)" for _ in cr_names]
                where_clauses.append(f"({' OR '.join(conds)})")
                for cr_item in cr_names:
                    sqlite_params.append(f"%{cr_item}%")
                    sqlite_params.append(f"%{cr_item}%")

    # College Type
    if college_type:
        t_list = [t.strip() for t in re.split(r"\|\||,", college_type) if t.strip()]
        if is_pg:
            where_clauses.append("col.college_type = ANY(:t_list)")
            params["t_list"] = t_list
        else:
            placeholders = ",".join(["?"] * len(t_list))
            where_clauses.append(f"col.college_type IN ({placeholders})")
            sqlite_params.extend(t_list)

    # Base Category
    if category:
        cat_list = [cat.strip() for cat in re.split(r"\|\||,", category) if cat.strip()]
        if is_pg:
            where_clauses.append("c.base_category = ANY(:cat_list)")
            params["cat_list"] = cat_list
        else:
            placeholders = ",".join(["?"] * len(cat_list))
            where_clauses.append(f"c.base_category IN ({placeholders})")
            sqlite_params.extend(cat_list)

    # Quota Category
    if quota:
        q_list = [q.strip() for q in re.split(r"\|\||,", quota) if q.strip()]
        if is_pg:
            where_clauses.append("c.quota_category = ANY(:q_list)")
            params["q_list"] = q_list
        else:
            placeholders = ",".join(["?"] * len(q_list))
            where_clauses.append(f"c.quota_category IN ({placeholders})")
            sqlite_params.extend(q_list)

    # Gender / Seat Quota filter
    if gender:
        g_val = gender.strip().lower()
        if g_val in ("women", "female", "w"):
            where_clauses.append(
                "((c.quota_category LIKE '%(W)%' OR c.quota_category LIKE '% (W)%' "
                "OR c.quota_category LIKE '%W' OR c.quota_category = 'W' "
                "OR c.quota_category LIKE '%Women%') "
                "AND c.quota_category NOT IN ('EWS', 'HEWS', 'PHEWS', 'PWD'))"
            )
        elif g_val in ("general", "male", "gen", "open"):
            where_clauses.append(
                "(NOT ((c.quota_category LIKE '%(W)%' OR c.quota_category LIKE '% (W)%' "
                "OR c.quota_category LIKE '%W' OR c.quota_category = 'W' "
                "OR c.quota_category LIKE '%Women%') "
                "AND c.quota_category NOT IN ('EWS', 'HEWS', 'PHEWS', 'PWD')))"
            )

    # Rank ranges
    if min_rank is not None:
        if is_pg:
            where_clauses.append("c.closing_rank >= :min_rank")
            params["min_rank"] = min_rank
        else:
            where_clauses.append("c.closing_rank >= ?")
            sqlite_params.append(min_rank)
    if max_rank is not None:
        if is_pg:
            where_clauses.append("c.closing_rank <= :max_rank")
            params["max_rank"] = max_rank
        else:
            where_clauses.append("c.closing_rank <= ?")
            sqlite_params.append(max_rank)

    # Score ranges
    if min_score is not None:
        if is_pg:
            where_clauses.append("c.closing_score >= :min_score")
            params["min_score"] = min_score
        else:
            where_clauses.append("c.closing_score >= ?")
            sqlite_params.append(min_score)
    if max_score is not None:
        if is_pg:
            where_clauses.append("c.closing_score <= :max_score")
            params["max_score"] = max_score
        else:
            where_clauses.append("c.closing_score <= ?")
            sqlite_params.append(max_score)

    # Student NEET AIR filter
    if student_rank is not None:
        threshold = int(student_rank * 0.90)
        if is_pg:
            where_clauses.append("(c.closing_rank IS NOT NULL AND c.closing_rank >= :student_threshold)")
            params["student_threshold"] = threshold
        else:
            where_clauses.append("(c.closing_rank IS NOT NULL AND c.closing_rank >= ?)")
            sqlite_params.append(threshold)

    # Student NEET Score filter
    if student_score is not None:
        if is_pg:
            where_clauses.append("(c.closing_score IS NULL OR c.closing_score <= :student_score)")
            params["student_score"] = student_score
        else:
            where_clauses.append("(c.closing_score IS NULL OR c.closing_score <= ?)")
            sqlite_params.append(student_score)

    where_sql = " AND ".join(where_clauses)

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

    offset = (page - 1) * page_size

    if is_pg:
        # Execute in Supabase PostgreSQL
        with engine.connect() as conn:
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM medical_cutoffs c
                JOIN medical_colleges col ON c.college_id = col.id
                JOIN medical_courses crs ON c.course_id = crs.id
                WHERE {where_sql}
            """
            total = conn.execute(text(count_sql), params).scalar() or 0

            query_sql = f"""
                SELECT 
                    c.id, c.academic_year, c.round, c.quota_category, c.base_category,
                    c.opening_rank, c.closing_rank, c.opening_score, c.closing_score,
                    c.allotted_seats, c.exam_name,
                    col.id AS college_id, col.college_code, col.college_name, col.college_type, col.city, col.state,
                    crs.id AS course_id, crs.course_code, crs.course_name, crs.degree_type
                FROM medical_cutoffs c
                JOIN medical_colleges col ON c.college_id = col.id
                JOIN medical_courses crs ON c.course_id = crs.id
                WHERE {where_sql}
                ORDER BY {order_by_sql}
                LIMIT :limit OFFSET :offset
            """
            exec_params = {**params, "limit": page_size, "offset": offset}
            rows = conn.execute(text(query_sql), exec_params).mappings().fetchall()
    else:
        # Execute in SQLite
        conn = get_medical_connection(counselling_type)
        try:
            cur = conn.cursor()
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM medical_cutoffs c
                JOIN medical_colleges col ON c.college_id = col.id
                JOIN medical_courses crs ON c.course_id = crs.id
                WHERE {where_sql}
            """
            cur.execute(count_sql, sqlite_params)
            total = cur.fetchone()["total"]

            query_sql = f"""
                SELECT 
                    c.id, c.academic_year, c.round, c.quota_category, c.base_category,
                    c.opening_rank, c.closing_rank, c.opening_score, c.closing_score,
                    c.allotted_seats, c.exam_name,
                    col.id AS college_id, col.college_code, col.college_name, col.college_type, col.city, col.state,
                    crs.id AS course_id, crs.course_code, crs.course_name, crs.degree_type
                FROM medical_cutoffs c
                JOIN medical_colleges col ON c.college_id = col.id
                JOIN medical_courses crs ON c.course_id = crs.id
                WHERE {where_sql}
                ORDER BY {order_by_sql}
                LIMIT ? OFFSET ?
            """
            cur.execute(query_sql, sqlite_params + [page_size, offset])
            rows = cur.fetchall()
        finally:
            conn.close()

    items = []
    for r in rows:
        c_rank = r["closing_rank"]
        c_score = r["closing_score"]

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


def get_medical_stats() -> Dict[str, Any]:
    """
    Returns counts of cutoffs, colleges, courses, available years from Supabase PostgreSQL (production)
    or local SQLite databases.
    """
    init_medical_database()

    is_pg = engine.dialect.name == "postgresql"

    if is_pg:
        with engine.connect() as conn:
            total_cutoffs = conn.execute(text("SELECT COUNT(id) FROM medical_cutoffs")).scalar() or 0
            mcc_cutoff_count = conn.execute(text("SELECT COUNT(id) FROM medical_cutoffs WHERE counselling_type = 'central' OR exam_name LIKE '%MCC%'")).scalar() or 0
            state_cutoff_count = conn.execute(text("SELECT COUNT(id) FROM medical_cutoffs WHERE (counselling_type = 'state' OR exam_name NOT LIKE '%MCC%') AND counselling_type != 'central'")).scalar() or 0
            total_colleges = conn.execute(text("SELECT COUNT(id) FROM medical_colleges")).scalar() or 0
            course_count = conn.execute(text("SELECT COUNT(DISTINCT course_id) FROM medical_cutoffs")).scalar() or 8
            years = [
                r[0] for r in conn.execute(text("SELECT DISTINCT academic_year FROM medical_cutoffs ORDER BY academic_year DESC")).fetchall()
            ]

            types_rows = conn.execute(text("""
                SELECT col.college_type, COUNT(c.id) as cnt
                FROM medical_colleges col
                JOIN medical_cutoffs c ON c.college_id = col.id
                GROUP BY col.college_type
            """)).fetchall()
            college_types = {r[0]: r[1] for r in types_rows if r[0]}

            breakdown_rows = conn.execute(text("""
                SELECT crs.course_code, COUNT(c.id) as cnt
                FROM medical_courses crs
                JOIN medical_cutoffs c ON c.course_id = crs.id
                GROUP BY crs.course_code
            """)).fetchall()
            courses_breakdown = {r[0]: r[1] for r in breakdown_rows}

            return {
                "cutoff_count": total_cutoffs,
                "college_count": total_colleges,
                "course_count": course_count or 8,
                "years": years,
                "college_types": college_types,
                "courses_breakdown": courses_breakdown,
                "mcc_cutoff_count": mcc_cutoff_count,
                "state_cutoff_count": state_cutoff_count,
            }

    # SQLite
    conn_c = get_medical_connection("central")
    mcc_cutoff_count = 0
    mcc_college_count = 0
    c_years = []
    try:
        cur_c = conn_c.cursor()
        cur_c.execute("SELECT COUNT(*) AS total FROM medical_cutoffs")
        mcc_cutoff_count = cur_c.fetchone()["total"]
        cur_c.execute("SELECT COUNT(*) AS total FROM medical_colleges")
        mcc_college_count = cur_c.fetchone()["total"]
        cur_c.execute("SELECT DISTINCT academic_year FROM medical_cutoffs ORDER BY academic_year DESC")
        c_years = [r["academic_year"] for r in cur_c.fetchall()]
    finally:
        conn_c.close()

    conn_s = get_medical_connection("state")
    state_cutoff_count = 0
    state_college_count = 0
    s_years = []
    courses_breakdown = {}
    try:
        cur_s = conn_s.cursor()
        cur_s.execute("SELECT COUNT(*) AS total FROM medical_cutoffs")
        state_cutoff_count = cur_s.fetchone()["total"]
        cur_s.execute("SELECT COUNT(*) AS total FROM medical_colleges")
        state_college_count = cur_s.fetchone()["total"]
        cur_s.execute("SELECT DISTINCT academic_year FROM medical_cutoffs ORDER BY academic_year DESC")
        s_years = [r["academic_year"] for r in cur_s.fetchall()]
        cur_s.execute("""
            SELECT crs.course_code, COUNT(c.id) as count 
            FROM medical_courses crs
            LEFT JOIN medical_cutoffs c ON c.course_id = crs.id
            GROUP BY crs.course_code
        """)
        courses_breakdown = {r["course_code"]: r["count"] for r in cur_s.fetchall()}
    finally:
        conn_s.close()

    all_years = sorted(list(set(c_years + s_years)), reverse=True)
    total_cutoffs = mcc_cutoff_count + state_cutoff_count
    total_colleges = mcc_college_count + state_college_count

    return {
        "cutoff_count": total_cutoffs,
        "college_count": total_colleges,
        "course_count": 8,
        "years": all_years,
        "college_types": {
            "Central / Deemed / AIIMS": mcc_college_count,
            "Maharashtra State": state_college_count
        },
        "courses_breakdown": courses_breakdown,
        "mcc_cutoff_count": mcc_cutoff_count,
        "state_cutoff_count": state_cutoff_count,
    }


def wipe_medical_database(counselling_type: Optional[str] = None):
    """
    Safely resets medical database in PostgreSQL and/or SQLite.
    """
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            if counselling_type:
                c_low = counselling_type.lower()
                if c_low in ("state", "maha", "state_cet"):
                    conn.execute(text("DELETE FROM medical_cutoffs WHERE counselling_type = 'state' OR exam_name NOT LIKE '%MCC%'"))
                else:
                    conn.execute(text("DELETE FROM medical_cutoffs WHERE counselling_type = 'central' OR exam_name LIKE '%MCC%'"))
            else:
                conn.execute(text("DELETE FROM medical_cutoffs"))
                conn.execute(text("DELETE FROM medical_colleges"))
                conn.execute(text("DELETE FROM medical_courses"))
                conn.execute(text("DELETE FROM medical_meta"))
                conn.execute(text("DELETE FROM medical_import_batches"))
        return

    # SQLite
    streams = []
    if counselling_type:
        c_low = counselling_type.lower()
        if c_low in ("state", "maha", "state_cet"):
            streams = ["state"]
        else:
            streams = ["central"]
    else:
        streams = ["central", "state"]

    for stream in streams:
        conn = get_medical_connection(stream)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM medical_cutoffs;")
            cur.execute("DELETE FROM medical_colleges;")
            cur.execute("DELETE FROM medical_courses;")
            cur.execute("DELETE FROM medical_meta;")
            conn.commit()
        finally:
            conn.close()
