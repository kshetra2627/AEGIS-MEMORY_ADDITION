# Aegis Triage Agent — Architecture + Evaluation & Risk Assessment Guide

> This document explains what each file/folder is doing and how Evaluation Dashboard scoring + risk assessment works. No code changes were made.

---

## 1) Top-level folders/files

### `app.py`
**Role:** Streamlit entrypoint (web app).

**What happens:**
- Loads environment variables (`load_dotenv()`).
- Sets Streamlit page configuration and injects CSS from `ui/styles.py`.
- Runs RAG ingestion on startup:
  - `rag.ingest.ingest_all(force_rebuild=False)` via `_startup_ingest()`.
- Requires authentication:
  - If `ui.auth.is_authenticated()` is false, it renders login (`ui.auth.render_login_screen()`) and stops.
- Builds navigation (`NAV_PAGES`) and renders the selected page from `ui/pages/*`.
- Does not directly call any LLM/tools; it delegates all “work” to the agent layer.

### `llm_provider.py`
**Role:** Unified LLM calling layer + failover between providers.

**What happens:**
- Loads env vars.
- Implements three provider call functions:
  - `_call_groq(messages, temperature)` using Groq OpenAI-compatible API.
  - `_call_gemini(messages, temperature)` using Google Gemini SDK.
  - `_call_openrouter(messages, temperature)` using OpenRouter OpenAI-compatible API.
- `get_llm_response(messages, temperature)` tries providers in this priority order:
  1. Groq
  2. Gemini
  3. OpenRouter
  
  If one fails, it continues to the next. It returns a dict like:
  - `{ "text": ..., "provider": ..., "attempts": [...] }`

**System prompt handling (important):**
- The system prompt is not stored here. It is taken from the incoming `messages` list.
- For Gemini, all `messages` entries with `role == "system"` are concatenated into `system_instruction`.

### `README.md`
**Role:** Project description / setup notes (not inspected here beyond file listing).

### `requirements.txt`
**Role:** Python dependencies.

### `.gitignore`
**Role:** Git ignore rules.

---

## 2) `agents/` (core workflow + logic)

### `agents/orchestrator.py`
**Role:** The main LangGraph workflow (the “brain”) that runs for each query.

**Key concepts:**
- Defines `GraphState` (a typed dict) carrying all intermediate + final results.
- `build_graph()` creates nodes and edges to form a deterministic pipeline.

**Execution nodes (in order):**
1. **`classify_topic`**
   - Tool: `classify_topic_tool`
   - Produces `topic` + `in_domain`

2. **`topic_routing`**
   - Tool: `identify_owner_tool`
   - Produces `owner` based on `topic`

3. **`rag_retrieval`**
   - Tool: `retrieve_policy_documents_tool`
   - Produces `retrieved_chunks` (top-k chunks with similarity scores)

4. **`context_validation`**
   - Checks whether any retrieved chunk is marked `qualifies`
   - Sets `context_available`

5. **`compliance_reasoning`**
   - If `in_domain` and `context_available`:
     - Calls `agents/compliance_agent.generate_draft_answer()`
     - Fills `draft_answer`, `llm_provider`, `llm_attempts`
   - Else:
     - Skips generation and sets empty draft

6. **`citation_generation`**
   - Tool: `generate_citations_tool`
   - Produces formatted citation strings in `citations`

7. **`confidence_calculation`**
   - Tool: `calculate_confidence_tool`
   - Produces deterministic `confidence = { score, level, ... }`

8. **`governance_validation`**
   - Calls `agents/governance_agent.validate(...)`
   - If governance fails, it discards the draft and returns a fixed refusal.
   - Produces `governance_passed`, `final_text`

9. **`risk_classification`**
   - Tool: `classify_risk_tool`
   - Produces `risk` = `Low` / `Medium` / `High`

10. **`human_review_gate`**
   - If `risk == "High"`:
     - Calls `human_review_tool` to set `review_status = "Pending"`
     - Holds answer for approval
   - Else:
     - Auto-finalizes (`Not Required`)

11. **`audit_logging`**
   - Tool: `log_audit_tool`
   - Persists a full record into SQLite (`database/audit.db`) and exports to JSON (`logs/audit_log.json`).

**Entry points:**
- `run_query(query, chat_history=None)` runs full graph synchronously.
- `run_query_streaming(query, chat_history=None, on_step=None)` streams node updates for live UI progress.

---

### `agents/router.py`
**Role:** Deterministic topic → owner routing.

**What happens:**
- `OWNER_MAP` maps known topics to owners, e.g.:
  - `GDPR` / `Data Privacy` → `DPO`
  - `Sanctions` / `AML` / `KYC` → `AML Officer`
  - `Licensing` / `Contracts` → `Legal`
  - `Cybersecurity` / `Information Security` → `Security Officer`
  - `Vendor Compliance` → `Procurement Compliance / Risk Officer`

- `identify_owner(topic)` returns the mapped owner or defaults to `Compliance Manager`.

---

### `agents/compliance_agent.py`
**Role:** Grounded answer generation logic.

**Key behaviors:**
- Defines a hard system prompt string:
  - `SYSTEM_PROMPT = """You are Aegis, a compliance advisory assistant..."""`
- That system prompt enforces strict grounding rules, especially:
  - Answer strictly and only from retrieved policy chunks.
  - Each factual sentence must include an inline citation tag `[Chunk <chunk_id>]`.
  - Every paragraph must include at least one citation.
  - If insufficient info, explicitly say so.

- `generate_draft_answer(query, chunks, chat_history_summary)`:
  1. Filters `qualifying` chunks.
  2. Builds `context` where each chunk includes metadata and full text.
  3. Builds a user prompt containing:
     - retrieved context
     - the question
     - instructions to use only the chunks
  4. Calls the model using `llm_provider.get_llm_response(messages, temperature=0.1)`.

**Important:**
- If no qualifying chunks exist, it returns empty text `{ text: "", provider: "none" ... }`.

---

### `agents/governance_agent.py`
**Role:** Post-generation governance gate that decides whether to accept the draft or refuse.

**What happens (validation rules):**
- If `in_domain` is false → refuse immediately.
- If evidence is insufficient:
  - If fewer than 2 qualifying chunks:
    - requires single chunk score to be at least `SIMILARITY_THRESHOLD + 0.10`.
- If answer is empty/blank → refuse.
- If the model is hedging / claiming lack of info incorrectly (regex patterns in `_is_hedged_non_answer`) → refuse.
- If confidence is too low:
  - `confidence.score < MIN_CONFIDENCE` (where `MIN_CONFIDENCE = 40`) → refuse.
- Citation coverage check:
  - `_every_paragraph_cited()` requires every non-empty paragraph to contain `[Chunk <...>]`.

**Outcome:**
- If all checks pass → `passed=True` and `final_text = draft_answer`.
- Otherwise → `passed=False` and `final_text = REFUSAL_MESSAGE`.

---

### `agents/escalation_agent.py`
**Role:** Risk classification logic (used via tool wrapper).

- In this repo, risk classification is invoked in orchestration via `classify_risk_tool`, which ultimately calls `agents.escalation_agent.classify_risk`.

*(The file wasn’t displayed above; if you want, I can read it in a follow-up, but the risk algorithm is also referenced by test scenarios and UI.)*

---

## 3) `tools/` (LangChain StructuredTools)

### `tools/compliance_tools.py`
**Role:** Tool implementations for each LangGraph node.

**Includes deterministic logic for:**
- Topic classification:
  - `classify_topic(query)` returns `{topic, in_domain}` using keyword lists.
- Owner identification:
  - `identify_owner(topic)` wraps `agents/router.identify_owner`.
- Retrieval:
  - `retrieve_policy_documents(query)` calls `rag.retriever.retrieve(query, k=5)`.
- Citation formatting:
  - `generate_citations(chunks)` formats a citation string per qualifying chunk.
- Confidence:
  - `calculate_confidence(chunks, citations)` uses `tools/confidence.calculate_confidence_score`.
- Risk:
  - `classify_risk(query, topic)` wraps `agents/escalation_agent.classify_risk`.
- Human review:
  - `human_review(risk, owner)` sets `status = Pending` only for `risk == "High"`.
- Audit logging:
  - `log_audit(record)` persists to SQLite via `tools/audit_logger.log_query(record)`.

**Tool wrappers:**
- At bottom of the file, each function is wrapped as a `StructuredTool` so orchestration nodes call them consistently.

### `tools/confidence.py`
**Role:** Deterministic confidence scoring (no LLM estimation).

**Confidence formula:**
- Let `qualifying = [c for c in chunks if c.qualifies]`.
- If no qualifying chunks:
  - score = 0, level = Low.

Otherwise:
1. **Retrieval component (70%)**
   - Average similarity across qualifying chunks → scaled to 0..70.
2. **Chunk count component (20%)**
   - Uses min(len(qualifying), 5) / 5 * 20.
3. **Citation component (10%)**
   - Citation coverage = len(citations)/len(qualifying), capped to 10.

**Total score is clamped to 0..100**.

**Level thresholds:**
- `score >= 75` → `High`
- `score >= 50` → `Medium`
- else → `Low`

### `tools/audit_logger.py`
**Role:** Persist and export full traceable audit records.

**What it does:**
- Creates SQLite DB at `database/audit.db`.
- Table: `audit_log` with fields like:
  - question, topic, owner, risk
  - retrieved_documents/chunks
  - confidence
  - answer + citations
  - escalated flag
  - approval_status + timestamps
  - provider + latencies

- `log_query(record)` inserts a new audit row and exports all rows to `logs/audit_log.json`.
- `update_approval(row_id, approval_status, ...)` updates approval status/reason and re-exports JSON.

---

## 4) `rag/` (retrieval pipeline)

*(File contents were not opened here, but the naming shows the standard RAG components.)*

Typical roles by filename:
- `rag/ingest.py`
  - Ingests documents from `data/policies/`.
  - Splits into chunks and stores embeddings.
- `rag/loader.py`
  - Loads PDFs/text from policy folder.
- `rag/splitter.py`
  - Splits documents into chunks.
- `rag/vectorstore.py`
  - Stores/retrieves embeddings (likely via Chroma under `database/chroma/`).
- `rag/retriever.py`
  - Implements `retrieve(query, k)` and sets `qualifies` based on similarity thresholds.
  - Defines `SIMILARITY_THRESHOLD` used by governance.
- `rag/embeddings.py`
  - Embedding model wrapper.
- `rag/multiquery.py`, `rag/query_rewrite.py`, `rag/hybrid.py`
  - Query rewriting / hybrid retrieval helpers to improve recall.

---

## 5) `ui/` (dashboard + visual pages)

### `ui/pages/evaluation.py` — Evaluation Dashboard
**Role:** Streamlit page that runs the test suite and displays results.

**What it shows:**
- Functional tests categories:
  - Covered Question
  - Out-of-Corpus Refusal
  - High-Risk Escalation
  - Routing Accuracy
  - Adversarial Governance

- RAGAS-like metrics (RAG evaluation):
  - `context_precision`
  - `context_recall`
  - `faithfulness`
  - `answer_relevancy`

- LLM-as-Judge metrics (8 dimensions):
  - faithfulness, completeness, citation_quality,
  - governance_compliance, safety, correctness,
  - clarity, helpfulness

**How it evaluates:**
- On “Run Evaluation Suite”, it calls:
  - `tests.eval_suite.run_all(run_ragas=..., run_judge=...)`

- It then renders:
  - Functional tests: PASS/FAIL counts by scenario category.
  - RAGAS: summary metrics + per-scenario score table/plot.
  - Judge: overall average and radar chart + per-scenario dimension table.

---

## 6) How risk is assessed (end-to-end)

### Where risk comes from
1. **Orchestrator node:** `risk_classification`
2. **Tool:** `classify_risk_tool` (from `tools/compliance_tools.py`)
3. **Wraps:** `agents/escalation_agent.classify_risk(query, topic)`
4. Sets `state["risk"]` to `Low`, `Medium`, or `High`.

### How risk triggers human review
- **Orchestrator node:** `human_review_gate`
- If `risk == "High"`:
  - `human_review_tool` returns `status = "Pending"`
  - Answer is held (`held_answer`) and `final_answer` remains None until approval.
- Otherwise:
  - `review_status = "Not Required"` and answer is auto-finalized.

### How analytics dashboard counts risk
- `ui/pages/analytics.py` computes a “Risk Distribution” by counting `df["risk"].value_counts()`.

---

## 7) How the Evaluation Suite runs (tests)

### `tests/eval_suite.py`
**Role:** Scenario-driven evaluation runner.

**Scenarios included (6 total):**
1. Retention policy question → should be covered/cited, not escalated.
2. Adversarial governance question (nonsense cybersecurity renewal) → should refuse via governance + escalate.
3. EU data in US storage question → should be High risk + escalated to DPO.
4. Sanctions screening → should route to AML Officer.
5. “Ignore GDPR” adversarial attempt → should not endorse rule-breaking; must escalate.
6. Weather question → must refuse out-of-corpus without escalation.

**For each scenario it runs:**
- `state = agents/orchestrator.run_query(sc['query'])`

Then it computes:
- `passed = sc['expect'](state)` (scenario-specific assertions)

If enabled:
- **RAGAS scoring:** `tests/ragas_metrics.evaluate(...)`
- **LLM-as-Judge:** `tests/llm_judge.judge(...)`

It aggregates summaries shown in the Evaluation dashboard.

### `tests/llm_judge.py`
**Role:** LLM-as-Judge scoring across 8 dimensions.

**What it does:**
- Builds a judge prompt including:
  - question
  - retrieved context chunks
  - citations attached
  - final answer shown to user
  - metadata flags: `governance_passed`, `escalated`, `risk`
- Uses `llm_provider.get_llm_response(..., temperature=0.0)` to ensure stable scoring.
- Requires a strict JSON output with 8 integer scores 0-10.
- Computes `overall` as the average of non-null dimension values.

### `tests/ragas_metrics.py`
**Role:** RAGAS-style metrics without requiring ground-truth.

**Four metrics and how they are computed:**
1. **Context Precision**
   - Judge marks each qualifying chunk as relevant/irrelevant.
   - Precision uses a rank-weighted “average precision”-like calculation.

2. **Context Recall**
   - Measures whether the final citations reference qualifying chunk IDs.

3. **Faithfulness**
   - Judge decomposes the answer into atomic claims and checks which are supported by the retrieved context.

4. **Answer Relevancy**
   - Judge produces 3 “reverse questions” the answer would address.
   - Embeds them with `rag/embeddings.get_embeddings()` and compares cosine similarity to the original query.

All judge calls use `temperature=0.0`.

---

## 8) Evaluation / risk visibility in the UI pages

### `ui/pages/dashboard.py`
**Role:** Operations homepage + quick actions.

**What it displays:**
- Today’s system health derived from audit logs.
- Provider usage, indexed documents, pending reviews count, high risk count.
- “AI Insights” and “Recent Activity” from `ui/insights.py`.

### `ui/pages/agent.py`
**Role:** Main workspace to run queries.

**What it does:**
- Uses `run_query_streaming()` from `agents/orchestrator.py`.
- Renders live stage progress by mapping node names to UI stages.
- If `review_status == "Pending"`, it opens a review gate experience in-session.

### `ui/pages/pending_reviews.py`
**Role:** Central human review page for high-risk held answers.

**What it does:**
- Loads audit rows and filters `approval_status == "Pending"`.
- For each pending item:
  - shows risk badge + owner
  - shows preview of drafted answer
  - allows Approve / Reject / Request Changes
- Approval updates are persisted via `tools/audit_logger.update_approval`.

### `ui/pages/analytics.py`
**Role:** Charts and aggregated metrics across audit logs.

**Risk-related visuals include:**
- Risk distribution pie chart
- Escalation rate over time

### `ui/pages/evaluation.py`
**Role:** Runs and visualizes evaluation metrics described above.

---

## 9) Summary: What to remember
- **System prompt is defined in** `agents/compliance_agent.py` and passed as `role: "system"` messages.
- **LLM provider** is in `llm_provider.py` with failover Groq→Gemini→OpenRouter.
- **Governance** is in `agents/governance_agent.py` and blocks drafts unless:
  - in-domain
  - sufficient evidence
  - minimum confidence
  - every paragraph is cited
- **Risk assessment** is produced by `agents/escalation_agent.classify_risk()` (called via tool wrapper) and triggers a **human review gate** only when `risk == "High"`.
- **Evaluation dashboard** runs `tests/eval_suite.py` which:
  - executes scenarios via the LangGraph orchestrator
  - then scores using:
    - RAGAS-style judge (`tests/ragas_metrics.py`)
    - LLM-as-judge 8 dimensions (`tests/llm_judge.py`)

---

## 10) Suggested next file to inspect (optional)
The only piece not fully shown above is the internal risk algorithm inside `agents/escalation_agent.py`. If you want, I can read that file next and add the exact rubric to this document—without changing code.
