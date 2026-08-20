from __future__ import annotations

from pathlib import Path

import pdfplumber

from cw_platform.models.document import Block, BoundingBox, ExtractedDocument, Page, Table, TableCell


def extract_layout(pdf_path: str | Path) -> ExtractedDocument:
    pages: list[Page] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, pdf_page in enumerate(pdf.pages, start=1):
            blocks = _extract_blocks(pdf_page, page_index)
            tables = _extract_tables(pdf_page, page_index)
            pages.append(
                Page(
                    number=page_index,
                    blocks=blocks,
                    tables=tables,
                    width=pdf_page.width,
                    height=pdf_page.height,
                )
            )
    return ExtractedDocument(source_filename=Path(pdf_path).name, pages=pages)


def _extract_blocks(pdf_page, page_index: int) -> list[Block]:
    blocks: list[Block] = []
    for line in pdf_page.extract_text_lines():
        bbox = BoundingBox(
            page=page_index,
            x0=line["x0"],
            y0=line["top"],
            x1=line["x1"],
            y1=line["bottom"],
        )
        blocks.append(Block(text=line["text"], bbox=bbox, kind="paragraph"))
    return blocks


def _extract_tables(pdf_page, page_index: int) -> list[Table]:
    tables: list[Table] = []
    for found_table in pdf_page.find_tables():
        cells: list[TableCell] = []
        rows = found_table.extract()
        for row_idx, row in enumerate(rows):
            for col_idx, cell_text in enumerate(row):
                if cell_text is None:
                    continue
                bbox = BoundingBox(
                    page=page_index,
                    x0=found_table.bbox[0],
                    y0=found_table.bbox[1],
                    x1=found_table.bbox[2],
                    y1=found_table.bbox[3],
                )
                cells.append(TableCell(text=cell_text, row=row_idx, col=col_idx, bbox=bbox))
        if cells:
            tables.append(Table(cells=cells, page=page_index))
    return tables
