from cw_platform.models.document import BoundingBox, Block, Table, TableCell, Page, ExtractedDocument


def test_bounding_box_fields():
    bbox = BoundingBox(page=1, x0=10.0, y0=20.0, x1=100.0, y1=40.0)
    assert bbox.page == 1
    assert bbox.x1 == 100.0


def test_extracted_document_full_text_concatenates_blocks_in_order():
    bbox = BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1)
    page1 = Page(
        number=1,
        blocks=[Block(text="Statement Period: Jan 2026", bbox=bbox, kind="paragraph")],
        tables=[],
        width=612,
        height=792,
    )
    page2 = Page(
        number=2,
        blocks=[Block(text="Ending Balance: 1,200.00", bbox=bbox, kind="paragraph")],
        tables=[],
        width=612,
        height=792,
    )
    doc = ExtractedDocument(source_filename="stmt.pdf", pages=[page1, page2])
    assert doc.full_text() == "Statement Period: Jan 2026\nEnding Balance: 1,200.00"


def test_page_with_table():
    bbox = BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1)
    cell = TableCell(text="1,200.00", row=0, col=1, bbox=bbox)
    table = Table(cells=[cell], page=1)
    page = Page(number=1, blocks=[], tables=[table], width=612, height=792)
    assert page.tables[0].cells[0].text == "1,200.00"
