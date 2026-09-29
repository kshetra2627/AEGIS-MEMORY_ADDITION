"""Compliance Agent page -- an enterprise analysis workspace, not a chat window.

T8b: Added "Correct this result" expander on every completed answer.
     Captures actual owner/risk/reason inputs and calls retain_correction().
     Works whether memory is enabled or not.

T9:  Memory ON/OFF toggle (sidebar).
     Recalled Memory card showing real memory_context from the Hindsight path.
     Memory Trace panel (Policy grounding | Memory context side by side).
     Compare mode button that runs the same query twice (retain=False) and
     renders both columns — no fabricated comparison results.
"""
import streamlit as st
from agents.orchestrator import run_query_streaming
from ui.components import (
    render_response_report, render_agent_timeline, render_live_stage_progress,
    NODE_TO_STAGE, empty_state, insight_card,
)
from ui.insights import load_audit_df, suggest_related_documents, recent_high_risk_repeat
from tools.audit_logger import update_approval
from agents.router import OWNER_MAP

SUGGESTED_PROMPTS = [
    "Retention policy", "GDPR", "Cross-border transfer", "Vendor onboarding",
    "AML", "KYC", "Sanctions", "Contracts",
]

_ALL_OWNERS = sorted(set(OWNER_MAP.values()) | {"Compliance Manager", "Legal", "HR Compliance"})
_RISK_LEVELS = ["Low", "Medium", "High"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _init_state():
    # Scope per-user session state: each authenticated user gets their own history.
    from ui.auth import get_current_user, load_user_data
    current_user = get_current_user()
    user_id = current_user["user_id"] if current_user else "anonymous"

    # If the user changed since last run, reset conversation data and reload from DB.
    if st.session_state.get("_agent_user_id") != user_id:
        for key in ("chat_history", "pinned_questions", "saved_responses", "recent_searches"):
            st.session_state.pop(key, None)
        st.session_state["_agent_user_id"] = user_id
        # Load persisted data for the (new) user from the database.
        if user_id != "anonymous":
            stored = load_user_data(user_id)
            for key, value in stored.items():
                if value:  # only overwrite if the DB actually has data
                    st.session_state[key] = value

    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("pending_reviews", {})
    st.session_state.setdefault("pinned_questions", [])
    st.session_state.setdefault("saved_responses", [])
    st.session_state.setdefault("recent_searches", [])
    # T9: memory toggle — default reads from hindsight_client.is_enabled()
    # NOTE: app.py owns the st.toggle(key="memory_toggle") widget.  Once that
    # widget is instantiated, Streamlit forbids writing to session_state["memory_toggle"]
    # directly (StreamlitAPIException).  We must only READ from it here and sync
    # memory_enabled accordingly.  We never write to memory_toggle from this function.
    if "memory_toggle" not in st.session_state and "memory_enabled" not in st.session_state:
        # First ever run before the widget exists — safe to set the default.
        try:
            from memory.hindsight_client import is_enabled
            st.session_state["memory_toggle"] = is_enabled()
        except Exception:
            st.session_state["memory_toggle"] = False
    # Always sync memory_enabled FROM memory_toggle (widget is source of truth).
    st.session_state["memory_enabled"] = bool(st.session_state.get("memory_toggle", False))


def _persist(key: str) -> None:
    """Write one session-state list to the per-user persistent store.

    No-ops silently when the user is not authenticated or save_user_data fails.
    """
    from ui.auth import get_current_user, save_user_data
    current_user = get_current_user()
    if not current_user:
        return
    user_id = current_user["user_id"]
    save_user_data(user_id, key, st.session_state.get(key, []))


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


def _do_retain_correction(state, corrected_owner, corrected_risk, reason):
    """Call retain_correction with the actual user inputs. No-ops when memory disabled."""
    try:
        from memory.service import retain_correction
        retain_correction(state, corrected_owner, corrected_risk, reason)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("retain_correction failed: %s", exc)


# ---------------------------------------------------------------------------
# T9: Recalled Memory card
# ---------------------------------------------------------------------------

def _render_memory_card(state: dict, turn_key):
    """Display real recalled memories from state["memory_context"].

    Shows nothing when memory is disabled or no memories were recalled.
    All data originates from the Hindsight recall result stored in state.
    turn_key is a per-turn unique identifier used for Streamlit widget keys.
    """
    memory_context = state.get("memory_context", [])
    memory_ok = state.get("memory_ok")
    memory_enabled = state.get("memory_enabled", False)
    latency_ms = state.get("memory_latency_ms", 0)

    if not memory_enabled:
        return  # Memory is OFF — no card shown

    with st.expander("🧠 Recalled Organisational Memory", expanded=bool(memory_context), key=f"expander_mem_{turn_key}"):
        if not memory_context:
            if memory_ok is False:
                err = state.get("memory_error", "")
                st.caption(f"Memory unavailable: {err}" if err else "Memory unavailable.")
            else:
                st.caption("No similar past cases found.")
            return

        st.caption(
            f"{len(memory_context)} similar past case(s) recalled · "
            f"Recall latency: {latency_ms} ms"
        )
        for item_idx, item in enumerate(memory_context):
            item_id = item.get("id", "unknown")
            item_date = item.get("date") or "unknown date"
            item_type = item.get("type") or "unknown"
            item_text = item.get("text", "")
            # Extract first QUESTION: or REASON: line for the card summary.
            summary = _extract_summary(item_text)
            score = item.get("score")
            score_str = f" · similarity {round(score * 100, 1)}%" if score else ""

            st.markdown(
                f"**[Memory {item_id[:12]}...]** &nbsp; `{item_date}` &nbsp; `{item_type}`{score_str}"
            )
            st.caption(summary)
            with st.expander(f"Full memory text — {item_id[:16]}...", expanded=False, key=f"expander_memtext_{turn_key}_{item_idx}"):
                st.text(item_text)
            st.divider()


def _extract_summary(text: str) -> str:
    """Return the first QUESTION: or REASON: value from a memory text, or first line."""
    import re
    for key in ("QUESTION", "REASON", "REFUSAL_REASON", "FINDING"):
        m = re.search(r"^" + key + r"\s*:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            return val[:200] + "..." if len(val) > 200 else val
    first = next((l.strip() for l in text.splitlines() if l.strip()), "(no text)")
    return first[:200]


# ---------------------------------------------------------------------------
# T9: Memory Trace panel (Policy grounding | Memory context)
# ---------------------------------------------------------------------------

def _render_memory_trace(state: dict, turn_key):
    """Side-by-side panel: Policy (grounding) on the left, Memory (context) on the right.
    turn_key is a per-turn unique identifier used for Streamlit widget keys.
    """
    memory_enabled = state.get("memory_enabled", False)
    memory_context = state.get("memory_context", [])
    chunks = state.get("retrieved_chunks", [])
    qualifying = [c for c in chunks if c.get("qualifies")]

    with st.expander("📊 Memory Trace — Policy (grounding) vs Memory (context)", expanded=False, key=f"expander_trace_{turn_key}"):
        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown("**📄 Policy — Grounding**")
            st.caption("Factual compliance claims must cite these chunks.")
            if qualifying:
                for c in qualifying:
                    st.markdown(
                        f"- `[Chunk {c['chunk_id']}]` · {round(c['score']*100,1)}% similarity  \n"
                        f"  {c.get('title','')}, p.{c.get('page','')} — {c.get('clause','')[:60] if c.get('clause') else ''}"
                    )
            else:
                st.caption("No qualifying chunks retrieved.")

        with right_col:
            st.markdown("**🧠 Memory — Context**")
            st.caption("Supplementary precedent only. Cannot replace [Chunk] citations.")
            if not memory_enabled:
                st.caption("Memory is OFF.")
            elif memory_context:
                for item in memory_context:
                    item_id = item.get("id", "")
                    item_date = item.get("date") or ""
                    item_type = item.get("type") or ""
                    summary = _extract_summary(item.get("text", ""))[:100]
                    st.markdown(f"- `[Memory {item_id[:12]}...]` · {item_date} · {item_type}  \n  {summary}")
            else:
                st.caption("No similar past cases recalled.")


# ---------------------------------------------------------------------------
# T9: Compare mode (memory OFF vs ON)
# ---------------------------------------------------------------------------

def _render_compare(query: str, chat_history: list, row_id):
    """Run the same query twice (retain=False) and render results side by side.

    The two columns show the actual query results — no fabricated answers.
    row_id is used to namespace Streamlit widget keys so multiple turns on the
    same page do not produce StreamlitDuplicateElementKey errors.
    """
    st.markdown("---")
    st.markdown("### Compare: Memory OFF vs Memory ON")

    # Keys are namespaced by row_id so each turn gets its own independent widgets.
    btn_key = f"compare_run_{row_id}"
    off_key = f"compare_off_{row_id}"
    on_key = f"compare_on_{row_id}"

    if st.button("▶ Run Comparison", key=btn_key):
        with st.spinner("Running query without memory..."):
            state_off = run_query_streaming(
                query, chat_history, memory_enabled=False, retain=False
            )
        with st.spinner("Running query with memory..."):
            state_on = run_query_streaming(
                query, chat_history, memory_enabled=True, retain=False
            )
        st.session_state[off_key] = state_off
        st.session_state[on_key] = state_on

    state_off = st.session_state.get(off_key)
    state_on = st.session_state.get(on_key)

    if state_off is None or state_on is None:
        st.caption("Click the button above to run the comparison.")
        return

    col_off, col_on = st.columns(2)

    with col_off:
        st.markdown("#### MEMORY OFF")
        _render_compare_column(state_off, memory_label="No prior context", col_key=f"{row_id}_off")

    with col_on:
        st.markdown("#### MEMORY ON")
        memory_items = state_on.get("memory_context", [])
        mem_label = f"{len(memory_items)} similar case(s) recalled" if memory_items else "No similar cases recalled"
        _render_compare_column(state_on, memory_label=mem_label, col_key=f"{row_id}_on")

    # "Why did memory change this?" section — derived from actual state differences.
    _render_compare_diff(state_off, state_on)


def _render_compare_column(state: dict, memory_label: str, col_key: str = ""):
    owner = state.get("owner", "N/A")
    risk = state.get("risk", "N/A")
    gov_passed = state.get("governance_passed", False)
    answer = state.get("final_answer") or state.get("final_text", "")

    st.markdown(f"**Owner:** {owner}")
    st.markdown(f"**Risk:** {risk}")
    st.markdown(f"**Governance:** {'Passed' if gov_passed else 'Refused'}")
    st.caption(memory_label)
    expander_key = f"expander_cmp_answer_{col_key}" if col_key else None
    with st.expander("Answer", expanded=False, key=expander_key):
        st.write(answer[:600] + "..." if len(answer) > 600 else answer or "_No answer generated._")


def _render_compare_diff(state_off: dict, state_on: dict):
    """Show differences attributable to memory — from real state values only."""
    memory_items = state_on.get("memory_context", [])
    if not memory_items:
        st.caption("Memory was enabled but no past cases were recalled — results may be identical.")
        return

    st.markdown("---")
    st.markdown("**Why did memory change this?**")
    for item in memory_items:
        item_type = item.get("type", "unknown")
        item_date = item.get("date") or "unknown date"
        summary = _extract_summary(item.get("text", ""))
        st.markdown(f"- **{item_type}** ({item_date}): {summary[:150]}")

    # Highlight owner/risk differences if they exist.
    owner_off = state_off.get("owner", "")
    owner_on = state_on.get("owner", "")
    risk_off = state_off.get("risk", "")
    risk_on = state_on.get("risk", "")
    if owner_off != owner_on:
        st.markdown(f"- Owner changed: **{owner_off}** → **{owner_on}**")
    if risk_off != risk_on:
        st.markdown(f"- Risk changed: **{risk_off}** → **{risk_on}**")
    if owner_off == owner_on and risk_off == risk_on:
        st.caption("Owner and risk are the same — memory provided contextual grounding but did not change the routing/risk (learned routing/risk adjustment lands in T10/T11).")


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render():
    _init_state()

    st.markdown('<div class="aegis-header">💬 Compliance Agent</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="aegis-subtitle">Ask a question; every request runs through the full LangGraph workflow.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 2.4])

    with left:
        st.markdown('<div class="section-title">🧠 Session Memory</div>', unsafe_allow_html=True)
        if st.session_state.chat_history and st.session_state.get("memory_toggle", False):
            last_state = st.session_state.chat_history[-1]["state"]
            st.caption(
                f"Topic: **{last_state.get('topic')}** · Owner: **{last_state.get('owner')}** · "
                f"Risk: **{last_state.get('risk')}** · Citations: **{len(last_state.get('citations', []))}**"
            )
        else:
            st.caption(
                "No preserved context yet."
                if not st.session_state.get("memory_toggle", False)
                else "No conversation yet."
            )

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
        chip_html = (
            '<div class="chip-row">'
            + "".join(f'<span class="chip">{c}</span>' for c in SUGGESTED_PROMPTS)
            + "</div>"
        )
        st.markdown(chip_html, unsafe_allow_html=True)

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.button("📎 Attach Policy", disabled=True, help="Upload from the Knowledge Base page.", use_container_width=True)
        col_b.button("🎙️ Voice", disabled=True, help="Voice input coming soon.", use_container_width=True)
        col_c.button("🔎 Search Policies", disabled=True, help="Use Knowledge Base search.", use_container_width=True)
        if col_d.button("🧹 Clear", use_container_width=True):
            st.session_state.chat_history = []
            _persist("chat_history")
            st.rerun()

        query = st.chat_input("Ask the Compliance Agent...")

        if query:
            st.session_state.recent_searches.append(query)
            _persist("recent_searches")
            # T9: pass the actual toggle value to the orchestrator.
            memory_on = st.session_state.get("memory_toggle", False)
            history_ctx = (
                [
                    {"query": t["query"], "topic": t["state"]["topic"], "owner": t["state"]["owner"]}
                    for t in st.session_state.chat_history
                ]
                if memory_on
                else []
            )
            status_placeholder = st.empty()

            def on_step(node_name, partial_state):
                stage = NODE_TO_STAGE.get(node_name, 0)
                render_live_stage_progress(status_placeholder, stage + 1)

            render_live_stage_progress(status_placeholder, 0)
            # Inject the real authenticated user_id so audit logs and memory retention
            # are correctly attributed.  Falls back to "anonymous" only if somehow
            # called outside an authenticated session.
            from ui.auth import get_current_user as _get_user
            _cur = _get_user()
            _uid = _cur["user_id"] if _cur else "anonymous"
            _role = _cur["role"] if _cur else "compliance_officer"
            # T9: memory_enabled drives actual orchestrator behavior, not just UI state.
            state = run_query_streaming(
                query,
                history_ctx,
                on_step=on_step,
                memory_enabled=memory_on,
                user_id=_uid,
                user_role=_role,
            )
            status_placeholder.empty()

            st.session_state.chat_history.append({"query": query, "state": state})
            _persist("chat_history")
            if state.get("review_status") == "Pending":
                st.session_state.pending_reviews[state["row_id"]] = state

        if not st.session_state.chat_history:
            empty_state(
                'Ask a compliance question above to get started — e.g. "What is the retention period for customer records?"',
                icon="🛡️",
            )

        for turn_idx, turn in enumerate(st.session_state.chat_history[::-1]):
            state = turn["state"]
            query_text = turn["query"]
            row_id = state.get("row_id")
            # turn_key is guaranteed unique per loop iteration even when row_id is None
            # (governance refusals are not logged to the audit DB so row_id stays None).
            turn_key = row_id if row_id is not None else f"t{turn_idx}"
            st.markdown(f"**You:** {query_text}")

            if (
                recent_high_risk_repeat(load_audit_df(), query_text, state.get("topic", ""))
                and state.get("risk") == "High"
            ):
                insight_card(
                    f"A similar high-risk **{state.get('topic')}** question occurred recently — this may need consistent handling.",
                    icon="⚠️",
                )

            render_response_report(state)

            # T9: Recalled Memory card — data from real state["memory_context"].
            _render_memory_card(state, turn_key)

            # T9: Memory Trace panel.
            _render_memory_trace(state, turn_key)

            # Inline review gate (High-risk answers in-session).
            if state.get("review_status") == "Pending" and row_id in st.session_state.pending_reviews:
                st.markdown('<div class="aegis-card">', unsafe_allow_html=True)
                st.markdown("**⚠ Human Review Required**")
                st.caption(
                    f"Status: Pending Approval · Assigned Reviewer: {state.get('owner')} · Risk: {state.get('risk')}"
                )
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("✅ Approve", key=f"approve_{turn_key}"):
                        _approve(row_id)
                        st.rerun()
                with c2:
                    if st.button("❌ Reject", key=f"reject_{turn_key}"):
                        st.session_state[f"reject_mode_{turn_key}"] = "reject"
                with c3:
                    if st.button("✏️ Request Changes", key=f"changes_{turn_key}"):
                        st.session_state[f"reject_mode_{turn_key}"] = "changes"
                mode = st.session_state.get(f"reject_mode_{turn_key}")
                if mode:
                    reason = st.text_input("Reason / requested changes", key=f"reason_{turn_key}")
                    if st.button("Confirm", key=f"confirm_{turn_key}") and reason:
                        _reject(row_id, reason, requested_changes=(mode == "changes"))
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # T8b: "Correct this result" expander — available on any completed answer.
            # Only shown after the answer is finalized (not while awaiting review).
            if state.get("review_status") != "Pending":
                with st.expander("✏️ Correct this result", expanded=False, key=f"expander_correct_{turn_key}"):
                    st.caption(
                        "If this answer has an incorrect owner or risk level, submit a correction. "
                        "Corrections are retained in organisational memory to improve future answers."
                    )
                    corr_key = f"corr_{turn_key}"
                    col_co, col_cr = st.columns(2)
                    with col_co:
                        corr_owner = st.selectbox(
                            "Correct owner",
                            options=_ALL_OWNERS,
                            index=_ALL_OWNERS.index(state.get("owner", ""))
                            if state.get("owner", "") in _ALL_OWNERS
                            else 0,
                            key=f"{corr_key}_owner",
                        )
                    with col_cr:
                        corr_risk = st.selectbox(
                            "Correct risk",
                            options=_RISK_LEVELS,
                            index=_RISK_LEVELS.index(state.get("risk", "Low"))
                            if state.get("risk", "Low") in _RISK_LEVELS
                            else 0,
                            key=f"{corr_key}_risk",
                        )
                    corr_reason = st.text_area(
                        "Reason for correction",
                        key=f"{corr_key}_reason",
                        placeholder="Explain why this correction is needed...",
                        height=70,
                    )
                    if st.button("Submit Correction", key=f"{corr_key}_submit"):
                        if corr_reason.strip():
                            _do_retain_correction(state, corr_owner, corr_risk, corr_reason)
                            st.success(
                                f"Correction retained: owner={corr_owner}, risk={corr_risk}. "
                                "Future similar queries will benefit from this correction."
                            )
                        else:
                            st.warning("Please provide a reason for the correction.")

            # T9: Compare mode button.
            chat_hist_for_compare = [
                {"query": t["query"], "topic": t["state"]["topic"], "owner": t["state"]["owner"]}
                for t in st.session_state.chat_history
                if t["query"] != query_text
            ]
            with st.expander("⚖️ Compare: Memory OFF vs Memory ON", expanded=False, key=f"expander_compare_{turn_key}"):
                _render_compare(query_text, chat_hist_for_compare, turn_key)

            citer_docs = {c["filename"] for c in state.get("retrieved_chunks", []) if c.get("qualifies")}
            related = suggest_related_documents(state.get("topic", ""), citer_docs)
            if related:
                insight_card(
                    "Related policies you may also want to review: " + ", ".join(related),
                    icon="📎",
                )

            b1, b2 = st.columns(2)
            with b1:
                if st.button("📌 Pin this question", key=f"pin_{turn_key}"):
                    st.session_state.pinned_questions.append(query_text)
                    _persist("pinned_questions")
            with b2:
                if st.button("💾 Save this response", key=f"save_{turn_key}"):
                    st.session_state.saved_responses.append(
                        {
                            "query": query_text,
                            "answer": state.get("final_answer") or state.get("final_text"),
                        }
                    )
                    _persist("saved_responses")

            st.markdown('<div class="section-title">🧭 Agent Timeline</div>', unsafe_allow_html=True)
            render_agent_timeline(state.get("trace", []))
            st.divider()
