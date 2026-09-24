"""
Category normalizer for MHT-CET CAP cutoff categories.

Normalizes raw category codes (e.g., GOPENS, GSCS, LSEBCH) into
structured components: gender, seat_category, and seat_location.

Category code structure:
  [Gender prefix][Seat Category][Seat Location suffix]

Gender prefix:
  G = General
  L = Ladies
  (none for special categories: EWS, TFWS, ORPHAN, PWD*, DEF*)

Seat Location suffix:
  S = State Level
  H = Home University
  O = Other Than Home University
  (none for special categories)

Seat Categories:
  OPEN   = Open/General Merit
  SC     = Scheduled Caste
  ST     = Scheduled Tribe
  VJ     = Vimukta Jati / Denotified Tribes
  NT1    = Nomadic Tribe 1
  NT2    = Nomadic Tribe 2
  NT3    = Nomadic Tribe 3
  OBC    = Other Backward Class
  SEBC   = Socially and Educationally Backward Class
  EWS    = Economically Weaker Section
  TFWS   = Tuition Fee Waiver Scheme
  ORPHAN = Orphan category
  PWD*   = Person with Disability (various sub-types)
  DEF*   = Defence category (various sub-types)
"""
from typing import TypedDict
import re


class NormalizedCategory(TypedDict):
    gender: str | None
    seat_category: str | None
    seat_location: str | None
    is_confident: bool


# Ordered list of seat category patterns to check (longer/more specific first)
_SEAT_CATEGORY_PATTERNS = [
    ('SEBC', 'SEBC'),
    ('OPEN', 'OPEN'),
    ('OBC', 'OBC'),
    ('SC', 'SC'),
    ('ST', 'ST'),
    ('VJ', 'VJ/DT-NT'),
    ('NT1', 'NT1'),
    ('NT2', 'NT2'),
    ('NT3', 'NT3'),
]


class CategoryNormalizer:
    """Normalizes MHT-CET category codes into structured components."""

    @staticmethod
    def normalize(category_code: str) -> NormalizedCategory:
        """
        Normalize a category code into gender, seat_category, and seat_location.

        Examples:
          GOPENS → General, OPEN, State Level
          GSCS   → General, SC, State Level
          LSEBCH → Ladies, SEBC, Home University
          EWS    → None, EWS, None
          TFWS   → None, TFWS, None
          ORPHANN → None, ORPHAN, None
          PWDOPENS → None, PWD-OPEN, State Level
          DEFOBCS  → None, DEF-OBC, State Level
        """
        code = category_code.upper().strip()

        result: NormalizedCategory = {
            "gender": None,
            "seat_category": None,
            "seat_location": None,
            "is_confident": True,
        }

        # Handle special standalone categories first
        if code == "EWS":
            result["seat_category"] = "EWS"
            return result

        if code == "TFWS":
            result["seat_category"] = "TFWS"
            return result

        if code.startswith("ORPHAN"):
            result["seat_category"] = "ORPHAN"
            return result

        # Handle PWD categories: PWDOPENS, PWDOBCS, PWDROBCS, etc.
        if code.startswith("PWD"):
            remainder = code[3:]  # e.g., "OPENS", "OBCS", "ROBCS"
            result["seat_category"] = f"PWD"
            # Try to extract the sub-category and location
            sub_norm = CategoryNormalizer._parse_remainder(remainder)
            if sub_norm["seat_category"]:
                result["seat_category"] = f"PWD-{sub_norm['seat_category']}"
            result["seat_location"] = sub_norm["seat_location"]
            return result

        # Handle DEF categories: DEFOPENS, DEFOBCS, DEFRSCS, etc.
        if code.startswith("DEF"):
            remainder = code[3:]  # e.g., "OPENS", "OBCS", "RSCS"
            result["seat_category"] = "DEF"
            sub_norm = CategoryNormalizer._parse_remainder(remainder)
            if sub_norm["seat_category"]:
                result["seat_category"] = f"DEF-{sub_norm['seat_category']}"
            result["seat_location"] = sub_norm["seat_location"]
            return result

        # Parse gender prefix
        working = code
        if working.startswith("G"):
            result["gender"] = "General"
            working = working[1:]
        elif working.startswith("L"):
            result["gender"] = "Ladies"
            working = working[1:]

        # Parse the remainder: seat category + location suffix
        parsed = CategoryNormalizer._parse_remainder(working)
        result["seat_category"] = parsed["seat_category"]
        result["seat_location"] = parsed["seat_location"]

        if not result["seat_category"] or parsed.get("is_fallback"):
            result["is_confident"] = False
            if not result["seat_category"]:
                result["seat_category"] = code  # Preserve original

        return result

    @staticmethod
    def _parse_remainder(remainder: str) -> dict:
        """
        Parse a category remainder string into seat_category and seat_location.
        The remainder is the code after gender/PWD/DEF prefix is stripped.
        
        Suffix rules:
          - Ends with 'S' → State Level (but must check it's not part of the category name)
          - Ends with 'H' → Home University
          - Ends with 'O' → Other Than Home University
        """
        result = {"seat_category": None, "seat_location": None}

        if not remainder:
            return result

        # Handle 'R' prefix (reserved/special quota): RSCS, ROBCS, etc.
        has_r_prefix = False
        working = remainder
        if working.startswith("R") and len(working) > 1:
            # Check if removing R reveals a known category
            test = working[1:]
            for pattern, cat_name in _SEAT_CATEGORY_PATTERNS:
                if test.startswith(pattern):
                    has_r_prefix = True
                    working = test
                    break

        # Try to match seat category patterns
        for pattern, cat_name in _SEAT_CATEGORY_PATTERNS:
            if working.startswith(pattern):
                result["seat_category"] = cat_name
                suffix = working[len(pattern):]
                if has_r_prefix:
                    result["seat_category"] = f"R-{cat_name}"

                # Parse location suffix
                if suffix == 'S':
                    result["seat_location"] = "State Level"
                elif suffix == 'H':
                    result["seat_location"] = "Home University"
                elif suffix == 'O':
                    result["seat_location"] = "Other Than Home University"
                # If no suffix or unrecognized suffix, location stays None

                return result

        # Fallback — couldn't parse
        result["seat_category"] = remainder
        result["is_fallback"] = True
        return result
