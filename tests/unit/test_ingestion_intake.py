import pytest
from cw_platform.ingestion.intake import RawDocument, UnsupportedFormatError, intake


def test_intake_accepts_pdf():
    doc = intake("statement.pdf", b"%PDF-1.4 fake bytes")
    assert isinstance(doc, RawDocument)
    assert doc.format == "pdf"
    assert doc.filename == "statement.pdf"


def test_intake_rejects_non_pdf():
    with pytest.raises(UnsupportedFormatError, match="docx"):
        intake("statement.docx", b"fake bytes")


def test_intake_rejects_no_extension():
    with pytest.raises(UnsupportedFormatError):
        intake("statement", b"fake bytes")
