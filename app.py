"""Aegis - Compliance Advisory & Triage Agent. Streamlit entrypoint.
Every query is executed through the LangGraph StateGraph in agents/orchestrator.py --
this file only renders state and routes between pages; it never calls tools or the
LLM directly.
"""
import html
import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

from rag.ingest import ingest_all, corpus_is_empty
from ui.styles import CSS
from ui.auth import is_authenticated, get_current_user, logout, render_login_screen
from ui.insights import get_indexed_policy_stats, load_audit_df
from ui.pages import dashboard, agent, pending_reviews, knowledge_base, audit_log, analytics, evaluation, settings

st.set_page_config(page_title="Aegis - Compliance Advisory & Triage Agent", page_icon="🛡️", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Ingesting compliance corpus...")
def _startup_ingest():
    if corpus_is_empty():
        return {"empty": True, "summary": None}
    summary = ingest_all(force_rebuild=False)
    return {"empty": False, "summary": summary}


if not is_authenticated():
    render_login_screen()
    st.stop()

startup = _startup_ingest()

NAV_PAGES = {
    "🏠 Dashboard": dashboard,
    "💬 Compliance Agent": agent,
    "⚠️ Pending Reviews": pending_reviews,
    "📁 Knowledge Base": knowledge_base,
    "📋 Audit Logs": audit_log,
    "📊 Analytics": analytics,
    "🧪 Evaluation Suite": evaluation,
    "⚙️ Settings": settings,
}

# ---------------------------------------------------------------- Top action bar
current_user = get_current_user()
if "memory_toggle" not in st.session_state:
    try:
        from memory.hindsight_client import is_enabled
        st.session_state["memory_toggle"] = is_enabled()
    except Exception:
        st.session_state["memory_toggle"] = False

brand_col, memory_col, provider_col, profile_col = st.columns([1.35, 1, 1.15, 0.95])
with brand_col:
    st.markdown(
        '<div class="top-brand"><span class="top-brand-shield">🛡️</span>'
        '<span><b>Aegis</b><small>Compliance Operations</small></span></div>',
        unsafe_allow_html=True,
    )
with memory_col:
    st.markdown('<div class="top-memory-anchor"></div>', unsafe_allow_html=True)
    memory_on = st.toggle(
        f"🧠 Memory {'ON' if st.session_state.get('memory_toggle', False) else 'OFF'}",
        value=bool(st.session_state.get("memory_toggle", False)),
        key="memory_toggle",
        help="Use the existing Hindsight memory setting for compliance queries.",
    )
    st.session_state["memory_enabled"] = bool(memory_on)
    st.markdown(
        f'<div class="memory-chip {"enabled" if memory_on else "disabled"}">'
        f'{"ON" if memory_on else "OFF"}</div>',
        unsafe_allow_html=True,
    )

provider_options = [
    ("Groq", bool(os.getenv("GROQ_API_KEY", "").strip())),
    ("Gemini", bool(os.getenv("GEMINI_API_KEY", "").strip())),
    ("OpenRouter", bool(os.getenv("OPENROUTER_API_KEY", "").strip() and os.getenv("OPENROUTER_MODEL", "").strip())),
]
configured_provider = next((name for name, configured in provider_options if configured), None)
audit_df = load_audit_df()
last_provider = (
    str(audit_df.sort_values("timestamp_dt").iloc[-1].get("llm_provider", "none"))
    if not audit_df.empty else ""
)
if last_provider:
    provider_ok = last_provider.lower() not in {"none", "skipped", ""}
    provider_class = "is-healthy" if provider_ok else "is-unavailable"
    provider_text = f"{last_provider.capitalize()} responded" if provider_ok else "Provider unavailable"
elif configured_provider:
    provider_class = "is-configured"
    provider_text = f"{configured_provider} configured"
else:
    provider_class = "is-unavailable"
    provider_text = "Provider unavailable"
with provider_col:
    st.markdown(
        f'<div class="top-status {provider_class}">'
        f'<span class="status-indicator"></span>{html.escape(provider_text)}</div>',
        unsafe_allow_html=True,
    )
with profile_col:
    profile_name = html.escape(current_user["display_name"] if current_user else "Account")
    st.markdown(
        f'<div class="top-profile">👤 <span>{profile_name}</span></div>',
        unsafe_allow_html=True,
    )
st.markdown('<div class="topbar-rule"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- Command palette (Ctrl+K best-effort focus helper)
components.html(
    """
    <script>
    window.parent.document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            const el = window.parent.document.querySelector('input[placeholder="Search pages or actions..."]');
            if (el) { el.focus(); el.select(); }
        }
    });
    </script>
    """,
    height=0,
)

with st.sidebar:
    st.markdown('<div class="aegis-header" style="font-size:1.5rem;">🛡️ Aegis</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-subtitle">Compliance Advisory & Triage Agent</div>', unsafe_allow_html=True)

    stats = get_indexed_policy_stats()
    memory_on = bool(st.session_state.get("memory_toggle", False))
    st.session_state["memory_enabled"] = memory_on
    turns = len(st.session_state.get("chat_history", []))
    st.caption(f"🤖 Provider: **{__import__('os').getenv('LLM_PROVIDER', 'groq').capitalize()}**")
    st.caption(f"📚 Indexed Documents: **{stats['documents']}**")
    st.caption(f"🧠 Memory: **{'ON' if memory_on else 'OFF'}** ({turns} turns)")
    from ui.pages.settings import APP_VERSION
    st.caption(f"🏷️ Aegis v{APP_VERSION}")

    st.divider()

    palette_query = st.text_input("Quick jump", placeholder="Search pages or actions... (Ctrl+K)", label_visibility="collapsed")
    matches = [p for p in NAV_PAGES if palette_query.lower() in p.lower()] if palette_query else list(NAV_PAGES.keys())

    default_page = st.session_state.get("nav_page", matches[0] if matches else "🏠 Dashboard")
    if default_page not in matches:
        default_page = matches[0] if matches else "🏠 Dashboard"
    st.session_state.nav_page = default_page

    # Custom-styled nav list -- replaces st.radio so no native radio circles are shown.
    st.markdown('<div class="nav-anchor"></div>', unsafe_allow_html=True)
    for name in matches:
        if name == default_page:
            st.markdown(f'<div class="nav-item nav-item-active">{name}</div>', unsafe_allow_html=True)
        else:
            if st.button(name, key=f"nav_{name}", use_container_width=True):
                st.session_state.nav_page = name
                st.rerun()
    page = st.session_state.nav_page

    st.divider()

    if startup["empty"]:
        st.warning("No documents found in data/policies/. Add files there or upload via Knowledge Base, then click Rebuild Index.")

    if current_user:
        user_name = html.escape(current_user.get("display_name") or current_user["email"])
        user_email = html.escape(current_user["email"])
        role = html.escape(current_user.get("role", "User").replace("_", " ").title())
        st.markdown(
            '<div class="sidebar-profile">'
            '<div class="user-avatar">👤</div><div class="user-details">'
            f'<strong>{user_name}</strong><span>{user_email}</span><small>{role}</small>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    if st.button("🚪 Sign Out", use_container_width=True):
        logout()
        st.rerun()

NAV_PAGES[page].render()

st.markdown('<div class="cmdk-hint">Press <kbd>Ctrl</kbd>+<kbd>K</kbd> to search pages</div>', unsafe_allow_html=True)
