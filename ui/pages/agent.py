"""Compliance Agent page -- an enterprise analysis workspace, not a chat window."""
import streamlit as st
from agents.orchestrator import run_query_streaming
from ui.components import (
    render_response_report, render_agent_timeline, render_live_stage_progress,
    NODE_TO_STAGE, empty_state, insight_card,
)
from ui.insights import load_audit_df, suggest_related_documents, recent_high_risk_repeat
from tools.audit_logger import update_approval

SUGGESTED_PROMPTS = [
    "Retention policy", "GDPR", "Cross-border transfer", "Vendor onboarding",
    "AML", "KYC", "Sanctions", "Contracts",
]


def _init_state():
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("pending_reviews", {})
    st.session_state.setdefault("pinned_questions", [])
    st.session_state.setdefault("saved_responses", [])
    st.session_state.setdefault("recent_searches", [])


def _approve(row_id: int):
    state = st.session_state.pending_reviews.get(row_id)
    if not state:
        return
    update_approval(row_id, "Approved")
    state["final_answer"] = state["held_answer"]
    state["review_status"] = "Approved"
    del st.session_state.pending_reviews[row_id]


def _reject(row_id: int, reason: str, requested_changes: bool = False):
    state = st.session_state.pending_reviews.get(row_id)
    if not state:
        return
    status = "Changes Requested" if requested_changes else "Rejected"
    update_approval(row_id, status, reason)
    verb = "Changes were requested on" if requested_changes else "This advisory was rejected during"
    state["final_answer"] = f"{verb} human review and will not be released as-is. Comment: {reason}"
    state["review_status"] = status
    del st.session_state.pending_reviews[row_id]


def render():
    _init_state()
    st.markdown('<div class="aegis-header">💬 Compliance Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-subtitle">Ask a question; every request runs through the full LangGraph workflow.</div>', unsafe_allow_html=True)

    left, right = st.columns([1, 2.4])

    with left:
        st.markdown('<div class="section-title">🧠 Session Memory</div>', unsafe_allow_html=True)
        if st.session_state.chat_history and st.session_state.get("memory_enabled", True):
            last_state = st.session_state.chat_history[-1]["state"]
            st.caption(
                f"Topic: **{last_state.get('topic')}** · Owner: **{last_state.get('owner')}** · "
                f"Risk: **{last_state.get('risk')}** · Citations: **{len(last_state.get('citations', []))}**"
            )
        else:
            st.caption("No preserved context yet." if st.session_state.get("memory_enabled", True) else "Memory is turned off (see Settings).")

        st.markdown('<div class="section-title">🕘 Conversation History</div>', unsafe_allow_html=True)
        if not st.session_state.chat_history:
            empty_state("No conversation yet.", icon="💬")
        else:
            for turn in st.session_state.chat_history[-10:][::-1]:
                st.caption(f"• {turn['query'][:60]}")

        st.markdown('<div class="section-title">📌 Pinned Questions</div>', unsafe_allow_html=True)
        if not st.session_state.pinned_questions:
            st.caption("Pin a question from the response panel to keep it handy.")
        else:
            for q in st.session_state.pinned_questions:
                st.caption(f"📌 {q}")

        st.markdown('<div class="section-title">🔍 Recent Searches</div>', unsafe_allow_html=True)
        if not st.session_state.recent_searches:
            st.caption("No searches yet.")
        else:
            for q in st.session_state.recent_searches[-5:][::-1]:
                st.caption(q)

        st.markdown('<div class="section-title">💾 Saved Responses</div>', unsafe_allow_html=True)
        if not st.session_state.saved_responses:
            st.caption("No saved responses yet.")
        else:
            for s in st.session_state.saved_responses[-5:][::-1]:
                st.caption(f"✅ {s['query'][:50]}")

    with right:
        chip_html = '<div class="chip-row">' + "".join(f'<span class="chip">{c}</span>' for c in SUGGESTED_PROMPTS) + "</div>"
        st.markdown(chip_html, unsafe_allow_html=True)

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.button("📎 Attach Policy", disabled=True, help="Upload from the Knowledge Base page.", use_container_width=True)
        col_b.button("🎙️ Voice", disabled=True, help="Voice input coming soon.", use_container_width=True)
        col_c.button("🔎 Search Policies", disabled=True, help="Use Knowledge Base search.", use_container_width=True)
        if col_d.button("🧹 Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

        query = st.chat_input("Ask the Compliance Agent...")

        if query:
            st.session_state.recent_searches.append(query)
            memory_on = st.session_state.get("memory_enabled", True)
            history_ctx = [
                {"query": t["query"], "topic": t["state"]["topic"], "owner": t["state"]["owner"]}
                for t in st.session_state.chat_history
            ] if memory_on else []
            status_placeholder = st.empty()

            def on_step(node_name, partial_state):
                stage = NODE_TO_STAGE.get(node_name, 0)
                render_live_stage_progress(status_placeholder, stage + 1)

            render_live_stage_progress(status_placeholder, 0)
            state = run_query_streaming(query, history_ctx, on_step=on_step)
            status_placeholder.empty()

            st.session_state.chat_history.append({"query": query, "state": state})
            if state.get("review_status") == "Pending":
                st.session_state.pending_reviews[state["row_id"]] = state

        if not st.session_state.chat_history:
            empty_state("Ask a compliance question above to get started — e.g. \"What is the retention period for customer records?\"", icon="🛡️")

        for turn in st.session_state.chat_history[::-1]:
            state = turn["state"]
            st.markdown(f"**You:** {turn['query']}")

            if recent_high_risk_repeat(load_audit_df(), turn["query"], state.get("topic", "")) and state.get("risk") == "High":
                insight_card(f"A similar high-risk **{state.get('topic')}** question occurred recently — this may need consistent handling.", icon="⚠️")

            render_response_report(state)

            row_id = state.get("row_id")
            if state.get("review_status") == "Pending" and row_id in st.session_state.pending_reviews:
                st.markdown('<div class="aegis-card">', unsafe_allow_html=True)
                st.markdown("**⚠ Human Review Required**")
                st.caption(f"Status: Pending Approval · Assigned Reviewer: {state.get('owner')} · Risk: {state.get('risk')}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("✅ Approve", key=f"approve_{row_id}"):
                        _approve(row_id)
                        st.rerun()
                with c2:
                    if st.button("❌ Reject", key=f"reject_{row_id}"):
                        st.session_state[f"reject_mode_{row_id}"] = "reject"
                with c3:
                    if st.button("✏️ Request Changes", key=f"changes_{row_id}"):
                        st.session_state[f"reject_mode_{row_id}"] = "changes"
                mode = st.session_state.get(f"reject_mode_{row_id}")
                if mode:
                    reason = st.text_input("Reason / requested changes", key=f"reason_{row_id}")
                    if st.button("Confirm", key=f"confirm_{row_id}") and reason:
                        _reject(row_id, reason, requested_changes=(mode == "changes"))
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            citer_docs = {c["filename"] for c in state.get("retrieved_chunks", []) if c.get("qualifies")}
            related = suggest_related_documents(state.get("topic", ""), citer_docs)
            if related:
                insight_card("Related policies you may also want to review: " + ", ".join(related), icon="📎")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("📌 Pin this question", key=f"pin_{row_id}"):
                    st.session_state.pinned_questions.append(turn["query"])
            with b2:
                if st.button("💾 Save this response", key=f"save_{row_id}"):
                    st.session_state.saved_responses.append({"query": turn["query"], "answer": state.get("final_answer") or state.get("final_text")})

            st.markdown('<div class="section-title">🧭 Agent Timeline</div>', unsafe_allow_html=True)
            render_agent_timeline(state.get("trace", []))
            st.divider()
