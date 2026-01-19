# app.py
from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional
import pandas as pd

import streamlit as st
from tools.sankey import render_sankey_section
from tools.analytics import render_analytics_section
from tools.auth import require_login, supabase_client


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
    "Wishlist",
    "Applied",
    "Recruiter Screen",
    "Interview 1",
    "Interview 2+",
    "Final Round",
    "Offer",
    "Accepted",
    "Rejected",
    "Withdrawn",
    "Ghosted",
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
    """
    Build a human-friendly label for the selectbox.
    """
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

def get_current_user_id() -> str:
    return require_login()

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

    # Sidebar
    with st.sidebar:
        st.sidebar.title("ApplicationTracker")
        st.sidebar.caption(
            "Log applications, track outcomes, and see patterns over time, without spreadsheets."
        )

        st.sidebar.markdown("### Filters")

        # Load all apps as DataFrame
        df = list_applications(user_id=user_id)

        # Sidebar filters
        status_filter = st.sidebar.multiselect(
            "Status",
            options=STATUS_OPTIONS,
            default=STATUS_OPTIONS,
        )

        location_filter = st.sidebar.multiselect(
            "Location type",
            options=LOCATION_TYPES,
            default=LOCATION_TYPES,
        )

        search_text = st.sidebar.text_input(
            "Search (company, title, notes)",
            value="",
            placeholder="e.g., backend, Netflix, remote",
        )

        # Filter in-memory
        filtered_df = df.copy()

        if not filtered_df.empty:
            if status_filter:
                filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]

            if location_filter:
                filtered_df = filtered_df[filtered_df["location_type"].isin(location_filter)]

            if search_text.strip():
                text = search_text.strip().lower()
                mask = (
                    filtered_df["company"].fillna("").str.lower().str.contains(text)
                    | filtered_df["title"].fillna("").str.lower().str.contains(text)
                    | filtered_df["notes"].fillna("").str.lower().str.contains(text)
                )
                filtered_df = filtered_df[mask]


        st.sidebar.caption(
            "Your applications and screenshots are stored in your private Supabase project. "
            "No data is uploaded to Streamlit or shared with any external services."
        )

        if st.button("Sign out", use_container_width=True):
            sb = supabase_client()
            sb.auth.sign_out()

            for k in ["sb_session", "login_email", "login_pw", "signup_email", "signup_pw"]:
                st.session_state.pop(k, None)

            st.rerun()


    # Session state for selection/mode
    if "selected_app_id" not in st.session_state:
        st.session_state["selected_app_id"] = None
    if "mode" not in st.session_state:
        st.session_state["mode"] = "view" 

    # Top layout
    st.title("ApplicationTracker")
    st.caption(
        "A lightweight tool for tracking job applications, follow-ups, and outcomes, "
        "designed to help you see patterns and momentum over time, not judge progress."
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
            st.info("No applications yet. Click **Add new application** to get started.")
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
            display_df = filtered_df[table_cols].copy()

            display_df["salary_min"] = display_df["salary_min"].apply(_money)
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
                height=350,
            )

            st.markdown("##### Select an application to view/edit")

            # Build options as (label, id)
            options = []
            for _, row in filtered_df.iterrows():
                options.append((_format_app_option(row), row["id"]))

            # Map from label to id
            label_to_id = {label: app_id for label, app_id in options}
            labels = [label for label, _ in options]

            current_label: Optional[str] = None
            if st.session_state["selected_app_id"]:
                # Try to find label that matches the current selected id in filtered df
                for label, app_id in options:
                    if app_id == st.session_state["selected_app_id"]:
                        current_label = label
                        break

            selected_label = st.selectbox(
                "Application",
                options=["(none)"] + labels,
                index=(labels.index(current_label) + 1) if current_label in labels else 0,
                label_visibility="collapsed",
            )

            if selected_label != "(none)":
                st.session_state["selected_app_id"] = label_to_id[selected_label]
                if st.session_state["mode"] == "new":
                    st.session_state["mode"] = "view"
            else:
                st.session_state["selected_app_id"] = None


    # -------------------------
    # Right column: detail/new form
    # -------------------------
    with col_right:
        st.subheader("Add/Review")
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
    # reset any previous "new application" form values
    _clear_new_application_form_state()
    st.session_state["mode"] = "new"
    st.session_state["selected_app_id"] = None


def _render_new_application_form(user_id: str):
    st.subheader("New application")

    # Let Streamlit keep widget values between reruns
    with st.form("new_application_form"):
        company = st.text_input("Company *")
        title = st.text_input("Job title *")

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

        status = st.selectbox("Status", STATUS_OPTIONS, index=1)  # default 'Applied'

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
            "Save application", width="stretch"
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
                "applied_date": applied_date.isoformat()
                if applied_date
                else None,
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
            location_type = st.selectbox("Location type", LOCATION_TYPES, index=LOCATION_TYPES.index(loc_type_value))
        with col2:
            location_detail = st.text_input("Location detail (city, state)", value=app["location_detail"] or "")

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

        status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(status_value))

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
            submitted = st.form_submit_button("Save changes", width="stretch")
        with col_delete:
            delete_clicked = st.form_submit_button("Delete", width="stretch")

        if submitted:
            if not company.strip() or not title.strip():
                st.error("Company and Job title are required.")
                return

            data = {
                "id": app_id,
                "company": company.strip(),
                "title": title.strip(),
                "location_type": location_type,
                "location_detail": location_detail.strip() if location_detail else "",
                "salary_min": float(salary_min) if salary_min else None,
                "salary_max": float(salary_max) if salary_max else None,
                "link_url": link_url.strip() if link_url else "",
                "status": status,
                "description_short": description_short.strip() if description_short else "",
                "notes": notes.strip() if notes else "",
                "applied_date": applied_date.isoformat() if applied_date else None,
                "next_follow_up_date": next_follow_up_date.isoformat() if next_follow_up_date else None,
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

    # Screenshot uploader
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

    # Show gallery
    snapshots = list_snapshots(app_id, user_id)
    if not snapshots:
        st.caption("No screenshots yet.")
    else:
        for snap in snapshots:
            st.caption(f"Captured at: {snap['captured_at']}")
            st.image(snap["image_path"], width="stretch")
            st.markdown("---")


if __name__ == "__main__":
    main()