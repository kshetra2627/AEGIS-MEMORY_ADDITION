"""Evaluation Suite -- Functional Tests, RAG Evaluation (RAGAS), and LLM-as-Judge
(8 Dimensions), all run end-to-end through the LangGraph workflow."""
import streamlit as st
import plotly.express as px
import pandas as pd

PLOTLY_LAYOUT = dict(paper_bgcolor="#131A2A", plot_bgcolor="#131A2A", font_color="#E5E9F0")

FUNCTIONAL_CATEGORIES = [
    "Covered Question", "Out-of-Corpus Refusal", "High-Risk Escalation",
    "Routing Accuracy", "Adversarial Governance",
]

RAGAS_METRICS = [
    ("context_precision", "Context Precision"),
    ("context_recall", "Context Recall"),
    ("faithfulness", "Faithfulness"),
    ("answer_relevancy", "Answer Relevancy"),
]

JUDGE_DIMENSIONS = [
    ("faithfulness", "Faithfulness"),
    ("completeness", "Completeness"),
    ("citation_quality", "Citation Quality"),
    ("governance_compliance", "Governance Compliance"),
    ("safety", "Safety"),
    ("correctness", "Correctness"),
    ("clarity", "Clarity"),
    ("helpfulness", "Helpfulness"),
]


def render():
    st.markdown('<div class="aegis-header">🧪 Evaluation Suite</div>', unsafe_allow_html=True)
    st.caption(
        "Runs required scenarios end-to-end through the LangGraph workflow, then scores "
        "the RAG pipeline with RAGAS-style metrics and an 8-dimension LLM-as-judge pass."
    )

    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        run_ragas = st.checkbox("RAG Evaluation (RAGAS)", value=True)
    with col3:
        run_judge = st.checkbox("LLM-as-Judge (8 Dimensions)", value=True)
    with col1:
        run = st.button("▶ Run Evaluation Suite", use_container_width=True)

    if not run:
        return

    from tests.eval_suite import run_all
    with st.spinner("Running scenarios, RAGAS scoring, and LLM-as-judge scoring..."):
        out = run_all(run_ragas=run_ragas, run_judge=run_judge)

    _render_functional_tests(out)
    if run_ragas:
        _render_ragas(out)
    if run_judge:
        _render_judge(out)

    st.subheader("Aggregate Metrics")
    st.json(out["metrics"])


def _render_functional_tests(out):
    st.subheader("Functional Tests")
    by_category = {cat: [] for cat in FUNCTIONAL_CATEGORIES}
    for r in out["results"]:
        by_category.setdefault(r.get("category", "Other"), []).append(r)

    for cat, rows in by_category.items():
        if not rows:
            continue
        passed = sum(1 for r in rows if r.get("passed"))
        st.markdown(f"**{cat}** — {passed}/{len(rows)} passed")
        for r in rows:
            status = "✅ PASS" if r.get("passed") else "❌ FAIL"
            with st.expander(f"{status} — Scenario {r['id']} [{r['layer']}]: {r['query']}"):
                st.write(r.get("description"))
                st.json({k: v for k, v in r.items() if k not in ("ragas", "judge")})


def _render_ragas(out):
    st.subheader("RAG Evaluation (RAGAS)")
    st.caption(
        "Context Precision, Context Recall, Faithfulness, and Answer Relevancy — computed "
        "with Aegis's own embedding model + failover LLM provider (no ground-truth answer "
        "set required)."
    )
    summary = out.get("ragas_summary") or {}
    if not summary:
        st.caption("No scenarios produced a scorable answer (all refused/out-of-corpus).")
        return

    cols = st.columns(len(RAGAS_METRICS))
    for col, (key, label) in zip(cols, RAGAS_METRICS):
        val = summary.get(key)
        col.metric(label, f"{val:.0%}" if val is not None else "N/A")

    rows = out.get("ragas_scores") or []
    if rows:
        df = pd.DataFrame(rows)[["id", "query"] + [k for k, _ in RAGAS_METRICS]]
        st.dataframe(df, use_container_width=True, hide_index=True)

        melted = df.melt(id_vars=["id", "query"], value_vars=[k for k, _ in RAGAS_METRICS],
                          var_name="metric", value_name="score")
        fig = px.bar(melted, x="query", y="score", color="metric", barmode="group",
                     title="RAGAS Scores by Scenario", range_y=[0, 1])
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)


def _render_judge(out):
    st.subheader("LLM-as-Judge (8 Dimensions)")
    st.caption(
        "Faithfulness, Completeness, Citation Quality, Governance Compliance, Safety, "
        "Correctness, Clarity, Helpfulness — each scored 0-10 by an LLM judge, including "
        "correct refusals/escalations."
    )
    summary = out.get("judge_summary") or {}
    if not summary:
        st.caption("No scenarios were scored (judge unavailable or all calls failed).")
        return

    st.metric("Overall Average", f"{summary.get('overall', 0)}/10")

    radar_df = pd.DataFrame({
        "dimension": [label for _, label in JUDGE_DIMENSIONS],
        "score": [summary.get(key) or 0 for key, _ in JUDGE_DIMENSIONS],
    })
    fig = px.line_polar(radar_df, r="score", theta="dimension", line_close=True, range_r=[0, 10],
                         title="Average Score per Dimension")
    fig.update_traces(fill="toself")
    fig.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

    rows = out.get("judge_scores") or []
    if rows:
        df = pd.DataFrame(rows)[["id", "query"] + [k for k, _ in JUDGE_DIMENSIONS] + ["overall"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
        with st.expander("Judge rationale per scenario"):
            for r in rows:
                st.markdown(f"**Scenario {r['id']}** ({r['query']}): {r.get('rationale', '')}")
