"""
Category header parser for MHT-CET CAP cutoff PDFs.

In the actual PDFs, category codes appear ONE PER LINE in a vertical list.
The parser must collect consecutive category code lines to form the full
category header for a section.

Example sequence of lines:
    GOPENS
    GSCS
    GSTS
    GVJS
    GNT1S
    GNT2S
    GNT3S
    GOBCS
    GSEBCS
    LOPENS
    ...
"""
from app.parser.patterns import CATEGORY_CODE_PATTERN


class CategoryParser:
    """Detects individual category codes from lines."""

    @staticmethod
    def parse_line(line: str) -> str | None:
        """
        Check if a line contains a single category code.
        Returns the category code if matched, else None.
        """
        stripped = line.strip()
        if not stripped:
            return None

        # Must match the category code pattern exactly
        if CATEGORY_CODE_PATTERN.match(stripped):
            # Additional validation: must be at least 2 chars, all uppercase + digits
            if len(stripped) >= 2:
                return stripped

        return None

    @staticmethod
    def is_known_category_prefix(code: str) -> bool:
        """Check if a code starts with a known category prefix."""
        known_prefixes = [
            'GOPEN', 'GSC', 'GST', 'GVJ', 'GNT', 'GOBC', 'GSEBC',
            'LOPEN', 'LSC', 'LST', 'LVJ', 'LNT', 'LOBC', 'LSEBC',
            'PWDOPEN', 'PWDOPC', 'PWDSC', 'PWDST', 'PWDVJ', 'PWDNT',
            'PWDOBC', 'PWDSEBC', 'PWDR',
            'DEFOPEN', 'DEFOBC', 'DEFSC', 'DEFST', 'DEFVJ', 'DEFNT',
            'DEFSEBC', 'DEFR',
            'TFWS', 'EWS', 'ORPHAN',
        ]
        upper_code = code.upper()
        return any(upper_code.startswith(prefix) for prefix in known_prefixes)
