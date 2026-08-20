from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from cw_platform.models.dictionary import DataDictionary


class FieldMapping(BaseModel):
    field_name: str
    status: Literal["found", "not_found", "ambiguous"]
    page: int | None
    text_span: str | None
    notes: str


class CoverageReport(BaseModel):
    document_type: str
    mappings: list[FieldMapping]

    def missing_required(self, dictionary: DataDictionary) -> list[str]:
        required_names = {f.name for f in dictionary.fields if f.required}
        by_name = {m.field_name: m for m in self.mappings}
        return [
            name
            for name in required_names
            if by_name.get(name) is None or by_name[name].status != "found"
        ]
