# tools/auth.py
from __future__ import annotations

import json

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def supabase_client() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"],
    )


def cookie_manager() -> EncryptedCookieManager:
    if "_cookie_manager" not in st.session_state:
        st.session_state["_cookie_manager"] = EncryptedCookieManager(
            prefix="apptracker_",
            password=st.secrets["cookies"]["secret"],
        )
    cm = st.session_state["_cookie_manager"]
    if not cm.ready():
        st.stop()
    return cm


def _save_session_cookie(session) -> None:
    cm = cookie_manager()
    cm["sb_session"] = json.dumps({
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    })
    cm.save()


def _load_session_from_cookie() -> bool:
    try:
        cm = cookie_manager()
        raw = cm.get("sb_session")
        if not raw:
            return False
        tokens = json.loads(raw)
        result = supabase_client().auth.set_session(
            tokens["access_token"],
            tokens["refresh_token"],
        )
        if result.user:
            st.session_state["sb_session"] = result.session
            return True
    except Exception:
        try:
            cm = cookie_manager()
            del cm["sb_session"]
            cm.save()
        except Exception:
            pass
    return False


def delete_session_cookie() -> None:
    try:
        cm = cookie_manager()
        del cm["sb_session"]
        cm.save()
    except Exception:
        pass