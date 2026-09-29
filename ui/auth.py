"""Real credential-based authentication for Aegis.

Stores users in the existing audit.db (database/auth_users table).
Passwords are hashed with bcrypt — never stored in plaintext.
No demo login, no OAuth fakes, no hardcoded credentials.

Public surface:
    is_authenticated() -> bool
    get_current_user()  -> dict | None   {user_id, email, role, display_name}
    logout()
    render_login_screen()
"""

import os
import sqlite3
import streamlit as st
import bcrypt
from datetime import datetime

# ---------------------------------------------------------------------------
# Database location — same file as audit_logger uses
# ---------------------------------------------------------------------------
_DB_PATH = os.path.join("database", "auth.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS auth_users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT   NOT NULL,
    password_hash TEXT  NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'compliance_officer',
    created_at  TEXT    NOT NULL
);
"""

# Per-user persistent data (chat_history, pinned_questions, saved_responses, recent_searches)
_SCHEMA_USER_DATA = """
CREATE TABLE IF NOT EXISTS user_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    data_type   TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    UNIQUE(user_id, data_type)
);
"""


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    conn.execute(_SCHEMA_USER_DATA)
    conn.commit()
    return conn


def _find_user(email: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM auth_users WHERE email = ? COLLATE NOCASE", (email.strip(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _create_user(email: str, display_name: str, plain_password: str, role: str = "compliance_officer") -> tuple[bool, str]:
    """Hash password with bcrypt and insert.  Returns (ok, message)."""
    if not email.strip() or "@" not in email:
        return False, "Enter a valid email address."
    if len(plain_password) < 8:
        return False, "Password must be at least 8 characters."
    if not display_name.strip():
        return False, "Display name is required."

    pw_hash = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO auth_users (email, display_name, password_hash, role, created_at) VALUES (?,?,?,?,?)",
            (email.strip().lower(), display_name.strip(), pw_hash, role, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "An account with that email already exists."
    except Exception as exc:
        return False, f"Registration failed: {exc}"


def _verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API (imported by app.py)
# ---------------------------------------------------------------------------

def is_authenticated() -> bool:
    """True only when a real credential-verified session is active."""
    return bool(st.session_state.get("_auth_verified") and st.session_state.get("_auth_user_id"))


def get_current_user() -> dict | None:
    """Returns the authenticated user dict or None."""
    if not is_authenticated():
        return None
    return {
        "user_id": st.session_state.get("_auth_user_id"),
        "email":   st.session_state.get("_auth_email"),
        "role":    st.session_state.get("_auth_role", "compliance_officer"),
        "display_name": st.session_state.get("_auth_display_name", ""),
    }


def _clear_user_state() -> None:
    """Clear user-owned UI state without touching unrelated app configuration."""
    keys = []
    for key in list(st.session_state.keys()):
        if key in {
            "chat_history", "pinned_questions", "saved_responses", "recent_searches",
            "pending_reviews", "memory_toggle", "memory_enabled", "_agent_user_id",
            "_auth_last_user", "nav_page", "compare_off", "compare_on",
        } or key.startswith(("compare_", "reject_mode_", "corr_", "expander_", "nav_")):
            keys.append(key)
    for key in keys:
        st.session_state.pop(key, None)


def logout() -> None:
    """Clear all auth session state."""
    _clear_user_state()
    for key in ("_auth_verified", "_auth_user_id", "_auth_email", "_auth_role",
                "_auth_display_name", "_auth_last_user"):
        st.session_state.pop(key, None)


def _do_signin(email: str, password: str) -> tuple[bool, str]:
    """Validate credentials.  Returns (ok, message)."""
    if not email.strip() or not password:
        return False, "Email and password are required."
    user = _find_user(email)
    if user is None:
        # Constant-time-ish failure (still run bcrypt to avoid timing oracle)
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt()))
        return False, "Invalid email or password."
    if not _verify_password(password, user["password_hash"]):
        return False, "Invalid email or password."
    # Clear any lingering user-scoped UI state before authenticating this user.
    _clear_user_state()
    st.session_state["_auth_verified"] = True
    st.session_state["_auth_user_id"]   = str(user["id"])
    st.session_state["_auth_email"]     = user["email"]
    st.session_state["_auth_role"]      = user["role"]
    st.session_state["_auth_display_name"] = user["display_name"]
    return True, "Signed in."


# ---------------------------------------------------------------------------
# Per-user persistent data helpers
# ---------------------------------------------------------------------------

_PERSISTED_KEYS = ("chat_history", "pinned_questions", "saved_responses", "recent_searches")


def load_user_data(user_id: str) -> dict:
    """Load all persisted user data from the DB.  Returns a dict with list values.

    Any key not yet stored returns an empty list.  Never raises.
    """
    result = {k: [] for k in _PERSISTED_KEYS}
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT data_type, payload FROM user_data WHERE user_id = ?", (int(user_id),)
        ).fetchall()
        conn.close()
        for row in rows:
            key = row["data_type"]
            if key in result:
                import json as _json
                result[key] = _json.loads(row["payload"])
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("load_user_data failed: %s", exc)
    return result


def save_user_data(user_id: str, key: str, value: list) -> None:
    """Upsert one persisted data list for a user.  Never raises."""
    if key not in _PERSISTED_KEYS:
        return
    try:
        import json as _json
        payload = _json.dumps(value, default=str)
        conn = _get_conn()
        conn.execute(
            """INSERT INTO user_data (user_id, data_type, payload, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, data_type) DO UPDATE SET
                   payload    = excluded.payload,
                   updated_at = excluded.updated_at""",
            (int(user_id), key, payload, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("save_user_data failed for key=%s: %s", key, exc)


# ---------------------------------------------------------------------------
# Login / Register UI
# ---------------------------------------------------------------------------

_LAPTOP_SVG = """<svg width="480" height="240" viewBox="0 0 480 240" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="lapDeskGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#2563eb" stop-opacity="0.38" />
      <stop offset="65%" stop-color="#1d4ed8" stop-opacity="0.12" />
      <stop offset="100%" stop-color="#0284c7" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="lapBezelGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
    <linearGradient id="lapDisplayGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#091322" />
      <stop offset="100%" stop-color="#050a14" />
    </linearGradient>
    <linearGradient id="lapDeckGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" />
      <stop offset="50%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#020617" />
    </linearGradient>
  </defs>
  <ellipse cx="240" cy="198" rx="195" ry="30" fill="url(#lapDeskGlow)" />
  <rect x="75" y="14" width="330" height="178" rx="12" fill="url(#lapBezelGrad)" stroke="#334155" stroke-width="1.5" />
  <rect x="77" y="16" width="326" height="174" rx="10" fill="none" stroke="#1e3a5f" stroke-width="1" />
  <rect x="85" y="24" width="310" height="158" rx="6" fill="url(#lapDisplayGrad)" stroke="#1e293b" stroke-width="0.8" />
  <rect x="85" y="24" width="310" height="18" rx="6" fill="#0d1829" />
  <circle cx="98" cy="33" r="3" fill="#ef4444" />
  <circle cx="108" cy="33" r="3" fill="#f59e0b" />
  <circle cx="118" cy="33" r="3" fill="#10b981" />
  <text x="240" y="36" text-anchor="middle" fill="#64748b" font-family="Inter,system-ui,sans-serif" font-size="8" font-weight="600">Aegis Compliance System — Active</text>
  <path d="M240 52 L262 61 C262 78 253 93 240 100 C227 93 218 78 218 61 Z" fill="#172554" stroke="#3b82f6" stroke-width="2" />
  <path d="M233 74 L238 79 L249 68" stroke="#60a5fa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none" />
  <rect x="96" y="108" width="86" height="60" rx="6" fill="#0c192c" stroke="#1e3a5f" stroke-width="0.8" />
  <text x="103" y="120" fill="#94a3b8" font-family="Inter,system-ui,sans-serif" font-size="7" font-weight="700">POLICY ENGINE</text>
  <rect x="103" y="126" width="72" height="4" rx="2" fill="#1e293b" />
  <rect x="103" y="126" width="60" height="4" rx="2" fill="#3b82f6" />
  <rect x="103" y="135" width="72" height="4" rx="2" fill="#1e293b" />
  <rect x="103" y="135" width="48" height="4" rx="2" fill="#0ea5e9" />
  <rect x="103" y="144" width="72" height="4" rx="2" fill="#1e293b" />
  <rect x="103" y="144" width="68" height="4" rx="2" fill="#22c55e" />
  <text x="103" y="160" fill="#38bdf8" font-family="Inter,system-ui,sans-serif" font-size="7" font-weight="600">Active · Grounded</text>
  <rect x="190" y="108" width="100" height="60" rx="6" fill="#0c192c" stroke="#1e3a5f" stroke-width="0.8" />
  <text x="197" y="120" fill="#94a3b8" font-family="Inter,system-ui,sans-serif" font-size="7" font-weight="700">RISK CLASSIFIER</text>
  <path d="M197 141 Q 210 125, 222 137 T 247 129 T 272 139 T 283 133" fill="none" stroke="#3b82f6" stroke-width="1.8" />
  <circle cx="283" cy="133" r="2.5" fill="#60a5fa" />
  <text x="197" y="160" fill="#4ade80" font-family="Inter,system-ui,sans-serif" font-size="7" font-weight="600">✓ Risk Monitored</text>
  <rect x="298" y="108" width="86" height="60" rx="6" fill="#0c192c" stroke="#1e3a5f" stroke-width="0.8" />
  <text x="305" y="120" fill="#94a3b8" font-family="Inter,system-ui,sans-serif" font-size="7" font-weight="700">GOVERNANCE GATE</text>
  <rect x="305" y="126" width="72" height="15" rx="3" fill="#142842" stroke="#2563eb" stroke-width="0.6" />
  <text x="341" y="137" text-anchor="middle" fill="#93c5fd" font-family="Inter,system-ui,sans-serif" font-size="7" font-weight="700">PASSED</text>
  <text x="305" y="160" fill="#cbd5e1" font-family="Inter,system-ui,sans-serif" font-size="7">Deterministic</text>
  <circle cx="240" cy="19" r="2" fill="#0f172a" stroke="#334155" stroke-width="0.6" />
  <path d="M40 210 L88 192 L392 192 L440 210 C442 211 443 213 441 215 L435 218 C433 219 431 220 428 220 L52 220 C49 220 47 219 45 218 L39 215 C37 213 38 211 40 210 Z" fill="url(#lapDeckGrad)" stroke="#334155" stroke-width="1.2" />
  <rect x="180" y="190" width="120" height="4" rx="2" fill="#0f172a" stroke="#1e293b" stroke-width="0.8" />
  <path d="M96 195 L112 208 L368 208 L384 195 Z" fill="#0b1220" opacity="0.85" />
  <path d="M216 210 L220 218 L260 218 L264 210 Z" fill="#131e33" stroke="#1e293b" stroke-width="0.6" />
  <line x1="60" y1="219" x2="420" y2="219" stroke="#3b82f6" stroke-width="1.2" opacity="0.6" />
</svg>"""


def render_login_screen() -> None:
    """Renders the Sign In / Register form.  No demo login, no fake OAuth."""
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(ellipse at 25% 35%, #0f1c33 0%, #070c18 65%, #040810 100%) !important;
            background-attachment: fixed !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        main .block-container {
            max-width: 1360px !important;
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # TOP HEADER: Aegis shield, Aegis, divider, Enterprise AI Agent for Compliance Operations, Secure • Intelligent • Compliant
    st.markdown(
        """
        <div class="login-top-header">
            <div class="login-brand-group">
                <span class="login-brand-shield">🛡️</span>
                <span class="login-brand-name">Aegis</span>
                <span class="login-brand-pipe">|</span>
                <span class="login-brand-sub">Enterprise AI Agent for Compliance Operations</span>
            </div>
            <div class="login-badge-pill">
                <span>Secure • Intelligent • Compliant</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_hero, col_card = st.columns([1.12, 0.88], gap="large")

    with col_hero:
        st.markdown(
            f"""
            <div class="login-hero-eyebrow">AI THAT WORKS FOR COMPLIANCE</div>
            <h1 class="login-hero-headline">Smarter Compliance.<br/><span class="hero-blue-accent">Stronger Enterprises.</span></h1>
            <p class="login-hero-desc">Aegis brings policy, risk, and governance into one traceable workflow for your compliance team.</p>
            <div class="login-hero-features">
                <div class="login-feature-item"><span class="login-feature-icon">🛡️</span> Automated Monitoring</div>
                <div class="login-feature-item"><span class="login-feature-icon">⚡</span> AI-Powered Agents</div>
                <div class="login-feature-item"><span class="login-feature-icon">✓</span> Audit Ready</div>
            </div>
            <div class="login-laptop-wrap">
                {_LAPTOP_SVG}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_card:
        with st.container(border=True):
            st.markdown('<div class="login-anchor"></div>', unsafe_allow_html=True)
            st.markdown('<div class="login-panel-mark">🛡️</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-title">Aegis</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="login-subtitle">Sign in to your account</div>',
                unsafe_allow_html=True,
            )

            tab_signin, tab_register = st.tabs(["Sign In", "Register"])

            # ---------------------------------------------------------------- Sign In
            with tab_signin:
                # If a successful registration just occurred, pre-fill the email.
                # We read the staging key here — before the widget is instantiated —
                # so writing to "_si_email" at this point is safe.
                if "_si_email_prefill" in st.session_state:
                    st.session_state["_si_email"] = st.session_state.pop("_si_email_prefill")
                si_email    = st.text_input("Email", placeholder="you@company.com", key="_si_email")
                si_password = st.text_input("Password", type="password", placeholder="••••••••", key="_si_password")

                if st.button("Sign In", use_container_width=True, key="_si_submit"):
                    ok, msg = _do_signin(si_email, si_password)
                    if ok:
                        # Scope per-user session data: clear any previous user's history
                        prev_user = st.session_state.get("_auth_last_user")
                        curr_user = st.session_state.get("_auth_user_id")
                        if prev_user and prev_user != curr_user:
                            for k in ("chat_history", "pinned_questions", "saved_responses", "recent_searches"):
                                st.session_state.pop(k, None)
                        st.session_state["_auth_last_user"] = curr_user
                        st.rerun()
                    else:
                        st.error(msg)

            # ---------------------------------------------------------------- Register
            with tab_register:
                reg_name     = st.text_input("Display Name", placeholder="Jane Smith", key="_reg_name")
                reg_email    = st.text_input("Email", placeholder="you@company.com", key="_reg_email")
                reg_password = st.text_input("Password (min 8 characters)", type="password", key="_reg_password")
                reg_confirm  = st.text_input("Confirm Password", type="password", key="_reg_confirm")

                if st.button("Create Account", use_container_width=True, key="_reg_submit"):
                    if reg_password != reg_confirm:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = _create_user(reg_email, reg_name, reg_password)
                        if ok:
                            # Pre-fill the Sign In email on the next render by staging
                            # the value under a separate key.  We cannot write directly
                            # to "_si_email" here because that key is already bound to
                            # the text_input widget instantiated earlier in this run
                            # (StreamlitAPIException: cannot modify after instantiation).
                            st.session_state["_si_email_prefill"] = reg_email.strip().lower()
                            st.success("Account created. Switching to Sign In…")
                            st.rerun()
                        else:
                            st.error(msg)

    # BOTTOM: Secure Access • AI-Powered • Built for Enterprises
    st.markdown(
        """
        <div class="login-bottom-trust">
            <div class="trust-item"><span class="login-feature-icon">🔒</span> Secure Access</div>
            <div class="trust-dot">•</div>
            <div class="trust-item"><span class="login-feature-icon">⚡</span> AI-Powered</div>
            <div class="trust-dot">•</div>
            <div class="trust-item"><span class="login-feature-icon">🏢</span> Built for Enterprises</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

