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
