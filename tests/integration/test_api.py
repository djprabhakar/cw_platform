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
