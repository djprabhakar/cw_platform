import pytest
from pydantic import ValidationError

from cw_platform.models.output import DocumentOutput
from cw_platform.models.review import ReviewItem


def test_status_complete_requires_no_review_items():
    output = DocumentOutput(
        document_id="doc-1",
        source_filename="stmt.pdf",
        document_type="bank_statement",
        template="base",
        classification_confidence=0.95,
        fields=[],
        review_items=[],
        status="complete",
    )
    assert output.status == "complete"


def test_status_complete_with_review_items_raises():
    with pytest.raises(ValidationError):
        DocumentOutput(
            document_id="doc-1",
            source_filename="stmt.pdf",
            document_type="bank_statement",
            template="base",
            classification_confidence=0.95,
            fields=[],
            review_items=[ReviewItem(field_name="x", reason="low_confidence", detail="d")],
            status="complete",
        )


def test_status_needs_review_requires_review_items():
    with pytest.raises(ValidationError):
        DocumentOutput(
            document_id="doc-1",
            source_filename="stmt.pdf",
            document_type="bank_statement",
            template="base",
            classification_confidence=0.95,
            fields=[],
            review_items=[],
            status="needs_review",
        )
