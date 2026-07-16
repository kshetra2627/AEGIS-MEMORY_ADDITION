"""Settings -- provider configuration, thresholds, memory toggle, provider health."""
import os
import streamlit as st
from ui.components import metric_card, empty_state
from ui.insights import load_audit_df

APP_VERSION = "1.0.0"


def _mask(key: str) -> str:
    if not key:
        return "Not configured"
    return f"••••••••{key[-4:]}" if len(key) > 4 else "••••••••"


def render():
    st.markdown('<div class="aegis-header">⚙️ Settings</div>', unsafe_allow_html=True)
    st.session_state.setdefault("memory_enabled", True)

    st.markdown('<div class="section-title">🔌 Provider Health</div>', unsafe_allow_html=True)
    df = load_audit_df()
    if df.empty:
        empty_state("No queries logged yet.")
    else:
        latest = df.sort_values("timestamp_dt").iloc[-1]
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("🤖", latest["llm_provider"].capitalize(), "Last Provider to Answer")
        with c2:
            metric_card("⏱️", round(df["total_latency"].mean(), 2), "Avg Latency (s)")
        with c3:
            counts = df["llm_provider"].value_counts()
            metric_card("📈", counts.idxmax().capitalize() if not counts.empty else "N/A", "Most-Used Provider")

        failovers = []
        for turn in st.session_state.get("chat_history", []):
            for a in turn["state"].get("llm_attempts", []):
                if a["status"] == "failed":
                    failovers.append(f"{a['provider']}: {a['error'][:60]}")
        if failovers:
            st.warning("Recent failovers this session: " + " | ".join(failovers[-5:]))
        else:
            st.caption("No provider failovers observed this session.")

    st.markdown('<div class="section-title">🧠 Conversation Memory</div>', unsafe_allow_html=True)
    st.toggle("Preserve conversation memory across turns", key="memory_enabled")
    turns = len(st.session_state.get("chat_history", []))
    st.caption(f"Memory is currently {'ON' if st.session_state.memory_enabled else 'OFF'} · {turns} turn(s) in this session.")

    st.markdown('<div class="section-title">🔑 LLM Provider Configuration</div>', unsafe_allow_html=True)
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
