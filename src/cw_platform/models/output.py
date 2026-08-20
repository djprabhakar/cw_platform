from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

from cw_platform.models.provenance import ProvenanceRecord
from cw_platform.models.review import ReviewItem


class OutputField(BaseModel):
    name: str
    value: str
    data_type: str
    confidence: float
    transformation_applied: str | None
    provenance: ProvenanceRecord


class DocumentOutput(BaseModel):
    document_id: str
    source_filename: str
    document_type: str
    template: str
    classification_confidence: float
    fields: list[OutputField]
    review_items: list[ReviewItem]
    status: Literal["complete", "needs_review"]

    @model_validator(mode="after")
    def _status_matches_review_items(self) -> "DocumentOutput":
        has_review_items = len(self.review_items) > 0
        if self.status == "complete" and has_review_items:
            raise ValueError("status cannot be 'complete' when review_items is non-empty")
        if self.status == "needs_review" and not has_review_items:
            raise ValueError("status cannot be 'needs_review' when review_items is empty")
        return self
