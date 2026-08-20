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
