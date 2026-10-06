import os
import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path

# Resolve path to josaa.db
def get_josaa_db_path() -> Path:
    # 1. Project root
    root_path = Path(__file__).resolve().parent.parent.parent / "josaa.db"
    if root_path.exists():
        return root_path
    
    # 2. App root (inside Docker /app/josaa.db)
    app_path = Path(__file__).resolve().parent.parent / "josaa.db"
    if app_path.exists():
        return app_path

    # 3. Current working directory
    cwd_path = Path.cwd() / "josaa.db"
    if cwd_path.exists():
        return cwd_path
    
    # 4. Desktopossa fallback
    desktop_jossa = Path(r"C:\Users\HP\OneDrive\Desktop\jossa\database\josaa.db")
    if desktop_jossa.exists():
        return desktop_jossa

    # Default fallback
    return root_path

def get_josaa_connection() -> sqlite3.Connection:
    db_path = get_josaa_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_josaa_filter_options() -> Dict[str, Any]:
    conn = get_josaa_connection()
    try:
        cursor = conn.cursor()
        
        # Rounds
        cursor.execute("SELECT DISTINCT round_no FROM cutoff_records ORDER BY round_no ASC")
        rounds = [r["round_no"] for r in cursor.fetchall() if r["round_no"] is not None]
        
        # Academic Years
        cursor.execute("SELECT DISTINCT academic_year FROM cutoff_records ORDER BY academic_year DESC")
        years = [r["academic_year"] for r in cursor.fetchall() if r["academic_year"] is not None]

        # Institute Types
        cursor.execute("SELECT DISTINCT institute_type FROM institutes WHERE institute_type IS NOT NULL AND institute_type != '' ORDER BY institute_type ASC")
        institute_types = [r["institute_type"] for r in cursor.fetchall()]

        # Institutes
        cursor.execute("SELECT id, institute_code, institute_name, institute_type, state FROM institutes ORDER BY institute_name ASC")
        institutes = [
            {
                "id": r["id"],
                "institute_code": r["institute_code"],
                "institute_name": r["institute_name"],
                "institute_type": r["institute_type"],
                "state": r["state"],
            }
            for r in cursor.fetchall()
        ]

        # Programs
        cursor.execute("SELECT id, program_code, program_name, degree_type FROM programs ORDER BY program_name ASC")
        programs = [
            {
                "id": r["id"],
                "program_code": r["program_code"],
                "program_name": r["program_name"],
                "degree_type": r["degree_type"],
            }
            for r in cursor.fetchall()
        ]

        # Categories
        cursor.execute("SELECT id, category_code, category_name FROM categories ORDER BY id ASC")
        categories = [
            {
                "id": r["id"],
                "category_code": r["category_code"],
                "category_name": r["category_name"],
            }
            for r in cursor.fetchall()
        ]

        # Quotas
        cursor.execute("SELECT DISTINCT quota FROM cutoff_records WHERE quota IS NOT NULL AND quota != '' ORDER BY quota ASC")
        quotas = [r["quota"] for r in cursor.fetchall()]

        # Genders
        cursor.execute("SELECT DISTINCT gender FROM cutoff_records WHERE gender IS NOT NULL AND gender != '' ORDER BY gender ASC")
        genders = [r["gender"] for r in cursor.fetchall()]

        # Home States (from institutes with state populated)
        cursor.execute("SELECT DISTINCT state FROM institutes WHERE state IS NOT NULL AND state != '' ORDER BY state ASC")
        states = [r["state"] for r in cursor.fetchall()]

        return {
            "rounds": rounds,
            "years": years,
            "institute_types": institute_types,
            "institutes": institutes,
            "programs": programs,
            "categories": categories,
            "quotas": quotas,
            "genders": genders,
            "states": states,
        }
    finally:
        conn.close()

def query_josaa_cutoffs(
    round_no: Optional[str] = None,
    institute_type: Optional[str] = None,
    institute_name: Optional[str] = None,
    institute_id: Optional[int] = None,
    state: Optional[str] = None,
    candidate_state: Optional[str] = None,
    academic_program: Optional[str] = None,
    program_id: Optional[int] = None,
    category: Optional[str] = None,
    quota: Optional[str] = None,
    gender: Optional[str] = None,
    academic_year: Optional[int] = None,
    max_rank: Optional[int] = None,
    page: int = 1,
    page_size: int = 100,
    sort_by: str = "rank_asc",
) -> Dict[str, Any]:
    conn = get_josaa_connection()
    try:
        cursor = conn.cursor()

        where_clauses = ["1=1"]
        params = []

        if round_no is not None:
            round_str = str(round_no).strip()
            round_nums = [int(r.strip()) for r in round_str.split(',') if r.strip().isdigit()]
            if len(round_nums) == 1:
                where_clauses.append("cr.round_no = ?")
                params.append(round_nums[0])
            elif len(round_nums) > 1:
                placeholders = ','.join(['?' for _ in round_nums])
                where_clauses.append(f"cr.round_no IN ({placeholders})")
                params.extend(round_nums)

        if academic_year is not None:
            where_clauses.append("cr.academic_year = ?")
            params.append(academic_year)

        if institute_id is not None:
            where_clauses.append("cr.institute_id = ?")
            params.append(institute_id)
        elif institute_name:
            # Check for '||' delimiter first (safe for names containing commas)
            if "||" in institute_name:
                names = [n.strip() for n in institute_name.split("||") if n.strip()]
            else:
                names = [institute_name.strip()]

            if len(names) == 1:
                where_clauses.append("(i.institute_name = ? OR i.institute_name LIKE ?)")
                params.extend([names[0], f"%{names[0]}%"])
            elif len(names) > 1:
                clause_parts = []
                for n in names:
                    clause_parts.append("(i.institute_name = ? OR i.institute_name LIKE ?)")
                    params.extend([n, f"%{n}%"])
                where_clauses.append(f"({' OR '.join(clause_parts)})")

        if institute_type:
            types = [t.strip() for t in institute_type.split(",") if t.strip()]
            if len(types) == 1:
                where_clauses.append("i.institute_type = ?")
                params.append(types[0])
            elif len(types) > 1:
                placeholders = ",".join(["?" for _ in types])
                where_clauses.append(f"i.institute_type IN ({placeholders})")
                params.extend(types)

        if state:
            states = [s.strip() for s in state.split(",") if s.strip()]
            if len(states) == 1:
                where_clauses.append("(i.state = ? OR i.state LIKE ?)")
                params.extend([states[0], f"%{states[0]}%"])
            elif len(states) > 1:
                clause_parts = []
                for s in states:
                    clause_parts.append("(i.state = ? OR i.state LIKE ?)")
                    params.extend([s, f"%{s}%"])
                where_clauses.append(f"({' OR '.join(clause_parts)})")

        # Candidate Home State Quota Resolver:
        # Candidate is eligible for:
        # 1. 'AI' (All India) quota across all institutes (IITs, IIITs, GFTIs)
        # 2. 'HS' (Home State) quota where institute is located in candidate's home state
        # 3. 'OS' (Other State) quota where institute is located outside candidate's home state
        # 4. Special quotas: 'GO' (if candidate is from Goa), 'JK' (if candidate is from J&K), 'LA' (if candidate is from Ladakh)
        if candidate_state:
            c_states = [s.strip() for s in candidate_state.split(",") if s.strip()]
            if len(c_states) == 1:
                cs = c_states[0]
                cand_clause = """(
                    cr.quota = 'AI'
                    OR (cr.quota = 'HS' AND (i.state = ? OR i.state LIKE ?))
                    OR (cr.quota = 'OS' AND (i.state IS NULL OR (i.state != ? AND i.state NOT LIKE ?)))
                    OR (cr.quota = 'GO' AND (? = 'Goa'))
                    OR (cr.quota = 'JK' AND (? = 'Jammu and Kashmir'))
                    OR (cr.quota = 'LA' AND (? = 'Ladakh'))
                )"""
                where_clauses.append(cand_clause)
                params.extend([cs, f"%{cs}%", cs, f"%{cs}%", cs, cs, cs])
            elif len(c_states) > 1:
                hs_parts = []
                os_parts = []
                for s in c_states:
                    hs_parts.append("(i.state = ? OR i.state LIKE ?)")
                    params.extend([s, f"%{s}%"])
                for s in c_states:
                    os_parts.append("(i.state != ? AND i.state NOT LIKE ?)")
                    params.extend([s, f"%{s}%"])

                special_parts = []
                if any(s.lower() == "goa" for s in c_states):
                    special_parts.append("cr.quota = 'GO'")
                if any("jammu" in s.lower() for s in c_states):
                    special_parts.append("cr.quota = 'JK'")
                if any("ladakh" in s.lower() for s in c_states):
                    special_parts.append("cr.quota = 'LA'")

                special_str = (" OR " + " OR ".join(special_parts)) if special_parts else ""
                cand_clause = f"""(
                    cr.quota = 'AI'
                    OR (cr.quota = 'HS' AND ({' OR '.join(hs_parts)}))
                    OR (cr.quota = 'OS' AND (i.state IS NULL OR ({' AND '.join(os_parts)})))
                    {special_str}
                )"""
                where_clauses.append(cand_clause)

        if program_id is not None:
            where_clauses.append("cr.program_id = ?")
            params.append(program_id)
        elif academic_program:
            # Check for '||' delimiter first (safe for program names containing commas)
            if "||" in academic_program:
                programs = [p.strip() for p in academic_program.split("||") if p.strip()]
            else:
                programs = [academic_program.strip()]

            if len(programs) == 1:
                where_clauses.append("(p.program_name = ? OR p.program_name LIKE ?)")
                params.extend([programs[0], f"%{programs[0]}%"])
            elif len(programs) > 1:
                clause_parts = []
                for p in programs:
                    clause_parts.append("(p.program_name = ? OR p.program_name LIKE ?)")
                    params.extend([p, f"%{p}%"])
                where_clauses.append(f"({' OR '.join(clause_parts)})")

        if category:
            cats = [c.strip() for c in category.split(",") if c.strip()]
            if len(cats) == 1:
                where_clauses.append("c.category_code = ?")
                params.append(cats[0])
            elif len(cats) > 1:
                placeholders = ",".join(["?" for _ in cats])
                where_clauses.append(f"c.category_code IN ({placeholders})")
                params.extend(cats)

        if quota:
            where_clauses.append("cr.quota = ?")
            params.append(quota)

        if gender:
            if "female" in gender.lower() or "ladies" in gender.lower():
                where_clauses.append("cr.gender LIKE '%Female%'")
            elif "neutral" in gender.lower():
                where_clauses.append("cr.gender LIKE '%Neutral%'")
            else:
                where_clauses.append("cr.gender = ?")
                params.append(gender)

        if max_rank is not None and max_rank > 0:
            # Candidate rank <= closing_rank (candidate is eligible)
            where_clauses.append("cr.closing_rank >= ?")
            params.append(max_rank)

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM cutoff_records cr
            JOIN institutes i ON cr.institute_id = i.id
            JOIN programs p ON cr.program_id = p.id
            JOIN categories c ON cr.category_id = c.id
            WHERE {where_sql}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]

        # Sort order
        order_by = "cr.closing_rank ASC, cr.opening_rank ASC"
        if sort_by == "rank_desc":
            order_by = "cr.closing_rank DESC, cr.opening_rank DESC"
        elif sort_by == "opening_rank_asc":
            order_by = "cr.opening_rank ASC, cr.closing_rank ASC"
        elif sort_by == "institute":
            order_by = "i.institute_name ASC, p.program_name ASC"
        elif sort_by == "program":
            order_by = "p.program_name ASC, cr.closing_rank ASC"

        # Pagination
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT 
                cr.id,
                cr.academic_year,
                cr.round_no,
                cr.quota,
                cr.gender,
                cr.opening_rank,
                cr.closing_rank,
                cr.is_preparatory,
                i.id AS institute_id,
                i.institute_code,
                i.institute_name,
                i.institute_type,
                i.state AS institute_state,
                p.id AS program_id,
                p.program_code,
                p.program_name,
                p.degree_type,
                c.id AS category_id,
                c.category_code,
                c.category_name
            FROM cutoff_records cr
            JOIN institutes i ON cr.institute_id = i.id
            JOIN programs p ON cr.program_id = p.id
            JOIN categories c ON cr.category_id = c.id
            WHERE {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        exec_params = list(params) + [page_size, offset]
        cursor.execute(query_sql, exec_params)
        rows = cursor.fetchall()

        items = [
            {
                "id": r["id"],
                "academic_year": r["academic_year"],
                "round_no": r["round_no"],
                "quota": r["quota"],
                "gender": r["gender"],
                "opening_rank": r["opening_rank"],
                "closing_rank": r["closing_rank"],
                "is_preparatory": bool(r["is_preparatory"]),
                "institute_id": r["institute_id"],
                "institute_code": r["institute_code"],
                "institute_name": r["institute_name"],
                "institute_type": r["institute_type"],
                "institute_state": r["institute_state"],
                "program_id": r["program_id"],
                "program_code": r["program_code"],
                "program_name": r["program_name"],
                "degree_type": r["degree_type"],
                "category_id": r["category_id"],
                "category_code": r["category_code"],
                "category_name": r["category_name"],
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

def wipe_josaa_database() -> Dict[str, Any]:
    """
    Safely wipes all records from josaa.db (cutoffs, programs, categories, institutes).
    Preserves SQLite schema so new data can be ingested or scraped immediately.
    """
    conn = get_josaa_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cutoff_records;")
        cursor.execute("DELETE FROM programs;")
        cursor.execute("DELETE FROM categories;")
        cursor.execute("DELETE FROM institutes;")
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('cutoff_records', 'programs', 'categories', 'institutes');")
        except Exception:
            pass
        conn.commit()
        return {"success": True, "message": "JoSAA database wiped successfully."}
    finally:
        conn.close()

def reload_sample_josaa_data() -> Dict[str, Any]:
    """
    Re-seeds official institute registry and cutoffs into josaa.db.
    First attempts full official ingestion (65,000+ records across 5 rounds),
    falling back to local sample seed file if offline.
    """
    try:
        from app.services.ingest_official_josaa_dataset import ingest_all_official_rounds
        res = ingest_all_official_rounds(year=2025)
        if isinstance(res, dict) and res.get("success"):
            return res
    except Exception as e:
        print(f"[!] Official online ingestion fallback triggered: {e}")

    import json
    import re

    conn = get_josaa_connection()
    try:
        cursor = conn.cursor()

        # Locate institute_registry.json
        candidate_paths = [
            Path(r"C:\Users\HP\OneDrive\Desktop\jossa\scripts\institute_registry.json"),
            Path(__file__).resolve().parent.parent.parent / "institute_registry.json"
        ]
        registry_path = next((p for p in candidate_paths if p.exists()), None)
        
        sample_paths = [
            Path(r"C:\Users\HP\OneDrive\Desktop\jossa\scripts\sample_josaa_data.json"),
            Path(__file__).resolve().parent.parent.parent / "sample_josaa_data.json"
        ]
        sample_path = next((p for p in sample_paths if p.exists()), None)

        if not registry_path or not sample_path:
            return {"success": False, "message": "Seed data files not found"}

        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        for inst_name, meta in registry.items():
            cursor.execute("""
                INSERT OR REPLACE INTO institutes (institute_code, institute_name, institute_type, state)
                VALUES (?, ?, ?, ?)
            """, (meta["code"], inst_name, meta["type"], meta.get("state")))

        with open(sample_path, "r", encoding="utf-8") as f:
            raw_records = json.load(f)

        def parse_deg(p_name: str) -> str:
            p = p_name.lower()
            if "dual degree" in p or "bachelor and master" in p:
                return "Dual Degree"
            if "integrated master" in p or "integrated m.tech" in p:
                return "Integrated M.Tech"
            if "bachelor of architecture" in p or "b.arch" in p:
                return "B.Arch"
            if "bachelor of planning" in p or "b.plan" in p:
                return "B.Plan"
            if "bachelor of science" in p or "bs" in p:
                return "BS"
            return "B.Tech"

        def parse_rk(val: Any):
            s = str(val).strip()
            is_p = "P" in s.upper()
            d = re.sub(r"[^\d]", "", s)
            return int(d) if d else 0, 1 if is_p else 0

        for r in raw_records:
            round_no = int(r.get("roundNo") or r.get("round") or 1)
            inst_name = r.get("instituteName", "").strip()
            cursor.execute("SELECT id FROM institutes WHERE institute_name = ?", (inst_name,))
            inst_row = cursor.fetchone()
            inst_id = inst_row[0] if inst_row else 1

            prog_name = r.get("programName", "").strip()
            deg = parse_deg(prog_name)
            cursor.execute("SELECT id FROM programs WHERE program_name = ?", (prog_name,))
            prog_row = cursor.fetchone()
            if not prog_row:
                cursor.execute("INSERT INTO programs (program_name, degree_type) VALUES (?, ?)", (prog_name, deg))
                prog_id = cursor.lastrowid
            else:
                prog_id = prog_row[0]

            cat_code = r.get("seatType", "").strip()
            cursor.execute("SELECT id FROM categories WHERE category_code = ?", (cat_code,))
            cat_row = cursor.fetchone()
            if not cat_row:
                cursor.execute("INSERT INTO categories (category_code, category_name) VALUES (?, ?)", (cat_code, cat_code))
                cat_id = cursor.lastrowid
            else:
                cat_id = cat_row[0]

            open_rk, open_p = parse_rk(r.get("openingRank"))
            close_rk, close_p = parse_rk(r.get("closingRank"))
            is_p = 1 if (open_p or close_p) else 0
            gender = r.get("gender", "Gender-Neutral").strip()

            cursor.execute("""
                INSERT OR REPLACE INTO cutoff_records (
                    academic_year, round_no, institute_id, program_id, category_id,
                    quota, gender, opening_rank, closing_rank, is_preparatory
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(r.get("academicYear", 2025)),
                round_no,
                inst_id,
                prog_id,
                cat_id,
                r.get("quota", "AI").strip().upper(),
                gender,
                open_rk,
                close_rk,
                is_p
            ))

        conn.commit()
        return {"success": True, "message": f"Successfully reloaded {len(raw_records)} official records into JoSAA database."}
    finally:
        conn.close()

