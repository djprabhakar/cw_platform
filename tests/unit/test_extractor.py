from cw_platform.extraction_agent.extractor import extract_fields
from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.models.instructions import Instruction, InstructionSet
from cw_platform.models.mapping import CoverageReport, FieldMapping


def test_extract_fields_applies_transform_when_instruction_present():
    coverage = CoverageReport(
        document_type="agent_bank_notice_interest_payment",
        mappings=[FieldMapping(field_name="payment_amount", status="found", page=1, text_span="45,000", notes="ok")],
    )
    instructions = InstructionSet(
        instructions=[
            Instruction(
                field_name="payment_amount",
                instruction_text="reported in thousands",
                transformation="multiply_by_1000",
                confidence=0.9,
            )
        ]
    )
    provider = FakeLLMProvider(script=["45000|0.97"])

    fields = extract_fields(coverage, instructions, provider)

    assert len(fields) == 1
    field = fields[0]
    assert field.name == "payment_amount"
    assert field.value == "45000000.00"
    assert field.transformation_applied == "multiply_by_1000"
    assert field.confidence == 0.97
    assert field.provenance.source.page == 1
    assert field.provenance.source.text_span == "45,000"


def test_extract_fields_no_transform_when_no_instruction():
    coverage = CoverageReport(
        document_type="bank_statement",
        mappings=[FieldMapping(field_name="ending_balance", status="found", page=1, text_span="1,200.00", notes="ok")],
    )
    instructions = InstructionSet(instructions=[])
    provider = FakeLLMProvider(script=["1200.00|0.95"])

    fields = extract_fields(coverage, instructions, provider)

    assert fields[0].value == "1200.00"
    assert fields[0].transformation_applied is None


def test_extract_fields_skips_not_found_mappings():
    coverage = CoverageReport(
        document_type="bank_statement",
        mappings=[FieldMapping(field_name="routing_number", status="not_found", page=None, text_span=None, notes="missing")],
    )
    fields = extract_fields(coverage, InstructionSet(instructions=[]), FakeLLMProvider(script=[]))
    assert fields == []
