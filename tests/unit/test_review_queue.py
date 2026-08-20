from cw_platform.models.instructions import Instruction, InstructionSet
from cw_platform.models.output import OutputField
from cw_platform.models.provenance import ProvenanceRecord, SourceRef
from cw_platform.review.queue import build_review_queue
from cw_platform.review.thresholds import DEFAULT_THRESHOLDS


def _field(name: str, confidence: float) -> OutputField:
    return OutputField(
        name=name,
        value="x",
        data_type="string",
        confidence=confidence,
        transformation_applied=None,
        provenance=ProvenanceRecord(
            field_name=name,
            source=SourceRef(page=1, bbox=None, text_span="x"),
            transformation_applied=None,
            agent="extraction_agent",
            confidence=confidence,
        ),
    )


def test_low_confidence_field_flagged():
    fields = [_field("ending_balance", 0.5)]
    items = build_review_queue("bank_statement", fields, ["ending_balance"], DEFAULT_THRESHOLDS)
    assert len(items) == 1
    assert items[0].reason == "low_confidence"
    assert items[0].field_name == "ending_balance"


def test_missing_required_field_flagged():
    items = build_review_queue("bank_statement", [], ["account_number"], DEFAULT_THRESHOLDS)
    assert len(items) == 1
    assert items[0].reason == "missing_required_field"
    assert items[0].field_name == "account_number"


def test_high_confidence_found_field_not_flagged():
    fields = [_field("ending_balance", 0.99)]
    items = build_review_queue("bank_statement", fields, ["ending_balance"], DEFAULT_THRESHOLDS)
    assert items == []


def _instruction(field_name: str, confidence: float) -> Instruction:
    return Instruction(
        field_name=field_name,
        instruction_text="reported in thousands",
        transformation="multiply_by_1000",
        confidence=confidence,
    )


def test_low_classification_confidence_flagged():
    fields = [_field("ending_balance", 0.99)]
    items = build_review_queue(
        "bank_statement",
        fields,
        ["ending_balance"],
        DEFAULT_THRESHOLDS,
        classification_confidence=0.30,
    )
    assert len(items) == 1
    assert items[0].field_name == "classification"
    assert items[0].reason == "low_confidence"
    assert "classification confidence 0.30" in items[0].detail


def test_low_instruction_confidence_flagged():
    fields = [_field("ending_balance", 0.99)]
    items = build_review_queue(
        "bank_statement",
        fields,
        ["ending_balance"],
        DEFAULT_THRESHOLDS,
        instructions=InstructionSet(instructions=[_instruction("ending_balance", 0.50)]),
    )
    assert len(items) == 1
    assert items[0].field_name == "ending_balance"
    assert items[0].reason == "low_confidence"
    assert "instruction interpretation confidence 0.50" in items[0].detail


def test_high_classification_and_instruction_confidence_not_flagged():
    fields = [_field("ending_balance", 0.99)]
    items = build_review_queue(
        "bank_statement",
        fields,
        ["ending_balance"],
        DEFAULT_THRESHOLDS,
        classification_confidence=0.97,
        instructions=InstructionSet(instructions=[_instruction("ending_balance", 0.95)]),
    )
    assert items == []
