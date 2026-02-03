# app.py
from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional
import pandas as pd

import streamlit as st
from tools.sankey import render_sankey_section
from tools.analytics import render_analytics_section
from tools.auth import supabase_client

from tools.db import (
    list_applications,
    get_application,
    upsert_application,
    delete_application,
    list_snapshots,
    add_snapshot,
)

# -------------------------
# Config & constants
# -------------------------
STATUS_OPTIONS = [
    "Applied",
    "Rejected",
    "Recruiter Screen",
    "Interview 1",
    "Interview 2+",
    "Final Round",
    "Offer",
    "Accepted",
    "Withdrawn",
    "Ghosted",
    "Wishlist",
]

LOCATION_TYPES = ["Remote", "Hybrid", "Onsite", "Unknown"]
SCREENSHOT_DIR = os.path.join("data", "screenshots")


# -------------------------
# Helpers
# -------------------------
def _ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _money(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    try:
        return f"${float(val):,.0f}"
    except Exception:
        return "—"


def _format_app_option(row) -> str:
    company = row.get("company") or "Unknown company"
    title = row.get("title") or "Unknown role"
    status = row.get("status") or "Unknown status"
    applied = row.get("applied_date") or ""
    if applied:
        return f"{company} — {title} ({status}, {applied})"
    return f"{company} — {title} ({status})"


def _parse_date_str(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None


def _clear_new_application_form_state():
    keys = [
        "new_company",
        "new_title",
        "new_location_type",
        "new_location_detail",
        "new_salary_min",
        "new_salary_max",
        "new_link_url",
        "new_applied_date",
        "new_status",
        "new_description_short",
        "new_notes",
        "new_next_follow_up_date",
    ]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


def get_current_user_id() -> Optional[str]:
    session = st.session_state.get("sb_session")
    if session is None:
        return None
    try:
        return session.user.id
    except Exception:
        return None


def _load_demo_applications() -> pd.DataFrame:
    data = [
        {
            "id": "demo-1",
            "company": "Ministry of Magic",
            "title": "Senior Auror",
            "status": "Interview 1",
            "location_type": "Hybrid",
            "location_detail": "London, UK (Level Two)",
            "salary_min": 120000,
            "salary_max": 150000,
            "link_url": "https://ministry.example/jobs/auror",
            "description_short": "High-risk field role focused on dark wizard containment and magical law enforcement.",
            "notes": "Kingsley seemed impressed; asked about Patronus proficiency.",
            "applied_date": "2025-01-10",
            "next_follow_up_date": "2025-01-20",
        },
        {
            "id": "demo-2",
            "company": "Weasleys' Wizard Wheezes",
            "title": "Magical Product Engineer",
            "status": "Applied",
            "location_type": "Onsite",
            "location_detail": "Diagon Alley, London",
            "salary_min": 85000,
            "salary_max": 110000,
            "link_url": "https://weasley.example/jobs/product-engineer",
            "description_short": "R&D for joke products, portable swamps, enchanted fireworks, and novelty magic.",
            "notes": "Job description says 'sense of humor required.' Perfect culture fit.",
            "applied_date": "2025-01-14",
            "next_follow_up_date": "2025-01-21",
        },
        {
            "id": "demo-3",
            "company": "Hogwarts School of Witchcraft & Wizardry",
            "title": "Defense Against the Dark Arts Professor",
            "status": "Rejected",
            "location_type": "Onsite",
            "location_detail": "Highlands, Scotland",
            "salary_min": 95000,
            "salary_max": 130000,
            "link_url": "",
            "description_short": "One-year renewable contract. Historically unstable role. Must be comfortable with curses.",
            "notes": "Letter said: 'Position filled by unexpected candidate.' Figures.",
            "applied_date": "2024-12-05",
            "next_follow_up_date": None,
        },
    ]
    return pd.DataFrame(data)


# -------------------------
# Main app
# -------------------------
def main():
    st.set_page_config(
        page_title="ApplicationTracker",
        layout="wide",
    )

    _ensure_dirs()

    user_id = get_current_user_id()
    is_logged_in = user_id is not None

    if is_logged_in:
        df = list_applications(user_id=user_id)
    else:
        df = _load_demo_applications()

    with st.sidebar:
        st.title("ApplicationTracker")
        st.caption(
            "You can use this tool without an account. If you want to save and come back later, log in or sign up below."
        )

        st.markdown("### Filters")

        status_filter = st.multiselect(
            "Status",
            options=STATUS_OPTIONS,
            default=STATUS_OPTIONS,
        )

        location_filter = st.multiselect(
            "Location type",
            options=LOCATION_TYPES,
            default=LOCATION_TYPES,
        )

        search_text = st.text_input(
            "Search (company, title, notes)",
            value="",
            placeholder="e.g., backend, Netflix, remote",
        )

        st.markdown("---")

        if is_logged_in:
            st.success("Signed in")
            st.caption("Your applications and screenshots are stored in a private, secure database.")

            if st.button("Sign out", use_container_width=True):
                sb = supabase_client()
                sb.auth.sign_out()
                for k in ["sb_session", "login_email", "login_pw", "signup_email", "signup_pw"]:
                    st.session_state.pop(k, None)
                st.rerun()

        else:
            with st.expander("Login / Sign Up", expanded=False):
                tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

                with tab_login:
                    st.subheader("Welcome back")
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

                with tab_signup:
                    st.subheader("Create an account")
                    email = st.text_input("Email", key="signup_email")
                    password = st.text_input("Password", type="password", key="signup_pw")

                    if st.button("Sign up", use_container_width=True):
                        try:
                            supabase_client().auth.sign_up(
                                {"email": email, "password": password}
                            )
                            st.success("Account created. Check your email if confirmations are enabled.")
                        except Exception as e:
                            st.error(f"Sign-up failed: {e}")

        filtered_df = df.copy()

        if not filtered_df.empty:
            if status_filter:
                filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]

            if location_filter:
                filtered_df = filtered_df[
                    filtered_df["location_type"].isin(location_filter)
                ]

            if search_text.strip():
                text = search_text.strip().lower()
                mask = (
                    filtered_df["company"]
                    .fillna("")
                    .str.lower()
                    .str.contains(text)
                    | filtered_df["title"]
                    .fillna("")
                    .str.lower()
                    .str.contains(text)
                    | filtered_df["notes"]
                    .fillna("")
                    .str.lower()
                    .str.contains(text)
                )
                filtered_df = filtered_df[mask]

    if "selected_app_id" not in st.session_state:
        st.session_state["selected_app_id"] = None
    if "mode" not in st.session_state:
        st.session_state["mode"] = "view"

    st.title("ApplicationTracker")

    if not is_logged_in:
        st.warning(
            "You're exploring the demo view. Sign in to add applications, edit details, and upload screenshots."
        )

    st.subheader("Overview")
    render_analytics_section(filtered_df)

    col_left, col_right = st.columns([0.6, 0.4])

    # -------------------------
    # Left column: Table & selection
    # -------------------------
    with col_left:
        st.subheader("Applications")

        if filtered_df.empty:
            if is_logged_in:
                st.info(
                    "No applications yet. Click **Add new application** to get started."
                )
            else:
                st.info(
                    "No demo data available. Sign in to start tracking your real applications."
                )
        else:
            table_cols = [
                "applied_date",
                "company",
                "title",
                "status",
                "location_type",
                "salary_min",
                "salary_max",
            ]
            table_cols = [c for c in table_cols if c in filtered_df.columns]
            display_df = filtered_df[table_cols].copy()

            if "salary_min" in display_df.columns:
                display_df["salary_min"] = display_df["salary_min"].apply(_money)
            if "salary_max" in display_df.columns:
                display_df["salary_max"] = display_df["salary_max"].apply(_money)

            st.dataframe(
                display_df.rename(
                    columns={
                        "applied_date": "Applied",
                        "company": "Company",
                        "title": "Title",
                        "status": "Status",
                        "location_type": "Location",
                        "salary_min": "Salary (min)",
                        "salary_max": "Salary (max)",
                    }
                ),
                use_container_width=True,
                height=600,
            )

            if is_logged_in:
                st.markdown("##### Select an application to view/edit")

                options = []
                for _, row in filtered_df.iterrows():
                    options.append((_format_app_option(row), row["id"]))

                label_to_id = {label: app_id for label, app_id in options}
                labels = [label for label, _ in options]

                current_label: Optional[str] = None
                if st.session_state["selected_app_id"]:
                    for label, app_id in options:
                        if app_id == st.session_state["selected_app_id"]:
                            current_label = label
                            break

                selected_label = st.selectbox(
                    "Application",
                    options=["(none)"] + labels,
                    index=(
                        labels.index(current_label) + 1
                        if current_label in labels
                        else 0
                    ),
                    label_visibility="collapsed",
                )

                if selected_label != "(none)":
                    st.session_state["selected_app_id"] = label_to_id[selected_label]
                    if st.session_state["mode"] == "new":
                        st.session_state["mode"] = "view"
                else:
                    st.session_state["selected_app_id"] = None
            else:
                st.caption(
                    "Demo view is read-only. Sign in to select applications and manage them."
                )

    # -------------------------
    # Right column: detail/new form
    # -------------------------
    with col_right:
        st.subheader("Add/Review")

        if not is_logged_in:
            st.button(
                "Sign in to add your own applications",
                use_container_width=True,
                disabled=True,
            )
            st.caption(
                "Once you're signed in, you'll be able to add new applications, edit details, and upload screenshots here."
            )
        else:
            st.button(
                "➕ Add new application",
                use_container_width=True,
                on_click=_set_mode_new,
            )

            if st.session_state["mode"] == "new":
                _render_new_application_form(user_id)
            else:
                _render_detail_panel(st.session_state["selected_app_id"], user_id)

    st.markdown("---")

    render_sankey_section(filtered_df)


# -------------------------
# UI subcomponents
# -------------------------
def _set_mode_new():
    _clear_new_application_form_state()
    st.session_state["mode"] = "new"
    st.session_state["selected_app_id"] = None


def _render_new_application_form(user_id: str):
    st.subheader("New application")

    with st.form("new_application_form"):
        title = st.text_input("Job title *")
        company = st.text_input("Company *")

        col1, col2 = st.columns(2)
        with col1:
            location_type = st.selectbox("Location type", LOCATION_TYPES, index=0)
        with col2:
            location_detail = st.text_input("Location detail (city, state)")

        col3, col4 = st.columns(2)
        with col3:
            salary_min = st.number_input(
                "Salary min (base)", min_value=0.0, step=1000.0
            )
        with col4:
            salary_max = st.number_input(
                "Salary max (base)", min_value=0.0, step=1000.0
            )

        link_url = st.text_input("Job posting URL")
        applied_date = st.date_input("Date applied", value=date.today())

        status = st.selectbox("Status", STATUS_OPTIONS, index=0)

        description_short = st.text_area(
            "Short description / key notes",
            placeholder=(
                "Key responsibilities, tech stack, why this role caught your eye..."
            ),
        )

        notes = st.text_area(
            "Private notes",
            placeholder="Interviewers, vibes, red flags, compensation details, etc.",
        )

        next_follow_up_date = st.date_input(
            "Next follow-up date",
            value=date.today(),
        )

        submitted = st.form_submit_button(
            "Save application", use_container_width=True
        )

        if submitted:
            if not company.strip() or not title.strip():
                st.error("Company and Job title are required.")
                return

            data = {
                "id": None,
                "company": company.strip(),
                "title": title.strip(),
                "location_type": location_type,
                "location_detail": location_detail.strip()
                if location_detail
                else "",
                "salary_min": float(salary_min) if salary_min else None,
                "salary_max": float(salary_max) if salary_max else None,
                "link_url": link_url.strip() if link_url else "",
                "status": status,
                "description_short": description_short.strip()
                if description_short
                else "",
                "notes": notes.strip() if notes else "",
                "applied_date": applied_date.isoformat() if applied_date else None,
                "next_follow_up_date": next_follow_up_date.isoformat()
                if next_follow_up_date
                else None,
            }

            new_id = upsert_application(data, user_id)

            _clear_new_application_form_state()
            st.success("Application saved.")
            st.session_state["mode"] = "view"
            st.session_state["selected_app_id"] = new_id
            st.rerun()


def _render_detail_panel(app_id: Optional[str], user_id: str):
    if not app_id:
        return

    app = get_application(app_id, user_id)
    if not app:
        st.warning("Selected application not found. It may have been deleted.")
        return

    st.subheader("Application details")

    with st.form(f"edit_application_form_{app_id}"):
        company = st.text_input("Company *", value=app["company"] or "")
        title = st.text_input("Job title *", value=app["title"] or "")

        col1, col2 = st.columns(2)
        with col1:
            loc_type_value = app["location_type"] or "Unknown"
            if loc_type_value not in LOCATION_TYPES:
                LOCATION_TYPES.append(loc_type_value)
            location_type = st.selectbox(
                "Location type",
                LOCATION_TYPES,
                index=LOCATION_TYPES.index(loc_type_value),
            )
        with col2:
            location_detail = st.text_input(
                "Location detail (city, state)", value=app["location_detail"] or ""
            )

        col3, col4 = st.columns(2)
        with col3:
            salary_min = st.number_input(
                "Salary min (base)",
                min_value=0.0,
                step=1000.0,
                value=float(app["salary_min"]) if app["salary_min"] is not None else 0.0,
            )
        with col4:
            salary_max = st.number_input(
                "Salary max (base)",
                min_value=0.0,
                step=1000.0,
                value=float(app["salary_max"]) if app["salary_max"] is not None else 0.0,
            )

        link_url = st.text_input("Job posting URL", value=app["link_url"] or "")

        applied_date = st.date_input(
            "Date applied",
            value=_parse_date_str(app["applied_date"]) or date.today(),
        )

        status_value = app["status"] or "Applied"
        if status_value not in STATUS_OPTIONS:
            STATUS_OPTIONS.append(status_value)

        status = st.selectbox(
            "Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(status_value)
        )

        description_short = st.text_area(
            "Short description / key notes",
            value=app["description_short"] or "",
        )

        notes = st.text_area(
            "Private notes",
            value=app["notes"] or "",
        )

        next_follow_up_date = st.date_input(
            "Next follow-up date",
            value=_parse_date_str(app["next_follow_up_date"]) or date.today(),
        )

        col_save, col_delete = st.columns([0.7, 0.3])
        with col_save:
            submitted = st.form_submit_button(
                "Save changes", use_container_width=True
            )
        with col_delete:
            delete_clicked = st.form_submit_button(
                "Delete", use_container_width=True
            )

        if submitted:
            if not company.strip() or not title.strip():
                st.error("Company and Job title are required.")
                return

            data = {
                "id": app_id,
                "company": company.strip(),
                "title": title.strip(),
                "location_type": location_type,
                "location_detail": location_detail.strip()
                if location_detail
                else "",
                "salary_min": float(salary_min) if salary_min else None,
                "salary_max": float(salary_max) if salary_max else None,
                "link_url": link_url.strip() if link_url else "",
                "status": status,
                "description_short": description_short.strip()
                if description_short
                else "",
                "notes": notes.strip() if notes else "",
                "applied_date": applied_date.isoformat() if applied_date else None,
                "next_follow_up_date": next_follow_up_date.isoformat()
                if next_follow_up_date
                else None,
            }

            upsert_application(data, user_id)
            st.success("Changes saved.")
            st.rerun()

        if delete_clicked:
            delete_application(app_id, user_id)
            st.success("Application deleted.")
            st.session_state["selected_app_id"] = None
            st.rerun()

    st.markdown("#### Screenshots")

    uploaded_files = st.file_uploader(
        "Attach screenshots of the job posting (optional)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for file in uploaded_files:
            app_dir = os.path.join(SCREENSHOT_DIR, app_id)
            os.makedirs(app_dir, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            filename = f"{timestamp}_{file.name}"
            file_path = os.path.join(app_dir, filename)

            with open(file_path, "wb") as f:
                f.write(file.getbuffer())

            add_snapshot(app_id, file_path, user_id)

        st.success("Screenshot(s) uploaded.")
        st.rerun()

    snapshots = list_snapshots(app_id, user_id)
    if not snapshots:
        st.caption("No screenshots yet.")
    else:
        for snap in snapshots:
            st.caption(f"Captured at: {snap['captured_at']}")
            st.image(snap["image_path"], use_column_width=True)
            st.markdown("---")


if __name__ == "__main__":
    main()