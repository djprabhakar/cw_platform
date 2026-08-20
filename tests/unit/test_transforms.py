import pytest
from cw_platform.extraction_agent.transforms import UnknownTransformError, apply_transform


def test_no_transform_returns_unchanged():
    assert apply_transform("1,200.00", None) == "1,200.00"
    assert apply_transform("1,200.00", "none") == "1,200.00"


def test_multiply_by_1000():
    assert apply_transform("45,000", "multiply_by_1000") == "45000000.00"


def test_strip_commas():
    assert apply_transform("1,200,000", "strip_commas") == "1200000"


def test_parse_date_mmddyyyy():
    assert apply_transform("02/15/2026", "parse_date_mmddyyyy") == "2026-02-15"


def test_unknown_transform_raises():
    with pytest.raises(UnknownTransformError, match="not_a_real_transform"):
        apply_transform("1,200.00", "not_a_real_transform")
