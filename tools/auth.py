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