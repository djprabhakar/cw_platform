from __future__ import annotations

from pydantic import BaseModel

from cw_platform.models.document import BoundingBox


class SourceRef(BaseModel):
    page: int
    bbox: BoundingBox | None
    text_span: str


class ProvenanceRecord(BaseModel):
    field_name: str
    source: SourceRef
    transformation_applied: str | None
    agent: str
    confidence: float
