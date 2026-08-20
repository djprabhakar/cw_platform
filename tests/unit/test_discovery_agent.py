from cw_platform.instructions.discovery_agent import discover_instructions
from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.models.document import Block, BoundingBox, ExtractedDocument, Page
from cw_platform.models.mapping import CoverageReport, FieldMapping


def _doc_with_footnote() -> ExtractedDocument:
    bbox = BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1)
    blocks = [
        Block(text="Payment Amount 45,000", bbox=bbox, kind="paragraph"),
        Block(text="Note 1: Payment Amount is reported in thousands.", bbox=bbox, kind="paragraph"),
    ]
    page = Page(number=1, blocks=blocks, tables=[], width=612, height=792)
    return ExtractedDocument(source_filename="notice.pdf", pages=[page])


def _coverage_with_one_found_field() -> CoverageReport:
    return CoverageReport(
        document_type="agent_bank_notice_interest_payment",
        mappings=[
            FieldMapping(field_name="payment_amount", status="found", page=1, text_span="45,000", notes="ok"),
            FieldMapping(field_name="interest_rate", status="not_found", page=None, text_span=None, notes="missing"),
        ],
    )


def test_discover_instructions_only_queries_found_fields():
    provider = FakeLLMProvider(script=["found|Payment Amount is reported in thousands.|multiply_by_1000|0.9"])
    result = discover_instructions(_doc_with_footnote(), _coverage_with_one_found_field(), provider)
    assert len(result.instructions) == 1
    assert result.instructions[0].field_name == "payment_amount"
    assert result.instructions[0].transformation == "multiply_by_1000"


def test_discover_instructions_skips_fields_with_no_instruction():
    provider = FakeLLMProvider(script=["none|-|-|0.95"])
    result = discover_instructions(_doc_with_footnote(), _coverage_with_one_found_field(), provider)
    assert result.instructions == []


def test_for_field_returns_none_when_absent():
    provider = FakeLLMProvider(script=["none|-|-|0.95"])
    result = discover_instructions(_doc_with_footnote(), _coverage_with_one_found_field(), provider)
    assert result.for_field("payment_amount") is None
