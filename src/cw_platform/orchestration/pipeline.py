from __future__ import annotations

import tempfile
from pathlib import Path

from cw_platform.classification.classifier import classify
from cw_platform.extraction.layout_extractor import extract_layout
from cw_platform.extraction_agent.extractor import extract_fields
from cw_platform.extraction_agent.transforms import UnknownTransformError
from cw_platform.ingestion.intake import UnsupportedFormatError, intake
from cw_platform.instructions.discovery_agent import discover_instructions
from cw_platform.knowledge_base.loader import load_data_dictionary
from cw_platform.llm.provider import LLMProvider
from cw_platform.mapping.mapping_agent import map_fields
from cw_platform.models.output import DocumentOutput
from cw_platform.models.review import ReviewItem
from cw_platform.review.queue import build_review_queue
from cw_platform.review.thresholds import DEFAULT_THRESHOLDS

# Document-level sentinel used when a whole stage fails, so the resulting
# ReviewItem is distinguishable from a field-level review item.
DOCUMENT_LEVEL_FIELD = "__document__"

# Exceptions the pipeline stages raise for inputs a human needs to look at:
# an unsupported upload format (intake), an unknown/unmapped document type or
# template (load_data_dictionary), a malformed LLM response (classify,
# map_fields, discover_instructions, extract_fields) and an unrecognised
# discovered transformation (extract_fields -> apply_transform).
_STAGE_FAILURES = (
    UnsupportedFormatError,
    FileNotFoundError,
    KeyError,
    ValueError,
    UnknownTransformError,
)


def process_document(filename: str, content: bytes, document_id: str, provider: LLMProvider) -> DocumentOutput:
    """Run the linear pipeline; a failed stage halts and routes to human review."""
    try:
        return _run_stages(filename, content, document_id, provider)
    except _STAGE_FAILURES as exc:
        return _stage_failure_output(filename, document_id, exc)


def _run_stages(filename: str, content: bytes, document_id: str, provider: LLMProvider) -> DocumentOutput:
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
        classification.document_type,
        fields,
        required_fields,
        DEFAULT_THRESHOLDS,
        classification_confidence=classification.confidence,
        instructions=instructions,
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


def _stage_failure_output(filename: str, document_id: str, exc: Exception) -> DocumentOutput:
    return DocumentOutput(
        document_id=document_id,
        source_filename=filename,
        document_type="unknown",
        template="unknown",
        classification_confidence=0.0,
        fields=[],
        review_items=[
            ReviewItem(
                field_name=DOCUMENT_LEVEL_FIELD,
                reason="stage_failure",
                detail=str(exc),
            )
        ],
        status="needs_review",
    )
