from __future__ import annotations

from cw_platform.llm.provider import LLMProvider
from cw_platform.models.dictionary import DataDictionary
from cw_platform.models.document import ExtractedDocument
from cw_platform.models.mapping import CoverageReport, FieldMapping

_PROMPT = """You are locating one field in a financial document.

Field: {field_name}
Description: {description}
Example values: {examples}

Determine whether this field is present in the document below. Respond in
exactly this format with no other text:
<found|not_found|ambiguous>|<page number or ->|<exact text span or ->|<short note>

Document text:
{text}
"""


def map_fields(doc: ExtractedDocument, dictionary: DataDictionary, provider: LLMProvider) -> CoverageReport:
    mappings: list[FieldMapping] = []
    full_text = doc.full_text()

    for field in dictionary.fields:
        prompt = _PROMPT.format(
            field_name=field.name,
            description=field.description,
            examples=", ".join(field.example_values),
            text=full_text,
        )
        response = provider.complete(prompt)
        status, page_str, text_span, notes = response.text.strip().split("|", maxsplit=3)
        page = None if page_str == "-" else int(page_str)
        span = None if text_span == "-" else text_span
        mappings.append(
            FieldMapping(field_name=field.name, status=status, page=page, text_span=span, notes=notes)
        )

    return CoverageReport(document_type=dictionary.document_type, mappings=mappings)
