from cw_platform.review.thresholds import DEFAULT_THRESHOLDS, get_threshold


def test_field_specific_threshold_used_when_present():
    assert get_threshold(DEFAULT_THRESHOLDS, "agent_bank_notice_interest_payment", "payment_amount") == 0.92


def test_document_type_default_used_when_field_not_configured():
    assert get_threshold(DEFAULT_THRESHOLDS, "bank_statement", "account_number") == 0.85


def test_global_fallback_used_for_unknown_document_type():
    assert get_threshold(DEFAULT_THRESHOLDS, "unknown_type", "some_field") == 0.85
