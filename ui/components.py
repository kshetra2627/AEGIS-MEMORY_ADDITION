"""Reusable UI component library -- built once, used across every page.
MetricCard, RiskBadge, StatusIndicator, DataTable, SkeletonLoader, EvidenceCard,
TimelineNode, InsightCard, plus the agent response report and timeline renderers.
"""
import html as _html
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from ui.styles import risk_pill, owner_pill, confidence_pill, status_dot

NODE_LABELS = {
    "Query Classification": "Classification",
    "Topic Routing": "Routing",
    "RAG Retrieval": "Retrieval",
    "Context Validation": "Validation",
    "Compliance Reasoning": "Compliance Analysis",
    "Citation Generation": "Citation Generation",
    "Confidence Calculation": "Confidence",
    "Governance Validation": "Governance",
    "Risk Classification": "Risk Classification",
    "Human Review Gate": "Human Review",
    "Audit Logging": "Audit Logging",
}

STATUS_CLASS = {
    "in-domain": "success", "out-of-domain": "skipped",
    "PASSED": "success", "REFUSED": "failed",
    "AWAITING APPROVAL": "skipped", "auto-finalized": "success",
    "skipped": "skipped", "logged": "success",
}


# ---------------------------------------------------------------- MetricCard
def metric_card(icon: str, value, label: str, animate: bool = False, suffix: str = ""):
    if animate and isinstance(value, (int, float)):
        _animated_metric(icon, value, label, suffix)
    else:
        st.markdown(
            f'<div class="metric-card" style="min-height:150px;display:flex;flex-direction:column;justify-content:center;">'
            f'<div class="metric-icon">{icon}</div>'
            f'<div class="metric-value">{value}{suffix}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )


def _animated_metric(icon: str, value: float, label: str, suffix: str = ""):
    uid = f"m{abs(hash(label + str(value)))}"
    # Height must fit a two-line label -- this card previously used a fixed 110px iframe,
    # which clipped labels like "Compliance Owners" / "Governance Pass Rate" mid-word.
    components.html(
        f"""
        <div style="font-family:Inter,system-ui,sans-serif;background:linear-gradient(160deg,rgba(19,26,42,0.95),rgba(15,20,33,0.9));
                    border:1px solid #232B3D;border-radius:14px;padding:1.1rem 1rem;text-align:center;
                    box-sizing:border-box;height:150px;display:flex;flex-direction:column;justify-content:center;">
            <div style="font-size:1.3rem;margin-bottom:0.2rem;">{icon}</div>
            <div id="{uid}" style="font-size:1.9rem;font-weight:800;color:#3B82F6;line-height:1.2;">0{suffix}</div>
            <div style="color:#8B93A7;font-size:0.8rem;margin-top:0.3rem;line-height:1.3;word-wrap:break-word;white-space:normal;">{label}</div>
        </div>
        <script>
        (function() {{
            const el = document.getElementById("{uid}");
            const target = {value};
            const suffix = "{suffix}";
            const isFloat = target % 1 !== 0;
            let start = null;
            const duration = 700;
            function step(ts) {{
                if (!start) start = ts;
                const progress = Math.min((ts - start) / duration, 1);
                const current = target * progress;
                el.textContent = (isFloat ? current.toFixed(1) : Math.round(current)) + suffix;
                if (progress < 1) requestAnimationFrame(step);
            }}
            requestAnimationFrame(step);
        }})();
        </script>
        """,
        height=160,
    )


# ---------------------------------------------------------------- RiskBadge / StatusIndicator
def risk_badge(risk: str) -> str:
    return risk_pill(risk)


def status_indicator(label: str, status: str):
    """status: 'online' | 'degraded' | 'offline'"""
    st.markdown(f'{status_dot(status)}<span>{label}</span>', unsafe_allow_html=True)


def system_health_card(status: str, sub_label: str = "System Health"):
    """Renders the health status entirely within a single markdown call -- opening
    a card div in one st.markdown() and closing it in another doesn't nest the
    widgets rendered in between (each call is its own DOM block), which previously
    left the status text floating outside an empty card."""
    label_text = {"online": "System Online", "degraded": "System Degraded", "offline": "System Offline"}.get(status, "Unknown")
    st.markdown(
        f'<div class="metric-card" style="min-height:150px;display:flex;flex-direction:column;justify-content:center;">'
        f'<div class="metric-icon">🖥️</div>'
        f'<div style="font-size:1.05rem;font-weight:700;">{status_dot(status)}{label_text}</div>'
        f'<div class="metric-label">{sub_label}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- SkeletonLoader
def skeleton_cards(n: int = 3):
    st.markdown("".join(f'<div class="skeleton skeleton-card"></div>' for _ in range(n)), unsafe_allow_html=True)


def skeleton_lines(n: int = 3):
    st.markdown("".join(f'<div class="skeleton skeleton-line"></div>' for _ in range(n)), unsafe_allow_html=True)


def load_with_skeleton(fetch_fn, n: int = 3):
    """Shows skeleton placeholder blocks while fetch_fn() (SQLite/ChromaDB/audit log
    access) runs, then swaps in real content. Never crashes the page on failure."""
    placeholder = st.empty()
    with placeholder.container():
        skeleton_cards(n)
    try:
        data = fetch_fn()
    except Exception as e:
        placeholder.empty()
        st.warning(f"Could not load data right now: {e}")
        return None
    placeholder.empty()
    return data


# ---------------------------------------------------------------- DataTable
def data_table(rows: list[dict], columns: list[str] = None, height: int = 420, empty_message: str = "No records yet."):
    if not rows:
        st.info(empty_message)
        return
    df = pd.DataFrame(rows)
    if columns:
        columns = [c for c in columns if c in df.columns]
        df = df[columns]
    st.dataframe(df, use_container_width=True, height=height)


# ---------------------------------------------------------------- InsightCard
def insight_card(text: str, icon: str = "💡"):
    st.markdown(f'<div class="insight-card">{icon} {text}</div>', unsafe_allow_html=True)


def notification_card(text: str, icon: str = "🔔"):
    st.markdown(f'<div class="notif-card">{icon} {text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- Empty state
def empty_state(message: str, icon: str = "✅"):
    st.markdown(
        f'<div class="aegis-card" style="text-align:center;color:#8B93A7;">'
        f'<div style="font-size:1.8rem;">{icon}</div><div style="margin-top:0.4rem;">{message}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- Agent Timeline (horizontal, staged)
def render_agent_timeline(trace: list[dict]):
    st.markdown('<div class="timeline">', unsafe_allow_html=True)
    nodes_html = []
    for step in trace:
        label = NODE_LABELS.get(step["node"], step["node"])
        cls = STATUS_CLASS.get(step["decision"], "success" if step["status"] == "success" else "failed")
        nodes_html.append(
            f'<div class="timeline-node {cls}"><div class="tl-title">{label}</div>'
            f'<div class="tl-time">{step["execution_time_ms"]} ms</div></div>'
        )
    st.markdown("".join(nodes_html) + "</div>", unsafe_allow_html=True)

    for step in trace:
        label = NODE_LABELS.get(step["node"], step["node"])
        with st.expander(f"{label} — {step['tool']} ({step['execution_time_ms']} ms)"):
            st.caption(f"Input: {step['input_summary']}")
            st.caption(f"Output: {step['output_summary']}")
            st.caption(f"Decision: {step['decision']}")


# ---------------------------------------------------------------- Vertical per-record timeline (Audit Log detail)
def render_record_timeline(record: dict):
    ts = record.get("timestamp", "")
    time_part = ts.split("T")[-1][:5] if "T" in str(ts) else str(ts)[:5]
    steps = [
        (time_part, "Query Received"),
        (time_part, f"Owner Assigned — {record.get('owner', 'N/A')}"),
        (time_part, f"Risk Classified — {record.get('risk', 'N/A')}"),
        (time_part, f"Human Review — {record.get('approval_status', 'N/A')}"),
        (record.get("approval_timestamp", time_part) or time_part, "Audit Logged"),
    ]
    items = "".join(
        f'<div class="vtimeline-item"><span class="vtimeline-time">{t}</span> &nbsp; '
        f'<span class="vtimeline-label">{label}</span></div>'
        for t, label in steps
    )
    st.markdown(f'<div class="vtimeline">{items}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- Knowledge Sources (grouped evidence, exception 2 display)
def render_knowledge_sources(chunks: list[dict]):
    qualifying = [c for c in chunks if c.get("qualifies")]
    if not qualifying:
        st.caption("No qualifying knowledge sources.")
        return

    grouped: dict[str, list[dict]] = {}
    for c in qualifying:
        grouped.setdefault(c["filename"], []).append(c)

    for filename, group in grouped.items():
        title = group[0].get("title") or filename
        avg_score = sum(c["score"] for c in group) / len(group)
        stars = "★" * max(1, round(avg_score * 5)) + "☆" * (5 - max(1, round(avg_score * 5)))
        pages = sorted({str(c.get("page", "")) for c in group}, key=lambda x: (len(x), x))

        st.markdown(
            f'<div class="evidence-card"><b>{title}</b> <span style="color:#8B93A7">({filename})</span><br/>'
            f'<span class="evidence-stars">{stars}</span> &nbsp; '
            f'{len(group)} supporting clause(s) &nbsp;|&nbsp; Pages: {", ".join(pages)} &nbsp;|&nbsp; '
            f'Avg. similarity: {round(avg_score * 100, 1)}%</div>',
            unsafe_allow_html=True,
        )
        for c in group:
            with st.expander(f"📄 Chunk {c['chunk_id']} — {round(c['score'] * 100, 1)}% similarity"):
                st.write(f"**Document:** {c['title']}")
                st.write(f"**Section:** {c.get('section') or '—'}")
                st.write(f"**Clause:** {c.get('clause') or '—'}")
                st.write(f"**Page:** {c.get('page')}")
                st.write(f"**Similarity:** {round(c['score'] * 100, 1)}%")
                st.button("📂 Open Document", key=f"open_{c['chunk_id']}", disabled=True,
                          help="Document preview is available from the Knowledge Base page.")
                citation_text = f"{c['title']} ({c['filename']}), Page {c['page']}, {c.get('clause') or c.get('section') or ''}, Chunk {c['chunk_id']}"
                st.code(citation_text, language=None)


# ---------------------------------------------------------------- Retrieval confidence display (scoped presentation exception)
def render_retrieval_confidence(state: dict):
    """Shows real retrieval numbers even on refusal -- never a bare 0% if documents were found.
    Presentation only: does not alter the confidence formula or governance decision.
    """
    chunks = state.get("retrieved_chunks", [])
    qualifying = [c for c in chunks if c.get("qualifies")]

    if not chunks:
        st.caption("No documents were retrieved for this query.")
        return

    avg_similarity = sum(c["score"] for c in chunks) / len(chunks)
    evidence_coverage = f"{len(qualifying)}/{len(chunks)} chunks above threshold"
    citation_coverage = f"{len(state.get('citations', []))}/{max(len(qualifying), 1)}"
    passed = state.get("governance_passed")

    label = "Evidence retrieved but below governance threshold." if not passed and qualifying == [] and avg_similarity > 0 else state.get("governance_reason", "")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Retrieved Similarity", f"{round(avg_similarity * 100, 1)}%")
    with c2:
        st.metric("Evidence Coverage", evidence_coverage)
    with c3:
        st.metric("Citation Coverage", citation_coverage)
    with c4:
        st.metric("Governance Result", "Passed" if passed else "Refused")

    if not passed:
        st.caption(f"ℹ️ {label}" if label else "ℹ️ Refused by governance.")


# ---------------------------------------------------------------- Response report card (Compliance Agent page)
def render_response_report(state: dict):
    escalated = state.get("escalated")
    review_status = state.get("review_status", "N/A")

    if review_status == "Pending":
        st.markdown(
            '<div class="escalation-banner">⚠ Human Review Required — awaiting compliance approval before this advisory can be released.</div>',
            unsafe_allow_html=True,
        )

    answer_text = state.get("final_answer")
    if answer_text is None and review_status != "Pending":
        answer_text = state.get("final_text", "")

    with st.container():
        st.markdown('<div class="aegis-card">', unsafe_allow_html=True)
        badges = (
            risk_pill(state.get("risk", "N/A"))
            + owner_pill(state.get("owner", "Compliance Manager"))
            + confidence_pill(state["confidence"]["level"], state["confidence"]["score"])
        )
        st.markdown(badges, unsafe_allow_html=True)

        with st.expander("📋 Executive Summary", expanded=True):
            if review_status == "Pending":
                st.info("Advisory drafted and held pending human approval.")
            elif answer_text:
                first_line = answer_text.strip().split("\n")[0]
                st.write(first_line[:280])
            else:
                st.write("No advisory could be generated for this query.")

        with st.expander("🧾 Detailed Advisory (Compliance Assessment)", expanded=review_status != "Pending"):
            if review_status == "Pending":
                st.caption("Held pending approval — use the controls below.")
            else:
                st.markdown(answer_text if answer_text else "_No answer available._")

        with st.expander("✅ Recommended Next Actions"):
            actions = []
            if review_status == "Pending":
                actions.append("Await human reviewer approval before communicating this advisory.")
            if escalated:
                actions.append(f"Notify {state.get('owner')} of this escalation.")
            if not state.get("governance_passed"):
                actions.append("Consider uploading additional policy documentation covering this topic.")
            if not actions:
                actions.append("No further action required — advisory is grounded and finalized.")
            for a in actions:
                st.write(f"- {a}")

        with st.expander("📚 Policy Evidence (Knowledge Sources)", expanded=False):
            render_knowledge_sources(state.get("retrieved_chunks", []))

        with st.expander("📊 Retrieval & Governance Detail"):
            render_retrieval_confidence(state)

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- Live staged status (Compliance Agent page)
LIVE_STAGES = [
    "Classifying Request...", "Identifying Owner...", "Searching Knowledge Base...",
    "Validating Evidence...", "Writing Advisory...", "Checking Governance...",
    "Assessing Risk...", "Logging Audit...",
]

NODE_TO_STAGE = {
    "classify_topic": 0, "topic_routing": 1, "rag_retrieval": 2, "context_validation": 3,
    "compliance_reasoning": 4, "citation_generation": 4, "confidence_calculation": 4,
    "governance_validation": 5, "risk_classification": 6, "human_review_gate": 6,
    "audit_logging": 7,
}


def render_live_stage_progress(placeholder, stage_index: int):
    lines = []
    for i, label in enumerate(LIVE_STAGES):
        if i < stage_index:
            lines.append(f"✓ {label}")
        elif i == stage_index:
            lines.append(f"⏳ {label}")
        else:
            lines.append(f"○ {label}")
    placeholder.markdown(
        '<div class="aegis-card">' + "<br/>".join(lines) + "</div>", unsafe_allow_html=True
    )
