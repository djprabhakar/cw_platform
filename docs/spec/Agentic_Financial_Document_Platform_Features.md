Agentic Financial Document
Intelligence Platform
Features Document
Prepared for: dj
Date: August 19, 2026
Status: Draft v1 — for review

## Table of Contents

## 1. Purpose & Scope
This document defines the feature set for an agentic platform that ingests a variety of financial documents — bank statements, agent bank notices (e.g., interest payment schedules), 10-K/10-Q filings, and similar — and produces structured, column-level data conforming to a per-document-type data dictionary. It builds on an initial pipeline concept (text extraction, document classification, data dictionary mapping, instruction discovery, and extraction) and extends it with the additional capabilities needed to make the platform accurate, auditable, cost-efficient, and maintainable in production.
The document is organized as a catalog of features grouped into functional modules, each written in the same format: what the feature is, why it matters, its key requirements, and what it depends on. It closes with non-functional requirements, a phased rollout, and a list of open questions that need an owner's decision before detailed design can begin.

## 2. Guiding Principles
- Prefer structured or pre-parsed data over raw document parsing whenever an authoritative structured source exists (e.g., XBRL for SEC filings); reserve agentic extraction for the fields and document types that genuinely require it.
- Every extraction rule the system learns (unit conversions, footnote interpretations, column locations) is captured once and reused, so the platform gets faster, cheaper, and more accurate over time rather than re-deriving the same reasoning on every document.
- No value reaches downstream systems without a traceable path back to its exact source location and the transformation applied to it.
- Confidence is verified, not just self-reported: an independent check and cross-field reconciliation catch error classes that per-field confidence scoring alone will miss.
- Human review is a feedback mechanism, not a dumping ground: every correction should make the knowledge base smarter, not just fix one document.
- Reasoning cost is tiered to the cheapest sufficient path for each document, escalating to full chain-of-thought only when a cheaper path is unavailable or insufficient.

## 3. Pipeline Overview
The table below summarizes the end-to-end processing flow. It is presented as a sequence for clarity, but the actual orchestration supports conditional loop-backs between stages — see Module K, Orchestration & Workflow Engine.

## 4. Feature Catalog

### A. Source Prioritization & Ingestion

#### A1. Structured-Source Short-Circuit
Description: Before any raw document parsing occurs, the platform checks whether a structured or pre-parsed equivalent of the document's data already exists — for example, SEC EDGAR XBRL tags for 10-K/10-Q filings, a custodian's structured data feed, or a previously machine-readable version of the same document — and uses that as the primary data source. Agentic parsing is invoked only for the fields not covered by the structured source.
Why It Matters: Avoids re-deriving data that is already authoritative and structured, cutting cost, latency, and error risk for the subset of document types where structured data exists. Public filings are the clearest case, but the same pattern applies to any issuer that already publishes structured feeds.
Key Requirements:
- Registry of known structured-data providers per document type and issuer (e.g., EDGAR full-text search plus the XBRL API for SEC filings)
- Field-level mapping between the platform's data dictionary and each structured source's own schema
- Reconciliation logic for partial coverage, where some fields come from the structured source and others still require extraction from the raw document
- Hybrid processing mode that runs the full agentic pipeline only on the residual, uncovered fields
Dependencies: Data Dictionary / Knowledge Base (for field mapping), Document Classification (to determine which registry applies)

#### A2. Pre-Parsed / Cached Document Detection
Description: Detect whether a document, or a near-duplicate/prior-period version of it, has already been processed by the platform, and reuse or diff against the prior extraction rather than reprocessing from scratch.
Why It Matters: Many financial documents — monthly statements, recurring notices — are highly similar to prior periods. Full reprocessing wastes compute and reasoning cycles on data that hasn't materially changed.
Key Requirements:
- Document fingerprinting/hashing and similarity detection keyed on issuer, template, and period
- Diff-based extraction that identifies and processes only changed values where feasible
- Storage of prior extraction results keyed by template, issuer, and period
Dependencies: Document Classification, Knowledge Base

#### A3. Multi-Format Ingestion
Description: Accept and normalize a range of input formats: digital and scanned PDF, TIFF/image, DOCX, XLSX, HTML/XBRL, email attachments, and multi-file ZIP bundles.
Why It Matters: Financial documents arrive from many channels and vendors in inconsistent formats; the pipeline needs a single normalized entry point regardless of source format.
Key Requirements:
- Format detection and normalization to a canonical intermediate representation
- Handling of multi-file packages as a single logical processing unit
- Ingestion channel support: SFTP, email, portal upload, and API submission
Dependencies: None upstream

### B. Document Pre-Processing & Extraction

#### B1. Layout-Aware Text & Table Extraction
Description: Extract text while preserving structural and spatial relationships — table rows and columns, headers, multi-column layouts — rather than flattening the document to plain text. Output is an intermediate structured representation (e.g., structured JSON or markdown tables with bounding boxes) that downstream agents can reason over directly.
Why It Matters: Loss of table structure during extraction is the single largest cause of misattributed values in financial documents; downstream agents cannot correctly map a value to its column and row if that structure was discarded upstream.
Key Requirements:
- OCR fallback for scanned or image-based pages
- Table structure detection distinct from plain paragraph text
- Position/bounding-box metadata retained per extracted token or cell
- Optional multimodal (vision-based) extraction path for complex or non-standard layouts
Dependencies: None

#### B2. Extraction Quality Assessment
Description: Score the quality and legibility of the extraction on a per-page basis — OCR confidence, garbled text detection, missing or blank pages — and flag documents that need special handling before they enter the rest of the pipeline.
Why It Matters: Prevents a poor-quality extraction from silently propagating errors through every downstream agent, where they become far more expensive to trace back and fix.
Key Requirements:
- OCR confidence scoring per page
- Page completeness and sequence checks
- Language detection
- Handling for corrupted or password-protected files, including a defined escalation path
Dependencies: None

#### B3. Document Set / Package Handling
Description: Support values that must be derived from multiple related documents or pages — an exhibit referenced by a notice, a schedule spanning multiple pages, or a table that continues across a page break.
Why It Matters: Many financial notices and filings reference or depend on companion documents; treating each file as an isolated unit will miss or misattribute this class of data.
Key Requirements:
- Cross-document linking within a submitted package
- Table-continuation stitching across page breaks
- Package-level, not just document-level, processing as the unit of work where applicable
Dependencies: Document Classification

### C. Document Classification

#### C1. Hierarchical, Multi-Label Classifier
Description: Classify documents at two levels: document type (e.g., Bank Statement, Agent Bank Notice — Interest Payment Schedule, 10-K Filing) and template/issuer variant (e.g., "Agent Bank Notice — Issuer X, Format v2"). Support documents that legitimately match more than one label.
Why It Matters: A flat, single-level classification cannot distinguish materially different layouts that share the same nominal document type, which is exactly the case the knowledge base needs to resolve correctly to load the right rules.
Key Requirements:
- Confidence score attached to every prediction, at both the type and template/variant level
- Multi-label support for documents that combine characteristics of more than one type
- A versioned template taxonomy maintained in the Knowledge Base
Dependencies: Knowledge Base (template taxonomy)

#### C2. Unknown-Template Detection & Bootstrapping Workflow
Description: When classification confidence is low across all known templates, route the document to a dedicated "new template" workflow instead of forcing it into the nearest match. A human confirms the document is genuinely new, and the system drafts an initial data dictionary/template entry, LLM-assisted, for review before it becomes part of the production knowledge base.
Why It Matters: Silently forcing a new or unrecognized format into the nearest existing template produces confident, systematically wrong extractions rather than a visible failure.
Key Requirements:
- Tunable confidence threshold below which a document is treated as unrecognized
- Human approval gate before a new template enters production
- LLM-assisted draft data dictionary generation as a starting point for the human reviewer
Dependencies: Knowledge Base governance workflow

#### C3. Classification Confidence Routing
Description: Route low-confidence classifications to human review before any downstream knowledge base loading or extraction occurs.
Why It Matters: An error at the classification step corrupts every subsequent step, since the wrong data dictionary and rule set get loaded.
Key Requirements:
- Configurable confidence threshold
- Integration with the human review queue
Dependencies: Confidence Scoring & Human-in-the-Loop Review module

### D. Knowledge Base & Data Dictionary Management

#### D1. Layered Data Dictionary Schema
Description: The data dictionary supports inheritance: a base schema of fields common across a document type, with template- or issuer-specific overrides and additions, rather than one flat, fully duplicated dictionary per template.
Why It Matters: Avoids duplicating shared fields across dozens of near-identical templates, and lets an update to a common field propagate automatically instead of requiring edits in every template variant.
Key Requirements:
- Base-plus-override schema model
- Field attributes: name, domain description, data type, example values, required/optional flag
- Inheritance resolution logic that merges base and override definitions at load time
Dependencies: None

#### D2. Persistent Extraction Rules ("Template Memory")
Description: Store, per template/issuer, the extraction and transformation rules discovered during instruction discovery and confirmed by human review — for example, "Payment Amount is reported in thousands" or "footnote 3 defines the reporting currency" — so they are reused directly on future documents of the same template instead of being re-derived through chain-of-thought reasoning every time.
Why It Matters: This is the core mechanism that makes the system get cheaper and more accurate over time rather than repeating full-cost reasoning on every document of a format it has already seen.
Key Requirements:
- Rule storage keyed by template and field
- Versioning of rules with full change history
- Automatic invalidation or re-verification of a rule when template drift is detected
Dependencies: Instruction Discovery Agent, Template Drift Detection

#### D3. Knowledge Base Governance & Versioning
Description: A formal approval workflow for new templates, new fields, and rule changes, with full version history, a change audit trail, and the ability to roll back a bad rule change.
Why It Matters: An agentic system capable of proposing changes to its own extraction rules needs human governance and a rollback safety net; ungoverned self-modification of extraction logic is not acceptable for financial data.
Key Requirements:
- Approval states: draft, pending review, approved
- Change log capturing author, timestamp, and reason for every change
- Rollback capability to a prior rule version
Dependencies: Confidence Scoring & Human-in-the-Loop Review module

#### D4. Similarity-Based Template Retrieval
Description: Use embedding-based similarity search to find the nearest known template for a new or ambiguous document, rather than requiring an exact type match, to assist both classification and the bootstrapping workflow.
Why It Matters: Speeds up handling of format variants that are close to, but not identical to, a known template, and gives the bootstrapping workflow a useful starting point instead of a blank page.
Key Requirements:
- Document and template embedding index
- Tunable similarity threshold
Dependencies: Document Classification

### E. Data Dictionary Mapping Agent

#### E1. Full-Coverage Column Mapping
Description: For each field in the loaded data dictionary, systematically confirm whether and where the corresponding data appears in the document, using a chain-of-thought approach designed to guarantee complete coverage of the document rather than a best-effort scan.
Why It Matters: Silent omission of a field that is actually present in the document is a hard-to-detect failure mode that a best-effort or single-pass scan is prone to.
Key Requirements:
- Explicit per-field presence/absence/ambiguous determination for every dictionary field
- A systematic, documented document-traversal strategy rather than an unstructured search
- Output that includes a location reference for every field found
Dependencies: Layered Data Dictionary, Layout-Aware Extraction

#### E2. Retrieval-Assisted Localization
Description: Before invoking full chain-of-thought reasoning, use a lightweight retrieval step — keyword or embedding search over the extracted document — to localize likely sections for each field, reserving expensive reasoning for confirmation and genuine edge cases.
Why It Matters: Brute-force chain-of-thought scanning of long documents such as 10-K filings, for every field, is costly and slow at production scale; retrieval narrows the search space first.
Key Requirements:
- Section/page indexing of the extracted document
- Retrieval scoring to rank candidate locations per field
- Integration with template memory so known field locations from prior documents of the same template are used directly
Dependencies: Persistent Extraction Rules

#### E3. Coverage Reporting & Gap Flagging
Description: Produce an explicit report of which data dictionary fields were found, not found, or ambiguous, rather than proceeding silently to extraction.
Why It Matters: Gives downstream agents and human reviewers a clear picture of completeness before extraction begins, instead of discovering gaps only after values are produced.
Key Requirements:
- Structured coverage output attached to every processed document
- Automatic routing to review when a required field is missing or ambiguous
Dependencies: Confidence Scoring & Human-in-the-Loop Review module

### F. Instruction Discovery Agent

#### F1. Value-Modifying Instruction Detection
Description: A chain-of-thought search of the full document — including footnotes, headers, legends, and any other location — for instructions that affect how a field's raw extracted value should be interpreted or transformed: unit scale (thousands versus millions), currency, sign conventions, date formats, and conditional definitions.
Why It Matters: This is the class of error that produces plausible-looking but numerically wrong values, and it is the hardest class for a naive extraction approach to catch, since the raw number itself looks entirely reasonable.
Key Requirements:
- Footnote and marker cross-referencing across the full document, not just the field's local context
- Document-wide search scope by design, since instructions can appear anywhere
- Structured output of {field, instruction, transformation} triples
Dependencies: Full-Coverage Column Mapping

#### F2. Confidence-Scored Instruction Interpretation
Description: Each discovered instruction is assigned a confidence score reflecting how certain the agent is in its interpretation. Scores below a configurable threshold generate a human review entry.
Why It Matters: Instruction misinterpretation, such as applying the wrong multiplier, silently corrupts every value for that field across the entire document, making this one of the highest-leverage places to apply review scrutiny.
Key Requirements:
- Calibrated confidence scoring, consistent with the approach defined in the Verification & Validation Layer
- Configurable threshold, tunable per field criticality
- Review entries that include the source text and the agent's reasoning, not just the conclusion
Dependencies: Verification & Validation Layer, Confidence Scoring & Human-in-the-Loop Review module

#### F3. Rule Persistence to Template Memory
Description: Once an instruction is confirmed, either by high confidence or by human review, persist it to the template's rule set in the Knowledge Base so it is reused directly for future documents of the same template.
Why It Matters: Closes the feedback loop that makes the system cheaper and faster over time; without this step, every document pays the full discovery cost regardless of how many times the same template has been seen before.
Key Requirements:
- Write-back to the Knowledge Base's persistent extraction rules
- Versioning and linkage to the specific review record that confirmed the rule
Dependencies: Persistent Extraction Rules (Knowledge Base)

### G. Extraction / Parsing Agent

#### G1. Instruction-Driven Extraction Prompt Construction
Description: For each field, dynamically construct an extraction prompt that incorporates the data dictionary definition, the field's location and mapping from the mapping agent, and any transformation instructions discovered — producing a final, post-transformation value.
Why It Matters: This is the agent that actually produces the output value; its correctness depends entirely on the quality of what the upstream mapping and instruction-discovery agents fed into the prompt, which is why those upstream steps are treated as first-class features rather than implementation detail.
Key Requirements:
- Dynamic, per-field prompt assembly
- Application of numeric, date, and currency transformations as part of extraction, not as a separate post-processing step prone to drift from the extracted value
- Structured output matching the data dictionary's schema exactly
Dependencies: Data Dictionary Mapping Agent, Instruction Discovery Agent, Knowledge Base

#### G2. Template-Memory Fast Path
Description: When a document matches a known template with persisted rules at sufficient confidence, extraction runs directly from template memory without repeating the full mapping and discovery chain-of-thought, reserving that heavier reasoning for new or drifted templates.
Why It Matters: This is the major cost and latency lever at production scale; most documents the platform sees in steady state should be able to take this path.
Key Requirements:
- A template-match confidence check before taking the fast path
- Automatic fallback to the full pipeline when match confidence is low
Dependencies: Persistent Extraction Rules, Template Drift Detection

### H. Verification & Validation Layer
Not present in the original design — added because per-field, self-reported confidence alone will miss two important error classes: individually plausible values that are wrong, and values that are wrong specifically because the model that produced them also rated its own confidence.

#### H1. Independent Verifier Agent
Description: A second agent, prompted independently of the extractor, checks each extracted value against the cited source span without seeing the extractor's reasoning, providing an independent check rather than relying solely on the extractor's self-reported confidence.
Why It Matters: Self-reported LLM confidence is often poorly calibrated; an independently prompted check, blind to the first agent's chain of reasoning, catches a different and often complementary error distribution.
Key Requirements:
- Independent prompting with no shared context or reasoning trace between extractor and verifier
- Disagreement between the two automatically flagged for human review
Dependencies: Extraction / Parsing Agent, Provenance & Audit Trail

#### H2. Cross-Field Reconciliation
Description: After extraction, run defined consistency checks across related fields within a document: balances tie out, subtotals sum correctly, dates are internally consistent, currency is consistent throughout — independent of any single field's confidence score.
Why It Matters: Catches errors that look entirely reasonable field by field but are wrong in aggregate, which is a common and damaging failure mode in financial statement data specifically.
Key Requirements:
- Defined reconciliation rule sets per document type
- Discrepancy flagging with automatic routing to review
Dependencies: Knowledge Base (reconciliation rules per document type)

#### H3. Stratified Confidence Sampling
Description: Periodically sample high-confidence extractions, not just below-threshold ones, for human QA review, to detect systematic confidence miscalibration or drift.
Why It Matters: A model that is confidently wrong in a consistent way will never be flagged by a threshold-only review approach, since by definition it never crosses the threshold.
Key Requirements:
- Defined sampling policy (rate, stratification by field/template)
- Sampling results fed into confidence calibration monitoring
Dependencies: Confidence Scoring & Human-in-the-Loop Review module, Testing & Evaluation Framework

### I. Confidence Scoring & Human-in-the-Loop Review

#### I1. Configurable Threshold Routing
Description: Confidence thresholds, for classification, instruction interpretation, and extracted values, are configurable per document type and per field criticality, rather than a single global constant.
Why It Matters: Not all fields carry equal risk; a materially important field such as Payment Amount may warrant a stricter threshold than a purely descriptive field.
Key Requirements:
- Per-field and per-document-type threshold configuration
- Administrative interface or configuration file for managing thresholds
Dependencies: Knowledge Base

#### I2. Review Queue with Prioritization & Routing
Description: Human review entries are queued with priority based on field criticality, document type, and SLA; routed to the appropriate reviewer; and presented with full context, including the source excerpt, extracted value, confidence score, and reasoning trace.
Why It Matters: An undifferentiated review inbox does not scale and buries the items that matter most; reviewers also need enough context to correct an item quickly without re-reading the entire source document.
Key Requirements:
- Priority and SLA logic
- Reviewer routing and assignment
- A review interface that shows source-to-value provenance directly, not just the extracted value
Dependencies: Provenance & Audit Trail

#### I3. Reviewer Correction Feedback Loop
Description: When a reviewer corrects a value, a mapping, or an instruction, that correction is captured not just as a fixed output but as a proposed update to the underlying template rule or data dictionary entry, subject to the Knowledge Base's governance approval.
Why It Matters: This is what turns human review from a recurring cost into a decreasing one; without it, the same correction gets made by a human on every future document of that template.
Key Requirements:
- Correction-capture interface built into the review workflow
- Explicit linkage from a correction to the specific Knowledge Base rule it affects
- Write-back workflow that routes through Knowledge Base governance rather than updating rules unilaterally
Dependencies: Knowledge Base Governance & Versioning

### J. Provenance & Audit Trail

#### J1. Field-Level Source Traceability
Description: Every extracted value carries a reference to its exact source — document, page, and bounding box or text span — and the transformation applied to reach the final value.
Why It Matters: Required for reviewer efficiency, for resolving disputes about a specific value, and for regulatory audit of how a reported number was derived.
Key Requirements:
- A consistent provenance metadata schema attached to every output value
- Provenance retained through every pipeline stage, not just at the point of extraction
Dependencies: Layout-Aware Text & Table Extraction

#### J2. Full Processing History
Description: Retain a complete history of which agent and rule version produced each value, what confidence it received, whether it was reviewed or corrected, and by whom.
Why It Matters: Supports audit and compliance requirements for financial data pipelines, and provides the underlying data the evaluation framework needs to measure accuracy over time.
Key Requirements:
- Immutable, append-only processing log
- Linkage across all pipeline stages for a given document and field
Dependencies: None

### K. Orchestration & Workflow Engine

#### K1. Non-Linear Agent Orchestration
Description: An orchestrator coordinates classification, knowledge base load, mapping, instruction discovery, extraction, verification, and review as a graph with conditional loop-backs — for example, a mapping gap can trigger reclassification, or a verification disagreement can trigger re-extraction — rather than as a strict one-way pipeline.
Why It Matters: Real documents do not always fit a linear happy path; the orchestration design needs to model retries and branch conditions explicitly rather than treating every deviation as a failure.
Key Requirements:
- A defined state machine or graph representation of the pipeline
- Retry policy per stage
- Error handling and dead-letter routing for documents that fail repeatedly
Dependencies: All agent modules

#### K2. Batch & Streaming Processing
Description: Support both bulk backfill processing of historical documents and streaming or near-real-time processing of newly arriving documents.
Why It Matters: Onboarding a new document type or client will likely require processing a large historical backlog, while steady-state production use is ongoing and incremental; the platform needs to handle both without one starving the other.
Key Requirements:
- Queueing and throughput management
- Prioritization policy between batch and streaming load
Dependencies: None

### L. Template Drift Detection & Monitoring

#### L1. Drift Detection
Description: Monitor per-template metrics over time — confidence scores, review-trigger rate, reconciliation failure rate — and flag when a previously "solved" template's metrics degrade, indicating the issuer has likely changed their document format.
Why It Matters: Issuers change document formats without notice; a static, unmonitored template will silently degrade in accuracy rather than failing visibly.
Key Requirements:
- Per-template metric tracking over time
- Statistical drift alerting
- Automatic routing to the unknown-template bootstrapping workflow once drift is confirmed
Dependencies: Knowledge Base, Testing & Evaluation Framework

#### L2. Operational Dashboards
Description: Dashboards showing pipeline throughput, review queue backlog, confidence distributions, per-template accuracy trends, and cost per document.
Why It Matters: Operational visibility for the team running the platform, and the first place drift or backlog problems will actually be noticed in practice.
Key Requirements:
- A metrics pipeline feeding the dashboards
- Dashboarding covering throughput, backlog, confidence, accuracy, and cost
Dependencies: Provenance & Audit Trail

### M. Security, Compliance & Data Governance

#### M1. Data Protection Controls
Description: Encryption at rest and in transit, role-based access control, data residency controls, and defined retention and deletion policies for financial documents and extracted data.
Why It Matters: Financial documents routinely contain personally identifiable information and potentially material non-public information; these controls are a baseline expectation, not an enhancement.
Key Requirements:
- Encryption at rest and in transit
- Role-based access control
- Configurable retention and deletion policy
- Data residency options where required
Dependencies: None

#### M2. Model & Vendor Data Handling Policy
Description: An explicit policy and technical controls governing whether and how sensitive document content is sent to third-party LLM APIs, including options for redaction, private or dedicated model deployment, or zero-data-retention agreements where third-party APIs are used.
Why It Matters: Sending sensitive financial data to external model providers carries real compliance implications that should be decided deliberately, by sensitivity tier, rather than defaulted into.
Key Requirements:
- Configurable model routing by document/data sensitivity tier
- Optional redaction pipeline for sensitive fields before any external model call
- Vendor data-handling agreement tracking
Dependencies: None

#### M3. Access Logging
Description: A full audit log of who accessed which documents and extracted values, and when.
Why It Matters: A standard control expectation for systems handling financial data, and a prerequisite for most compliance frameworks the platform is likely to be assessed against.
Key Requirements:
- Access logging integrated with existing identity and access management
- Defined log retention
Dependencies: None

### N. Testing & Evaluation Framework

#### N1. Golden Dataset per Template
Description: Maintain a human-verified ground-truth dataset for each document template, used to measure extraction accuracy — precision and recall per field — and to detect regressions when prompts, models, or rules change.
Why It Matters: Without this, there is no objective way to know whether a change to a prompt, model, or rule improved or degraded the system; changes would otherwise be evaluated on intuition alone.
Key Requirements:
- Golden dataset storage and versioning per template
- Automated scoring pipeline
- Regression gating before rule or prompt changes are promoted to production
Dependencies: Reviewer Correction Feedback Loop, as the primary source of ground truth

#### N2. Confidence Calibration Monitoring
Description: Continuously compare confidence scores against actual correctness, drawn from review outcomes and golden dataset scoring, to detect and correct calibration drift.
Why It Matters: Uncalibrated confidence undermines the entire threshold-based review-routing design; a threshold is only meaningful if the confidence scores it acts on are accurate.
Key Requirements:
- Calibration metrics such as reliability curves
- A periodic recalibration process
Dependencies: Stratified Confidence Sampling

### O. Output & Downstream Integration

#### O1. Canonical Structured Output
Description: The final output conforms to a canonical schema matching the data dictionary, including the value, data type, provenance metadata, confidence score, and a transformation-applied flag for every field.
Why It Matters: A consistent, well-defined output schema is what makes the platform usable by downstream systems without bespoke handling per document type.
Key Requirements:
- A formal schema definition
- Validation of every output record against that schema before it is finalized
Dependencies: Provenance & Audit Trail

#### O2. Reprocessing & Versioning
Description: Support reprocessing a document, for example after a knowledge base rule correction, with clear versioning of results: a new extraction supersedes but does not silently overwrite prior results.
Why It Matters: Needed for auditability and for measuring the actual impact of a knowledge base rule change across previously processed documents.
Key Requirements:
- Result versioning with supersession linkage
- Idempotent reprocessing
Dependencies: Provenance & Audit Trail

#### O3. Downstream Delivery
Description: APIs and export mechanisms — database write, event or webhook, file export — to deliver extracted data to downstream systems such as reporting, reconciliation, or a data warehouse.
Why It Matters: The platform needs to actually connect to whatever consumes the data; extraction alone is not a complete deliverable.
Key Requirements:
- API design covering the delivery mechanisms in scope
- Delivery guarantees and error handling for failed deliveries
Dependencies: Canonical Structured Output

### P. Cost & Performance Engineering

#### P1. Reasoning-Cost Tiering
Description: Route each document through the cheapest sufficient path: structured-source short-circuit, then template-memory fast path, then retrieval-assisted mapping, escalating to full chain-of-thought discovery only when a cheaper path is unavailable or insufficient.
Why It Matters: Chain-of-thought reasoning over long documents is the single largest cost driver at scale; this tiering is what makes the system economically viable in production rather than only viable as a proof of concept.
Key Requirements:
- Explicit tiering logic with defined escalation conditions
- Cost tracking per document and per tier
Dependencies: Structured-Source Short-Circuit, Persistent Extraction Rules, Retrieval-Assisted Localization

#### P2. Cost & Latency Monitoring
Description: Track cost and processing latency per document, per template, and per tier, to inform where further optimization — such as promoting a template to the fast path — is warranted.
Why It Matters: Visibility needed to actually manage the economics of the platform on an ongoing basis, rather than discovering cost problems only after they are large.
Key Requirements:
- Cost and latency instrumentation throughout the pipeline
- Reporting integrated with the operational dashboards
Dependencies: Operational Dashboards

## 5. Non-Functional Requirements

## 6. Phased Roadmap
A suggested phasing to de-risk delivery: prove the core pipeline and feedback loop on a small number of document types before investing in the monitoring, governance, and scale features that matter most once volume and template variety grow.

## 7. Open Questions & Decisions Needed
- Which document types are in scope for the MVP? Recommend starting with two to three types to bootstrap the Knowledge Base and prove the feedback loop before expanding breadth.
- What are the ingestion channels in practice — email, SFTP, portal upload, API — and which need to be supported at launch versus later?
- Which downstream systems will consume the extracted data, and what schema or API do they already expect?
- Build versus buy for OCR/layout extraction and document classification, versus relying on a general-purpose multimodal LLM for both?
- What LLM providers and deployment models (API versus self-hosted/private) are acceptable given the sensitivity of the financial data involved, and what redaction policy, if any, applies before data is sent externally?
- Who owns Knowledge Base governance approvals within the organization — new templates, new fields, and rule changes?
- What accuracy threshold and error budget are acceptable per field-criticality tier, and who signs off on that threshold?
- For document types with an available structured source (e.g., XBRL for SEC filings), is the intent to fully trust that source, or to use it as a cross-check against agentic extraction of the same fields?

---

## Appendix: Tables

### Table 0

| Stage | Purpose |
|---|---|
| 1. Source Prioritization | Check for an existing structured/pre-parsed source (e.g., XBRL, prior extraction) before any raw parsing begins. |
| 2. Ingestion & Pre-Processing | Normalize input format; perform layout-aware text and table extraction with position metadata; assess extraction quality. |
| 3. Document Classification | Determine document type and template/issuer variant with a confidence score; route unknown formats to bootstrapping. |
| 4. Knowledge Base Load | Load the applicable data dictionary, including any template-specific overrides and persisted extraction rules. |
| 5. Data Dictionary Mapping | Confirm, field by field, whether and where each data dictionary column is present in the document (chain-of-thought, full coverage). |
| 6. Instruction Discovery | Search the document for value-modifying instructions (unit scale, currency, footnote definitions); score confidence; persist confirmed rules. |
| 7. Extraction / Parsing | Construct field-level prompts from the mapping and instructions; extract and transform each value. |
| 8. Verification & Validation | Independently verify extracted values; run cross-field reconciliation checks. |
| 9. Confidence Routing & Human Review | Route low-confidence or failed-reconciliation items to a prioritized human review queue; feed corrections back into the knowledge base. |
| 10. Output & Delivery | Emit canonical structured output with full provenance and confidence metadata to downstream systems. |

### Table 1

| Category | Requirement |
|---|---|
| Scalability | Handle both large historical backfills and ongoing incremental volume without one starving the other; horizontal scaling of extraction and review capacity. |
| Extensibility | New document types and template variants can be onboarded by adding Knowledge Base entries and data dictionaries, without code changes to the core pipeline. |
| Latency | Defined SLA tiers: near-real-time for interactive/streaming use cases, best-effort throughput for batch backfills. |
| Availability | Pipeline and review queue availability consistent with the platform's role in operational financial workflows. |
| Observability | Full metrics, logging, and tracing across every agent and pipeline stage, feeding the operational dashboards. |
| Security & Compliance | As detailed in Module M — encryption, access control, retention policy, and vendor data-handling policy. |
| Cost Predictability | Reasoning cost tiering and per-document cost tracking, as detailed in Module P, to keep unit economics predictable as volume grows. |

### Table 2

| Phase | Scope |
|---|---|
| Phase 1 — MVP | Two to three document types to bootstrap the Knowledge Base. Core linear pipeline: ingestion, layout-aware extraction, classification, mapping, instruction discovery, extraction. Manually seeded data dictionaries. Basic confidence-threshold review routing. Field-level provenance capture. |
| Phase 2 — Feedback Loop & Efficiency | Persistent extraction rules (template memory) and the reviewer correction feedback loop. Independent verifier agent and cross-field reconciliation. Structured-source short-circuit for document types with a known structured source (e.g., public filings). Reasoning-cost tiering. |
| Phase 3 — Scale & Governance | Template drift detection and monitoring. Stratified QA sampling and confidence calibration monitoring. Golden-dataset evaluation framework. Operational dashboards. Knowledge Base governance workflow with versioning and rollback. Downstream delivery APIs at production scale. Security and compliance hardening for broader rollout. |

