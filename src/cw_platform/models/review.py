from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReviewItem(BaseModel):
    field_name: str
    reason: Literal["low_confidence", "missing_required_field"]
    detail: str
