"""Custom dark enterprise CSS theme for Aegis -- the AI Compliance Operations Platform."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-main: #0b1322;
    --bg-card: #172438;
    --bg-sidebar: #0f1a2b;
    --border: #2b3b52;
    --accent: #5790f5;
    --accent-hover: #3f7ce8;
    --text-primary: #edf3fb;
    --text-muted: #b1bfd2;
    --risk-low: #4ade80;
    --risk-medium: #fbbf24;
    --risk-high: #fb7185;
    --escalation-bg: #3a1d2a;
    --success: #4ade80;
}

html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
.stApp {
    background-color: var(--bg-main);
    background-image:
        linear-gradient(rgba(91,145,238,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(91,145,238,0.045) 1px, transparent 1px),
        linear-gradient(145deg, #0b1322 0%, #101c2d 52%, #121f32 100%);
    background-size: 32px 32px, 32px 32px, 100% 100%;
    color: var(--text-primary);
}
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #101b2d 0%, #0d1726 100%); border-right: 1px solid #25354a; }
main .block-container { max-width: 1540px; padding-top: 1.25rem; padding-bottom: 2.2rem; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 8px; }

/* ---------- Typography ---------- */
.aegis-header { font-size: 1.8rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0; letter-spacing: -0.02em; }
.aegis-subtitle { color: var(--text-muted); font-size: 0.88rem; margin-top: 0.1rem; margin-bottom: 0.3rem; }
.aegis-tagline { color: var(--accent); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1rem; }
.section-title { font-size: 0.95rem; font-weight: 750; color: #e5edf8; margin: 1.45rem 0 0.7rem 0; padding-left: 0.65rem; border-left: 3px solid #5790f5; }

/* ---------- Sticky top bar ---------- */
.top-nav {
    position: sticky; top: 0; z-index: 999;
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.7rem 0.2rem; margin-bottom: 0.8rem;
    background: rgba(15,26,43,0.9); backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
}
.top-nav-brand { font-weight: 800; font-size: 1.1rem; }
.top-nav-meta { color: var(--text-muted); font-size: 0.78rem; }
.top-brand { display: flex; align-items: center; gap: 0.65rem; min-height: 2.8rem; color: var(--text-primary); }
.stApp div[data-testid="stHorizontalBlock"]:has(.top-brand) {
    align-items: center; padding: 0.5rem 0.65rem;
    border: 1px solid #293a52; border-radius: 12px;
    background: linear-gradient(105deg, rgba(20,33,52,0.98), rgba(24,40,62,0.96));
    box-shadow: 0 8px 22px rgba(0,0,0,0.2);
}
.top-brand-shield { display: grid; place-items: center; width: 2.35rem; height: 2.35rem; border-radius: 9px; background: #1b3150; box-shadow: inset 0 0 0 1px #2d4d76; font-size: 1.2rem; }
.top-brand b { display: block; color: var(--text-primary); font-size: 1.08rem; line-height: 1.2; }
.top-brand small { display: block; color: var(--text-muted); font-size: 0.68rem; }
.top-status, .top-profile { display: flex; align-items: center; gap: 0.45rem; min-height: 2.4rem; padding: 0.45rem 0.65rem; border: 1px solid var(--border); border-radius: 9px; background: #1a293e; color: var(--text-muted); font-size: 0.76rem; font-weight: 600; }
.status-indicator { width: 8px; height: 8px; flex: 0 0 8px; border-radius: 50%; background: #16a34a; }
.top-status.is-unavailable .status-indicator { background: #dc2626; }
.top-status.is-unavailable { color: #fecdd3; background: #3b202c; }
.top-status.is-configured .status-indicator { background: #2563eb; }
.top-status.is-configured { color: #bfdbfe; background: #1a2e49; }
.top-profile { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.topbar-rule { border-bottom: 1px solid rgba(148,163,184,0.28); margin: 0.65rem 0 1.25rem; }
.memory-chip { display: inline-block; margin: -0.35rem 0 0.2rem 1.8rem; padding: 0.12rem 0.45rem; border-radius: 999px; font-size: 0.64rem; font-weight: 800; }
.memory-chip.enabled { color: #86efac; background: #143528; }
.memory-chip.disabled { color: #cbd5e1; background: #27364a; }
.stApp div[data-testid="stElementContainer"]:has(.top-memory-anchor) + div[data-testid="stElementContainer"] [role="switch"][aria-checked="true"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.settings-memory-anchor) [role="switch"][aria-checked="true"],
div[data-testid="stVerticalBlock"]:has(.settings-memory-anchor) [role="switch"][aria-checked="true"],
div.stVerticalBlock:has(.settings-memory-anchor) [role="switch"][aria-checked="true"] {
    background: #16804a !important; border-color: #16804a !important;
}
.stApp div[data-testid="stElementContainer"]:has(.top-memory-anchor) + div[data-testid="stElementContainer"] [role="switch"][aria-checked="false"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.settings-memory-anchor) [role="switch"][aria-checked="false"],
div[data-testid="stVerticalBlock"]:has(.settings-memory-anchor) [role="switch"][aria-checked="false"],
div.stVerticalBlock:has(.settings-memory-anchor) [role="switch"][aria-checked="false"] {
    background: #53647a !important; border-color: #53647a !important;
}

/* ---------- Settings cards ---------- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.settings-card-heading),
div[data-testid="stVerticalBlock"]:has(.settings-card-heading),
div.stVerticalBlock:has(.settings-card-heading) {
    padding: 1rem 1.15rem 0.8rem;
    margin: 0.65rem 0;
    border: 1px solid #2a3b52 !important;
    border-radius: 11px;
    background: linear-gradient(145deg, #172438, #142033);
    box-shadow: 0 8px 24px rgba(0,0,0,0.18);
}
.settings-card-heading { display: flex; align-items: flex-start; gap: 0.7rem; margin-bottom: 0.55rem; }
.settings-card-heading > span { display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: 8px; background: #203653; font-size: 1rem; }
.settings-card-heading h3 { margin: 0; color: var(--text-primary); font-size: 1rem; font-weight: 700; }
.settings-card-heading p { margin: 0.15rem 0 0; color: var(--text-muted); font-size: 0.78rem; }
.health-badge { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.28rem 0.58rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.health-badge > span { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.health-badge.healthy { color: #86efac; background: #143528; }
.health-badge.configured { color: #bfdbfe; background: #1a2e49; }
.health-badge.unavailable { color: #fecdd3; background: #3b202c; }
.compact-empty { margin: 0.5rem 0; padding: 0.65rem 0.8rem; border: 1px dashed #40516a; border-radius: 8px; background: #111d30; color: var(--text-muted); font-size: 0.82rem; }
.memory-state { display: inline-block; margin: 0.25rem 0 0.6rem; padding: 0.34rem 0.65rem; border-radius: 8px; font-size: 0.8rem; font-weight: 700; }
.memory-state.enabled { color: #86efac; background: #143528; }
.memory-state.disabled { color: #cbd5e1; background: #27364a; }

/* ---------- Cards (glass) ---------- */
.aegis-card {
    background: linear-gradient(150deg, #172438, #142033);
    border: 1px solid #2a3b52;
    border-radius: 11px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    backdrop-filter: blur(6px);
    animation: fadeIn 0.35s ease-out;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.aegis-card:hover { box-shadow: 0 12px 30px rgba(0,0,0,0.24); }

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
.pill-owner { color: #a9c9ff; background: rgba(59,130,246,0.18); }
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
    background: linear-gradient(150deg, #19283d 0%, #142136 100%);
    border: 1px solid #2b3d56;
    border-radius: 10px;
    padding: 1rem 0.85rem;
    text-align: center;
    box-shadow: 0 8px 22px rgba(0,0,0,0.18);
    transition: transform 0.15s ease, border-color 0.15s ease;
}
.metric-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.metric-value { font-size: 1.5rem; font-weight: 800; color: #8db7ff; }
.metric-label { color: var(--text-muted); font-size: 0.76rem; margin-top: 0.15rem; white-space: normal; word-wrap: break-word; line-height: 1.3; }
.metric-icon { font-size: 1.2rem; margin-bottom: 0.2rem; }

/* ---------- Status indicator ---------- */
.status-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 0.4rem; }
.status-online { background: var(--risk-low); box-shadow: 0 0 8px var(--risk-low); }
.status-degraded { background: var(--risk-medium); box-shadow: 0 0 8px var(--risk-medium); }
.status-offline { background: var(--risk-high); box-shadow: 0 0 8px var(--risk-high); }

/* ---------- Insight / notification cards ---------- */
.insight-card {
    background: rgba(59,130,246,0.05); border: 1px solid var(--border); border-left: 3px solid var(--accent);
    border-radius: 8px; padding: 0.65rem 0.9rem; margin-bottom: 0.5rem; font-size: 0.88rem;
}
.notif-card {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.6rem 0.85rem; margin-bottom: 0.45rem; font-size: 0.85rem;
}

/* ---------- Skeleton loaders ---------- */
.skeleton { background: linear-gradient(90deg, #1a293e 25%, #24364f 37%, #1a293e 63%); background-size: 400% 100%;
    animation: skeleton-shine 1.4s ease infinite; border-radius: 10px; }
@keyframes skeleton-shine { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
.skeleton-card { height: 84px; margin-bottom: 0.8rem; }
.skeleton-line { height: 14px; margin-bottom: 0.5rem; }

/* ---------- Quick action cards ---------- */
.quick-action {
    background: linear-gradient(150deg, #19283d 0%, #142136 100%); border: 1px solid #2b3d56; border-radius: 10px;
    padding: 0.9rem; text-align: center; transition: all 0.16s ease; cursor: pointer;
    box-shadow: 0 6px 18px rgba(0,0,0,0.16);
}
.quick-action:hover { border-color: #5d8fe2; transform: translateY(-2px); box-shadow: 0 9px 22px rgba(0,0,0,0.23); }
.quick-action .qa-icon { display: grid; place-items: center; width: 2.2rem; height: 2.2rem; margin: 0 auto 0.45rem; border-radius: 9px; background: #203653; font-size: 1.15rem; }

/* ---------- Login ---------- */
.login-top-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.65rem 0.5rem 1.2rem;
    margin-bottom: 1.2rem;
    border-bottom: 1px solid rgba(59, 130, 246, 0.16);
}
.login-brand-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.login-brand-shield {
    display: grid;
    place-items: center;
    width: 2.35rem;
    height: 2.35rem;
    border-radius: 9px;
    background: #193251;
    box-shadow: inset 0 0 0 1px #31517a, 0 0 14px rgba(37,99,235,0.22);
    font-size: 1.25rem;
}
.login-brand-name {
    font-size: 1.35rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.01em;
}
.login-brand-pipe {
    color: #3b506d;
    font-size: 1.1rem;
    font-weight: 300;
}
.login-brand-sub {
    color: #94a3b8;
    font-size: 0.82rem;
    font-weight: 500;
}
.login-badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    background: rgba(26, 44, 71, 0.75);
    border: 1px solid rgba(59, 130, 246, 0.28);
    color: #7dd3fc;
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.login-hero-eyebrow {
    color: #38bdf8;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.09em;
    margin-bottom: 0.55rem;
    text-transform: uppercase;
}
.login-hero-headline {
    font-size: 2.45rem;
    font-weight: 800;
    line-height: 1.12;
    color: #f8fafc;
    margin: 0 0 0.85rem 0;
    letter-spacing: -0.02em;
}
.hero-blue-accent {
    color: #3b82f6;
    text-shadow: 0 0 24px rgba(59, 130, 246, 0.35);
}
.login-hero-desc {
    color: #94a3b8;
    font-size: 0.92rem;
    line-height: 1.55;
    margin-bottom: 1.15rem;
    max-width: 520px;
}
.login-hero-features {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-bottom: 1.25rem;
}
.login-feature-item {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    background: rgba(22, 38, 62, 0.75);
    border: 1px solid rgba(59, 130, 246, 0.22);
    color: #e2e8f0;
    font-size: 0.78rem;
    font-weight: 600;
}
.login-feature-icon {
    font-size: 0.85rem;
}
.login-laptop-wrap {
    width: 100%;
    max-width: 480px;
    margin-top: 0.5rem;
}
.login-laptop-wrap svg {
    width: 100%;
    height: auto;
    display: block;
}
.login-panel-mark {
    display: grid;
    place-items: center;
    width: 3.2rem;
    height: 3.2rem;
    margin: 0 auto 0.45rem;
    border: 1px solid #355780;
    border-radius: 14px;
    background: #1a3150;
    font-size: 1.7rem;
    box-shadow: 0 0 20px rgba(37, 99, 235, 0.25);
}
.login-title {
    text-align: center;
    color: #f1f5fb;
    font-weight: 800;
    font-size: 1.6rem;
    margin: 0.1rem 0 0.1rem;
}
.login-subtitle {
    text-align: center;
    color: #94a3b8;
    font-size: 0.84rem;
    margin-bottom: 1.1rem;
}
.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(div.login-anchor) {
    position: relative;
    overflow: hidden;
    width: 100%;
    max-width: 520px;
    border: 1px solid rgba(59, 130, 246, 0.3) !important;
    border-radius: 18px !important;
    background: linear-gradient(160deg, rgba(22, 36, 58, 0.94) 0%, rgba(14, 23, 38, 0.96) 100%) !important;
    padding: 1.8rem 2rem !important;
    box-shadow: 0 24px 64px rgba(0,0,0,0.55), 0 0 35px rgba(37,99,235,0.14) !important;
    backdrop-filter: blur(18px) !important;
}
.stApp div[data-testid="stVerticalBlockBorderWrapper"]:has(div.login-anchor)::before {
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #2563eb 0%, #38bdf8 50%, #2563eb 100%);
    content: "";
}
.login-bottom-trust {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1.25rem;
    margin-top: 2.2rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(59, 130, 246, 0.15);
    color: #94a3b8;
    font-size: 0.78rem;
    font-weight: 600;
}
.trust-item {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    color: #cbd5e1;
}
.trust-dot {
    color: #475569;
    font-size: 0.7rem;
}
@media (max-width: 760px) {
    .login-top-header { flex-direction: column; gap: 0.6rem; align-items: flex-start; }
    .stApp div[data-testid="stHorizontalBlock"]:has(.login-hero-eyebrow) > div[data-testid="stColumn"]:has(.login-anchor) { order: -1; }
    .login-hero-headline { font-size: 1.9rem; }
    .login-bottom-trust { flex-wrap: wrap; gap: 0.65rem; }
}


/* ---------- Streamlit text and controls ---------- */
.stApp, .stApp [data-testid="stAppViewContainer"],
.stApp [data-testid="stMain"], .stApp [data-testid="stSidebar"] {
    color: var(--text-primary) !important;
}
.stApp p, .stApp li, .stApp label, .stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stExpander"] summary, .stApp [data-testid="stChatMessage"] {
    color: var(--text-primary) !important;
}
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] *,
.stApp [data-baseweb="input"] *, .stApp [data-testid="stChatInput"] textarea {
    color: var(--text-primary) !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    background-color: #101b2b !important;
}
.stApp input::placeholder, .stApp textarea::placeholder,
.stApp [data-testid="stChatInput"] textarea::placeholder {
    color: #a5b4c8 !important;
    -webkit-text-fill-color: #a5b4c8 !important;
    opacity: 1 !important;
}
.stApp [data-testid="stDataFrame"], .stApp [data-testid="stTable"] {
    color: var(--text-primary) !important;
    background-color: #172438 !important;
}
.stApp [data-testid="stAlert"], .stApp [data-testid="stNotification"] {
    background: #172438 !important;
    border-color: #33465f !important;
}
.stApp [data-testid="stExpander"] {
    background: rgba(19,31,49,0.72);
    border: 1px solid #2a3b52;
    border-radius: 9px;
}
.stApp [role="listbox"], .stApp [role="option"] {
    color: var(--text-primary) !important;
    background: #172438 !important;
}
.stApp pre, .stApp code {
    color: #dce8f8 !important;
    background: #101b2b !important;
}
.stApp [data-testid="stAlert"] *, .stApp [data-testid="stNotification"] * {
    color: var(--text-primary) !important;
}
.stApp button[kind="secondary"], .stApp [data-testid="stBaseButton-secondary"] {
    color: #ffffff !important;
}
.stApp button[kind="secondary"] *, .stApp [data-testid="stBaseButton-secondary"] * {
    color: #ffffff !important;
}
.stApp div[data-testid="stVerticalBlock"]:has(> div.nav-anchor) [data-testid="stBaseButton-secondary"],
.stApp div[data-testid="stVerticalBlock"]:has(> div.nav-anchor) [data-testid="stBaseButton-secondary"] * {
    color: var(--text-primary) !important;
}
.stApp button[kind="primary"], .stApp [data-testid="stBaseButton-primary"] {
    color: #ffffff !important;
}
.stApp button[kind="primary"] *, .stApp [data-testid="stBaseButton-primary"] *,
.stApp div[data-testid="stVerticalBlockBorderWrapper"] button * {
    color: #ffffff !important;
}

/* ---------- Sidebar nav list (replaces st.radio) ---------- */
.nav-item {
    padding: 0.4rem 0.7rem; border-radius: 7px; margin-bottom: 0.1rem;
    font-weight: 600; color: var(--text-muted); font-size: 0.86rem;
}
.nav-item-active {
    background: #1b3150; color: #b7d0ff !important;
    border-left: 3px solid var(--accent); font-weight: 700;
}
.sidebar-profile {
    display: flex; align-items: center; gap: 0.65rem;
    margin: 0.9rem 0 0.4rem; padding: 0.7rem;
    border: 1px solid #2b3d56; border-radius: 10px;
    background: linear-gradient(145deg, #172438, #142033);
}
.user-avatar {
    display: grid; place-items: center; flex: 0 0 2.2rem;
    width: 2.2rem; height: 2.2rem; border-radius: 50%;
    background: #223958; color: #c3d8ff; font-size: 1rem;
}
.user-details { display: flex; flex-direction: column; min-width: 0; line-height: 1.35; }
.user-details strong { overflow: hidden; color: var(--text-primary); font-size: 0.82rem; text-overflow: ellipsis; white-space: nowrap; }
.user-details span { overflow: hidden; color: var(--text-muted); font-size: 0.72rem; text-overflow: ellipsis; white-space: nowrap; }
.user-details small { color: #a5b4c8; font-size: 0.68rem; text-transform: capitalize; }
div[data-testid="stVerticalBlock"]:has(> div.nav-anchor) div[data-testid="stButton"] > button {
    background: transparent; color: var(--text-primary); text-align: left; justify-content: flex-start;
    border: 1px solid transparent; border-radius: 7px; font-weight: 600; box-shadow: none; padding: 0.4rem 0.7rem; min-height: 2.25rem;
}
div[data-testid="stVerticalBlock"]:has(> div.nav-anchor) div[data-testid="stButton"] > button:hover {
    background: rgba(59,130,246,0.1); border-color: var(--accent); transform: none;
}

/* ---------- Buttons / inputs ---------- */
div.stButton > button {
    background: linear-gradient(180deg, #3978e8, #2867d5); color: #ffffff; border-radius: 8px; border: 1px solid #5489e5; font-weight: 650; min-height: 2.35rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    transition: background-color 0.15s ease, transform 0.1s ease, box-shadow 0.15s ease;
}
div.stButton > button:hover { background: var(--accent-hover); transform: translateY(-1px); box-shadow: 0 6px 16px rgba(0,0,0,0.28); }
div.stButton > button:focus-visible { outline: 3px solid rgba(122,169,255,0.48); outline-offset: 2px; }
div[data-baseweb="input"] > div, .stTextInput input, .stChatInput textarea {
    background-color: var(--bg-card) !important; border: 1px solid var(--border) !important; color: var(--text-primary) !important;
    border-radius: 10px !important;
}
div[data-baseweb="input"] > div:focus-within, .stTextInput input:focus, .stChatInput textarea:focus {
    border-color: #6b9af0 !important; box-shadow: 0 0 0 3px rgba(87,144,245,0.24) !important;
}
div[data-testid="stChatInput"] textarea { font-size: 0.96rem; }

/* Improve legibility for all default Streamlit text */
div, p, li, span, label, .stMarkdown, .stCaption, .stDataFrame, .stTable {
    color: var(--text-primary);
}

[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
button[kind="secondary"],
button[kind="primary"] {
    color: #ffffff !important;
}

/* ---------- Suggested prompt chips ---------- */
.chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.5rem 0 1rem 0; }
.chip {
    background: rgba(59,130,246,0.16); border: 1px solid #4b80d0; color: #c0d6ff;
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
kbd { background: #26364c; color: var(--text-primary); border: 1px solid #40516a; border-radius: 4px; padding: 0 5px; font-size: 0.75rem; }
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
