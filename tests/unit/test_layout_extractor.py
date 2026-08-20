from pathlib import Path

from cw_platform.extraction.layout_extractor import extract_layout

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_layout_returns_one_page():
    doc = extract_layout(FIXTURES / "bank_statement_sample.pdf")
    assert len(doc.pages) == 1


def test_extract_layout_captures_account_number_text():
    doc = extract_layout(FIXTURES / "bank_statement_sample.pdf")
    assert "1234567890" in doc.full_text()


def test_extract_layout_blocks_have_bounding_boxes():
    doc = extract_layout(FIXTURES / "bank_statement_sample.pdf")
    block = doc.pages[0].blocks[0]
    assert block.bbox.page == 1
    assert block.bbox.x1 > block.bbox.x0


def test_extract_layout_notice_pdf_text():
    doc = extract_layout(FIXTURES / "agent_bank_notice_sample.pdf")
    assert "Interest Payment Notice" in doc.full_text()
    assert "Note 1: Payment Amount is reported in whole dollars." in doc.full_text()
