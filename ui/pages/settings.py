"""Settings -- provider configuration, thresholds, memory toggle, provider health."""
import os
import streamlit as st
from ui.insights import load_audit_df

APP_VERSION = "1.0.0"


def _mask(key: str) -> str:
    if not key:
        return "Not configured"
    return f"••••••••{key[-4:]}" if len(key) > 4 else "••••••••"


def render():
    st.markdown('<div class="aegis-header">⚙️ Settings</div>', unsafe_allow_html=True)
    # Only initialise if neither key exists yet (first ever load, no widget bound).
    # Do NOT write to memory_toggle unconditionally — app.py binds st.toggle to
    # that key in the top bar before any page renders, so overwriting it after
    # instantiation raises StreamlitAPIException.
    if "memory_toggle" not in st.session_state and "memory_enabled" not in st.session_state:
        st.session_state["memory_toggle"] = True
    if "memory_enabled" not in st.session_state:
        st.session_state["memory_enabled"] = st.session_state.get("memory_toggle", True)

    df = load_audit_df()
    latest = df.sort_values("timestamp_dt").iloc[-1] if not df.empty else None
    provider = str(latest.get("llm_provider", "none")).capitalize() if latest is not None else ""
    if latest is not None and provider.lower() not in {"none", "skipped", ""}:
        provider_status, status_class = "Healthy", "healthy"
    elif latest is not None:
        provider_status, status_class = "Unavailable", "unavailable"
    elif any(os.getenv(key, "").strip() for key in ("GROQ_API_KEY", "GEMINI_API_KEY")) or (
        os.getenv("OPENROUTER_API_KEY", "").strip() and os.getenv("OPENROUTER_MODEL", "").strip()
    ):
        provider_status, status_class = "Configured · awaiting first response", "configured"
    else:
        provider_status, status_class = "Unavailable", "unavailable"

    with st.container(border=True):
        st.markdown(
            '<div class="settings-card-heading"><span>🔌</span><div><h3>Provider Health</h3>'
            '<p>Recent provider availability for your account.</p></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="health-badge {status_class}"><span></span>{provider_status}</div>',
            unsafe_allow_html=True,
        )
        if latest is None:
            st.markdown('<div class="compact-empty">No queries yet. Provider health will appear after your first response.</div>', unsafe_allow_html=True)
        else:
            cols = st.columns(3)
            cols[0].markdown(f"**Last provider**<br>{provider or 'Unavailable'}", unsafe_allow_html=True)
            cols[1].markdown(f"**Average latency**<br>{round(df['total_latency'].mean(), 2)} s", unsafe_allow_html=True)
            counts = df["llm_provider"].value_counts()
            cols[2].markdown(f"**Most used**<br>{counts.idxmax().capitalize() if not counts.empty else 'N/A'}", unsafe_allow_html=True)
        failovers = [
            f"{attempt['provider']}: {attempt['error'][:60]}"
            for turn in st.session_state.get("chat_history", [])
            for attempt in turn["state"].get("llm_attempts", [])
            if attempt["status"] == "failed"
        ]
        if failovers:
            st.warning("Recent failovers this session: " + " | ".join(failovers[-5:]))
        elif latest is not None:
            st.caption("No provider failovers observed this session.")

    with st.container(border=True):
        st.markdown('<div class="settings-memory-anchor"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="settings-card-heading"><span>🧠</span><div><h3>Conversation Memory</h3>'
            '<p>Control whether Hindsight context is used across turns.</p></div></div>',
            unsafe_allow_html=True,
        )
        mem_enabled = st.toggle(
            "Memory", value=bool(st.session_state.get("memory_enabled", False)),
            key="memory_enabled",
        )
        # Do NOT write to memory_toggle here — that key is bound to the
        # st.toggle widget in app.py's top bar. Writing to it after instantiation
        # raises StreamlitAPIException. The top bar reads memory_enabled on the
        # next rerun and keeps both values in sync automatically.
        turns = len(st.session_state.get("chat_history", []))
        memory_copy = f"Memory is ON • {turns} turns" if mem_enabled else "Memory is OFF"
        st.markdown(
            f'<div class="memory-state {"enabled" if mem_enabled else "disabled"}">{memory_copy}</div>',
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown(
            '<div class="settings-card-heading"><span>🔑</span><div><h3>LLM Provider Configuration</h3>'
            '<p>Active provider models and masked credential status.</p></div></div>',
            unsafe_allow_html=True,
        )
        st.caption("Configured via .env — edit the file and restart to change these.")
        rows = [
            {"Provider": "Groq (primary)", "Model": os.getenv("GROQ_MODEL", ""), "API Key": _mask(os.getenv("GROQ_API_KEY", ""))},
            {"Provider": "Gemini (fallback)", "Model": os.getenv("GEMINI_MODEL", ""), "API Key": _mask(os.getenv("GEMINI_API_KEY", ""))},
            {"Provider": "OpenRouter (optional)", "Model": os.getenv("OPENROUTER_MODEL", "") or "—", "API Key": _mask(os.getenv("OPENROUTER_API_KEY", ""))},
        ]
        st.table(rows)

    st.markdown('<div class="section-title">🎛️ Retrieval Configuration</div>', unsafe_allow_html=True)
    st.write(f"**Similarity Threshold:** {os.getenv('SIMILARITY_THRESHOLD', '0.65')}")
    st.write(f"**Embedding Model:** {os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')}")

    st.markdown('<div class="section-title">ℹ️ About</div>', unsafe_allow_html=True)
    st.write(f"**Aegis version:** {APP_VERSION}")
