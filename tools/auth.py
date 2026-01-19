# tools/auth.py
from __future__ import annotations

import streamlit as st
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def supabase_client() -> Client:
    """
    Cached Supabase client using anon key.
    Used for auth + anything else Supabase-related.
    """
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"],
    )


def require_login() -> str:
    """
    Ensure the user is logged in.
    - If logged in: return the Supabase auth user's UUID.
    - If not: render login/signup UI and stop the app.
    """
    # If we already have a session, just return the user id
    if "sb_session" in st.session_state and st.session_state["sb_session"]:
        return st.session_state["sb_session"].user.id

    st.subheader("Sign in")

    tab_login, tab_signup = st.tabs(["Log in", "Create account"])

    # --- Login tab ---
    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")

        if st.button("Log in", use_container_width=True):
            try:
                res = supabase_client().auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                if res.session:
                    st.session_state["sb_session"] = res.session
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
            except Exception as e:
                st.error(f"Login failed: {e}")

    # --- Signup tab ---
    with tab_signup:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pw")

        if st.button("Create account", use_container_width=True):
            try:
                supabase_client().auth.sign_up(
                    {"email": email, "password": password}
                )
                st.success(
                    "Account created. Check your email if confirmations are enabled."
                )
            except Exception as e:
                st.error(f"Sign-up failed: {e}")

    # Stop the Streamlit script until the user logs in
    st.stop()