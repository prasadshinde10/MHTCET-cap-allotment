from decimal import Decimal
from typing import Any


class RecordValidator:
    @staticmethod
    def validate_cutoff(record: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validates a cutoff record dict.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        
        if not record.get("college_code"):
            errors.append("college_code must not be empty")
        if not record.get("course_code"):
            errors.append("course_code must not be empty")
        if not record.get("category_code"):
            errors.append("category_code must not be empty")
        if not record.get("stage"):
            errors.append("stage must not be empty")
            
        merit_number = record.get("merit_number")
        if merit_number is not None:
            try:
                if int(merit_number) <= 0:
                    errors.append("merit_number must be positive integer if present")
            except ValueError:
                errors.append("merit_number must be an integer")
                
        percentile = record.get("percentile")
        if percentile is not None:
            try:
                val = Decimal(str(percentile))
                if val < Decimal('0') or val > Decimal('100'):
                    errors.append("percentile must be between 0 and 100 if present")
            except Exception:
                errors.append("percentile must be a valid number")

        valid_sections = ['HOME_UNIVERSITY', 'OTHER_THAN_HOME_UNIVERSITY', 'STATE_LEVEL']
        if record.get("seat_section") not in valid_sections:
            errors.append("seat_section must be one of the normalized values")

        year = record.get("year")
        if year is not None:
            if not (2020 <= int(year) <= 2050):
                errors.append("year must be reasonable (2020-2050)")
                
        cap_round = record.get("cap_round")
        if cap_round is not None:
            if not (1 <= int(cap_round) <= 4):
                errors.append("cap_round must be 1-4")

        source_page = record.get("source_page")
        if source_page is not None:
            if int(source_page) <= 0:
                errors.append("source_page must be positive")

        return len(errors) == 0, errors

    @staticmethod
    def validate_batch(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Returns (valid_records, invalid_records_with_errors).
        """
        valid = []
        invalid = []
        
        for r in records:
            is_valid, errors = RecordValidator.validate_cutoff(r)
            if is_valid:
                valid.append(r)
            else:
                invalid.append({"record": r, "errors": errors})
                
        return valid, invalid

    @staticmethod
    def check_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Returns records that appear to be duplicates based on (course_code, category_code, stage, seat_section)
        """
        seen = set()
        duplicates = []
        
        for r in records:
            key = (
                r.get("course_code"),
                r.get("category_code"),
                r.get("stage"),
                r.get("seat_section")
            )
            if key in seen:
                duplicates.append(r)
            else:
                seen.add(key)
                
        return duplicates
