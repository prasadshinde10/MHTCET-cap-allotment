import sqlite3
import logging
from app.database import SessionLocal
from app.auth.seed import seed_admin_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate():
    logger.info("Starting population of backend tables from cutoff_records...")
    conn = sqlite3.connect('cutoff.db')
    cur = conn.cursor()
    
    # 1. Seed/ensure admin user
    db = SessionLocal()
    try:
        seed_admin_user(db)
        logger.info("Admin user seeded/verified.")
    finally:
        db.close()

    # 2. Populate cap_rounds
    logger.info("Populating cap_rounds...")
    cur.execute("DELETE FROM cap_rounds;")
    for r in range(1, 5):
        cnt = cur.execute("SELECT COUNT(*) FROM cutoff_records WHERE cap_round = ?", (r,)).fetchone()[0]
        pages = cur.execute("SELECT MAX(page_number) FROM cutoff_records WHERE cap_round = ?", (r,)).fetchone()[0] or 0
        cur.execute("""
            INSERT INTO cap_rounds (id, year, round_number, round_name, source_filename, processing_status, total_records, total_pages, error_count, created_at, updated_at)
            VALUES (?, 2024, ?, ?, ?, 'COMPLETED', ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (r, r, f"CAP Round {r}", f"MHT-CET_CAP{r}_Cutoff.pdf", cnt, pages))

    # 3. Populate colleges
    logger.info("Populating colleges...")
    cur.execute("DELETE FROM colleges;")
    cur.execute("""
        INSERT INTO colleges (college_code, college_name, city, district, college_type, funding_type, minority_status, minority_type, home_university, status, created_at, updated_at)
        SELECT 
            college_code,
            college_name,
            district AS city,
            district,
            COALESCE(is_autonomous, 'Unknown') AS college_type,
            COALESCE(governance_type, 'Unknown') AS funding_type,
            'Non-Minority' AS minority_status,
            '' AS minority_type,
            '' AS home_university,
            'Active' AS status,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM cutoff_records
        GROUP BY college_code;
    """)

    # 4. Populate courses
    logger.info("Populating courses...")
    cur.execute("DELETE FROM courses;")
    cur.execute("""
        INSERT INTO courses (college_id, course_code, course_name, created_at, updated_at)
        SELECT 
            col.id AS college_id,
            cr.course_code,
            cr.course_name,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM (SELECT DISTINCT college_code, course_code, course_name FROM cutoff_records) cr
        JOIN colleges col ON col.college_code = cr.college_code
        GROUP BY col.id, cr.course_code;
    """)

    # 5. Populate cutoffs
    logger.info("Populating cutoffs from cutoff_records...")
    cur.execute("DELETE FROM cutoffs;")
    cur.execute("""
        INSERT INTO cutoffs (
            year, cap_round_id, course_id, seat_section, seat_section_raw,
            category_code, gender, seat_category, stage, merit_number,
            percentile, source_page, source_pdf, is_manually_corrected, is_deleted,
            created_at, updated_at
        )
        SELECT
            2024 AS year,
            r.cap_round AS cap_round_id,
            crs.id AS course_id,
            COALESCE(r.quota_type, r.seat_category, 'State Level') AS seat_section,
            r.seat_category AS seat_section_raw,
            COALESCE(r.category, 'OPEN') AS category_code,
            CASE 
                WHEN r.category LIKE 'L%' THEN 'Ladies'
                WHEN r.category LIKE 'G%' THEN 'General'
                ELSE 'General'
            END AS gender,
            r.seat_category AS seat_category,
            COALESCE(r.stage, 'Stage-I') AS stage,
            r.merit_rank AS merit_number,
            r.percentile AS percentile,
            r.page_number AS source_page,
            'CAP' || r.cap_round || '_Cutoff.pdf' AS source_pdf,
            0 AS is_manually_corrected,
            0 AS is_deleted,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM cutoff_records r
        JOIN colleges col ON col.college_code = r.college_code
        JOIN courses crs ON crs.college_id = col.id AND crs.course_code = r.course_code;
    """)

    conn.commit()

    # Verification
    col_cnt = cur.execute("SELECT COUNT(*) FROM colleges;").fetchone()[0]
    crs_cnt = cur.execute("SELECT COUNT(*) FROM courses;").fetchone()[0]
    cut_cnt = cur.execute("SELECT COUNT(*) FROM cutoffs;").fetchone()[0]
    rnd_cnt = cur.execute("SELECT COUNT(*) FROM cap_rounds;").fetchone()[0]
    adm_cnt = cur.execute("SELECT COUNT(*) FROM admin_users;").fetchone()[0]

    logger.info("=== POPULATION COMPLETE ===")
    logger.info(f"Colleges: {col_cnt}")
    logger.info(f"Courses: {crs_cnt}")
    logger.info(f"Cutoffs: {cut_cnt}")
    logger.info(f"CAP Rounds: {rnd_cnt}")
    logger.info(f"Admin Users: {adm_cnt}")

    conn.close()

if __name__ == "__main__":
    populate()
