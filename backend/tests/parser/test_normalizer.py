"""Tests for CategoryNormalizer."""
import pytest
from app.parser.normalizer import CategoryNormalizer


class TestCategoryNormalizer:
    def test_gopens(self):
        result = CategoryNormalizer.normalize("GOPENS")
        assert result["gender"] == "General"
        assert result["seat_category"] == "OPEN"
        assert result["seat_location"] == "State Level"
        assert result["is_confident"] is True

    def test_gopenh(self):
        result = CategoryNormalizer.normalize("GOPENH")
        assert result["gender"] == "General"
        assert result["seat_category"] == "OPEN"
        assert result["seat_location"] == "Home University"

    def test_gopeno(self):
        result = CategoryNormalizer.normalize("GOPENO")
        assert result["gender"] == "General"
        assert result["seat_category"] == "OPEN"
        assert result["seat_location"] == "Other Than Home University"

    def test_lopen_ladies(self):
        result = CategoryNormalizer.normalize("LOPENS")
        assert result["gender"] == "Ladies"
        assert result["seat_category"] == "OPEN"
        assert result["seat_location"] == "State Level"

    def test_gscs(self):
        result = CategoryNormalizer.normalize("GSCS")
        assert result["gender"] == "General"
        assert result["seat_category"] == "SC"
        assert result["seat_location"] == "State Level"

    def test_gsch(self):
        result = CategoryNormalizer.normalize("GSCH")
        assert result["gender"] == "General"
        assert result["seat_category"] == "SC"
        assert result["seat_location"] == "Home University"

    def test_gsebcs(self):
        result = CategoryNormalizer.normalize("GSEBCS")
        assert result["gender"] == "General"
        assert result["seat_category"] == "SEBC"
        assert result["seat_location"] == "State Level"

    def test_gvjs(self):
        result = CategoryNormalizer.normalize("GVJS")
        assert result["gender"] == "General"
        assert result["seat_category"] == "VJ/DT-NT"
        assert result["seat_location"] == "State Level"

    def test_gobcs(self):
        result = CategoryNormalizer.normalize("GOBCS")
        assert result["gender"] == "General"
        assert result["seat_category"] == "OBC"
        assert result["seat_location"] == "State Level"

    def test_ews(self):
        result = CategoryNormalizer.normalize("EWS")
        assert result["gender"] is None
        assert result["seat_category"] == "EWS"
        assert result["seat_location"] is None

    def test_tfws(self):
        result = CategoryNormalizer.normalize("TFWS")
        assert result["gender"] is None
        assert result["seat_category"] == "TFWS"
        assert result["seat_location"] is None

    def test_orphan(self):
        result = CategoryNormalizer.normalize("ORPHANN")
        assert result["seat_category"] == "ORPHAN"
        assert result["gender"] is None

    def test_pwdopens(self):
        result = CategoryNormalizer.normalize("PWDOPENS")
        assert result["gender"] is None
        assert result["seat_category"] == "PWD-OPEN"
        assert result["seat_location"] == "State Level"

    def test_defobcs(self):
        result = CategoryNormalizer.normalize("DEFOBCS")
        assert result["gender"] is None
        assert result["seat_category"] == "DEF-OBC"
        assert result["seat_location"] == "State Level"

    def test_defrscs(self):
        """DEF + R + SC + S → DEF-R-SC, State Level."""
        result = CategoryNormalizer.normalize("DEFRSCS")
        assert result["seat_category"] == "DEF-R-SC"
        assert result["seat_location"] == "State Level"

    def test_gnt1s(self):
        result = CategoryNormalizer.normalize("GNT1S")
        assert result["gender"] == "General"
        assert result["seat_category"] == "NT1"
        assert result["seat_location"] == "State Level"

    def test_lnt2h(self):
        result = CategoryNormalizer.normalize("LNT2H")
        assert result["gender"] == "Ladies"
        assert result["seat_category"] == "NT2"
        assert result["seat_location"] == "Home University"

    def test_unknown_preserves_original(self):
        result = CategoryNormalizer.normalize("XYZABC")
        assert result["is_confident"] is False
