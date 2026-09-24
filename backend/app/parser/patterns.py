"""
Centralized compiled regex patterns for MHT-CET CAP cutoff PDF parsing.

These patterns are derived from actual 2026 MHT-CET Engineering CAP cutoff PDFs.
The PDF uses a VERTICAL layout:
  - Category codes appear one per line
  - Stage (Roman numeral) appears on its own line with leading whitespace
  - Merit numbers appear one per line
  - Percentiles appear as (xx.xxxxxxx) on the next line
"""
import re

# College header: 5-digit code + " - " + college name
# Example: "01002 - Government College of Engineering, Amravati"
COLLEGE_PATTERN = re.compile(r'^\s*(\d{5})\s*-\s*(.+?)\s*$')

# Course header: 10-digit code + " - " + course name
# Example: "0100219110 - Civil Engineering"
COURSE_PATTERN = re.compile(r'^\s*(\d{10})\s*-\s*(.+?)\s*$')

# Seat section patterns — these can be quite varied
# Examples from actual PDFs:
#   "Home University Seats Allotted to Home University Candidates"
#   "Other Than Home University Seats Allotted to Other Than Home University Candidates"
#   "Home University Seats Allotted to Other Than Home University Candidates"
#   "Other Than Home University Seats Allotted to Home University Candidates"
#   "State Level"
SEAT_SECTION_PATTERNS = {
    'HOME_UNIVERSITY': re.compile(
        r'(?i)^Home\s+University\s+Seats\b', re.IGNORECASE
    ),
    'OTHER_THAN_HOME_UNIVERSITY': re.compile(
        r'(?i)^Other\s+Than\s+Home\s+University\s+Seats\b', re.IGNORECASE
    ),
    'STATE_LEVEL': re.compile(
        r'(?i)^State\s+Level\s*$', re.IGNORECASE
    ),
}

# Category code pattern — uppercase letters, digits, and hyphens, 2+ chars
# Examples: GOPENS, GSCS, GSTS, GVJS, GNT1S, GNT2S, GNT3S, GOBCS, GSEBCS,
#           LOPENS, LSCS, LSTS, LOBCS, LSEBCS, PWDOPENS, PWDOBCS,
#           DEFOPENS, DEFOBCS, TFWS, PWDRSTS, DEFRSCS, EWS, ORPHANN, ORPHANI
CATEGORY_CODE_PATTERN = re.compile(r'^[A-Z][A-Z0-9]{1,}$')

# Stage pattern — Roman numeral, typically with leading whitespace
# In the PDF, stages appear as "  I", "  II", "  VII" etc.
STAGE_PATTERN = re.compile(r'^\s+(I{1,3}V?|IV|V|VI{0,3}|IX|X{0,3}I{0,3}V?)\s*$')

# Just the roman numeral for validation
ROMAN_NUMERAL = re.compile(r'^(I{1,3}V?|IV|V|VI{0,3}|IX|X{0,3}I{0,3}V?)$')

# Merit number — just a plain integer on its own line
MERIT_NUMBER_PATTERN = re.compile(r'^\s*(\d+)\s*$')

# Percentile — number in parentheses on its own line
# Example: "(91.7858261)"
PERCENTILE_PATTERN = re.compile(r'^\s*\((\d+\.\d+)\)\s*$')

# Combined merit + percentile (some PDFs may have them on one line)
MERIT_PERCENTILE_COMBINED = re.compile(r'^\s*(\d+)\s*\((\d+\.\d+)\)\s*$')

# Dash pattern — indicates no data for a category
DASH_PATTERN = re.compile(r'^\s*-+\s*$')

# Page header lines to skip
# The PDF starts each page with "D", "i", "r" on separate lines, then the title
PAGE_HEADER_PATTERNS = [
    re.compile(r'^D$'),
    re.compile(r'^i$'),
    re.compile(r'^r$'),
    re.compile(r'^State Common Entrance Test Cell'),
    re.compile(r'^Cut Off List for Maharashtra'),
    re.compile(r'^Degree Courses In Engineering'),
    re.compile(r'^Government of Maharashtra'),
]

# Status line — appears after course header
# Example: "Government Autonomous Home University : Autonomous Institute"
# Example: "Un-Aided Home University : Mumbai University"
STATUS_PATTERN = re.compile(r'^Status:\s*$')
STATUS_LINE_PATTERN = re.compile(r'^(?:Government|Un-Aided|Aided|University|Minority)\s+')

# Legend line at page bottom
LEGEND_PATTERN = re.compile(r'^Legends:\s+Starting\s+character\s+G-General')

# The word "Stage" appearing alone as a section-end marker
STAGE_LABEL_PATTERN = re.compile(r'^\s*Stage\s*$')

# Page number at bottom
PAGE_NUMBER_PATTERN = re.compile(r'^\s*\d{1,4}\s*$')
