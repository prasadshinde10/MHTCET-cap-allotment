import pytest
from app.parser.course_parser import CourseParser

def test_valid_course_header():
    code, name = CourseParser.parse_line("0100219110 - Civil Engineering")
    assert code == "0100219110"
    assert name == "Civil Engineering"

def test_course_with_extra_whitespace():
    code, name = CourseParser.parse_line("  1234567890  -   Computer Science  ")
    assert code == "1234567890"
    assert name == "Computer Science"

def test_not_a_course_line():
    assert CourseParser.parse_line("This is just some text") is None

def test_college_line_not_matched_as_course():
    assert CourseParser.parse_line("01002 - Government College") is None
