from __future__ import annotations

from pydantic import BaseModel

from cw_platform.llm.provider import LLMProvider
from cw_platform.models.document import ExtractedDocument

KNOWN_TYPES = ["bank_statement", "agent_bank_notice_interest_payment"]


class ClassificationResult(BaseModel):
    document_type: str
    template: str
    confidence: float


_PROMPT = """Classify this financial document into exactly one of: {types}, or "unknown".
Also give the template variant (use "base" if there is only one known template) and a
confidence between 0 and 1. Respond in exactly this format with no other text:
<document_type>|<template>|<confidence>

Document text:
{text}
"""


def classify(doc: ExtractedDocument, provider: LLMProvider) -> ClassificationResult:
    prompt = _PROMPT.format(types=", ".join(KNOWN_TYPES), text=doc.full_text())
    response = provider.complete(prompt)
    parts = response.text.strip().split("|")
    if len(parts) != 3:
        raise ValueError(f"Malformed classifier response: {response.text!r}")

    document_type, template, confidence_str = parts
    try:
        confidence = float(confidence_str)
    except ValueError as exc:
        raise ValueError(f"Malformed confidence value: {confidence_str!r}") from exc

    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"Confidence out of range [0,1]: {confidence}")

    return ClassificationResult(document_type=document_type, template=template, confidence=confidence)
