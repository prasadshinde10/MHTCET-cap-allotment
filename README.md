# MHT-CET Cutoff PDF Parser & Web Scraping Database Normalizer

A complete Python toolkit for parsing MHT-CET Engineering Cutoff PDF data across **CAP Rounds 1, 2, 3, and 4** into a structured SQLite database (`cutoff.db`), extracting official metadata, affiliated universities, minority status, and branchwise intake directly from the MAH CET Portal, and executing multi-filter queries.

---

## Features & Scraped Data Attributes

1. **Multi-Round CAP Cutoff Parsing (`parse_txt_to_db.py`)**:
   - Automatically processes CAP Round PDF/text files (`2026ENGG_CAP1_MH_CutOff_V1.txt`, `2026ENGG_CAP2_MH_CutOff.txt`, `2026ENGG_CAP3_MH_CutOff.txt`, `2026ENGG_CAP4_MH_CutOff.txt`).
   - Stores **93,680 total cutoff records** with exact `cap_round` tagging (CAP 1: 36,005, CAP 2: 26,950, CAP 3: 17,478, CAP 4: 13,247).

2. **Web Scraping & Full Normalization (`scrape_institutes.py`)**:
   - Scrapes official institute profiles from [MAH CET 2026 Portal](https://fe2026.mahacet.org/StaticPages/frmInstituteList?did=1884).
   - Extracts `District`, `Region`, `Status` (Government, Un-Aided, Govt-Aided, University Department), `Autonomy Status`, `Minority Status`, `Address`, and `Affiliated University`.
   - Extracts all **4,331 Choice Codes** and branchwise seat intake (totaling **203,227 seats**) into `institute_courses`.
   - Syncs web-scraped district and status metadata across **100% of multi-round cutoff records** (93,680 / 93,680 records).

3. **Multi-Filter Interactive Query Tool (`query.py`)**:
   - Search cutoffs by CAP Round, Branch, District, Affiliated University, Minority Status, Seat Category, Autonomy, and Status.
   - Search branchwise intake (`python query.py intake`).
   - Run custom SQL queries against `cutoff.db`.

---

## Database Schema (`cutoff.db`)

### 1. `institutes` Table (Master Institute Metadata)
- `dte_code` (TEXT PRIMARY KEY) - 5-digit DTE Institute Code (e.g. `06004`)
- `institute_name` (TEXT) - Official institute name
- `district` (TEXT) - Scraped District Name (e.g. `Pune`, `Amravati`, `Mumbai City`)
- `region` (TEXT) - Scraped Region (e.g. `Pune`, `Nashik`, `Nagpur`)
- `status` (TEXT) - Scraped Status (Government, Un-Aided, Govt-Aided, etc.)
- `autonomy_status` (TEXT) - Scraped Autonomy Status (Autonomous / Non-Autonomous)
- `minority_status` (TEXT) - Scraped Minority Status
- `address` (TEXT) - Scraped Full Address
- `affiliated_university` (TEXT) - Scraped Primary Affiliated University

### 2. `institute_courses` Table (Branchwise Seat Intake)
- `choice_code` (TEXT PRIMARY KEY) - 10-digit Choice Code (e.g. `0600424510`)
- `dte_code` (TEXT REFERENCES institutes(dte_code))
- `course_name` (TEXT) - Engineering Branch Name
- `university` (TEXT) - Affiliated University
- `status` (TEXT) - Branch-level Status
- `autonomy_status` (TEXT) - Branch-level Autonomy
- `minority_status` (TEXT) - Branch-level Minority Status
- `shift` (TEXT) - Shift (e.g. General Shift)
- `accreditation` (TEXT) - Accreditation Status (e.g. NAAC A+)
- `gender_type` (TEXT) - Intake Type (`Co-Education` / `Girls`)
- `total_intake` (INTEGER) - Total Sanctioned Seat Intake

### 3. `cutoff_records` Table (Multi-Round Cutoffs)
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `cap_round` (INTEGER) - CAP Round Number (1, 2, 3, 4)
- `page_number` (INTEGER)
- `college_code` (TEXT REFERENCES institutes(dte_code))
- `college_name` (TEXT)
- `district` (TEXT) - Scraped District Name
- `course_code` (TEXT)
- `course_name` (TEXT)
- `status` (TEXT) - Scraped Status
- `is_autonomous` (TEXT) - Scraped Autonomy Status
- `governance_type` (TEXT)
- `reservation_level` (TEXT)
- `category` (TEXT)
- `seat_category` (TEXT)
- `stage` (TEXT)
- `merit_rank` (INTEGER)
- `percentile` (REAL)

---

## Installation & Setup

```bash
pip install beautifulsoup4 requests pypdf PyMuPDF
```

---

## Usage

### 1. Build Database & Web Scrape Profiles
```bash
python parse_txt_to_db.py
python scrape_institutes.py
```

### 2. Interactive Search & Queries
```bash
# Query Cutoffs for CAP Round 2 in Pune District
python -c "from query import filter_records; filter_records(cap_round=2, branch='Computer', district='Pune', category='OPEN')"

# Query Branchwise Seat Intake
python query.py intake

# Run Custom SQL Query
python query.py sql "SELECT cap_round, COUNT(*) FROM cutoff_records GROUP BY cap_round;"
```
