"""Pending Reviews -- human review gate for every High-risk query, independent of session.

T8a: Added optional corrected owner, corrected risk, and reason inputs.
     On submit, calls retain_review() with the real reviewer inputs so the
     decision is stored in Hindsight for future recall.
     If memory is disabled, the existing approval workflow still works unchanged.
"""
import streamlit as st
from ui.components import risk_badge, owner_pill, empty_state, load_with_skeleton
from ui.insights import load_audit_df
from tools.audit_logger import update_approval
from agents.router import OWNER_MAP

# All owner values available for correction dropdown.
_ALL_OWNERS = sorted(set(OWNER_MAP.values()) | {"Compliance Manager", "Legal", "HR Compliance"})
_RISK_LEVELS = ["Low", "Medium", "High"]


def _do_retain_review(row_id, decision, reason, corrected_owner, corrected_risk, row):
    """Call retain_review with the real reviewer inputs.  No-ops silently when memory
    is disabled; any error is logged but never surfaces to the reviewer UI."""
    try:
        from memory.service import retain_review
        # Reconstruct minimal state from the audit row so retain_review has context.
        state = {
            "query": row.get("question", ""),
            "topic": row.get("topic", "Unknown"),
            "owner": row.get("owner", "Unknown"),
            "risk": row.get("risk", "Unknown"),
        }
        retain_review(
            row_id=int(row_id),
            decision=decision,
            reason=reason or "",
            corrected_owner=corrected_owner if corrected_owner else None,
            corrected_risk=corrected_risk if corrected_risk else None,
            state=state,
        )
    except Exception as exc:
        # Memory failures must never block the review workflow.
        import logging
        logging.getLogger(__name__).warning("retain_review failed: %s", exc)


def render():
    st.markdown('<div class="aegis-header">⚠️ Pending Reviews</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="aegis-subtitle">High-risk advisories held for human approval before release.</div>',
        unsafe_allow_html=True,
    )

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
        st.caption(
            f"Status: Pending Approval · Assigned Reviewer: {row['owner']} · Logged: {row['timestamp']}"
        )

        with st.expander("Preview drafted advisory (hidden from requester until approved)"):
            st.markdown(row["answer"] or "_No draft available._")

        row_id = row["id"]

        # T8a: Review inputs — reason, corrected owner, corrected risk.
        # These are optional; if left blank the review records the decision only.
        with st.expander("Review inputs (optional: correct owner / risk)", expanded=False):
            pr_reason = st.text_area(
                "Reviewer notes / reason",
                key=f"pr_reason_text_{row_id}",
                placeholder="Explain the decision or requested changes...",
                height=80,
            )
            col_o, col_r = st.columns(2)
            with col_o:
                pr_corrected_owner = st.selectbox(
                    "Correct owner (leave blank if unchanged)",
                    options=[""] + _ALL_OWNERS,
                    key=f"pr_corr_owner_{row_id}",
                )
            with col_r:
                pr_corrected_risk = st.selectbox(
                    "Correct risk (leave blank if unchanged)",
                    options=[""] + _RISK_LEVELS,
                    key=f"pr_corr_risk_{row_id}",
                )

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✅ Approve", key=f"pr_approve_{row_id}"):
                reason = st.session_state.get(f"pr_reason_text_{row_id}", "")
                corrected_owner = st.session_state.get(f"pr_corr_owner_{row_id}", "") or None
                corrected_risk = st.session_state.get(f"pr_corr_risk_{row_id}", "") or None
                update_approval(int(row_id), "Approved", reason or None)
                _do_retain_review(row_id, "approve", reason, corrected_owner, corrected_risk, row)
                st.rerun()
        with c2:
            if st.button("❌ Reject", key=f"pr_reject_{row_id}"):
                st.session_state[f"pr_mode_{row_id}"] = "reject"
        with c3:
            if st.button("✏️ Request Changes", key=f"pr_changes_{row_id}"):
                st.session_state[f"pr_mode_{row_id}"] = "changes"

        mode = st.session_state.get(f"pr_mode_{row_id}")
        if mode:
            confirm_reason = st.text_input(
                "Reason / requested changes (required)",
                key=f"pr_confirm_reason_{row_id}",
            )
            if st.button("Confirm", key=f"pr_confirm_{row_id}") and confirm_reason:
                status = "Changes Requested" if mode == "changes" else "Rejected"
                decision_str = "request_changes" if mode == "changes" else "reject"
                corrected_owner = st.session_state.get(f"pr_corr_owner_{row_id}", "") or None
                corrected_risk = st.session_state.get(f"pr_corr_risk_{row_id}", "") or None
                update_approval(int(row_id), status, confirm_reason)
                _do_retain_review(row_id, decision_str, confirm_reason, corrected_owner, corrected_risk, row)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
