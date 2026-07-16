"""Pending Reviews -- human review gate for every High-risk query, independent of session."""
import streamlit as st
from ui.components import risk_badge, owner_pill, empty_state, load_with_skeleton
from ui.insights import load_audit_df
from tools.audit_logger import update_approval


def render():
    st.markdown('<div class="aegis-header">⚠️ Pending Reviews</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-subtitle">High-risk advisories held for human approval before release.</div>', unsafe_allow_html=True)

    df = load_with_skeleton(load_audit_df, n=2)
    if df is None:
        return
    if df.empty:
        empty_state("No queries logged yet.")
        return

    pending = df[df["approval_status"] == "Pending"]
    if pending.empty:
        empty_state("Everything looks healthy today. No pending critical escalations.")
        return

    for _, row in pending.iterrows():
        st.markdown('<div class="aegis-card">', unsafe_allow_html=True)
        st.markdown("**⚠ Human Review Required**")
        st.write(f"**Question:** {row['question']}")
        st.markdown(risk_badge(row["risk"]) + owner_pill(row["owner"]), unsafe_allow_html=True)
        st.caption(f"Status: Pending Approval · Assigned Reviewer: {row['owner']} · Logged: {row['timestamp']}")

        with st.expander("Preview drafted advisory (hidden from requester until approved)"):
            st.markdown(row["answer"] or "_No draft available._")

        row_id = row["id"]
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✅ Approve", key=f"pr_approve_{row_id}"):
                update_approval(int(row_id), "Approved")
                st.rerun()
        with c2:
            if st.button("❌ Reject", key=f"pr_reject_{row_id}"):
                st.session_state[f"pr_mode_{row_id}"] = "reject"
        with c3:
            if st.button("✏️ Request Changes", key=f"pr_changes_{row_id}"):
                st.session_state[f"pr_mode_{row_id}"] = "changes"

        mode = st.session_state.get(f"pr_mode_{row_id}")
        if mode:
            reason = st.text_input("Reason / requested changes", key=f"pr_reason_{row_id}")
            if st.button("Confirm", key=f"pr_confirm_{row_id}") and reason:
                status = "Changes Requested" if mode == "changes" else "Rejected"
                update_approval(int(row_id), status, reason)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
