"""Audit Log -- enterprise-grade filterable table with per-record activity history."""
import json
import streamlit as st
from ui.components import data_table, empty_state, load_with_skeleton, render_record_timeline
from ui.insights import load_audit_df


def render():
    st.markdown('<div class="aegis-header">📋 Audit Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-subtitle">Complete record of every query executed through the Aegis workflow.</div>', unsafe_allow_html=True)

    df = load_with_skeleton(load_audit_df, n=3)
    if df is None:
        return
    if df.empty:
        empty_state("No queries logged yet.")
        return

    with st.expander("🔎 Filters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            topic_filter = st.multiselect("Topic", sorted(df["topic"].dropna().unique().tolist()))
        with c2:
            risk_filter = st.multiselect("Risk", sorted(df["risk"].dropna().unique().tolist()))
        with c3:
            owner_filter = st.multiselect("Owner", sorted(df["owner"].dropna().unique().tolist()))
        with c4:
            status_filter = st.multiselect("Approval Status", sorted(df["approval_status"].dropna().unique().tolist()))
        c5, c6 = st.columns(2)
        with c5:
            min_conf, max_conf = st.slider("Confidence range", 0, 100, (0, 100))
        with c6:
            search = st.text_input("Free-text search (question)")

    filtered = df.copy()
    if topic_filter:
        filtered = filtered[filtered["topic"].isin(topic_filter)]
    if risk_filter:
        filtered = filtered[filtered["risk"].isin(risk_filter)]
    if owner_filter:
        filtered = filtered[filtered["owner"].isin(owner_filter)]
    if status_filter:
        filtered = filtered[filtered["approval_status"].isin(status_filter)]
    filtered = filtered[(filtered["confidence"] >= min_conf) & (filtered["confidence"] <= max_conf)]
    if search:
        filtered = filtered[filtered["question"].str.contains(search, case=False, na=False)]

    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        st.download_button("⬇ Export CSV", filtered.drop(columns=["retrieved_documents", "retrieved_chunks", "citations"], errors="ignore").to_csv(index=False),
                            file_name="aegis_audit_log.csv", mime="text/csv")
    with c2:
        st.download_button("⬇ Export JSON", filtered.to_json(orient="records", indent=2), file_name="aegis_audit_log.json", mime="application/json")

    data_table(
        filtered.drop(columns=["retrieved_documents", "retrieved_chunks", "citations", "timestamp_dt", "date"], errors="ignore").to_dict("records"),
        columns=["timestamp", "question", "answer", "topic", "owner", "risk", "confidence", "escalated", "approval_status"],
        height=420,
    )

    st.markdown('<div class="section-title">🔍 View Record Details</div>', unsafe_allow_html=True)
    if filtered.empty:
        st.caption("No records match the current filters.")
        return

    options = {f"#{r['id']} · {r['timestamp']} · {r['question'][:50]}": r["id"] for _, r in filtered.iterrows()}
    choice = st.selectbox("Select a record", list(options.keys()))
    row_id = options[choice]
    record = filtered[filtered["id"] == row_id].iloc[0]

    with st.container():
        st.markdown('<div class="aegis-card">', unsafe_allow_html=True)
        st.write(f"**Question:** {record['question']}")
        st.write(f"**Answer:** {record['answer']}")
        st.write(f"**Topic:** {record['topic']} · **Owner:** {record['owner']} · **Risk:** {record['risk']} · **Confidence:** {record['confidence']}%")
        st.write(f"**Citations:** {', '.join(record['citations']) if record['citations'] else 'None'}")
        st.write(f"**Retrieved Documents:** {', '.join(record['retrieved_documents']) if record['retrieved_documents'] else 'None'}")
        st.markdown("**Activity Timeline**")
        render_record_timeline(record.to_dict())
        st.markdown("</div>", unsafe_allow_html=True)
