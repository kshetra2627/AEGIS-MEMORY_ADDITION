"""Aegis - Compliance Advisory & Triage Agent. Streamlit entrypoint.
Every query is executed through the LangGraph StateGraph in agents/orchestrator.py --
this file only renders state and routes between pages; it never calls tools or the
LLM directly.
"""
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

from rag.ingest import ingest_all, corpus_is_empty
from ui.styles import CSS
from ui.auth import is_authenticated, render_login_screen
from ui.insights import get_indexed_policy_stats
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

# ---------------------------------------------------------------- Sticky top nav
st.markdown(
    '<div class="top-nav"><div class="top-nav-brand">🛡️ Aegis</div>'
    '<div class="top-nav-meta">Enterprise AI Agent for Compliance Operations</div></div>',
    unsafe_allow_html=True,
)

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

    stats = get_indexed_policy_stats()
    memory_on = st.session_state.get("memory_enabled", True)
    turns = len(st.session_state.get("chat_history", []))
    st.caption(f"🤖 Provider: **{__import__('os').getenv('LLM_PROVIDER', 'groq').capitalize()}**")
    st.caption(f"📚 Indexed Documents: **{stats['documents']}**")
    st.caption(f"🧠 Memory: **{'ON' if memory_on else 'OFF'}** ({turns} turns)")
    from ui.pages.settings import APP_VERSION
    st.caption(f"🏷️ Aegis v{APP_VERSION}")

    if startup["empty"]:
        st.warning("No documents found in data/policies/. Add files there or upload via Knowledge Base, then click Rebuild Index.")

    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

NAV_PAGES[page].render()

st.markdown('<div class="cmdk-hint">Press <kbd>Ctrl</kbd>+<kbd>K</kbd> to search pages</div>', unsafe_allow_html=True)
