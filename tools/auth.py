# tools/auth.py
from __future__ import annotations

import json
from datetime import datetime, timedelta

import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def supabase_client() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"],
    )


@st.cache_resource(show_spinner=False)
def cookie_manager():
    cm = stx.CookieManager()
    _ = cm.get_all()  # force initialization on first render
    return cm


def _save_session_cookie(session) -> None:
    cookie_manager().set(
        "sb_session",
        json.dumps({
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }),
        expires_at=datetime.now() + timedelta(days=30),
    )


def _load_session_from_cookie() -> bool:
    raw = cookie_manager().get("sb_session")
    if not raw:
        return False
    try:
        tokens = json.loads(raw)
        result = supabase_client().auth.set_session(
            tokens["access_token"],
            tokens["refresh_token"],
        )
        if result.user:
            st.session_state["sb_session"] = result.session
            return True
    except Exception:
        cookie_manager().delete("sb_session")
    return False


def logout() -> None:
    supabase_client().auth.sign_out()
    cookie_manager().delete("sb_session")
    st.session_state.pop("sb_session", None)
    st.rerun()


def require_login() -> str:
    # 1. Already have an in-memory session
    if st.session_state.get("sb_session"):
        return st.session_state["sb_session"].user.id

    # 2. Try to restore from cookie (survives tab close / refresh)
    if _load_session_from_cookie():
        return st.session_state["sb_session"].user.id

    # 3. No session — show login UI
    st.subheader("Sign in")
    tab_login, tab_signup = st.tabs(["Log in", "Create account"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")

        if st.button("Log in", width="stretch"):
            try:
                res = supabase_client().auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                if res.session:
                    st.session_state["sb_session"] = res.session
                    _save_session_cookie(res.session)
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab_signup:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pw")

        if st.button("Create account", width="stretch"):
            try:
                supabase_client().auth.sign_up(
                    {"email": email, "password": password}
                )
                st.success(
                    "Account created. Check your email if confirmations are enabled."
                )
            except Exception as e:
                st.error(f"Sign-up failed: {e}")

    st.stop()