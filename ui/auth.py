"""Simple session-based login gate. No real backend auth is required per spec --
this only gates access to the app for a polished enterprise feel."""
import streamlit as st


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def login():
    st.session_state.authenticated = True
    st.session_state.user_email = st.session_state.get("_login_email") or "demo.user@aegis.ai"


def logout():
    st.session_state.authenticated = False


def render_login_screen():
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(div.login-anchor) {
            background: rgba(19,26,42,0.92); border: 1px solid #232B3D !important; border-radius: 18px;
            padding: 1rem 1.4rem; box-shadow: 0 12px 40px rgba(0,0,0,0.45);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.markdown('<div class="login-anchor"></div>', unsafe_allow_html=True)
            st.markdown('<div class="login-logo">🛡️</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-title">Aegis</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-subtitle">Enterprise AI Agent for Compliance Operations</div>', unsafe_allow_html=True)

            st.text_input("Email", placeholder="you@company.com", key="_login_email")
            st.text_input("Password", type="password", placeholder="••••••••", key="_login_password")
            st.checkbox("Remember me", key="_login_remember")

            if st.button("Sign In", use_container_width=True):
                login()
                st.rerun()

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🪟 Microsoft", use_container_width=True):
                    login()
                    st.rerun()
            with c2:
                if st.button("🔵 Google", use_container_width=True):
                    login()
                    st.rerun()

            st.divider()
            if st.button("▶ Demo Login", use_container_width=True):
                login()
                st.rerun()
