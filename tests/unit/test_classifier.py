import pytest
from cw_platform.classification.classifier import ClassificationResult, classify
from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.models.document import Block, BoundingBox, ExtractedDocument, Page


def _doc_with_text(text: str) -> ExtractedDocument:
    bbox = BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1)
    page = Page(number=1, blocks=[Block(text=text, bbox=bbox, kind="paragraph")], tables=[], width=612, height=792)
    return ExtractedDocument(source_filename="doc.pdf", pages=[page])


def test_classify_parses_provider_response():
    doc = _doc_with_text("Monthly Bank Statement, Account Number: 1234567890")
    provider = FakeLLMProvider(script=["bank_statement|base|0.93"])
    result = classify(doc, provider)
    assert result == ClassificationResult(document_type="bank_statement", template="base", confidence=0.93)


def test_classify_raises_on_malformed_response():
    doc = _doc_with_text("irrelevant")
    provider = FakeLLMProvider(script=["not a valid response"])
    with pytest.raises(ValueError):
        classify(doc, provider)


def test_classify_raises_on_out_of_range_confidence():
    doc = _doc_with_text("irrelevant")
    provider = FakeLLMProvider(script=["bank_statement|base|1.5"])
    with pytest.raises(ValueError):
        classify(doc, provider)
