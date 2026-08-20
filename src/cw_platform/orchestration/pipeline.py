from __future__ import annotations

import tempfile
from pathlib import Path

from cw_platform.classification.classifier import classify
from cw_platform.extraction.layout_extractor import extract_layout
from cw_platform.extraction_agent.extractor import extract_fields
from cw_platform.ingestion.intake import intake
from cw_platform.instructions.discovery_agent import discover_instructions
from cw_platform.knowledge_base.loader import load_data_dictionary
from cw_platform.llm.provider import LLMProvider
from cw_platform.mapping.mapping_agent import map_fields
from cw_platform.models.output import DocumentOutput
from cw_platform.review.queue import build_review_queue
from cw_platform.review.thresholds import DEFAULT_THRESHOLDS


def process_document(filename: str, content: bytes, document_id: str, provider: LLMProvider) -> DocumentOutput:
    raw_document = intake(filename, content)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(raw_document.content)
        tmp_path = Path(tmp.name)

    try:
        extracted = extract_layout(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    classification = classify(extracted, provider)
    dictionary = load_data_dictionary(classification.document_type, classification.template)
    coverage = map_fields(extracted, dictionary, provider)
    instructions = discover_instructions(extracted, coverage, provider)
    fields = extract_fields(coverage, instructions, provider)

    required_fields = [f.name for f in dictionary.fields if f.required]
    review_items = build_review_queue(
        classification.document_type, fields, required_fields, DEFAULT_THRESHOLDS
    )

    return DocumentOutput(
        document_id=document_id,
        source_filename=filename,
        document_type=classification.document_type,
        template=classification.template,
        classification_confidence=classification.confidence,
        fields=fields,
        review_items=review_items,
        status="needs_review" if review_items else "complete",
    )
