# tests/integration/test_pipeline_end_to_end.py
from pathlib import Path

from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.orchestration.pipeline import process_document

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_pipeline_produces_complete_output_for_bank_statement():
    content = (FIXTURES / "bank_statement_sample.pdf").read_bytes()

    # Script order: classify, then one map_fields call per dictionary field
    # (account_number, statement_period_end, ending_balance), then one
    # discover_instructions call per found field, then one extract_fields
    # call per found field. All three fields are made to resolve as found
    # with high confidence so the pipeline reaches status="complete".
    provider = FakeLLMProvider(
        script=[
            "bank_statement|base|0.97",
            "found|1|1234567890|account number located",
            "found|1|01/31/2026|period end located",
            "found|1|1,200.00|balance located",
            "none|-|-|0.9",
            "none|-|-|0.9",
            "none|-|-|0.9",
            "1234567890|0.96",
            "2026-01-31|0.96",
            "1200.00|0.96",
        ]
    )

    output = process_document("bank_statement_sample.pdf", content, "doc-1", provider)

    assert output.document_type == "bank_statement"
    assert output.status == "complete"
    assert {f.name for f in output.fields} == {"account_number", "statement_period_end", "ending_balance"}
    assert output.review_items == []


def test_pipeline_routes_low_confidence_field_to_review():
    content = (FIXTURES / "bank_statement_sample.pdf").read_bytes()
    provider = FakeLLMProvider(
        script=[
            "bank_statement|base|0.97",
            "found|1|1234567890|ok",
            "found|1|01/31/2026|ok",
            "found|1|1,200.00|ok",
            "none|-|-|0.9",
            "none|-|-|0.9",
            "none|-|-|0.9",
            "1234567890|0.96",
            "2026-01-31|0.96",
            "1200.00|0.40",
        ]
    )

    output = process_document("bank_statement_sample.pdf", content, "doc-2", provider)

    assert output.status == "needs_review"
    assert any(item.field_name == "ending_balance" for item in output.review_items)
