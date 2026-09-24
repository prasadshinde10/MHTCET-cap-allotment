"""Tests for SectionParser."""
import pytest
from app.parser.section_parser import SectionParser


class TestSectionParser:
    def test_state_level(self):
        result = SectionParser.parse_line("State Level")
        assert result is not None
        assert result[0] == "STATE_LEVEL"
        assert result[1] == "State Level"

    def test_home_university_full(self):
        line = "Home University Seats Allotted to Home University Candidates"
        result = SectionParser.parse_line(line)
        assert result is not None
        assert result[0] == "HOME_UNIVERSITY"

    def test_other_than_home_university(self):
        line = "Other Than Home University Seats Allotted to Other Than Home University Candidates"
        result = SectionParser.parse_line(line)
        assert result is not None
        assert result[0] == "OTHER_THAN_HOME_UNIVERSITY"

    def test_home_university_allotted_to_other(self):
        """Home University Seats allotted to Other TH candidates — still HOME_UNIVERSITY."""
        line = "Home University Seats Allotted to Other Than Home University Candidates"
        result = SectionParser.parse_line(line)
        assert result is not None
        assert result[0] == "HOME_UNIVERSITY"

    def test_other_allotted_to_home(self):
        """Other Than HU Seats allotted to HU candidates — still OTHER_THAN_HOME_UNIVERSITY."""
        line = "Other Than Home University Seats Allotted to Home University Candidates"
        result = SectionParser.parse_line(line)
        assert result is not None
        assert result[0] == "OTHER_THAN_HOME_UNIVERSITY"

    def test_case_insensitive(self):
        result = SectionParser.parse_line("state level")
        assert result is not None
        assert result[0] == "STATE_LEVEL"

    def test_not_a_section(self):
        assert SectionParser.parse_line("GOPENS") is None
        assert SectionParser.parse_line("01002 - College Name") is None

    def test_empty_line(self):
        assert SectionParser.parse_line("") is None
