"""
Seat section parser for MHT-CET CAP cutoff PDFs.

Seat sections in the actual PDFs include:
  - "Home University Seats Allotted to Home University Candidates"
  - "Other Than Home University Seats Allotted to Other Than Home University Candidates"
  - "Home University Seats Allotted to Other Than Home University Candidates"
  - "Other Than Home University Seats Allotted to Home University Candidates"
  - "State Level"

These are normalized to controlled values.
"""
import re

# More precise section patterns from actual PDF content
_SECTION_MAP = [
    # Order matters — check more specific patterns first
    (
        'OTHER_THAN_HOME_UNIVERSITY',
        re.compile(r'Other\s+Than\s+Home\s+University\s+Seats', re.IGNORECASE),
    ),
    (
        'HOME_UNIVERSITY',
        re.compile(r'Home\s+University\s+Seats', re.IGNORECASE),
    ),
    (
        'STATE_LEVEL',
        re.compile(r'^\s*State\s+Level\s*$', re.IGNORECASE),
    ),
]


class SectionParser:
    """Detects seat section headers."""

    @staticmethod
    def parse_line(line: str) -> tuple[str, str] | None:
        """
        Check if a line is a seat section header.
        Returns (normalized_section, raw_text) or None.
        """
        stripped = line.strip()
        if not stripped:
            return None

        for normalized, pattern in _SECTION_MAP:
            if pattern.search(stripped):
                return (normalized, stripped)

        return None
