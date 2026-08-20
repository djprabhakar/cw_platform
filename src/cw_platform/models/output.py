from __future__ import annotations

from pydantic import BaseModel

from cw_platform.models.provenance import ProvenanceRecord


class OutputField(BaseModel):
    name: str
    value: str
    data_type: str
    confidence: float
    transformation_applied: str | None
    provenance: ProvenanceRecord
