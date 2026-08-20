from cw_platform.models.document import BoundingBox
from cw_platform.models.provenance import ProvenanceRecord, SourceRef


def test_provenance_record_round_trip():
    bbox = BoundingBox(page=2, x0=10, y0=20, x1=110, y1=40)
    source = SourceRef(page=2, bbox=bbox, text_span="1,200.00")
    record = ProvenanceRecord(
        field_name="ending_balance",
        source=source,
        transformation_applied="parsed_decimal(strip_commas)",
        agent="extraction_agent",
        confidence=0.94,
    )
    assert record.source.page == 2
    assert record.confidence == 0.94
    assert record.transformation_applied == "parsed_decimal(strip_commas)"


def test_provenance_record_allows_no_transformation():
    source = SourceRef(page=1, bbox=None, text_span="Jan 2026")
    record = ProvenanceRecord(
        field_name="statement_period",
        source=source,
        transformation_applied=None,
        agent="extraction_agent",
        confidence=0.88,
    )
    assert record.transformation_applied is None
