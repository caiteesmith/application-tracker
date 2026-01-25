# tools/analytics.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from tools.job_title_utils import normalize_job_title

def _fmt_int(val: float | None) -> str:
    if val is None or pd.isna(val):
        return "—"
    return f"{val:,.0f}"


def _prepare_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "applied_date" in df.columns:
        df["applied_date_parsed"] = pd.to_datetime(
            df["applied_date"], errors="coerce"
        ).dt.date
    else:
        df["applied_date_parsed"] = pd.NaT
    return df


def _job_title_counts(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Return a small table of role categories and application counts,
    or None if we can't compute it.
    """
    # Find the title column
    title_col = None
    for cand in ["job_title", "Job Title", "title", "Title"]:
        if cand in df.columns:
            title_col = cand
            break

    if not title_col or df[title_col].dropna().empty:
        return None

    titles = df[title_col].fillna("").astype(str)

    df_norm = df.copy()
    df_norm["role_category"] = titles.apply(normalize_job_title)

    counts = (
        df_norm["role_category"]
        .value_counts()
        .rename_axis("Roles applied to")
        .reset_index(name="Applications")
    )

    if counts.empty:
        return None

    # Keep it compact
    return counts.head(6)

def _compute_apps_per_week(df_dates: pd.DataFrame) -> float:
    """
    Compute average applications per week over the span of your search.
    """
    if "applied_date_parsed" not in df_dates.columns:
        return 0.0

    valid = df_dates["applied_date_parsed"].dropna()
    if valid.empty:
        return 0.0

    first = valid.min()
    last = valid.max()
    days = (last - first).days + 1
    weeks = max(1.0, days / 7.0)

    return round(len(valid) / weeks, 1)


def _avg_salary_range(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """
    Compute the average min and max salary (base) across applications.
    Returns (avg_min, avg_max); values may be None if there is no data.
    """
    avg_min = avg_max = None

    if "salary_min" in df.columns:
        mins = pd.to_numeric(df["salary_min"], errors="coerce")
        if mins.notna().any():
            avg_min = float(mins.mean())

    if "salary_max" in df.columns:
        maxs = pd.to_numeric(df["salary_max"], errors="coerce")
        if maxs.notna().any():
            avg_max = float(maxs.mean())

    return avg_min, avg_max


def _kpi_row(df: pd.DataFrame) -> None:
    today = date.today()
    last_30 = today - timedelta(days=30)

    total_apps = len(df)

    df_dates = _prepare_dates(df)
    apps_last_30 = df_dates[
        (df_dates["applied_date_parsed"].notna())
        & (df_dates["applied_date_parsed"] >= last_30)
    ].shape[0]

    apps_per_week = _compute_apps_per_week(df_dates)
    avg_min, avg_max = _avg_salary_range(df)
    counts = _job_title_counts(df)

    col1, col2, col3 = st.columns([1, 1, 1.4])

    with col1:
        with st.container(border=True):
            st.metric("Total applications", total_apps)

        with st.container(border=True):
            st.metric("Applied in last 30 days", apps_last_30)

    with col2:
        with st.container(border=True):
            st.metric("Average apps per week", apps_per_week)

        with st.container(border=True):
            if avg_min is None and avg_max is None:
                st.metric("Avg salary range (base, $)", "—")
            else:
                if avg_min is not None and avg_max is not None:
                    value = f"{_fmt_int(avg_min)}–{_fmt_int(avg_max)}"
                elif avg_min is not None:
                    value = f"Min {_fmt_int(avg_min)}"
                else:
                    value = f"Max {_fmt_int(avg_max)}"

                st.metric("Average salary range", value)

    with col3:
        if counts is None:
            st.caption("Add applications with job titles to see this fill in.")
        else:
            st.dataframe(
                counts,
                hide_index=True,
                use_container_width=True,
                height=225,
            )


def render_analytics_section(filtered_df: pd.DataFrame) -> None:
    """
    High-level overview for the applications table.
    """
    if filtered_df is None or filtered_df.empty:
        st.caption("No applications to analyze yet.")
        return

    _kpi_row(filtered_df)