#!/usr/bin/env python3
"""
Enhanced Search & Query Tool for cutoff.db
Supports querying multi-round CAP cutoffs (CAP 1, 2, 3, 4), normalized institutes,
course choices, total intake, affiliated universities, and minority status.
"""

import sqlite3
import sys

DB_PATH = "cutoff.db"

def filter_records(cap_round=None, branch=None, district=None, university=None, minority=None, category=None, autonomy=None, status=None, reservation=None):
    """Filters cutoff records joined with scraped institute metadata across CAP rounds."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT
            c.cap_round,
            c.college_code,
            COALESCE(i.institute_name, c.college_name) AS institute_name,
            i.district,
            i.affiliated_university,
            c.course_name,
            i.status,
            i.autonomy_status,
            i.minority_status,
            c.reservation_level,
            c.seat_category,
            c.category,
            c.merit_rank,
            c.percentile
        FROM cutoff_records c
        LEFT JOIN institutes i ON c.college_code = i.dte_code
        WHERE 1=1
    """
    params = []

    if cap_round:
        query += " AND c.cap_round = ?"
        params.append(int(cap_round))
    if branch:
        query += " AND c.course_name LIKE ?"
        params.append(f"%{branch}%")
    if district:
        query += " AND i.district LIKE ?"
        params.append(f"%{district}%")
    if university:
        query += " AND i.affiliated_university LIKE ?"
        params.append(f"%{university}%")
    if minority:
        query += " AND i.minority_status LIKE ?"
        params.append(f"%{minority}%")
    if category:
        query += " AND (c.seat_category = ? OR c.category = ?)"
        params.extend([category.upper(), category.upper()])
    if autonomy:
        query += " AND i.autonomy_status LIKE ?"
        params.append(f"%{autonomy}%")
    if status:
        query += " AND i.status LIKE ?"
        params.append(f"%{status}%")
    if reservation:
        query += " AND c.reservation_level LIKE ?"
        params.append(f"%{reservation}%")

    query += " ORDER BY c.merit_rank ASC LIMIT 25;"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No matching cutoff records found.")
        return

    print(f"\n--- Found matching record(s) (Showing top {len(rows)}) ---")
    for r in rows:
        print(f"[CAP Round {r[0]}] [{r[1]}] {r[2]}")
        print(f"    District: {r[3]} | University: {r[4]}")
        print(f"    Branch: {r[5]} | Autonomy: {r[7]} | Status: {r[6]}")
        print(f"    Minority: {r[8]} | Quota: {r[9]} | Cat: {r[10]} ({r[11]})")
        print(f"    Cutoff Rank: {r[12]} | Percentile: {r[13]}")
        print("-" * 75)


def search_courses(branch=None, district=None, university=None, min_intake=0):
    """Searches branchwise intake from institute_courses table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT
            ic.choice_code,
            i.institute_name,
            i.district,
            ic.course_name,
            ic.university,
            ic.status,
            ic.autonomy_status,
            ic.gender_type,
            ic.total_intake
        FROM institute_courses ic
        JOIN institutes i ON ic.dte_code = i.dte_code
        WHERE ic.total_intake >= ?
    """
    params = [min_intake]

    if branch:
        query += " AND ic.course_name LIKE ?"
        params.append(f"%{branch}%")
    if district:
        query += " AND i.district LIKE ?"
        params.append(f"%{district}%")
    if university:
        query += " AND ic.university LIKE ?"
        params.append(f"%{university}%")

    query += " ORDER BY ic.total_intake DESC LIMIT 25;"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No matching course intake records found.")
        return

    print(f"\n--- Course Intake Results (Showing top {len(rows)}) ---")
    for r in rows:
        print(f"[{r[0]}] {r[1]} ({r[2]})")
        print(f"    Course: {r[3]} | University: {r[4]}")
        print(f"    Status: {r[5]} ({r[6]}) | Type: {r[7]} | Total Intake: {r[8]}")
        print("-" * 75)


def custom_sql(sql_query: str):
    """Executes custom SQL query on cutoff.db."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cols = [description[0] for description in cursor.description]
        print(" | ".join(cols))
        print("=" * 80)
        for r in rows[:25]:
            print(" | ".join(str(x) for x in r))
        print(f"\nTotal rows returned: {len(rows)}")
    except Exception as e:
        print(f"SQL Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sql" and len(sys.argv) > 2:
        custom_sql(" ".join(sys.argv[2:]))
    elif len(sys.argv) > 1 and sys.argv[1] == "intake":
        print("Example Intake Query: Computer Engineering courses in Pune District")
        search_courses(branch="Computer", district="Pune")
    else:
        print("Example Multi-Round Cutoff Query: Computer Science in Pune District (CAP Round 1 & 2)")
        filter_records(cap_round=1, branch="Computer", district="Pune", category="OPEN", autonomy="Autonomous")
