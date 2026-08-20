from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BoundingBox(BaseModel):
    page: int
    x0: float
    y0: float
    x1: float
    y1: float


class TableCell(BaseModel):
    text: str
    row: int
    col: int
    bbox: BoundingBox


class Table(BaseModel):
    cells: list[TableCell]
    page: int


class Block(BaseModel):
    text: str
    bbox: BoundingBox
    kind: Literal["paragraph", "heading"]


class Page(BaseModel):
    number: int
    blocks: list[Block]
    tables: list[Table]
    width: float
    height: float


class ExtractedDocument(BaseModel):
    source_filename: str
    pages: list[Page]

    def full_text(self) -> str:
        lines: list[str] = []
        for page in self.pages:
            for block in page.blocks:
                lines.append(block.text)
        return "\n".join(lines)
