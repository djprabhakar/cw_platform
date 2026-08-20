from __future__ import annotations

from cw_platform.extraction_agent.transforms import apply_transform
from cw_platform.llm.provider import LLMProvider
from cw_platform.models.dictionary import DataDictionary
from cw_platform.models.instructions import InstructionSet
from cw_platform.models.mapping import CoverageReport
from cw_platform.models.output import OutputField
from cw_platform.models.provenance import ProvenanceRecord, SourceRef

_PROMPT = """Read the exact value for this field from the text span below and return it
verbatim, unmodified. Respond in exactly this format with no other text:
<value>|<confidence>

Field: {field_name}
Text span: {text_span}
"""


_DEFAULT_DATA_TYPE = "string"


def extract_fields(
    coverage: CoverageReport,
    instructions: InstructionSet,
    provider: LLMProvider,
    dictionary: DataDictionary | None = None,
) -> list[OutputField]:
    fields: list[OutputField] = []
    declared_types = {f.name: f.data_type for f in dictionary.fields} if dictionary else {}

    for mapping in coverage.mappings:
        if mapping.status != "found" or mapping.page is None or mapping.text_span is None:
            continue

        prompt = _PROMPT.format(field_name=mapping.field_name, text_span=mapping.text_span)
        response = provider.complete(prompt)
        raw_value, confidence_str = response.text.strip().split("|", maxsplit=1)

        instruction = instructions.for_field(mapping.field_name)
        transformation = instruction.transformation if instruction else None
        value = apply_transform(raw_value, transformation)

        provenance = ProvenanceRecord(
            field_name=mapping.field_name,
            source=SourceRef(page=mapping.page, bbox=None, text_span=mapping.text_span),
            transformation_applied=transformation,
            agent="extraction_agent",
            confidence=float(confidence_str),
        )
        fields.append(
            OutputField(
                name=mapping.field_name,
                value=value,
                data_type=declared_types.get(mapping.field_name, _DEFAULT_DATA_TYPE),
                confidence=float(confidence_str),
                transformation_applied=transformation,
                provenance=provenance,
            )
        )

    return fields
