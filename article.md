# Designing Aegis Around Policy and Organisational Memory

A compliance agent can retrieve the relevant policy and still lack context that matters to a decision: how the organisation has handled comparable cases. Policy text establishes the authoritative rule. Prior decisions, review outcomes, corrections, and identified policy gaps record how the organisation has applied or questioned that rule. Those sources are useful together, but they do not have the same authority.

I designed Aegis around that distinction. Its request path includes two retrieval systems from the start: policy retrieval through ChromaDB, and organisational-memory retrieval through Hindsight. The engineering problem is not to merge them into one source. It is to let the reasoning step consider both while keeping policy evidence authoritative and citations tied to real policy chunks.

## What I Built

Aegis is a compliance advisory and triage agent implemented as a LangGraph `StateGraph`. It classifies questions, retrieves and validates evidence, drafts cited answers, and checks governance and confidence. In-domain cases classified as `High` go through the human-review gate; other risk levels do not currently trigger that gate. Streamlit renders the workflow; the graph owns orchestration.

The policy corpus accepts PDF, DOCX, and TXT files from `data/policies/`. LangChain's `RecursiveCharacterTextSplitter` creates 800-character chunks with 150 characters of overlap; embeddings are indexed in Chroma. Retrieval combines vector search, BM25 candidates, and reranking, returns up to five chunks, and marks qualification against the configured threshold. Citations use qualifying chunks and their source metadata.

Hindsight is the persistent organisational-memory source. Aegis retains selected cases, corpus gaps, review decisions, and owner/risk corrections as typed records. Later in-domain queries can recall these as prompt context; they do not become policy citations or directly change owner routing.

## The Technical Problem

The design question is: **How can an agent use organisational precedent without allowing memory to replace authoritative policy evidence?**

Chroma answers, "What does the policy say?" Hindsight answers, "How has this organisation handled something similar before?" Only policy chunks support factual compliance claims and citations. Memory can describe an outcome, correction, or gap, but may be incomplete or context-specific. The model needs both sources with an explicit authority boundary.

## Architecture

The request path is deliberately ordered so classification informs recall, and both retrieval results are available to reasoning:

```text
Query
  -> Topic Classification
  -> Hindsight Memory Recall (when enabled and in-domain)
  -> Topic Routing
  -> Chroma Policy Retrieval
  -> Context Validation
  -> Compliance Reasoning (policy chunks + memory block)
  -> Citation Generation
  -> Confidence Calculation
  -> Governance Validation
  -> Risk Classification
  -> Human Review Gate (when required)
  -> Audit Logging
  -> Hindsight Memory Retain
  -> Response
```

Recall follows topic classification and precedes routing and policy retrieval. The service appends a known topic to the query; out-of-domain and memory-disabled requests skip recall. Graph state keeps recalled memories separate from policy chunks, and reasoning receives both with distinct labels.

The graph logs the audit record before invoking its memory-retain node. The service stores governance-passed cases and insufficient-evidence gaps; review decisions and corrections are retained at their review actions. Each memory event therefore reflects its actual workflow outcome.

## Hindsight and the Memory Schema

I chose Hindsight for its persistent `retain()` and query-based `recall()` operations. The repository declares `hindsight-client>=0.10.1`. Configuration uses `HINDSIGHT_API_URL`, `HINDSIGHT_API_KEY`, and `HINDSIGHT_BANK_ID` (default `aegis-northwind`). Memory requires `MEMORY_ENABLED=true` plus URL and key; `MEMORY_TOP_K` defaults to five and `MEMORY_TIMEOUT_SECONDS` to five seconds.

I structured retained text so each event exposes the fields useful for later retrieval and interpretation:

```text
TYPE: case
DATE: 2026-09-15
QUESTION: Can we transfer personal data from our EU office to our US subsidiary without SCCs?
TOPIC: GDPR
OWNER: DPO
RISK: High
GOVERNANCE_OUTCOME: passed
ANSWER_SUMMARY: [summary of the generated answer]
```

The four event types are `case` (governance-passed answer), `corpus_gap` (insufficient policy evidence), `review_decision` (approval, rejection, or requested change), and `correction` (human-supplied owner/risk correction and reason). Typed events distinguish organisational outcomes more clearly than whole conversation transcripts.

The client stores metadata and tags alongside text. Cases and gaps include fields such as `mem_type`, `topic`, `user_id`, and `user_role`; review/correction records use event-specific metadata. Aegis uses one organisation bank, and recall does not filter results by user ID.

See the [Hindsight repository](https://github.com/vectorize-io/hindsight) and [Hindsight documentation](https://hindsight.vectorize.io/) for the memory API. [Vectorize's overview of agent memory](https://vectorize.io/what-is-agent-memory) gives useful context for the broader design problem.

## Code Walkthrough

In `memory/service.py`, `recall_for_query()` checks the memory configuration and adds a topic hint only when classification produced a known topic:

```python
def recall_for_query(query: str, topic: str | None = None) -> MemoryResult:
    if not is_enabled():
        return MemoryResult(ok=False, error="Memory disabled or not configured")

    effective_query = query
    if topic and topic not in ("Unknown", "Out-of-Domain"):
        effective_query = "{} [topic: {}]".format(query, topic)

    return _recall(effective_query, top_k=_MAX_ITEMS)
```

This service boundary returns a `MemoryResult`, not policy documents. `node_memory_recall()` in `agents/orchestrator.py` stores items in `memory_context` and a separate `memory_block`. `agents/compliance_agent.py` puts policy chunks first; `format_prompt_block()` labels memory as non-policy context and preserves `[Chunk <id>]` as the factual citation requirement.

The retention implementation in `memory/service.py` builds a case record only after governance passes, then submits text, metadata, and tags to the client wrapper:

```python
if not gov_passed:
    return

case_text = (
    "TYPE: case\n"
    "DATE: {date}\n"
    "QUESTION: {q}\n"
    "TOPIC: {topic}\n"
    "OWNER: {owner}\n"
    "RISK: {risk}\n"
    "GOVERNANCE_OUTCOME: passed\n"
    "ANSWER_SUMMARY: {summary}"
).format(
    date=today,
    q=mask_pii(query),
    topic=topic,
    owner=owner,
    risk=risk,
    summary=mask_pii(answer_summary),
)

ok, err = _retain(
    case_text,
    metadata={
        "mem_type": "case",
        "topic": topic,
        "risk": risk,
        "owner": owner,
        "user_id": user_id,
        "user_role": user_role,
    },
    tags=["case", topic.lower().replace(" ", "-"), risk.lower()],
)
```

`memory/hindsight_client.py` calls the SDK with `retain_async=True`; errors are logged and do not interrupt the response. The graph also retains insufficient-evidence gaps, while review decisions and corrections use dedicated service functions.

Before retention, `mask_pii()` in `memory/service.py` applies regular expressions to emails, US and UK phone formats, long numeric references, and SSN-like patterns:

```python
_PII_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'), "[EMAIL]"),
    (re.compile(r'\b(?:\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b'), "[PHONE]"),
    (re.compile(r'\b(?:\+44\s?|0)(?:\d\s?){9,10}\b'), "[PHONE]"),
    (re.compile(r'\b\d{8,}\b'), "[ACCOUNT_NUM]"),
    (re.compile(r'\b\d{3}[-\s]\d{2}[-\s]\d{4}\b'), "[NATIONAL_ID]"),
]
```

That is pattern-based masking, not comprehensive entity detection; names in natural-language text are not generally removed.

## One Request, Two Sources of Context

Consider an illustrative in-domain question about a cross-border transfer. Chroma returns matching chunks and source metadata; when enabled, Hindsight separately recalls relevant records. Reasoning receives qualifying policy evidence plus the delimited memory block. Factual claims require `[Chunk <id>]` citations; `[Memory <id>]` identifies supplementary precedent. Governance and risk checks follow, and audit logging records the answer and memory provenance.

For a later similar question, the same path may recall a retained case, review decision, correction, or gap. A match is not guaranteed, and memory does not automatically change routing. It gives the LLM precedent context while policy remains authoritative.

## What I Learned

**Schema is part of retrieval quality.** `TYPE`, `DATE`, `QUESTION`, `TOPIC`, `OWNER`, `RISK`, `GOVERNANCE_OUTCOME`, and `ANSWER_SUMMARY` give cases stable anchors; review and correction events need their own fields.

**Authority needs an explicit boundary.** Separate state fields and prompt sections label memory as non-policy context and retain chunk citations for factual claims.

**Retention policy is architectural.** Aegis keeps selected cases, gaps, reviews, and corrections rather than every turn. Asynchronous writes and logged failures keep retention from blocking responses.

**Debugging needs separate traces.** I inspect Chroma chunks and Hindsight recall independently; Aegis records memory IDs and shows policy evidence and recalled context separately.

## Limitations

The implementation uses one organisation bank. Cases and gaps store `user_id` and `user_role`, but recall does not filter by them; review and correction metadata also differs. This is not tenant-isolated memory.

PII masking is regex-based; it does not reliably identify names or every sensitive value. The prompt is capped at five items and 3,000 characters by default, so some recalled history may not fit.

## Conclusion

A compliance agent needs both authoritative knowledge and organisational knowledge. Chroma answers, "What does the policy say?" Hindsight answers, "What has the organisation learned or decided before?" The strength of Aegis comes from designing for both sources while keeping their roles distinct: memory can inform precedent, but policy chunks remain the evidence for compliance claims.
