from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.mapping.mapping_agent import map_fields
from cw_platform.models.dictionary import DataDictionary, FieldDef
from cw_platform.models.document import Block, BoundingBox, ExtractedDocument, Page


def _sample_doc() -> ExtractedDocument:
    bbox = BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1)
    page = Page(
        number=1,
        blocks=[Block(text="Ending Balance 1,200.00", bbox=bbox, kind="paragraph")],
        tables=[],
        width=612,
        height=792,
    )
    return ExtractedDocument(source_filename="doc.pdf", pages=[page])


def _sample_dictionary() -> DataDictionary:
    return DataDictionary(
        document_type="bank_statement",
        template="base",
        fields=[
            FieldDef(
                name="ending_balance",
                description="Ending balance",
                data_type="currency_amount",
                example_values=["1,200.00"],
                required=True,
            ),
            FieldDef(
                name="routing_number",
                description="Bank routing number",
                data_type="string",
                example_values=["021000021"],
                required=True,
            ),
        ],
    )


def test_map_fields_issues_one_call_per_field_and_parses_results():
    provider = FakeLLMProvider(
        script=[
            "found|1|Ending Balance 1,200.00|located near label 'Ending Balance'",
            "not_found|-|-|no routing number present in document",
        ]
    )
    report = map_fields(_sample_doc(), _sample_dictionary(), provider)
    assert len(report.mappings) == 2
    assert report.mappings[0].field_name == "ending_balance"
    assert report.mappings[0].status == "found"
    assert report.mappings[0].page == 1
    assert report.mappings[1].status == "not_found"
    assert report.mappings[1].page is None


def test_missing_required_lists_not_found_required_fields():
    provider = FakeLLMProvider(
        script=[
            "found|1|Ending Balance 1,200.00|ok",
            "not_found|-|-|missing",
        ]
    )
    dictionary = _sample_dictionary()
    report = map_fields(_sample_doc(), dictionary, provider)
    assert report.missing_required(dictionary) == ["routing_number"]
