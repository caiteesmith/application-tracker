# tools/analytics.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _prepare_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "applied_date" in df.columns:
        df["applied_date_parsed"] = pd.to_datetime(
            df["applied_date"], errors="coerce"
        ).dt.date
    else:
        df["applied_date_parsed"] = pd.NaT
    return df


def _kpi_row(df: pd.DataFrame):
    today = date.today()
    last_30 = today - timedelta(days=30)

    total_apps = len(df)

    total_companies = (
        df["company"].dropna().nunique() if "company" in df.columns else 0
    )

    df_dates = _prepare_dates(df)
    apps_last_30 = df_dates[
        (df_dates["applied_date_parsed"].notna())
        & (df_dates["applied_date_parsed"] >= last_30)
    ].shape[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric("Total applications", total_apps)
    with col2:
        with st.container(border=True):
            st.metric("Unique companies", total_companies)
    with col3:
        with st.container(border=True):
            st.metric("Applied in last 30 days", apps_last_30)


def _status_bar_chart(df: pd.DataFrame):
    if "status" not in df.columns:
        return

    counts = (
        df["status"]
        .fillna("Unknown")
        .replace("", "Unknown")
        .value_counts()
        .reset_index()
    )
    counts.columns = ["Status", "Count"]

    if counts.empty:
        return

    fig = go.Figure(
        data=[
            go.Bar(
                x=counts["Status"],
                y=counts["Count"],
                text=counts["Count"],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title_text="Applications by status",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(title="Status"),
        yaxis=dict(title="Count"),
    )
    st.plotly_chart(fig, width="stretch")


def _timeline_chart(df: pd.DataFrame):
    df_dates = _prepare_dates(df)
    if df_dates["applied_date_parsed"].isna().all():
        return

    timeline = (
        df_dates.dropna(subset=["applied_date_parsed"])
        .groupby("applied_date_parsed")
        .size()
        .sort_index()
    )
    if timeline.empty:
        return

    cumulative = timeline.cumsum()

    fig = go.Figure(
        data=[
            go.Scatter(
                x=list(cumulative.index),
                y=list(cumulative.values),
                mode="lines+markers",
            )
        ]
    )
    fig.update_layout(
        title_text="Cumulative applications over time",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(title="Applied date"),
        yaxis=dict(title="Total applications"),
    )
    st.plotly_chart(fig, width="stretch")


def render_analytics_section(filtered_df: pd.DataFrame) -> None:
    """
    High-level overview for the applications table
    """
    if filtered_df is None or filtered_df.empty:
        st.caption("No applications to analyze yet.")
        return

    _kpi_row(filtered_df)

        # col1, col2 = st.columns(2)
        # with col1:
        #     _status_bar_chart(filtered_df)
        # with col2:
        #     _timeline_chart(filtered_df)