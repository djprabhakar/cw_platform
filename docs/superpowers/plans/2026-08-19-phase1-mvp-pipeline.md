# Financial Document Platform — Phase 1 MVP Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core linear extraction pipeline (ingestion → layout-aware extraction → classification → data-dictionary mapping → instruction discovery → extraction → confidence routing → provenance-tagged canonical output) for two document types — Bank Statements and Agent Bank Notices (Interest Payment Schedules) — matching the spec's Phase 1 — MVP scope.

**Architecture:** A single Python package (`cw_platform`) with one module per pipeline stage, each stage a pure function/class operating on typed dataclasses that flow through a sequential orchestrator (`orchestration/pipeline.py`). All LLM calls go through one abstract `LLMProvider` interface so the concrete vendor (Anthropic, Azure OpenAI, self-hosted, etc.) is a Phase 1.5 decision, not a Phase 1 blocker — tests run entirely against a scripted `FakeLLMProvider`. A thin FastAPI app exposes submit/status/result endpoints as the only downstream-delivery surface for Phase 1 (full delivery integrations are Phase 3 / Module O3).

**Tech Stack:** Python 3.11+, `pydantic` (typed models + schema validation), `pdfplumber` (layout-aware PDF text/table extraction), `pytest` (TDD), FastAPI + `httpx`/`TestClient` (API layer), `PyYAML` (data dictionary files stored as YAML), no external services required to run the test suite.

**Spec:** [docs/spec/Agentic_Financial_Document_Platform_Features.md](../../spec/Agentic_Financial_Document_Platform_Features.md) — this plan implements the "Phase 1 — MVP" row of Section 6 (Phased Roadmap): *"Two to three document types to bootstrap the Knowledge Base. Core linear pipeline: ingestion, layout-aware extraction, classification, mapping, instruction discovery, extraction. Manually seeded data dictionaries. Basic confidence-threshold review routing. Field-level provenance capture."*

## Global Constraints

- MVP document types are exactly two: **Bank Statement** and **Agent Bank Notice — Interest Payment Schedule** (per user decision; spec Section 7 recommends 2-3 types to bootstrap the Knowledge Base).
- MVP input format is **digital (text-layer) PDF only**. Scanned/OCR, TIFF, DOCX, XLSX, HTML/XBRL, email, and ZIP bundles are explicitly out of scope for this plan (spec Module A3 lists them as targets for a later ingestion-hardening plan).
- The pipeline is **strictly linear** for Phase 1 (spec Module K1's conditional loop-back orchestration is Phase 3 scope) — a failed stage routes the document to human review and halts, it does not trigger automatic re-routing to an earlier stage.
- **No knowledge-base persistence of learned rules** in this plan (spec Module D2 "Template Memory" and F3 "Rule Persistence" are Phase 2). Instruction discovery and mapping results are computed fresh per document and attached to that document's output only.
- **No independent verifier agent or cross-field reconciliation** (spec Module H is explicitly "not present in the original design" and is Phase 2/3 scope here).
- Data dictionaries are **manually authored YAML files** checked into the repo, not a governed/versioned Knowledge Base service (spec Module D1 base-plus-override model is respected structurally, but D3 governance workflow is Phase 3).
- Every extracted field value in the final output MUST carry a source location (page + bounding box or text span) and the transformation applied — per spec's Guiding Principle #3 and Module J1, this is non-negotiable even at MVP scope.
- All LLM-backed agents (classifier, mapping agent, instruction discovery agent, extraction agent) MUST be written against the `LLMProvider` abstract interface from Task 1 — no task may import a concrete vendor SDK directly.
- Confidence thresholds (classification, instruction interpretation, extracted value) MUST be configurable per document type and per field, per spec Module I1 — not hardcoded constants.

---

## File Structure

```
CW_Data_Platform/
  pyproject.toml
  src/
    cw_platform/
      __init__.py
      llm/
        __init__.py
        provider.py            # LLMProvider ABC, LLMResponse, FakeLLMProvider
      models/
        __init__.py
        document.py             # Page, Block, TableCell, ExtractedDocument
        provenance.py           # SourceRef, ProvenanceRecord
        dictionary.py           # FieldDef, DataDictionary
        mapping.py              # FieldMapping, CoverageReport
        instructions.py         # Instruction, InstructionSet
        review.py               # ReviewReason, ReviewItem
        output.py                # OutputField, DocumentOutput
      ingestion/
        __init__.py
        intake.py                # normalize raw bytes + filename -> RawDocument
      extraction/
        __init__.py
        layout_extractor.py      # PDF -> ExtractedDocument (pdfplumber-based)
      knowledge_base/
        __init__.py
        loader.py                 # YAML -> DataDictionary, base+override merge
        dictionaries/
          bank_statement.yaml
          agent_bank_notice_interest_payment.yaml
      classification/
        __init__.py
        classifier.py              # ExtractedDocument -> ClassificationResult
      mapping/
        __init__.py
        mapping_agent.py            # (ExtractedDocument, DataDictionary) -> CoverageReport
      instructions/
        __init__.py
        discovery_agent.py          # (ExtractedDocument, CoverageReport) -> InstructionSet
      extraction_agent/
        __init__.py
        transforms.py                # apply numeric/date/currency transforms
        extractor.py                 # (CoverageReport, InstructionSet) -> list[OutputField]
      review/
        __init__.py
        thresholds.py                 # per-type/per-field threshold config + lookup
        queue.py                      # ReviewItem creation/routing
      orchestration/
        __init__.py
        pipeline.py                    # wires all stages, produces DocumentOutput
      api/
        __init__.py
        app.py                          # FastAPI: POST /documents, GET /documents/{id}
  tests/
    conftest.py
    fixtures/
      bank_statement_sample.pdf
      agent_bank_notice_sample.pdf
      make_fixtures.py                  # script that generates the two PDFs above
    unit/
      test_llm_provider.py
      test_models_document.py
      test_ingestion_intake.py
      test_layout_extractor.py
      test_kb_loader.py
      test_classifier.py
      test_mapping_agent.py
      test_discovery_agent.py
      test_transforms.py
      test_extractor.py
      test_thresholds.py
      test_review_queue.py
      test_output_schema.py
    integration/
      test_pipeline_end_to_end.py
      test_api.py
```

---

### Task 1: LLM Provider Abstraction

**Files:**
- Create: `src/cw_platform/llm/__init__.py`
- Create: `src/cw_platform/llm/provider.py`
- Test: `tests/unit/test_llm_provider.py`

**Interfaces:**
- Produces: `LLMResponse(text: str, raw: dict | None = None)`; `LLMProvider` ABC with `complete(self, prompt: str, *, system: str | None = None, response_schema: dict | None = None) -> LLMResponse`; `FakeLLMProvider(script: list[str] | dict[str, str])` implementing `LLMProvider`, used by every later agent's tests — `FakeLLMProvider(script=["resp1", "resp2"])` returns scripted responses in call order, `FakeLLMProvider(script={"substring": "resp"})` returns the first response whose key is a substring of the prompt (raises `AssertionError` if no script entry matches and no default is set).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_llm_provider.py
import pytest
from cw_platform.llm.provider import LLMProvider, LLMResponse, FakeLLMProvider


def test_fake_provider_returns_scripted_responses_in_order():
    provider = FakeLLMProvider(script=["first", "second"])
    r1 = provider.complete("prompt one")
    r2 = provider.complete("prompt two")
    assert r1 == LLMResponse(text="first")
    assert r2 == LLMResponse(text="second")


def test_fake_provider_raises_when_script_exhausted():
    provider = FakeLLMProvider(script=["only one"])
    provider.complete("prompt one")
    with pytest.raises(IndexError):
        provider.complete("prompt two")


def test_fake_provider_matches_by_prompt_substring():
    provider = FakeLLMProvider(script={"currency": "USD found", "unit scale": "thousands"})
    r = provider.complete("Please determine the currency for this field")
    assert r.text == "USD found"


def test_fake_provider_substring_no_match_raises():
    provider = FakeLLMProvider(script={"currency": "USD found"})
    with pytest.raises(AssertionError):
        provider.complete("totally unrelated prompt")


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_llm_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.llm.provider'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/llm/__init__.py
```

```python
# src/cw_platform/llm/provider.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    raw: dict | None = None


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        raise NotImplementedError


class FakeLLMProvider(LLMProvider):
    def __init__(self, script: list[str] | dict[str, str]):
        self._script = script
        self._index = 0

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        if isinstance(self._script, list):
            text = self._script[self._index]
            self._index += 1
            return LLMResponse(text=text)

        for key, text in self._script.items():
            if key in prompt:
                return LLMResponse(text=text)
        raise AssertionError(f"FakeLLMProvider: no script entry matches prompt: {prompt!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_llm_provider.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/llm/ tests/unit/test_llm_provider.py
git commit -m "feat: add LLMProvider abstraction with fake test provider"
```

---

### Task 2: Core Document Models

**Files:**
- Create: `src/cw_platform/models/__init__.py`
- Create: `src/cw_platform/models/document.py`
- Test: `tests/unit/test_models_document.py`

**Interfaces:**
- Produces: `BoundingBox(page: int, x0: float, y0: float, x1: float, y1: float)`; `TableCell(text: str, row: int, col: int, bbox: BoundingBox)`; `Table(cells: list[TableCell], page: int)`; `Block(text: str, bbox: BoundingBox, kind: Literal["paragraph", "heading"])`; `Page(number: int, blocks: list[Block], tables: list[Table], width: float, height: float)`; `ExtractedDocument(source_filename: str, pages: list[Page])` with method `full_text(self) -> str` that concatenates all block text across pages in page order, separated by `"\n"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_models_document.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models_document.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.models.document'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/models/__init__.py
```

```python
# src/cw_platform/models/document.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_models_document.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/models/__init__.py src/cw_platform/models/document.py tests/unit/test_models_document.py
git commit -m "feat: add core document models (Page, Block, Table, ExtractedDocument)"
```

---

### Task 3: Provenance Model

**Files:**
- Create: `src/cw_platform/models/provenance.py`
- Test: `tests/unit/test_provenance.py`

**Interfaces:**
- Consumes: `BoundingBox` from `cw_platform.models.document` (Task 2).
- Produces: `SourceRef(page: int, bbox: BoundingBox | None, text_span: str)`; `ProvenanceRecord(field_name: str, source: SourceRef, transformation_applied: str | None, agent: str, confidence: float)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_provenance.py
from cw_platform.models.document import BoundingBox
from cw_platform.models.provenance import ProvenanceRecord, SourceRef


def test_provenance_record_round_trip():
    bbox = BoundingBox(page=2, x0=10, y0=20, x1=110, y1=40)
    source = SourceRef(page=2, bbox=bbox, text_span="1,200.00")
    record = ProvenanceRecord(
        field_name="ending_balance",
        source=source,
        transformation_applied="parsed_decimal(strip_commas)",
        agent="extraction_agent",
        confidence=0.94,
    )
    assert record.source.page == 2
    assert record.confidence == 0.94
    assert record.transformation_applied == "parsed_decimal(strip_commas)"


def test_provenance_record_allows_no_transformation():
    source = SourceRef(page=1, bbox=None, text_span="Jan 2026")
    record = ProvenanceRecord(
        field_name="statement_period",
        source=source,
        transformation_applied=None,
        agent="extraction_agent",
        confidence=0.88,
    )
    assert record.transformation_applied is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_provenance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.models.provenance'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/models/provenance.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_provenance.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/models/provenance.py tests/unit/test_provenance.py
git commit -m "feat: add provenance record models"
```

---

### Task 4: Data Dictionary Model + Base/Override Loader

**Files:**
- Create: `src/cw_platform/models/dictionary.py`
- Create: `src/cw_platform/knowledge_base/__init__.py`
- Create: `src/cw_platform/knowledge_base/loader.py`
- Create: `src/cw_platform/knowledge_base/dictionaries/bank_statement.yaml`
- Create: `src/cw_platform/knowledge_base/dictionaries/agent_bank_notice_interest_payment.yaml`
- Test: `tests/unit/test_kb_loader.py`

**Interfaces:**
- Produces: `FieldDef(name: str, description: str, data_type: Literal["string","decimal","date","currency_amount"], example_values: list[str], required: bool)`; `DataDictionary(document_type: str, template: str, fields: list[FieldDef])`; `load_data_dictionary(document_type: str, template: str) -> DataDictionary` — reads `{document_type}.yaml` as base, applies an `overrides` section keyed by template name if present (override fields replace base fields of the same `name`; base fields not overridden pass through unchanged), raises `FileNotFoundError` if no YAML exists for `document_type`, raises `KeyError` if `template` is not `"base"` and not present in the file's `overrides` section.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_kb_loader.py
import pytest
from cw_platform.knowledge_base.loader import load_data_dictionary


def test_loads_base_bank_statement_dictionary():
    dd = load_data_dictionary("bank_statement", "base")
    assert dd.document_type == "bank_statement"
    field_names = {f.name for f in dd.fields}
    assert "ending_balance" in field_names
    assert "statement_period_end" in field_names


def test_loads_agent_bank_notice_dictionary():
    dd = load_data_dictionary("agent_bank_notice_interest_payment", "base")
    field_names = {f.name for f in dd.fields}
    assert "payment_amount" in field_names
    assert "interest_rate" in field_names


def test_unknown_document_type_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_data_dictionary("nonexistent_type", "base")


def test_unknown_template_raises_key_error():
    with pytest.raises(KeyError):
        load_data_dictionary("bank_statement", "nonexistent_template")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_kb_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.knowledge_base.loader'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/models/dictionary.py
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
```

```python
# src/cw_platform/knowledge_base/__init__.py
```

```yaml
# src/cw_platform/knowledge_base/dictionaries/bank_statement.yaml
document_type: bank_statement
fields:
  - name: account_number
    description: The account number the statement is issued for.
    data_type: string
    example_values: ["1234567890"]
    required: true
  - name: statement_period_end
    description: The last date covered by this statement.
    data_type: date
    example_values: ["2026-01-31"]
    required: true
  - name: ending_balance
    description: The account balance as of the statement period end date.
    data_type: currency_amount
    example_values: ["1,200.00"]
    required: true
overrides: {}
```

```yaml
# src/cw_platform/knowledge_base/dictionaries/agent_bank_notice_interest_payment.yaml
document_type: agent_bank_notice_interest_payment
fields:
  - name: payment_amount
    description: The interest payment amount due for this period.
    data_type: currency_amount
    example_values: ["45,000.00"]
    required: true
  - name: interest_rate
    description: The interest rate applied for this payment period.
    data_type: decimal
    example_values: ["4.75%"]
    required: true
  - name: payment_date
    description: The date the interest payment is due or was made.
    data_type: date
    example_values: ["2026-02-15"]
    required: true
overrides: {}
```

```python
# src/cw_platform/knowledge_base/loader.py
from __future__ import annotations

from pathlib import Path

import yaml

from cw_platform.models.dictionary import DataDictionary, FieldDef

_DICT_DIR = Path(__file__).parent / "dictionaries"


def load_data_dictionary(document_type: str, template: str) -> DataDictionary:
    path = _DICT_DIR / f"{document_type}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No data dictionary for document type: {document_type}")

    raw = yaml.safe_load(path.read_text())
    base_fields = {f["name"]: f for f in raw["fields"]}

    if template != "base":
        overrides = raw.get("overrides", {})
        if template not in overrides:
            raise KeyError(f"No override template '{template}' for document type '{document_type}'")
        for override_field in overrides[template]:
            base_fields[override_field["name"]] = override_field

    fields = [FieldDef(**f) for f in base_fields.values()]
    return DataDictionary(document_type=document_type, template=template, fields=fields)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_kb_loader.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/models/dictionary.py src/cw_platform/knowledge_base/ tests/unit/test_kb_loader.py
git commit -m "feat: add data dictionary model and base/override YAML loader"
```

---

### Task 5: Test Fixture PDFs

**Files:**
- Create: `tests/fixtures/make_fixtures.py`
- Create: `tests/fixtures/bank_statement_sample.pdf` (generated, not hand-written)
- Create: `tests/fixtures/agent_bank_notice_sample.pdf` (generated, not hand-written)

**Interfaces:**
- Produces: two on-disk PDF fixtures used by Tasks 6, 9, 10, 11, 15, 16. `bank_statement_sample.pdf` contains the text "Account Number: 1234567890", "Statement Period End: 01/31/2026", and a table with a row `Ending Balance | 1,200.00`. `agent_bank_notice_sample.pdf` contains "Interest Payment Notice", a table with rows `Payment Amount | 45,000` and `Interest Rate | 4.75%`, "Payment Date: 02/15/2026", and a footnote `Note 1: Payment Amount is reported in whole dollars.`

- [ ] **Step 1: Write the fixture-generation script**

```python
# tests/fixtures/make_fixtures.py
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

FIXTURES_DIR = Path(__file__).parent


def make_bank_statement_pdf() -> None:
    path = FIXTURES_DIR / "bank_statement_sample.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, "Monthly Bank Statement")
    c.drawString(72, 690, "Account Number: 1234567890")
    c.drawString(72, 670, "Statement Period End: 01/31/2026")
    c.drawString(72, 620, "Ending Balance")
    c.drawString(250, 620, "1,200.00")
    c.save()


def make_agent_bank_notice_pdf() -> None:
    path = FIXTURES_DIR / "agent_bank_notice_sample.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, "Interest Payment Notice")
    c.drawString(72, 680, "Payment Amount")
    c.drawString(250, 680, "45,000")
    c.drawString(72, 660, "Interest Rate")
    c.drawString(250, 660, "4.75%")
    c.drawString(72, 640, "Payment Date: 02/15/2026")
    c.setFont("Helvetica", 9)
    c.drawString(72, 100, "Note 1: Payment Amount is reported in whole dollars.")
    c.save()


if __name__ == "__main__":
    make_bank_statement_pdf()
    make_agent_bank_notice_pdf()
    print("Fixtures written to", FIXTURES_DIR)
```

- [ ] **Step 2: Add reportlab as a dev dependency and generate the fixtures**

Run: `pip install reportlab` then `python tests/fixtures/make_fixtures.py`
Expected: prints `Fixtures written to .../tests/fixtures` and both PDF files exist on disk.

- [ ] **Step 3: Verify fixtures are readable**

Run: `python -c "import pdfplumber; print(pdfplumber.open('tests/fixtures/bank_statement_sample.pdf').pages[0].extract_text())"`
Expected: prints text including `Account Number: 1234567890`.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/make_fixtures.py tests/fixtures/bank_statement_sample.pdf tests/fixtures/agent_bank_notice_sample.pdf
git commit -m "test: add generated PDF fixtures for bank statement and agent bank notice"
```

---

### Task 6: Layout-Aware PDF Extraction

**Files:**
- Create: `src/cw_platform/extraction/__init__.py`
- Create: `src/cw_platform/extraction/layout_extractor.py`
- Test: `tests/unit/test_layout_extractor.py`

**Interfaces:**
- Consumes: `ExtractedDocument`, `Page`, `Block`, `Table`, `TableCell`, `BoundingBox` from `cw_platform.models.document` (Task 2); fixture PDFs from Task 5.
- Produces: `extract_layout(pdf_path: str | Path) -> ExtractedDocument` — opens the PDF with `pdfplumber`, emits one `Page` per PDF page with `blocks` from `page.extract_words()` grouped into lines (one `Block` per line of text, `kind="paragraph"`) and `tables` from `page.extract_tables()` converted into `Table`/`TableCell` objects with bounding boxes from `page.find_tables()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_layout_extractor.py
from pathlib import Path

from cw_platform.extraction.layout_extractor import extract_layout

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_layout_returns_one_page():
    doc = extract_layout(FIXTURES / "bank_statement_sample.pdf")
    assert len(doc.pages) == 1


def test_extract_layout_captures_account_number_text():
    doc = extract_layout(FIXTURES / "bank_statement_sample.pdf")
    assert "1234567890" in doc.full_text()


def test_extract_layout_blocks_have_bounding_boxes():
    doc = extract_layout(FIXTURES / "bank_statement_sample.pdf")
    block = doc.pages[0].blocks[0]
    assert block.bbox.page == 1
    assert block.bbox.x1 > block.bbox.x0


def test_extract_layout_notice_pdf_text():
    doc = extract_layout(FIXTURES / "agent_bank_notice_sample.pdf")
    assert "Interest Payment Notice" in doc.full_text()
    assert "Note 1: Payment Amount is reported in whole dollars." in doc.full_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_layout_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.extraction.layout_extractor'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/extraction/__init__.py
```

```python
# src/cw_platform/extraction/layout_extractor.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_layout_extractor.py -v`
Expected: PASS (4 passed) — if `extract_text_lines` groups the "Ending Balance" / "1,200.00" pair differently than expected, adjust the fixture assertions to match actual `pdfplumber` line grouping rather than the extractor (verify with a scratch script printing `pdf_page.extract_text_lines()` before changing implementation code).

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/extraction/ tests/unit/test_layout_extractor.py
git commit -m "feat: add layout-aware PDF text and table extraction"
```

---

### Task 7: Ingestion Intake (Multi-Format Entry Point, PDF-Only for MVP)

**Files:**
- Create: `src/cw_platform/ingestion/__init__.py`
- Create: `src/cw_platform/ingestion/intake.py`
- Test: `tests/unit/test_ingestion_intake.py`

**Interfaces:**
- Produces: `UnsupportedFormatError(Exception)`; `RawDocument(filename: str, content: bytes, format: Literal["pdf"])`; `intake(filename: str, content: bytes) -> RawDocument` — inspects the filename extension, returns a `RawDocument` with `format="pdf"` for `.pdf` files, raises `UnsupportedFormatError` for any other extension (message names the extension and states only PDF is supported in this release).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_ingestion_intake.py
import pytest
from cw_platform.ingestion.intake import RawDocument, UnsupportedFormatError, intake


def test_intake_accepts_pdf():
    doc = intake("statement.pdf", b"%PDF-1.4 fake bytes")
    assert isinstance(doc, RawDocument)
    assert doc.format == "pdf"
    assert doc.filename == "statement.pdf"


def test_intake_rejects_non_pdf():
    with pytest.raises(UnsupportedFormatError, match="docx"):
        intake("statement.docx", b"fake bytes")


def test_intake_rejects_no_extension():
    with pytest.raises(UnsupportedFormatError):
        intake("statement", b"fake bytes")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_ingestion_intake.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.ingestion.intake'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/ingestion/__init__.py
```

```python
# src/cw_platform/ingestion/intake.py
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class UnsupportedFormatError(Exception):
    pass


class RawDocument(BaseModel):
    filename: str
    content: bytes
    format: Literal["pdf"]


def intake(filename: str, content: bytes) -> RawDocument:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix != "pdf":
        raise UnsupportedFormatError(
            f"Unsupported file extension '.{suffix}': only PDF is supported in this release."
        )
    return RawDocument(filename=filename, content=content, format="pdf")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_ingestion_intake.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/ingestion/ tests/unit/test_ingestion_intake.py
git commit -m "feat: add PDF-only ingestion intake with unsupported-format guard"
```

---

### Task 8: Document Classifier

**Files:**
- Create: `src/cw_platform/classification/__init__.py`
- Create: `src/cw_platform/classification/classifier.py`
- Test: `tests/unit/test_classifier.py`

**Interfaces:**
- Consumes: `ExtractedDocument` (Task 2), `LLMProvider`/`FakeLLMProvider` (Task 1).
- Produces: `ClassificationResult(document_type: str, template: str, confidence: float)`; `classify(doc: ExtractedDocument, provider: LLMProvider) -> ClassificationResult` — sends a prompt containing `doc.full_text()` and the two known type labels (`bank_statement`, `agent_bank_notice_interest_payment`) plus `"unknown"`, asking the LLM to respond as `"<document_type>|<template>|<confidence 0-1>"`; parses that pipe-delimited response. Raises `ValueError` if the response cannot be parsed into exactly three parts or confidence is not a float in `[0, 1]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_classifier.py
import pytest
from cw_platform.classification.classifier import ClassificationResult, classify
from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.models.document import Block, BoundingBox, ExtractedDocument, Page


def _doc_with_text(text: str) -> ExtractedDocument:
    bbox = BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1)
    page = Page(number=1, blocks=[Block(text=text, bbox=bbox, kind="paragraph")], tables=[], width=612, height=792)
    return ExtractedDocument(source_filename="doc.pdf", pages=[page])


def test_classify_parses_provider_response():
    doc = _doc_with_text("Monthly Bank Statement, Account Number: 1234567890")
    provider = FakeLLMProvider(script=["bank_statement|base|0.93"])
    result = classify(doc, provider)
    assert result == ClassificationResult(document_type="bank_statement", template="base", confidence=0.93)


def test_classify_raises_on_malformed_response():
    doc = _doc_with_text("irrelevant")
    provider = FakeLLMProvider(script=["not a valid response"])
    with pytest.raises(ValueError):
        classify(doc, provider)


def test_classify_raises_on_out_of_range_confidence():
    doc = _doc_with_text("irrelevant")
    provider = FakeLLMProvider(script=["bank_statement|base|1.5"])
    with pytest.raises(ValueError):
        classify(doc, provider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.classification.classifier'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/classification/__init__.py
```

```python
# src/cw_platform/classification/classifier.py
from __future__ import annotations

from pydantic import BaseModel

from cw_platform.llm.provider import LLMProvider
from cw_platform.models.document import ExtractedDocument

KNOWN_TYPES = ["bank_statement", "agent_bank_notice_interest_payment"]


class ClassificationResult(BaseModel):
    document_type: str
    template: str
    confidence: float


_PROMPT = """Classify this financial document into exactly one of: {types}, or "unknown".
Also give the template variant (use "base" if there is only one known template) and a
confidence between 0 and 1. Respond in exactly this format with no other text:
<document_type>|<template>|<confidence>

Document text:
{text}
"""


def classify(doc: ExtractedDocument, provider: LLMProvider) -> ClassificationResult:
    prompt = _PROMPT.format(types=", ".join(KNOWN_TYPES), text=doc.full_text())
    response = provider.complete(prompt)
    parts = response.text.strip().split("|")
    if len(parts) != 3:
        raise ValueError(f"Malformed classifier response: {response.text!r}")

    document_type, template, confidence_str = parts
    try:
        confidence = float(confidence_str)
    except ValueError as exc:
        raise ValueError(f"Malformed confidence value: {confidence_str!r}") from exc

    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"Confidence out of range [0,1]: {confidence}")

    return ClassificationResult(document_type=document_type, template=template, confidence=confidence)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_classifier.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/classification/ tests/unit/test_classifier.py
git commit -m "feat: add LLM-backed document classifier with parsed confidence output"
```

---

### Task 9: Data Dictionary Mapping Agent (Full-Coverage)

**Files:**
- Create: `src/cw_platform/models/mapping.py`
- Create: `src/cw_platform/mapping/__init__.py`
- Create: `src/cw_platform/mapping/mapping_agent.py`
- Test: `tests/unit/test_mapping_agent.py`

**Interfaces:**
- Consumes: `ExtractedDocument` (Task 2), `DataDictionary`/`FieldDef` (Task 4), `LLMProvider` (Task 1).
- Produces: `FieldMapping(field_name: str, status: Literal["found","not_found","ambiguous"], page: int | None, text_span: str | None, notes: str)`; `CoverageReport(document_type: str, mappings: list[FieldMapping])` with method `missing_required(self, dictionary: DataDictionary) -> list[str]` returning names of required fields whose mapping status is not `"found"`; `map_fields(doc: ExtractedDocument, dictionary: DataDictionary, provider: LLMProvider) -> CoverageReport` — issues one `provider.complete(...)` call per field in `dictionary.fields` (guaranteeing full coverage per spec E1), parsing each response as `"<status>|<page>|<text_span>|<notes>"` where `page` is `"-"` when status is `"not_found"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_mapping_agent.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_mapping_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.mapping.mapping_agent'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/models/mapping.py
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
```

```python
# src/cw_platform/mapping/__init__.py
```

```python
# src/cw_platform/mapping/mapping_agent.py
from __future__ import annotations

from cw_platform.llm.provider import LLMProvider
from cw_platform.models.dictionary import DataDictionary
from cw_platform.models.document import ExtractedDocument
from cw_platform.models.mapping import CoverageReport, FieldMapping

_PROMPT = """You are locating one field in a financial document.

Field: {field_name}
Description: {description}
Example values: {examples}

Determine whether this field is present in the document below. Respond in
exactly this format with no other text:
<found|not_found|ambiguous>|<page number or ->|<exact text span or ->|<short note>

Document text:
{text}
"""


def map_fields(doc: ExtractedDocument, dictionary: DataDictionary, provider: LLMProvider) -> CoverageReport:
    mappings: list[FieldMapping] = []
    full_text = doc.full_text()

    for field in dictionary.fields:
        prompt = _PROMPT.format(
            field_name=field.name,
            description=field.description,
            examples=", ".join(field.example_values),
            text=full_text,
        )
        response = provider.complete(prompt)
        status, page_str, text_span, notes = response.text.strip().split("|", maxsplit=3)
        page = None if page_str == "-" else int(page_str)
        span = None if text_span == "-" else text_span
        mappings.append(
            FieldMapping(field_name=field.name, status=status, page=page, text_span=span, notes=notes)
        )

    return CoverageReport(document_type=dictionary.document_type, mappings=mappings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_mapping_agent.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/models/mapping.py src/cw_platform/mapping/ tests/unit/test_mapping_agent.py
git commit -m "feat: add full-coverage data dictionary mapping agent"
```

---

### Task 10: Instruction Discovery Agent

**Files:**
- Create: `src/cw_platform/models/instructions.py`
- Create: `src/cw_platform/instructions/__init__.py`
- Create: `src/cw_platform/instructions/discovery_agent.py`
- Test: `tests/unit/test_discovery_agent.py`

**Interfaces:**
- Consumes: `ExtractedDocument` (Task 2), `CoverageReport`/`FieldMapping` (Task 9), `LLMProvider` (Task 1).
- Produces: `Instruction(field_name: str, instruction_text: str, transformation: str, confidence: float)`; `InstructionSet(instructions: list[Instruction])` with method `for_field(self, field_name: str) -> Instruction | None`; `discover_instructions(doc: ExtractedDocument, coverage: CoverageReport, provider: LLMProvider) -> InstructionSet` — for every mapping with `status == "found"`, issues one document-wide `provider.complete(...)` call (full document text, not just the field's local context, per spec F1's "document-wide search scope by design") asking for any value-modifying instruction; parses `"<none|found>|<instruction_text or ->|<transformation or ->|<confidence>"`; only appends an `Instruction` to the result when the parsed status is `"found"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_discovery_agent.py
from cw_platform.instructions.discovery_agent import discover_instructions
from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.models.document import Block, BoundingBox, ExtractedDocument, Page
from cw_platform.models.mapping import CoverageReport, FieldMapping


def _doc_with_footnote() -> ExtractedDocument:
    bbox = BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1)
    blocks = [
        Block(text="Payment Amount 45,000", bbox=bbox, kind="paragraph"),
        Block(text="Note 1: Payment Amount is reported in thousands.", bbox=bbox, kind="paragraph"),
    ]
    page = Page(number=1, blocks=blocks, tables=[], width=612, height=792)
    return ExtractedDocument(source_filename="notice.pdf", pages=[page])


def _coverage_with_one_found_field() -> CoverageReport:
    return CoverageReport(
        document_type="agent_bank_notice_interest_payment",
        mappings=[
            FieldMapping(field_name="payment_amount", status="found", page=1, text_span="45,000", notes="ok"),
            FieldMapping(field_name="interest_rate", status="not_found", page=None, text_span=None, notes="missing"),
        ],
    )


def test_discover_instructions_only_queries_found_fields():
    provider = FakeLLMProvider(script=["found|Payment Amount is reported in thousands.|multiply_by_1000|0.9"])
    result = discover_instructions(_doc_with_footnote(), _coverage_with_one_found_field(), provider)
    assert len(result.instructions) == 1
    assert result.instructions[0].field_name == "payment_amount"
    assert result.instructions[0].transformation == "multiply_by_1000"


def test_discover_instructions_skips_fields_with_no_instruction():
    provider = FakeLLMProvider(script=["none|-|-|0.95"])
    result = discover_instructions(_doc_with_footnote(), _coverage_with_one_found_field(), provider)
    assert result.instructions == []


def test_for_field_returns_none_when_absent():
    provider = FakeLLMProvider(script=["none|-|-|0.95"])
    result = discover_instructions(_doc_with_footnote(), _coverage_with_one_found_field(), provider)
    assert result.for_field("payment_amount") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_discovery_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.instructions.discovery_agent'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/models/instructions.py
from __future__ import annotations

from pydantic import BaseModel


class Instruction(BaseModel):
    field_name: str
    instruction_text: str
    transformation: str
    confidence: float


class InstructionSet(BaseModel):
    instructions: list[Instruction]

    def for_field(self, field_name: str) -> Instruction | None:
        for instruction in self.instructions:
            if instruction.field_name == field_name:
                return instruction
        return None
```

```python
# src/cw_platform/instructions/__init__.py
```

```python
# src/cw_platform/instructions/discovery_agent.py
from __future__ import annotations

from cw_platform.llm.provider import LLMProvider
from cw_platform.models.document import ExtractedDocument
from cw_platform.models.instructions import Instruction, InstructionSet
from cw_platform.models.mapping import CoverageReport

_PROMPT = """Search this ENTIRE document, including footnotes, headers, and legends anywhere
in the text, for any instruction that changes how the field "{field_name}" should be
interpreted (unit scale, currency, sign convention, date format, or a conditional
definition). Respond in exactly this format with no other text:
<none|found>|<instruction text or ->|<transformation or ->|<confidence>

Full document text:
{text}
"""


def discover_instructions(
    doc: ExtractedDocument, coverage: CoverageReport, provider: LLMProvider
) -> InstructionSet:
    instructions: list[Instruction] = []
    full_text = doc.full_text()

    for mapping in coverage.mappings:
        if mapping.status != "found":
            continue

        prompt = _PROMPT.format(field_name=mapping.field_name, text=full_text)
        response = provider.complete(prompt)
        status, instruction_text, transformation, confidence_str = response.text.strip().split("|", maxsplit=3)

        if status != "found":
            continue

        instructions.append(
            Instruction(
                field_name=mapping.field_name,
                instruction_text=instruction_text,
                transformation=transformation,
                confidence=float(confidence_str),
            )
        )

    return InstructionSet(instructions=instructions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_discovery_agent.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/models/instructions.py src/cw_platform/instructions/ tests/unit/test_discovery_agent.py
git commit -m "feat: add document-wide instruction discovery agent"
```

---

### Task 11: Value Transforms

**Files:**
- Create: `src/cw_platform/extraction_agent/__init__.py`
- Create: `src/cw_platform/extraction_agent/transforms.py`
- Test: `tests/unit/test_transforms.py`

**Interfaces:**
- Produces: `UnknownTransformError(Exception)`; `apply_transform(raw_text: str, transformation: str | None) -> str` — supports `None`/`"none"` (returns `raw_text` unchanged), `"multiply_by_1000"` (strips commas/currency symbols, parses as float, multiplies by 1000, formats with 2 decimal places), `"strip_commas"` (removes `,` characters only), `"parse_date_mmddyyyy"` (parses `MM/DD/YYYY` and returns ISO `YYYY-MM-DD`); raises `UnknownTransformError` for any other transformation string.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_transforms.py
import pytest
from cw_platform.extraction_agent.transforms import UnknownTransformError, apply_transform


def test_no_transform_returns_unchanged():
    assert apply_transform("1,200.00", None) == "1,200.00"
    assert apply_transform("1,200.00", "none") == "1,200.00"


def test_multiply_by_1000():
    assert apply_transform("45,000", "multiply_by_1000") == "45000000.00"


def test_strip_commas():
    assert apply_transform("1,200,000", "strip_commas") == "1200000"


def test_parse_date_mmddyyyy():
    assert apply_transform("02/15/2026", "parse_date_mmddyyyy") == "2026-02-15"


def test_unknown_transform_raises():
    with pytest.raises(UnknownTransformError, match="not_a_real_transform"):
        apply_transform("1,200.00", "not_a_real_transform")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_transforms.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.extraction_agent.transforms'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/extraction_agent/__init__.py
```

```python
# src/cw_platform/extraction_agent/transforms.py
from __future__ import annotations

from datetime import datetime


class UnknownTransformError(Exception):
    pass


def apply_transform(raw_text: str, transformation: str | None) -> str:
    if transformation is None or transformation == "none":
        return raw_text

    if transformation == "strip_commas":
        return raw_text.replace(",", "")

    if transformation == "multiply_by_1000":
        cleaned = raw_text.replace(",", "").replace("$", "")
        value = float(cleaned) * 1000
        return f"{value:.2f}"

    if transformation == "parse_date_mmddyyyy":
        parsed = datetime.strptime(raw_text, "%m/%d/%Y")
        return parsed.strftime("%Y-%m-%d")

    raise UnknownTransformError(f"Unknown transformation: {transformation}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_transforms.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/extraction_agent/ tests/unit/test_transforms.py
git commit -m "feat: add value transformation functions (unit scale, date, comma-strip)"
```

---

### Task 12: Extraction / Parsing Agent

**Files:**
- Create: `src/cw_platform/models/output.py`
- Create: `src/cw_platform/extraction_agent/extractor.py`
- Test: `tests/unit/test_extractor.py`

**Interfaces:**
- Consumes: `CoverageReport`/`FieldMapping` (Task 9), `InstructionSet` (Task 10), `apply_transform` (Task 11), `LLMProvider` (Task 1), `ProvenanceRecord`/`SourceRef` (Task 3).
- Produces: `OutputField(name: str, value: str, data_type: str, confidence: float, transformation_applied: str | None, provenance: ProvenanceRecord)`; `extract_fields(coverage: CoverageReport, instructions: InstructionSet, provider: LLMProvider) -> list[OutputField]` — for each mapping with `status == "found"`, issues one `provider.complete(...)` call asking the LLM to read the exact value out of `mapping.text_span` and return `"<value>|<confidence>"`, applies `apply_transform(value, instruction.transformation)` if `instructions.for_field(...)` returns an instruction, and builds an `OutputField` with a `ProvenanceRecord` pointing at `mapping.page`/`mapping.text_span` and `agent="extraction_agent"`. Fields with `status != "found"` are skipped (they surface as `"missing_required_field"` review items via the review queue built in Task 14, not by this agent).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_extractor.py
from cw_platform.extraction_agent.extractor import extract_fields
from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.models.instructions import Instruction, InstructionSet
from cw_platform.models.mapping import CoverageReport, FieldMapping


def test_extract_fields_applies_transform_when_instruction_present():
    coverage = CoverageReport(
        document_type="agent_bank_notice_interest_payment",
        mappings=[FieldMapping(field_name="payment_amount", status="found", page=1, text_span="45,000", notes="ok")],
    )
    instructions = InstructionSet(
        instructions=[
            Instruction(
                field_name="payment_amount",
                instruction_text="reported in thousands",
                transformation="multiply_by_1000",
                confidence=0.9,
            )
        ]
    )
    provider = FakeLLMProvider(script=["45000|0.97"])

    fields = extract_fields(coverage, instructions, provider)

    assert len(fields) == 1
    field = fields[0]
    assert field.name == "payment_amount"
    assert field.value == "45000000.00"
    assert field.transformation_applied == "multiply_by_1000"
    assert field.confidence == 0.97
    assert field.provenance.source.page == 1
    assert field.provenance.source.text_span == "45,000"


def test_extract_fields_no_transform_when_no_instruction():
    coverage = CoverageReport(
        document_type="bank_statement",
        mappings=[FieldMapping(field_name="ending_balance", status="found", page=1, text_span="1,200.00", notes="ok")],
    )
    instructions = InstructionSet(instructions=[])
    provider = FakeLLMProvider(script=["1200.00|0.95"])

    fields = extract_fields(coverage, instructions, provider)

    assert fields[0].value == "1200.00"
    assert fields[0].transformation_applied is None


def test_extract_fields_skips_not_found_mappings():
    coverage = CoverageReport(
        document_type="bank_statement",
        mappings=[FieldMapping(field_name="routing_number", status="not_found", page=None, text_span=None, notes="missing")],
    )
    fields = extract_fields(coverage, InstructionSet(instructions=[]), FakeLLMProvider(script=[]))
    assert fields == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.extraction_agent.extractor'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/models/output.py
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
```

```python
# src/cw_platform/extraction_agent/extractor.py
from __future__ import annotations

from cw_platform.extraction_agent.transforms import apply_transform
from cw_platform.llm.provider import LLMProvider
from cw_platform.models.instructions import InstructionSet
from cw_platform.models.mapping import CoverageReport
from cw_platform.models.output import OutputField
from cw_platform.models.provenance import ProvenanceRecord, SourceRef

_PROMPT = """Read the exact value for this field from the text span below and return it
verbatim, unmodified. Respond in exactly this format with no other text:
<value>|<confidence>

Field: {field_name}
Text span: {text_span}
"""


def extract_fields(coverage: CoverageReport, instructions: InstructionSet, provider: LLMProvider) -> list[OutputField]:
    fields: list[OutputField] = []

    for mapping in coverage.mappings:
        if mapping.status != "found":
            continue

        prompt = _PROMPT.format(field_name=mapping.field_name, text_span=mapping.text_span)
        response = provider.complete(prompt)
        raw_value, confidence_str = response.text.strip().split("|", maxsplit=1)

        instruction = instructions.for_field(mapping.field_name)
        transformation = instruction.transformation if instruction else None
        value = apply_transform(raw_value, transformation)

        provenance = ProvenanceRecord(
            field_name=mapping.field_name,
            source=SourceRef(page=mapping.page, bbox=None, text_span=mapping.text_span or ""),
            transformation_applied=transformation,
            agent="extraction_agent",
            confidence=float(confidence_str),
        )
        fields.append(
            OutputField(
                name=mapping.field_name,
                value=value,
                data_type="string",
                confidence=float(confidence_str),
                transformation_applied=transformation,
                provenance=provenance,
            )
        )

    return fields
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_extractor.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/models/output.py src/cw_platform/extraction_agent/extractor.py tests/unit/test_extractor.py
git commit -m "feat: add extraction agent that transforms values and attaches provenance"
```

---

### Task 13: Confidence Thresholds

**Files:**
- Create: `src/cw_platform/review/__init__.py`
- Create: `src/cw_platform/review/thresholds.py`
- Test: `tests/unit/test_thresholds.py`

**Interfaces:**
- Produces: `ThresholdConfig` — a dict-backed config with structure `{document_type: {"default": float, "fields": {field_name: float}}}`; `DEFAULT_THRESHOLDS: ThresholdConfig` seeding `0.85` default for both MVP document types with `payment_amount` and `ending_balance` set to `0.92` (higher-criticality fields, per spec I1's example); `get_threshold(config: ThresholdConfig, document_type: str, field_name: str) -> float` — returns the field-specific threshold if present, else the document type's `"default"`, else a hardcoded global fallback of `0.85`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_thresholds.py
from cw_platform.review.thresholds import DEFAULT_THRESHOLDS, get_threshold


def test_field_specific_threshold_used_when_present():
    assert get_threshold(DEFAULT_THRESHOLDS, "agent_bank_notice_interest_payment", "payment_amount") == 0.92


def test_document_type_default_used_when_field_not_configured():
    assert get_threshold(DEFAULT_THRESHOLDS, "bank_statement", "account_number") == 0.85


def test_global_fallback_used_for_unknown_document_type():
    assert get_threshold(DEFAULT_THRESHOLDS, "unknown_type", "some_field") == 0.85
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_thresholds.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.review.thresholds'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/review/__init__.py
```

```python
# src/cw_platform/review/thresholds.py
from __future__ import annotations

ThresholdConfig = dict[str, dict[str, object]]

GLOBAL_FALLBACK_THRESHOLD = 0.85

DEFAULT_THRESHOLDS: ThresholdConfig = {
    "bank_statement": {
        "default": 0.85,
        "fields": {"ending_balance": 0.92},
    },
    "agent_bank_notice_interest_payment": {
        "default": 0.85,
        "fields": {"payment_amount": 0.92},
    },
}


def get_threshold(config: ThresholdConfig, document_type: str, field_name: str) -> float:
    type_config = config.get(document_type)
    if type_config is None:
        return GLOBAL_FALLBACK_THRESHOLD

    field_thresholds: dict[str, float] = type_config.get("fields", {})  # type: ignore[assignment]
    if field_name in field_thresholds:
        return field_thresholds[field_name]

    return type_config.get("default", GLOBAL_FALLBACK_THRESHOLD)  # type: ignore[return-value]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_thresholds.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/review/thresholds.py tests/unit/test_thresholds.py
git commit -m "feat: add per-document-type, per-field confidence threshold config"
```

---

### Task 14: Review Queue Routing

**Files:**
- Create: `src/cw_platform/models/review.py`
- Create: `src/cw_platform/review/queue.py`
- Test: `tests/unit/test_review_queue.py`

**Interfaces:**
- Consumes: `OutputField` (Task 12), `ThresholdConfig`/`get_threshold` (Task 13).
- Produces: `ReviewItem(field_name: str, reason: Literal["low_confidence","missing_required_field"], detail: str)`; `build_review_queue(document_type: str, fields: list[OutputField], dictionary_required_fields: list[str], thresholds: ThresholdConfig) -> list[ReviewItem]` — emits a `"low_confidence"` item for every `OutputField` whose `confidence` is below `get_threshold(thresholds, document_type, field.name)`, and a `"missing_required_field"` item for every name in `dictionary_required_fields` that has no `OutputField` in `fields` at all (i.e., it was never found by mapping — a `CoverageReport` is not needed here since absence from `fields` already reflects mapping status).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_review_queue.py
from cw_platform.models.output import OutputField
from cw_platform.models.provenance import ProvenanceRecord, SourceRef
from cw_platform.review.queue import build_review_queue
from cw_platform.review.thresholds import DEFAULT_THRESHOLDS


def _field(name: str, confidence: float) -> OutputField:
    return OutputField(
        name=name,
        value="x",
        data_type="string",
        confidence=confidence,
        transformation_applied=None,
        provenance=ProvenanceRecord(
            field_name=name,
            source=SourceRef(page=1, bbox=None, text_span="x"),
            transformation_applied=None,
            agent="extraction_agent",
            confidence=confidence,
        ),
    )


def test_low_confidence_field_flagged():
    fields = [_field("ending_balance", 0.5)]
    items = build_review_queue("bank_statement", fields, ["ending_balance"], DEFAULT_THRESHOLDS)
    assert len(items) == 1
    assert items[0].reason == "low_confidence"
    assert items[0].field_name == "ending_balance"


def test_missing_required_field_flagged():
    items = build_review_queue("bank_statement", [], ["account_number"], DEFAULT_THRESHOLDS)
    assert len(items) == 1
    assert items[0].reason == "missing_required_field"
    assert items[0].field_name == "account_number"


def test_high_confidence_found_field_not_flagged():
    fields = [_field("ending_balance", 0.99)]
    items = build_review_queue("bank_statement", fields, ["ending_balance"], DEFAULT_THRESHOLDS)
    assert items == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_review_queue.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.review.queue'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/models/review.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReviewItem(BaseModel):
    field_name: str
    reason: Literal["low_confidence", "missing_required_field"]
    detail: str
```

```python
# src/cw_platform/review/queue.py
from __future__ import annotations

from cw_platform.models.output import OutputField
from cw_platform.models.review import ReviewItem
from cw_platform.review.thresholds import ThresholdConfig, get_threshold


def build_review_queue(
    document_type: str,
    fields: list[OutputField],
    dictionary_required_fields: list[str],
    thresholds: ThresholdConfig,
) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    fields_by_name = {f.name: f for f in fields}

    for field in fields:
        threshold = get_threshold(thresholds, document_type, field.name)
        if field.confidence < threshold:
            items.append(
                ReviewItem(
                    field_name=field.name,
                    reason="low_confidence",
                    detail=f"confidence {field.confidence:.2f} below threshold {threshold:.2f}",
                )
            )

    for required_name in dictionary_required_fields:
        if required_name not in fields_by_name:
            items.append(
                ReviewItem(
                    field_name=required_name,
                    reason="missing_required_field",
                    detail="required field was not found during mapping or extraction",
                )
            )

    return items
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_review_queue.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/models/review.py src/cw_platform/review/queue.py tests/unit/test_review_queue.py
git commit -m "feat: add review queue routing for low-confidence and missing fields"
```

---

### Task 15: Canonical Output Schema + Validation

**Files:**
- Modify: `src/cw_platform/models/output.py`
- Test: `tests/unit/test_output_schema.py`

**Interfaces:**
- Consumes: `OutputField` (Task 12), `ReviewItem` (Task 14), `ClassificationResult` (Task 8).
- Produces (appended to `cw_platform.models.output`): `DocumentOutput(document_id: str, source_filename: str, document_type: str, template: str, classification_confidence: float, fields: list[OutputField], review_items: list[ReviewItem], status: Literal["complete","needs_review"])` with a `pydantic` `model_validator` enforcing that `status == "needs_review"` whenever `review_items` is non-empty, and `status == "complete"` only when `review_items` is empty (raises `pydantic.ValidationError` if the two are inconsistent).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_output_schema.py
import pytest
from pydantic import ValidationError

from cw_platform.models.output import DocumentOutput
from cw_platform.models.review import ReviewItem


def test_status_complete_requires_no_review_items():
    output = DocumentOutput(
        document_id="doc-1",
        source_filename="stmt.pdf",
        document_type="bank_statement",
        template="base",
        classification_confidence=0.95,
        fields=[],
        review_items=[],
        status="complete",
    )
    assert output.status == "complete"


def test_status_complete_with_review_items_raises():
    with pytest.raises(ValidationError):
        DocumentOutput(
            document_id="doc-1",
            source_filename="stmt.pdf",
            document_type="bank_statement",
            template="base",
            classification_confidence=0.95,
            fields=[],
            review_items=[ReviewItem(field_name="x", reason="low_confidence", detail="d")],
            status="complete",
        )


def test_status_needs_review_requires_review_items():
    with pytest.raises(ValidationError):
        DocumentOutput(
            document_id="doc-1",
            source_filename="stmt.pdf",
            document_type="bank_statement",
            template="base",
            classification_confidence=0.95,
            fields=[],
            review_items=[],
            status="needs_review",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_output_schema.py -v`
Expected: FAIL with `ImportError: cannot import name 'DocumentOutput' from 'cw_platform.models.output'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/models/output.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_output_schema.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/models/output.py tests/unit/test_output_schema.py
git commit -m "feat: add canonical DocumentOutput schema with status/review-item consistency check"
```

---

### Task 16: Sequential Pipeline Orchestrator

**Files:**
- Create: `src/cw_platform/orchestration/__init__.py`
- Create: `src/cw_platform/orchestration/pipeline.py`
- Test: `tests/integration/test_pipeline_end_to_end.py`

**Interfaces:**
- Consumes every module built in Tasks 1–15: `intake` (7), `extract_layout` (6), `classify` (8), `load_data_dictionary` (4), `map_fields` (9), `discover_instructions` (10), `extract_fields` (12), `build_review_queue` (14), `DEFAULT_THRESHOLDS` (13), `DocumentOutput` (15).
- Produces: `process_document(filename: str, content: bytes, document_id: str, provider: LLMProvider) -> DocumentOutput` — runs the full linear pipeline: `intake` → `extract_layout` → `classify` → `load_data_dictionary(classification.document_type, classification.template)` → `map_fields` → `discover_instructions` → `extract_fields` → `build_review_queue` → assembles `DocumentOutput` with `status` set from whether `review_items` is empty. This is the only place all stages are wired together; every stage function is called exactly once with the outputs of the previous stage, matching the linear pipeline in the Global Constraints.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_pipeline_end_to_end.py
from pathlib import Path

from cw_platform.llm.provider import FakeLLMProvider
from cw_platform.orchestration.pipeline import process_document

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_pipeline_produces_complete_output_for_bank_statement():
    content = (FIXTURES / "bank_statement_sample.pdf").read_bytes()

    # Script order: classify, then one map_fields call per dictionary field
    # (account_number, statement_period_end, ending_balance), then one
    # discover_instructions call per found field, then one extract_fields
    # call per found field. All three fields are made to resolve as found
    # with high confidence so the pipeline reaches status="complete".
    provider = FakeLLMProvider(
        script=[
            "bank_statement|base|0.97",
            "found|1|1234567890|account number located",
            "found|1|01/31/2026|period end located",
            "found|1|1,200.00|balance located",
            "none|-|-|0.9",
            "none|-|-|0.9",
            "none|-|-|0.9",
            "1234567890|0.96",
            "2026-01-31|0.96",
            "1200.00|0.96",
        ]
    )

    output = process_document("bank_statement_sample.pdf", content, "doc-1", provider)

    assert output.document_type == "bank_statement"
    assert output.status == "complete"
    assert {f.name for f in output.fields} == {"account_number", "statement_period_end", "ending_balance"}
    assert output.review_items == []


def test_pipeline_routes_low_confidence_field_to_review():
    content = (FIXTURES / "bank_statement_sample.pdf").read_bytes()
    provider = FakeLLMProvider(
        script=[
            "bank_statement|base|0.97",
            "found|1|1234567890|ok",
            "found|1|01/31/2026|ok",
            "found|1|1,200.00|ok",
            "none|-|-|0.9",
            "none|-|-|0.9",
            "none|-|-|0.9",
            "1234567890|0.96",
            "2026-01-31|0.96",
            "1200.00|0.40",
        ]
    )

    output = process_document("bank_statement_sample.pdf", content, "doc-2", provider)

    assert output.status == "needs_review"
    assert any(item.field_name == "ending_balance" for item in output.review_items)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_pipeline_end_to_end.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.orchestration.pipeline'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/orchestration/__init__.py
```

```python
# src/cw_platform/orchestration/pipeline.py
from __future__ import annotations

import tempfile
from pathlib import Path

from cw_platform.classification.classifier import classify
from cw_platform.extraction.layout_extractor import extract_layout
from cw_platform.extraction_agent.extractor import extract_fields
from cw_platform.ingestion.intake import intake
from cw_platform.instructions.discovery_agent import discover_instructions
from cw_platform.knowledge_base.loader import load_data_dictionary
from cw_platform.llm.provider import LLMProvider
from cw_platform.mapping.mapping_agent import map_fields
from cw_platform.models.output import DocumentOutput
from cw_platform.review.queue import build_review_queue
from cw_platform.review.thresholds import DEFAULT_THRESHOLDS


def process_document(filename: str, content: bytes, document_id: str, provider: LLMProvider) -> DocumentOutput:
    raw_document = intake(filename, content)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(raw_document.content)
        tmp_path = Path(tmp.name)

    try:
        extracted = extract_layout(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    classification = classify(extracted, provider)
    dictionary = load_data_dictionary(classification.document_type, classification.template)
    coverage = map_fields(extracted, dictionary, provider)
    instructions = discover_instructions(extracted, coverage, provider)
    fields = extract_fields(coverage, instructions, provider)

    required_fields = [f.name for f in dictionary.fields if f.required]
    review_items = build_review_queue(
        classification.document_type, fields, required_fields, DEFAULT_THRESHOLDS
    )

    return DocumentOutput(
        document_id=document_id,
        source_filename=filename,
        document_type=classification.document_type,
        template=classification.template,
        classification_confidence=classification.confidence,
        fields=fields,
        review_items=review_items,
        status="needs_review" if review_items else "complete",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_pipeline_end_to_end.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/orchestration/ tests/integration/test_pipeline_end_to_end.py
git commit -m "feat: wire pipeline stages into sequential orchestrator"
```

---

### Task 17: Minimal Submission/Result API

**Files:**
- Create: `src/cw_platform/api/__init__.py`
- Create: `src/cw_platform/api/app.py`
- Test: `tests/integration/test_api.py`

**Interfaces:**
- Consumes: `process_document` (Task 16), `FakeLLMProvider`/`LLMProvider` (Task 1).
- Produces: FastAPI app `app` with `POST /documents` (multipart file upload, form field `document_id`; runs `process_document` synchronously and stores the resulting `DocumentOutput` in an in-memory `dict[str, DocumentOutput]`; returns `{"document_id": ..., "status": ...}`) and `GET /documents/{document_id}` (returns the stored `DocumentOutput` as JSON, or a `404` with `{"detail": "document not found"}` if the id is unknown). The app takes its `LLMProvider` via FastAPI dependency override so tests inject `FakeLLMProvider` instead of a real vendor client — production wiring of a concrete provider is deferred (Global Constraints: LLM vendor is a Phase 1.5 decision).

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_api.py
from pathlib import Path

from fastapi.testclient import TestClient

from cw_platform.api.app import app, get_llm_provider
from cw_platform.llm.provider import FakeLLMProvider

FIXTURES = Path(__file__).parent.parent / "fixtures"

_SCRIPT = [
    "bank_statement|base|0.97",
    "found|1|1234567890|ok",
    "found|1|01/31/2026|ok",
    "found|1|1,200.00|ok",
    "none|-|-|0.9",
    "none|-|-|0.9",
    "none|-|-|0.9",
    "1234567890|0.96",
    "2026-01-31|0.96",
    "1200.00|0.96",
]


def _client() -> TestClient:
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider(script=list(_SCRIPT))
    return TestClient(app)


def test_submit_and_fetch_document():
    client = _client()
    content = (FIXTURES / "bank_statement_sample.pdf").read_bytes()

    submit_response = client.post(
        "/documents",
        data={"document_id": "doc-abc"},
        files={"file": ("bank_statement_sample.pdf", content, "application/pdf")},
    )
    assert submit_response.status_code == 200
    assert submit_response.json() == {"document_id": "doc-abc", "status": "complete"}

    fetch_response = client.get("/documents/doc-abc")
    assert fetch_response.status_code == 200
    assert fetch_response.json()["document_type"] == "bank_statement"


def test_fetch_unknown_document_returns_404():
    client = _client()
    response = client.get("/documents/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "document not found"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_platform.api.app'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cw_platform/api/__init__.py
```

```python
# src/cw_platform/api/app.py
from __future__ import annotations

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile

from cw_platform.llm.provider import LLMProvider
from cw_platform.models.output import DocumentOutput
from cw_platform.orchestration.pipeline import process_document

app = FastAPI(title="Financial Document Platform — Phase 1 MVP")

_STORE: dict[str, DocumentOutput] = {}


def get_llm_provider() -> LLMProvider:
    raise NotImplementedError(
        "No LLMProvider configured for this deployment. Override get_llm_provider "
        "with a concrete provider before serving production traffic."
    )


@app.post("/documents")
async def submit_document(
    document_id: str = Form(...),
    file: UploadFile = File(...),
    provider: LLMProvider = Depends(get_llm_provider),
):
    content = await file.read()
    output = process_document(file.filename, content, document_id, provider)
    _STORE[document_id] = output
    return {"document_id": document_id, "status": output.status}


@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    output = _STORE.get(document_id)
    if output is None:
        raise HTTPException(status_code=404, detail="document not found")
    return output.model_dump()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cw_platform/api/ tests/integration/test_api.py
git commit -m "feat: add minimal document submission/result API"
```

---

### Task 18: Project Scaffolding, Full Suite, and README

**Files:**
- Create: `pyproject.toml`
- Create: `tests/conftest.py`
- Create: `README.md`

**Interfaces:**
- Produces: an installable `src`-layout package (`pip install -e .`) with pinned dependencies (`pydantic`, `pdfplumber`, `pyyaml`, `fastapi`, `httpx`, `python-multipart`) and dev dependencies (`pytest`, `reportlab`); `tests/conftest.py` adds `src/` to `sys.path` for local test runs without install (belt-and-suspenders alongside the `pyproject.toml` src-layout config referenced in Task 1).

This task should be done *first* in execution order in practice (subagent-driven-development will naturally want a runnable project before Task 1's test can execute) — it is placed last in the plan document only because it has no interesting TDD cycle of its own. Note this explicitly to whoever executes the plan.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
# pyproject.toml
[project]
name = "cw-data-platform"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "pdfplumber>=0.11",
    "pyyaml>=6.0",
    "fastapi>=0.110",
    "httpx>=0.27",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "reportlab>=4.1"]

[tool.setuptools.packages.find]
where = ["src"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Write `tests/conftest.py`**

```python
# tests/conftest.py
import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

- [ ] **Step 3: Install the project in editable mode with dev dependencies**

Run: `pip install -e ".[dev]"`
Expected: install succeeds with no errors.

- [ ] **Step 4: Run the full test suite**

Run: `pytest -v`
Expected: all tests from Tasks 1–17 PASS (50 tests total; Task 5 has no pytest tests of its own, only the fixture-generation script).

- [ ] **Step 5: Write `README.md`**

```markdown
# CW Data Platform — Phase 1 MVP

Agentic financial document extraction pipeline. Phase 1 MVP scope: two
document types (Bank Statement, Agent Bank Notice — Interest Payment
Schedule), digital-PDF input only, linear pipeline with no persisted
template memory. See `docs/spec/Agentic_Financial_Document_Platform_Features.md`
for the full feature catalog and `docs/superpowers/plans/2026-08-19-phase1-mvp-pipeline.md`
for this plan's task breakdown.

## Setup

    pip install -e ".[dev]"
    python tests/fixtures/make_fixtures.py

## Run tests

    pytest -v

## Run the API locally

    uvicorn cw_platform.api.app:app --reload

`get_llm_provider` in `src/cw_platform/api/app.py` must be overridden with a
concrete `LLMProvider` before serving real traffic — no vendor is wired in
by default (see plan Global Constraints).
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tests/conftest.py README.md
git commit -m "chore: add project scaffolding, pytest path config, and README"
```

---

## Explicitly Out of Scope for This Plan (Phase 2 / Phase 3 per spec)

- Structured-source short-circuit (A1), pre-parsed/cached document detection (A2), document set/package handling (B3)
- Extraction quality assessment (B2), multi-format ingestion beyond PDF, OCR fallback
- Unknown-template bootstrapping workflow (C2), similarity-based template retrieval (D4)
- Persistent extraction rules / template memory (D2), Knowledge Base governance & versioning (D3)
- Retrieval-assisted localization (E2), coverage reporting beyond the in-memory `CoverageReport` (E3's routing integration)
- Rule persistence to template memory (F3), template-memory fast path (G2)
- Independent verifier agent, cross-field reconciliation, stratified confidence sampling (Module H)
- Review queue prioritization/SLA/reviewer routing UI (I2 beyond the data model), reviewer correction feedback loop into the Knowledge Base (I3)
- Full processing history / append-only audit log (J2)
- Non-linear orchestration with loop-backs, batch/streaming processing (K1/K2)
- Template drift detection, operational dashboards (Module L)
- Security/compliance hardening, vendor data-handling policy enforcement (Module M) — concrete LLM provider selection and any redaction pipeline must be resolved before production use
- Golden dataset evaluation framework, confidence calibration monitoring (Module N)
- Reprocessing/versioning, downstream delivery beyond the two MVP API endpoints (O2/O3)
- Reasoning-cost tiering, cost/latency monitoring (Module P)

These map directly to the spec's Phase 2 ("Feedback Loop & Efficiency") and Phase 3 ("Scale & Governance") rows and should become their own plans once this one is merged and validated end-to-end.
