import pytest
from app.parser.college_parser import CollegeParser

def test_valid_college_header():
    code, name = CollegeParser.parse_line("01002 - Government College of Engineering, Amravati")
    assert code == "01002"
    assert name == "Government College of Engineering, Amravati"

def test_college_with_extra_whitespace():
    code, name = CollegeParser.parse_line("  12345  -   Some College Name  ")
    assert code == "12345"
    assert name == "Some College Name"

def test_not_a_college_line():
    assert CollegeParser.parse_line("This is just some text") is None
    assert CollegeParser.parse_line("1234 - Too short") is None

def test_course_line_not_matched_as_college():
    assert CollegeParser.parse_line("0100219110 - Civil Engineering") is None
