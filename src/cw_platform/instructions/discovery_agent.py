from __future__ import annotations

from cw_platform.llm.provider import LLMProvider
from cw_platform.models.document import ExtractedDocument
from cw_platform.models.instructions import Instruction, InstructionSet
from cw_platform.models.mapping import CoverageReport

_PROMPT = """Search this ENTIRE document, including footnotes, headers, and legends anywhere
in the text, for any instruction that changes how the field "{field_name}" should be
interpreted (unit scale, currency, sign convention, date format, or a conditional
definition). Respond in exactly this format with no other text:
<none|found>|<instruction text or ->|<transformation or ->|<confidence>

Full document text:
{text}
"""


def discover_instructions(
    doc: ExtractedDocument, coverage: CoverageReport, provider: LLMProvider
) -> InstructionSet:
    instructions: list[Instruction] = []
    full_text = doc.full_text()

    for mapping in coverage.mappings:
        if mapping.status != "found":
            continue

        prompt = _PROMPT.format(field_name=mapping.field_name, text=full_text)
        response = provider.complete(prompt)
        status, instruction_text, transformation, confidence_str = response.text.strip().split("|", maxsplit=3)

        if status != "found":
            continue

        instructions.append(
            Instruction(
                field_name=mapping.field_name,
                instruction_text=instruction_text,
                transformation=transformation,
                confidence=float(confidence_str),
            )
        )

    return InstructionSet(instructions=instructions)
