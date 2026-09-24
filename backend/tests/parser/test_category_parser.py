"""Tests for CategoryParser."""
import pytest
from app.parser.category_parser import CategoryParser


class TestCategoryParser:
    def test_valid_category_gopens(self):
        assert CategoryParser.parse_line("GOPENS") == "GOPENS"

    def test_valid_category_gscs(self):
        assert CategoryParser.parse_line("GSCS") == "GSCS"

    def test_valid_category_ews(self):
        assert CategoryParser.parse_line("EWS") == "EWS"

    def test_valid_category_tfws(self):
        assert CategoryParser.parse_line("TFWS") == "TFWS"

    def test_valid_category_pwdopens(self):
        assert CategoryParser.parse_line("PWDOPENS") == "PWDOPENS"

    def test_valid_category_defobcs(self):
        assert CategoryParser.parse_line("DEFOBCS") == "DEFOBCS"

    def test_valid_category_orphann(self):
        assert CategoryParser.parse_line("ORPHANN") == "ORPHANN"

    def test_valid_category_gnt1s(self):
        assert CategoryParser.parse_line("GNT1S") == "GNT1S"

    def test_valid_category_gsebch(self):
        assert CategoryParser.parse_line("GSEBCH") == "GSEBCH"

    def test_with_whitespace(self):
        assert CategoryParser.parse_line("  GOPENS  ") == "GOPENS"

    def test_not_a_category_lowercase(self):
        assert CategoryParser.parse_line("gopens") is None

    def test_not_a_category_sentence(self):
        assert CategoryParser.parse_line("Government College of Engineering") is None

    def test_not_a_category_single_char(self):
        assert CategoryParser.parse_line("D") is None

    def test_not_a_category_number(self):
        assert CategoryParser.parse_line("12345") is None

    def test_empty_line(self):
        assert CategoryParser.parse_line("") is None

    def test_not_a_category_mixed_case(self):
        assert CategoryParser.parse_line("GopenS") is None

    def test_known_prefix_gopens(self):
        assert CategoryParser.is_known_category_prefix("GOPENS") is True

    def test_known_prefix_defrscs(self):
        assert CategoryParser.is_known_category_prefix("DEFRSCS") is True

    def test_known_prefix_unknown(self):
        assert CategoryParser.is_known_category_prefix("XYZABC") is False
