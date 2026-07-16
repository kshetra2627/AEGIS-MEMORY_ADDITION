"""Analytics -- fully dynamic metrics and charts computed from the audit log."""
import re
import streamlit as st
import plotly.express as px
from ui.components import metric_card, empty_state, load_with_skeleton
from ui.insights import load_audit_df
from agents.governance_agent import REFUSAL_MESSAGE

PLOTLY_LAYOUT = dict(paper_bgcolor="#131A2A", plot_bgcolor="#131A2A", font_color="#E5E9F0")


def render():
    st.markdown('<div class="aegis-header">📊 Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-subtitle">Operational metrics across every query the agent has handled.</div>', unsafe_allow_html=True)

    df = load_with_skeleton(load_audit_df, n=3)
    if df is None:
        return
    if df.empty:
        empty_state("No queries logged yet -- analytics will populate as the agent is used.")
        return

    from datetime import date
    today_df = df[df["date"] == date.today()]

    routing_accuracy = round((df["owner"] != "Compliance Manager").mean() * 100, 1)
    escalation_rate = round(df["escalated"].mean() * 100, 1)
    refused = df["answer"].fillna("").str.contains(re.escape(REFUSAL_MESSAGE[:40]))
    governance_pass_rate = round((1 - refused.mean()) * 100, 1)
    avg_latency = round(df["total_latency"].mean(), 2) if "total_latency" in df else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        metric_card("💬", len(today_df), "Queries Today", animate=True)
    with c2:
        metric_card("📊", round(df["confidence"].mean(), 1), "Average Confidence", animate=True, suffix="%")
    with c3:
        metric_card("🧭", routing_accuracy, "Routing Accuracy", animate=True, suffix="%")
    with c4:
        metric_card("⚠️", escalation_rate, "Escalation Rate", animate=True, suffix="%")
    with c5:
        metric_card("🛡️", governance_pass_rate, "Governance Pass Rate", animate=True, suffix="%")
    with c6:
        metric_card("⏱️", avg_latency, "Avg Latency", animate=True, suffix="s")

    row1 = st.columns(2)
    with row1[0]:
        counts = df["risk"].value_counts().reset_index()
        counts.columns = ["risk", "count"]
        fig = px.pie(counts, names="risk", values="count", title="Risk Distribution",
                     color="risk", color_discrete_map={"Low": "#22C55E", "Medium": "#F59E0B", "High": "#EF4444", "N/A": "#8B93A7"})
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    with row1[1]:
        counts = df["topic"].value_counts().reset_index()
        counts.columns = ["topic", "count"]
        fig = px.pie(counts, names="topic", values="count", title="Topic Distribution")
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    row2 = st.columns(2)
    with row2[0]:
        counts = df["llm_provider"].value_counts().reset_index()
        counts.columns = ["provider", "count"]
        fig = px.bar(counts, x="provider", y="count", title="Provider Usage")
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    with row2[1]:
        trend = df.sort_values("timestamp_dt")
        fig = px.line(trend, x="timestamp_dt", y="confidence", title="Confidence Trend")
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    row3 = st.columns(2)
    with row3[0]:
        trend = df.sort_values("timestamp_dt")
        fig = px.line(trend, x="timestamp_dt", y="total_latency", title="Latency Trend")
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    with row3[1]:
        esc = df[df["escalated"] == 1].groupby("date").size().reset_index(name="escalations")
        if esc.empty:
            st.caption("No escalations yet.")
        else:
            fig = px.bar(esc, x="date", y="escalations", title="Escalations Over Time")
            fig.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

    row4 = st.columns(2)
    with row4[0]:
        counts = df["owner"].value_counts().reset_index()
        counts.columns = ["owner", "count"]
        fig = px.bar(counts, x="owner", y="count", title="Queries Per Department (Owner)")
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    with row4[1]:
        doc_counts = {}
        for docs in df["retrieved_documents"]:
            for d in docs or []:
                doc_counts[d] = doc_counts.get(d, 0) + 1
        if not doc_counts:
            st.caption("No documents retrieved yet.")
        else:
            import pandas as pd
            doc_df = pd.DataFrame(sorted(doc_counts.items(), key=lambda x: -x[1])[:10], columns=["document", "retrievals"])
            fig = px.bar(doc_df, x="retrievals", y="document", orientation="h", title="Most Retrieved Policies")
            fig.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
