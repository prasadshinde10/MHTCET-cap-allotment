import pytest
from app.parser.validator import RecordValidator

def get_valid_record():
    return {
        "college_code": "01002",
        "course_code": "0100219110",
        "category_code": "GOPENS",
        "stage": "I",
        "merit_number": 34692,
        "percentile": 91.7858261,
        "seat_section": "STATE_LEVEL",
        "year": 2023,
        "cap_round": 1,
        "source_page": 10
    }

def test_valid_record():
    rec = get_valid_record()
    is_valid, errors = RecordValidator.validate_cutoff(rec)
    assert is_valid
    assert len(errors) == 0

def test_missing_college_code():
    rec = get_valid_record()
    rec["college_code"] = ""
    is_valid, errors = RecordValidator.validate_cutoff(rec)
    assert not is_valid
    assert "college_code must not be empty" in errors

def test_negative_merit():
    rec = get_valid_record()
    rec["merit_number"] = -1
    is_valid, errors = RecordValidator.validate_cutoff(rec)
    assert not is_valid
    assert "merit_number must be positive integer if present" in errors

def test_percentile_out_of_range():
    rec = get_valid_record()
    rec["percentile"] = 150
    is_valid, errors = RecordValidator.validate_cutoff(rec)
    assert not is_valid
    assert "percentile must be between 0 and 100 if present" in errors

def test_duplicate_detection():
    r1 = get_valid_record()
    r2 = get_valid_record()
    dups = RecordValidator.check_duplicates([r1, r2])
    assert len(dups) == 1
