import pytest
from cw_platform.knowledge_base.loader import load_data_dictionary


def test_loads_base_bank_statement_dictionary():
    dd = load_data_dictionary("bank_statement", "base")
    assert dd.document_type == "bank_statement"
    field_names = {f.name for f in dd.fields}
    assert "ending_balance" in field_names
    assert "statement_period_end" in field_names


def test_loads_agent_bank_notice_dictionary():
    dd = load_data_dictionary("agent_bank_notice_interest_payment", "base")
    field_names = {f.name for f in dd.fields}
    assert "payment_amount" in field_names
    assert "interest_rate" in field_names


def test_unknown_document_type_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_data_dictionary("nonexistent_type", "base")


def test_unknown_template_raises_key_error():
    with pytest.raises(KeyError):
        load_data_dictionary("bank_statement", "nonexistent_template")
