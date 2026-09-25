"""Tests for the CutoffBlockParser — the most critical parser component."""
import pytest
from decimal import Decimal
from app.parser.cutoff_parser import CutoffBlockParser, CutoffRecord


class TestCutoffBlockParser:
    """Test the vertical-layout cutoff block parser."""

    def test_single_stage_single_category(self):
        """Parse a block with one stage and one category."""
        parser = CutoffBlockParser(categories=["TFWS"])
        lines = [
            "  I",
            "24536",
            "(94.2142883)",
            "Stage",
        ]
        for line in lines:
            done = parser.feed_line(line)
            if done:
                break

        records = parser.get_records()
        assert len(records) == 1
        assert records[0].category_code == "TFWS"
        assert records[0].stage == "I"
        assert records[0].merit_number == 24536
        assert records[0].percentile == Decimal("94.2142883")

    def test_single_stage_multiple_categories(self):
        """Parse stage I with multiple categories (like page 1 Civil Eng)."""
        categories = ["GOPENS", "GSCS", "GSTS", "EWS"]
        parser = CutoffBlockParser(categories=categories)
        lines = [
            "  I",
            "34692",
            "(91.7858261)",
            "59898",
            "(85.6921506)",
            "83081",
            "(79.9864621)",
            "65351",
            "(84.3786315)",
            "Stage",
        ]
        for line in lines:
            done = parser.feed_line(line)
            if done:
                break

        records = parser.get_records()
        assert len(records) == 4

        assert records[0].category_code == "GOPENS"
        assert records[0].merit_number == 34692
        assert records[0].percentile == Decimal("91.7858261")

        assert records[1].category_code == "GSCS"
        assert records[1].merit_number == 59898
        assert records[1].percentile == Decimal("85.6921506")

        assert records[2].category_code == "GSTS"
        assert records[2].merit_number == 83081

        assert records[3].category_code == "EWS"
        assert records[3].merit_number == 65351
        assert records[3].percentile == Decimal("84.3786315")

    def test_multi_stage(self):
        """Parse a block with multiple stages (I and II)."""
        categories = ["GOPENH", "GSCH", "GOBCH"]
        parser = CutoffBlockParser(categories=categories)
        lines = [
            "  I",
            "200707",
            "(34.7115718)",
            "220146",
            "(17.7299217)",
            "214866",
            "(23.5097171)",
            "  II",
            "210732",
            "(27.2101033)",
            "Stage",
        ]
        for line in lines:
            done = parser.feed_line(line)
            if done:
                break

        records = parser.get_records()
        # Stage I: 3 records, Stage II: 1 record
        assert len(records) == 4

        stage_i = [r for r in records if r.stage == "I"]
        stage_ii = [r for r in records if r.stage == "II"]

        assert len(stage_i) == 3
        assert len(stage_ii) == 1

        assert stage_i[0].category_code == "GOPENH"
        assert stage_i[0].merit_number == 200707

        assert stage_ii[0].category_code == "GOPENH"
        assert stage_ii[0].merit_number == 210732
        assert stage_ii[0].percentile == Decimal("27.2101033")

    def test_percentile_precision_7_decimals(self):
        """Ensure percentile is stored as Decimal with full precision."""
        parser = CutoffBlockParser(categories=["GOPENS"])
        lines = [
            "  I",
            "10819",
            "(97.4547994)",
            "Stage",
        ]
        for line in lines:
            parser.feed_line(line)

        records = parser.get_records()
        assert len(records) == 1
        assert isinstance(records[0].percentile, Decimal)
        assert records[0].percentile == Decimal("97.4547994")

    def test_empty_block(self):
        """Parser should handle an empty block gracefully."""
        parser = CutoffBlockParser(categories=["GOPENS"])
        parser.feed_line("Stage")
        records = parser.get_records()
        assert len(records) == 0

    def test_stage_roman_numerals(self):
        """Test various Roman numeral stages."""
        for stage_str in ["I", "II", "III", "IV", "V", "VI", "VII"]:
            parser = CutoffBlockParser(categories=["GOPENS"])
            lines = [
                f"  {stage_str}",
                "12345",
                "(90.1234567)",
                "Stage",
            ]
            for line in lines:
                parser.feed_line(line)
            records = parser.get_records()
            assert len(records) == 1
            assert records[0].stage == stage_str

    def test_reset(self):
        """Test resetting parser for a new block."""
        parser = CutoffBlockParser(categories=["GOPENS"])
        parser.feed_line("  I")
        parser.feed_line("12345")
        parser.feed_line("(90.1234567)")
        parser.feed_line("Stage")

        parser.reset(categories=["GSCS", "GSTS"])
        parser.feed_line("  I")
        parser.feed_line("54321")
        parser.feed_line("(80.1234567)")
        parser.feed_line("99999")
        parser.feed_line("(70.1234567)")
        parser.feed_line("Stage")

        records = parser.get_records()
        assert len(records) == 2
        assert records[0].category_code == "GSCS"
        assert records[1].category_code == "GSTS"
