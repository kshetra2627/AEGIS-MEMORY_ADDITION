"""Agent Workspace homepage -- NOT a chat landing page. A live operations dashboard."""
import os
from datetime import datetime
import streamlit as st

from ui.components import metric_card, insight_card, notification_card, empty_state, load_with_skeleton, system_health_card
from ui.insights import (
    load_audit_df, get_system_health, get_indexed_policy_stats, get_latest_corpus_update,
    get_compliance_owners, today_metrics, generate_ai_insights, recent_activity_feed,
)


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    if hour < 18:
        return "Good Afternoon"
    return "Good Evening"


def render():
    st.markdown('<div class="aegis-header">🛡️ Aegis</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-tagline">Enterprise AI Agent for Compliance Operations</div>', unsafe_allow_html=True)

    df = load_with_skeleton(load_audit_df, n=2)
    if df is None:
        return

    metrics = today_metrics(df)
    st.markdown(f'<div class="aegis-subtitle">{_greeting()}, Welcome back.</div>', unsafe_allow_html=True)
    if metrics["pending_reviews"] == 0 and metrics["high_risk"] == 0:
        st.caption("✅ Everything looks healthy today. No pending critical escalations.")

    st.markdown('<div class="section-title">Today\'s Status</div>', unsafe_allow_html=True)
    health = get_system_health(df)
    policy_stats = get_indexed_policy_stats()
    owners = get_compliance_owners()

    row1 = st.columns(5)
    with row1[0]:
        system_health_card(health["status"])
    with row1[1]:
        metric_card("🤖", health["last_provider"].capitalize() if health["last_provider"] != "none" else "None", "AI Provider")
    with row1[2]:
        metric_card("📚", policy_stats["documents"], "Indexed Policies", animate=True)
    with row1[3]:
        metric_card("🧭", len(owners), "Compliance Owners", animate=True)
    with row1[4]:
        metric_card("⏳", metrics["pending_reviews"], "Pending Reviews", animate=True)

    row2 = st.columns(5)
    with row2[0]:
        metric_card("💬", metrics["queries_today"], "Queries Today", animate=True)
    with row2[1]:
        metric_card("📊", metrics["avg_confidence"], "Average Confidence", animate=True, suffix="%")
    with row2[2]:
        metric_card("🔴", metrics["high_risk"], "High Risk Cases", animate=True)
    with row2[3]:
        metric_card("🛡️", metrics["governance_pass_rate"], "Governance Pass Rate", animate=True, suffix="%")
    with row2[4]:
        metric_card("🕒", get_latest_corpus_update(), "Latest Corpus Update")

    st.markdown('<div class="section-title">Quick Actions</div>', unsafe_allow_html=True)
    qa = st.columns(4)
    actions = [
        ("💬", "Ask Compliance Agent", "💬 Compliance Agent"),
        ("⚠️", "Review Pending Cases", "⚠️ Pending Reviews"),
        ("📋", "Audit Logs", "📋 Audit Logs"),
        ("📁", "Manage Knowledge Base", "📁 Knowledge Base"),
    ]
    for col, (icon, label, target) in zip(qa, actions):
        with col:
            st.markdown(f'<div class="quick-action"><div class="qa-icon">{icon}</div>{label}</div>', unsafe_allow_html=True)
            if st.button("Go", key=f"qa_{target}", use_container_width=True):
                st.session_state.nav_page = target
                st.rerun()

    col_left, col_right = st.columns([1.4, 1])
    with col_left:
        st.markdown('<div class="section-title">🧠 AI Insights</div>', unsafe_allow_html=True)
        insights = generate_ai_insights(df)
        for line in insights:
            insight_card(line)

        st.markdown('<div class="section-title">📰 Recent Activity</div>', unsafe_allow_html=True)
        feed = recent_activity_feed(df, n=8)
        if not feed:
            empty_state("No activity yet. Ask the Compliance Agent a question to get started.")
        else:
            for item in feed:
                icon = "⚠️" if item["escalated"] else "✅"
                st.markdown(
                    f'<div class="notif-card">{icon} <b>{item["question"][:70]}</b><br/>'
                    f'<span style="color:#8B93A7;font-size:0.78rem;">{item["time"]} · {item["topic"]} · {item["risk"]} risk</span></div>',
                    unsafe_allow_html=True,
                )

    with col_right:
        st.markdown('<div class="section-title">🔔 Notification Center</div>', unsafe_allow_html=True)
        # Dedup on record id (not question text) -- two different queries can share
        # wording and both deserve a notification; the same row must only appear once.
        pending = df[df["approval_status"] == "Pending"].drop_duplicates(subset=["id"]) if not df.empty else df
        if not df.empty and len(pending) > 0:
            for _, r in pending.iterrows():
                notification_card(f"Pending review: <b>{r['question'][:50]}</b> ({r['owner']})", "⚠️")
        else:
            notification_card("No pending reviews.", "✅")

        recent_docs = _recently_indexed()
        for d in recent_docs:
            notification_card(f"Newly indexed: <b>{d}</b>", "📄")
        if not recent_docs:
            notification_card("No new documents indexed in the last 24 hours.", "📁")


def _recently_indexed(hours: int = 24) -> list[str]:
    folder = os.path.join("data", "policies")
    if not os.path.isdir(folder):
        return []
    cutoff = datetime.now().timestamp() - hours * 3600
    recent = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and os.path.getmtime(path) >= cutoff:
            recent.append(name)
    return recent
