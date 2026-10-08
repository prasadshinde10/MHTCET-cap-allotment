import os
import sqlite3
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

# Path to dedicated medical.db
# Paths to dedicated medical databases (separate for Central MCC and State CET Cell)
def get_medical_db_path(counselling_type: Optional[str] = None) -> Path:
    c_low = (counselling_type or "").lower().strip()
    is_state = c_low in ("state", "maha", "state_cet", "maharashtra")
    db_filename = "medical_state.db" if is_state else "medical_central.db"

    app_path = Path(__file__).resolve().parent.parent / db_filename
    if app_path.exists():
        return app_path
    root_path = Path(__file__).resolve().parent.parent.parent / db_filename
    if root_path.exists():
        return root_path
    cwd_path = Path.cwd() / db_filename
    if cwd_path.exists():
        return cwd_path
    return app_path


def get_medical_connection(counselling_type: Optional[str] = None) -> sqlite3.Connection:
    db_path = get_medical_db_path(counselling_type)
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def _init_single_db(conn: sqlite3.Connection):
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


def init_medical_database(counselling_type: Optional[str] = None):
    """
    Initializes dedicated Medical database schema and indexes for Central and/or State DBs.
    Completely isolated from MHT CET, JoSAA, IISER, and BITS.
    """
    if counselling_type:
        _init_single_db(get_medical_connection(counselling_type))
    else:
        _init_single_db(get_medical_connection("central"))
        _init_single_db(get_medical_connection("state"))


def fetch_medical_filter_options(counselling_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns available filter options from the dedicated Central or State medical database:
    academic_years, rounds, colleges, courses, college_types, categories, quotas, states, cities.
    """
    init_medical_database(counselling_type)
    conn = get_medical_connection(counselling_type)
    try:
        cur = conn.cursor()

        where_cond = "1=1"
        if counselling_type:
            c_low = counselling_type.lower()
            if c_low in ("central", "mcc", "aiq"):
                where_cond = "c.exam_name LIKE '%MCC%'"
            elif c_low in ("state", "maha", "state_cet"):
                where_cond = "c.exam_name NOT LIKE '%MCC%'"

        # Academic Years sorted descending
        cur.execute(f"SELECT DISTINCT c.academic_year FROM medical_cutoffs c WHERE {where_cond} AND c.academic_year IS NOT NULL ORDER BY c.academic_year DESC")
        academic_years = [r["academic_year"] for r in cur.fetchall() if r["academic_year"]]

        # Rounds
        cur.execute(f"SELECT DISTINCT c.round FROM medical_cutoffs c WHERE {where_cond} AND c.round IS NOT NULL ORDER BY c.round ASC")
        rounds = [r["round"] for r in cur.fetchall() if r["round"]]

        # Colleges
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

        # Courses
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

        # College Types
        cur.execute(f"""
            SELECT DISTINCT col.college_type 
            FROM medical_colleges col
            JOIN medical_cutoffs c ON c.college_id = col.id
            WHERE {where_cond} AND col.college_type IS NOT NULL 
            ORDER BY col.college_type ASC
        """)
        college_types = [r["college_type"] for r in cur.fetchall()]

        # Base Categories
        cur.execute(f"SELECT DISTINCT c.base_category FROM medical_cutoffs c WHERE {where_cond} AND c.base_category IS NOT NULL ORDER BY c.base_category ASC")
        categories = [r["base_category"] for r in cur.fetchall()]

        # Quotas
        cur.execute(f"SELECT DISTINCT c.quota_category FROM medical_cutoffs c WHERE {where_cond} AND c.quota_category IS NOT NULL ORDER BY c.quota_category ASC")
        quotas = [r["quota_category"] for r in cur.fetchall()]

        # Indian States (especially for MCC Central Counselling)
        cur.execute(f"""
            SELECT DISTINCT col.state 
            FROM medical_colleges col
            JOIN medical_cutoffs c ON c.college_id = col.id
            WHERE {where_cond} AND col.state IS NOT NULL AND col.state != ''
            ORDER BY col.state ASC
        """)
        states = [r["state"] for r in cur.fetchall()]

        # Cities (especially for Maharashtra State Medical Counselling)
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
    Search and filter cutoffs from dedicated medical.db with pagination and student chance calculation.
    """
    init_medical_database(counselling_type)
    conn = get_medical_connection(counselling_type)
    try:
        cur = conn.cursor()

        where_clauses = ["1=1"]
        params: List[Any] = []

        # Counselling Type filter: central (MCC) vs state (Maharashtra)
        if counselling_type:
            c_low = counselling_type.lower()
            if c_low in ("central", "mcc", "aiq"):
                where_clauses.append("c.exam_name LIKE '%MCC%'")
            elif c_low in ("state", "maha", "state_cet"):
                where_clauses.append("c.exam_name NOT LIKE '%MCC%'")

        # Indian State filter (e.g. for Central MCC Counselling)
        if state:
            if "||" in state or "," in state:
                st_list = [s.strip() for s in re.split(r"\|\||,", state) if s.strip()]
                placeholders = ",".join(["?"] * len(st_list))
                where_clauses.append(f"col.state IN ({placeholders})")
                params.extend(st_list)
            else:
                where_clauses.append("col.state = ?")
                params.append(state.strip())

        # City filter (e.g. for State Medical Counselling)
        if city:
            if "||" in city or "," in city:
                ct_list = [c.strip() for c in re.split(r"\|\||,", city) if c.strip()]
                placeholders = ",".join(["?"] * len(ct_list))
                where_clauses.append(f"col.city IN ({placeholders})")
                params.extend(ct_list)
            else:
                where_clauses.append("col.city = ?")
                params.append(city.strip())

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

        # Gender / Seat Quota filter: women (horizontal 30% quota) vs general (open to all)
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
    Returns counts of cutoffs, colleges, courses, available years from both medical_central.db and medical_state.db.
    """
    init_medical_database()

    # 1. Central MCC Database
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

    # 2. State CET Cell Database
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
    Safely resets medical database(s).
    """
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
