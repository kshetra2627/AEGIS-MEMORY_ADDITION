"""Custom dark enterprise CSS theme for Aegis -- the AI Compliance Operations Platform."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-main: #0B0F19;
    --bg-card: #131A2A;
    --bg-sidebar: #0D1220;
    --border: #232B3D;
    --accent: #3B82F6;
    --accent-hover: #2563EB;
    --text-primary: #E5E9F0;
    --text-muted: #8B93A7;
    --risk-low: #22C55E;
    --risk-medium: #F59E0B;
    --risk-high: #EF4444;
    --escalation-bg: #2A1414;
    --success: #22C55E;
}

html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: radial-gradient(circle at 20% 0%, #101627 0%, #0B0F19 45%); color: var(--text-primary); }
section[data-testid="stSidebar"] { background-color: var(--bg-sidebar); border-right: 1px solid var(--border); }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 8px; }

/* ---------- Typography ---------- */
.aegis-header { font-size: 2.2rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0; letter-spacing: -0.02em; }
.aegis-subtitle { color: var(--text-muted); font-size: 1rem; margin-top: 0.1rem; margin-bottom: 0.3rem; }
.aegis-tagline { color: var(--accent); font-size: 0.82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1.2rem; }
.section-title { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 1.4rem 0 0.7rem 0; }

/* ---------- Sticky top bar ---------- */
.top-nav {
    position: sticky; top: 0; z-index: 999;
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.7rem 0.2rem; margin-bottom: 0.8rem;
    background: rgba(11,15,25,0.85); backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
}
.top-nav-brand { font-weight: 800; font-size: 1.1rem; }
.top-nav-meta { color: var(--text-muted); font-size: 0.78rem; }

/* ---------- Cards (glass) ---------- */
.aegis-card {
    background: linear-gradient(180deg, rgba(19,26,42,0.95), rgba(19,26,42,0.85));
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 18px rgba(0,0,0,0.28);
    backdrop-filter: blur(6px);
    animation: fadeIn 0.35s ease-out;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.aegis-card:hover { box-shadow: 0 8px 26px rgba(0,0,0,0.38); }

.hover-card { cursor: pointer; }
.hover-card:hover { transform: translateY(-3px); border-color: var(--accent); }

@keyframes fadeIn { from { opacity: 0; transform: translateY(6px);} to { opacity: 1; transform: translateY(0);} }

/* ---------- Pills / badges ---------- */
.pill {
    display: inline-block;
    padding: 0.28rem 0.8rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-right: 0.4rem;
    margin-bottom: 0.3rem;
    border: 1px solid currentColor;
}
.pill-low { color: var(--risk-low); background: rgba(34,197,94,0.15); }
.pill-medium { color: var(--risk-medium); background: rgba(245,158,11,0.15); }
.pill-high { color: var(--risk-high); background: rgba(239,68,68,0.15); }
.pill-owner { color: var(--accent); background: rgba(59,130,246,0.15); }
.pill-na { color: var(--text-muted); background: rgba(139,147,167,0.15); }

/* ---------- Escalation banner ---------- */
.escalation-banner {
    background-color: var(--escalation-bg);
    border: 1px solid var(--risk-high);
    color: var(--risk-high);
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    font-weight: 700;
    margin-bottom: 0.8rem;
    animation: fadeIn 0.3s ease-out;
}

/* ---------- Citations / evidence ---------- */
.citation-item {
    background: rgba(59,130,246,0.08);
    border-left: 3px solid var(--accent);
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.4rem;
    border-radius: 6px;
    font-size: 0.85rem;
    color: var(--text-primary);
}
.evidence-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
}
.evidence-stars { color: var(--risk-medium); letter-spacing: 2px; font-size: 0.9rem; }

/* ---------- Trace / timeline ---------- */
.trace-row { border-bottom: 1px solid var(--border); padding: 0.55rem 0; font-size: 0.85rem; }

.timeline { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.6rem 0 1rem 0; }
.timeline-node {
    flex: 1 1 110px; min-width: 110px;
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
    padding: 0.6rem 0.7rem; font-size: 0.78rem; text-align: center; position: relative;
}
.timeline-node.success { border-color: var(--risk-low); }
.timeline-node.skipped { border-color: var(--risk-medium); }
.timeline-node.failed { border-color: var(--risk-high); }
.timeline-node .tl-title { font-weight: 700; margin-bottom: 0.2rem; }
.timeline-node .tl-time { color: var(--text-muted); font-size: 0.72rem; }

.vtimeline { border-left: 2px solid var(--border); margin-left: 0.6rem; padding-left: 1rem; }
.vtimeline-item { position: relative; padding-bottom: 1rem; }
.vtimeline-item::before {
    content: ''; position: absolute; left: -1.31rem; top: 0.15rem;
    width: 10px; height: 10px; border-radius: 50%; background: var(--accent);
}
.vtimeline-time { color: var(--text-muted); font-size: 0.75rem; }
.vtimeline-label { font-weight: 600; }

/* ---------- Metric / KPI cards ---------- */
.metric-card {
    background: linear-gradient(160deg, rgba(19,26,42,0.95), rgba(15,20,33,0.9));
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.1rem 1rem;
    text-align: center;
    transition: transform 0.15s ease, border-color 0.15s ease;
}
.metric-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.metric-value { font-size: 1.9rem; font-weight: 800; color: var(--accent); }
.metric-label { color: var(--text-muted); font-size: 0.8rem; margin-top: 0.15rem; white-space: normal; word-wrap: break-word; line-height: 1.3; }
.metric-icon { font-size: 1.3rem; margin-bottom: 0.2rem; }

/* ---------- Status indicator ---------- */
.status-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 0.4rem; }
.status-online { background: var(--risk-low); box-shadow: 0 0 8px var(--risk-low); }
.status-degraded { background: var(--risk-medium); box-shadow: 0 0 8px var(--risk-medium); }
.status-offline { background: var(--risk-high); box-shadow: 0 0 8px var(--risk-high); }

/* ---------- Insight / notification cards ---------- */
.insight-card {
    background: rgba(59,130,246,0.06); border: 1px solid var(--border); border-left: 3px solid var(--accent);
    border-radius: 8px; padding: 0.65rem 0.9rem; margin-bottom: 0.5rem; font-size: 0.88rem;
}
.notif-card {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.6rem 0.85rem; margin-bottom: 0.45rem; font-size: 0.85rem;
}

/* ---------- Skeleton loaders ---------- */
.skeleton { background: linear-gradient(90deg, #131A2A 25%, #1b2438 37%, #131A2A 63%); background-size: 400% 100%;
    animation: skeleton-shine 1.4s ease infinite; border-radius: 10px; }
@keyframes skeleton-shine { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
.skeleton-card { height: 84px; margin-bottom: 0.8rem; }
.skeleton-line { height: 14px; margin-bottom: 0.5rem; }

/* ---------- Quick action cards ---------- */
.quick-action {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px;
    padding: 1.1rem; text-align: center; transition: all 0.15s ease; cursor: pointer;
}
.quick-action:hover { border-color: var(--accent); transform: translateY(-3px); box-shadow: 0 8px 20px rgba(59,130,246,0.15); }
.quick-action .qa-icon { font-size: 1.8rem; margin-bottom: 0.4rem; }

/* ---------- Login ---------- */
.login-wrapper { display: flex; justify-content: center; align-items: center; min-height: 80vh; }
.login-card {
    background: rgba(19,26,42,0.92); border: 1px solid var(--border); border-radius: 18px;
    padding: 2.4rem 2.6rem; width: 100%; max-width: 420px; backdrop-filter: blur(12px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.45); animation: fadeIn 0.4s ease-out;
}
.login-logo { font-size: 2.6rem; text-align: center; margin-bottom: 0.2rem; }
.login-title { text-align: center; font-weight: 800; font-size: 1.4rem; margin-bottom: 0.1rem; }
.login-subtitle { text-align: center; color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1.4rem; }

/* ---------- Sidebar nav list (replaces st.radio) ---------- */
.nav-item {
    padding: 0.5rem 0.8rem; border-radius: 8px; margin-bottom: 0.25rem;
    font-weight: 500; color: var(--text-muted);
}
.nav-item-active {
    background: rgba(59,130,246,0.15); color: var(--accent) !important;
    border-left: 3px solid var(--accent); font-weight: 700;
}
div[data-testid="stVerticalBlock"]:has(> div.nav-anchor) div[data-testid="stButton"] > button {
    background: transparent; color: var(--text-primary); text-align: left; justify-content: flex-start;
    border: 1px solid transparent; font-weight: 500; box-shadow: none; padding: 0.5rem 0.8rem;
}
div[data-testid="stVerticalBlock"]:has(> div.nav-anchor) div[data-testid="stButton"] > button:hover {
    background: rgba(59,130,246,0.1); border-color: var(--accent); transform: none;
}

/* ---------- Buttons / inputs ---------- */
div.stButton > button {
    background-color: var(--accent); color: white; border-radius: 9px; border: none; font-weight: 600;
    transition: background-color 0.15s ease, transform 0.1s ease;
}
div.stButton > button:hover { background-color: var(--accent-hover); transform: translateY(-1px); }
div[data-baseweb="input"] > div, .stTextInput input, .stChatInput textarea {
    background-color: var(--bg-card) !important; border: 1px solid var(--border) !important; color: var(--text-primary) !important;
    border-radius: 10px !important;
}
div[data-testid="stChatInput"] textarea { font-size: 1rem; }

/* ---------- Suggested prompt chips ---------- */
.chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.5rem 0 1rem 0; }
.chip {
    background: rgba(59,130,246,0.1); border: 1px solid var(--accent); color: var(--accent);
    border-radius: 999px; padding: 0.28rem 0.85rem; font-size: 0.78rem; font-weight: 600;
}

/* ---------- Data table wrapper ---------- */
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }

/* ---------- Command palette hint ---------- */
.cmdk-hint {
    position: fixed; bottom: 14px; right: 18px; z-index: 998;
    background: var(--bg-card); border: 1px solid var(--border); color: var(--text-muted);
    padding: 0.35rem 0.7rem; border-radius: 8px; font-size: 0.75rem;
}
kbd { background: #1b2438; border: 1px solid var(--border); border-radius: 4px; padding: 0 5px; font-size: 0.75rem; }
</style>
"""


def risk_pill(risk: str) -> str:
    cls = {"Low": "pill-low", "Medium": "pill-medium", "High": "pill-high"}.get(risk, "pill-na")
    icon = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(risk, "⚪")
    return f'<span class="pill {cls}">{icon} Risk: {risk}</span>'


def owner_pill(owner: str) -> str:
    return f'<span class="pill pill-owner">🧭 Owner: {owner}</span>'


def confidence_pill(level: str, score: float) -> str:
    cls = {"Low": "pill-low", "Medium": "pill-medium", "High": "pill-high"}.get(level, "pill-na")
    return f'<span class="pill {cls}">📊 Confidence: {score}% ({level})</span>'


def status_dot(status: str) -> str:
    cls = {"online": "status-online", "degraded": "status-degraded", "offline": "status-offline"}.get(status, "status-offline")
    return f'<span class="status-dot {cls}"></span>'
