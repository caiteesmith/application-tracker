# tools/auth.py
from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def supabase_client() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"],
    )


def load_session_from_storage() -> bool:
    """
    Injects a JS snippet that reads tokens from localStorage and
    writes them into the URL query params so Streamlit can read them.
    Only runs if there's no active session in session_state already.
    """
    if st.session_state.get("sb_session"):
        return True

    # Read tokens from localStorage and push into query params
    components.html(
        """
        <script>
        const access = localStorage.getItem('sb_access_token');
        const refresh = localStorage.getItem('sb_refresh_token');
        if (access && refresh) {
            const url = new URL(window.parent.location.href);
            const current_access = url.searchParams.get('sb_access');
            // Only update if not already set to avoid infinite reloads
            if (!current_access) {
                url.searchParams.set('sb_access', access);
                url.searchParams.set('sb_refresh', refresh);
                window.parent.location.replace(url.toString());
            }
        }
        </script>
        """,
        height=0,
    )

    # Try to restore from query params
    params = st.query_params
    access_token = params.get("sb_access")
    refresh_token = params.get("sb_refresh")

    if access_token and refresh_token:
        try:
            result = supabase_client().auth.set_session(access_token, refresh_token)
            if result.user:
                st.session_state["sb_session"] = result.session
                # Clear tokens from URL so they're not visible
                st.query_params.clear()
                return True
        except Exception:
            st.query_params.clear()

    return False


def save_session_to_storage(session) -> None:
    """
    Saves tokens to localStorage via a JS snippet so they persist
    across tab closes and refreshes.
    """
    access = session.access_token
    refresh = session.refresh_token
    components.html(
        f"""
        <script>
        localStorage.setItem('sb_access_token', '{access}');
        localStorage.setItem('sb_refresh_token', '{refresh}');
        </script>
        """,
        height=0,
    )


def clear_session_storage() -> None:
    """Clears tokens from localStorage on sign out."""
    components.html(
        """
        <script>
        localStorage.removeItem('sb_access_token');
        localStorage.removeItem('sb_refresh_token');
        </script>
        """,
        height=0,
    )