from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FieldDef(BaseModel):
    name: str
    description: str
    data_type: Literal["string", "decimal", "date", "currency_amount"]
    example_values: list[str]
    required: bool


class DataDictionary(BaseModel):
    document_type: str
    template: str
    fields: list[FieldDef]
