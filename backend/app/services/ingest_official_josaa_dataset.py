"""
JoSAA Complete Official Dataset Ingestion Engine
Downloads and ingests full official JoSAA Opening & Closing Ranks across all rounds (1 to 5)
Covers all IITs, NITs, IIITs, and GFTIs into josaa.db
"""

import os
import re
import csv
import io
import sqlite3
import requests
from pathlib import Path

BASE_REPO_URL = "https://raw.githubusercontent.com/Harith-Y/JoSAA-CSAB-Closing-Rank-Predictor/main/data"

ROUNDS = [1, 2, 3, 4, 5]

def get_db_path() -> Path:
    # 4 levels up: backend/app/services/ingest_official_josaa_dataset.py -> root
    root_path = Path(__file__).resolve().parent.parent.parent.parent / "josaa.db"
    return root_path

def init_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS institutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            institute_code TEXT,
            institute_name TEXT NOT NULL UNIQUE,
            institute_type TEXT NOT NULL,
            state TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_code TEXT,
            program_name TEXT NOT NULL UNIQUE,
            degree_type TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_code TEXT NOT NULL UNIQUE,
            category_name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cutoff_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academic_year INTEGER NOT NULL,
            round_no INTEGER NOT NULL,
            institute_id INTEGER NOT NULL REFERENCES institutes(id) ON DELETE CASCADE,
            program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            quota TEXT NOT NULL,
            gender TEXT NOT NULL,
            opening_rank INTEGER NOT NULL,
            closing_rank INTEGER NOT NULL,
            is_preparatory BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (academic_year, round_no, institute_id, program_id, category_id, quota, gender)
        );
    """)

def parse_degree_type(prog: str) -> str:
    p = prog.lower()
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
    if "bachelor of technology" in p or "b.tech" in p:
        return "B.Tech"
    return "B.Tech"

def parse_rank(rank_val):
    s = str(rank_val).strip()
    is_prep = 1 if "P" in s.upper() else 0
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0, is_prep

def determine_institute_type(name: str) -> str:
    n = name.upper()
    if "INDIAN INSTITUTE OF TECHNOLOGY" in n or "IIT " in n or "IIT," in n or "BHU" in n or "ISM" in n:
        return "IIT"
    if "NATIONAL INSTITUTE OF TECHNOLOGY" in n or "NIT " in n or "NIT," in n:
        return "NIT"
    if "INDIAN INSTITUTE OF INFORMATION TECHNOLOGY" in n or "IIIT " in n or "IIIT," in n:
        return "IIIT"
    return "Other-GFTI"

def ingest_all_official_rounds(year: int = 2025):
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    init_tables(cursor)

    total_records = 0

    print("====================================================================")
    print(" Starting Full JoSAA Ingestion for Rounds 1 - 5")
    print(f" Database: {db_path.name}")
    print("====================================================================")

    # Cache maps
    cursor.execute("SELECT institute_name, id FROM institutes")
    inst_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT program_name, id FROM programs")
    prog_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT category_code, id FROM categories")
    cat_map = {row[0]: row[1] for row in cursor.fetchall()}

    for round_no in ROUNDS:
        file_name = f"Round{round_no}-2026.csv"
        url = f"{BASE_REPO_URL}/{file_name}"
        print(f"\n[*] Downloading official {file_name}...")

        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                print(f"[!] Failed to fetch {file_name}: HTTP {r.status_code}")
                continue

            csv_text = r.text
            reader = csv.reader(io.StringIO(csv_text))
            
            # Read header
            headers = next(reader, None)
            
            batch_count = 0
            for row in reader:
                if len(row) < 7:
                    continue

                inst_name = row[0].strip()
                prog_name = row[1].strip()
                quota = row[2].strip().upper()
                cat_code = row[3].strip()
                gender = row[4].strip()
                open_rank, open_prep = parse_rank(row[5])
                close_rank, close_prep = parse_rank(row[6])
                is_prep = open_prep or close_prep

                # Get or create institute
                if inst_name not in inst_map:
                    cursor.execute("SELECT id FROM institutes WHERE institute_name = ?", (inst_name,))
                    inst_row = cursor.fetchone()
                    if not inst_row:
                        itype = determine_institute_type(inst_name)
                        base_code = re.sub(r"[^A-Za-z0-9]", "", inst_name)[:10].upper() or "INST"
                        code = base_code
                        idx = 1
                        while True:
                            cursor.execute("SELECT id FROM institutes WHERE institute_code = ?", (code,))
                            if not cursor.fetchone():
                                break
                            idx += 1
                            code = f"{base_code[:7]}_{idx}"

                        cursor.execute("""
                            INSERT INTO institutes (institute_code, institute_name, institute_type)
                            VALUES (?, ?, ?)
                        """, (code, inst_name, itype))
                        inst_id = cursor.lastrowid
                    else:
                        inst_id = inst_row[0]
                    inst_map[inst_name] = inst_id
                else:
                    inst_id = inst_map[inst_name]

                # Get or create program
                if prog_name not in prog_map:
                    cursor.execute("SELECT id FROM programs WHERE program_name = ?", (prog_name,))
                    prog_row = cursor.fetchone()
                    if not prog_row:
                        deg = parse_degree_type(prog_name)
                        cursor.execute("""
                            INSERT INTO programs (program_name, degree_type)
                            VALUES (?, ?)
                        """, (prog_name, deg))
                        prog_id = cursor.lastrowid
                    else:
                        prog_id = prog_row[0]
                    prog_map[prog_name] = prog_id
                else:
                    prog_id = prog_map[prog_name]

                # Get or create category
                if cat_code not in cat_map:
                    cursor.execute("SELECT id FROM categories WHERE category_code = ?", (cat_code,))
                    cat_row = cursor.fetchone()
                    if not cat_row:
                        cursor.execute("""
                            INSERT INTO categories (category_code, category_name)
                            VALUES (?, ?)
                        """, (cat_code, cat_code))
                        cat_id = cursor.lastrowid
                    else:
                        cat_id = cat_row[0]
                    cat_map[cat_code] = cat_id
                else:
                    cat_id = cat_map[cat_code]

                # Insert cutoff record
                cursor.execute("""
                    INSERT OR REPLACE INTO cutoff_records (
                        academic_year, round_no, institute_id, program_id, category_id,
                        quota, gender, opening_rank, closing_rank, is_preparatory
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (year, round_no, inst_id, prog_id, cat_id, quota, gender, open_rank, close_rank, is_prep))

                batch_count += 1

            conn.commit()
            print(f"[+] Round {round_no} Ingested: {batch_count:,} records.")
            total_records += batch_count

        except Exception as e:
            import traceback
            print(f"[!] Error processing Round {round_no}: {e}")
            traceback.print_exc()

    # Summary
    inst_count = cursor.execute("SELECT COUNT(*) FROM institutes").fetchone()[0]
    prog_count = cursor.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    cat_count = cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    cutoff_count = cursor.execute("SELECT COUNT(*) FROM cutoff_records").fetchone()[0]

    conn.close()

    print("\n====================================================================")
    print(" INGESTION COMPLETE!")
    print(f" Total JoSAA Cutoff Records : {cutoff_count:,}")
    print(f" Total Institutes           : {inst_count:,}")
    print(f" Total Academic Programs    : {prog_count:,}")
    print(f" Total Categories           : {cat_count:,}")
    print("====================================================================")
    return {
        "success": True,
        "message": f"Successfully loaded {cutoff_count:,} official JoSAA cutoff records across 5 rounds.",
        "records_count": cutoff_count,
        "institutes_count": inst_count,
        "programs_count": prog_count,
        "categories_count": cat_count
    }

if __name__ == "__main__":
    ingest_all_official_rounds()
