# tools/sankey.py
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Statuses that never left "Applied" in a meaningful sense, or never entered it.
EXCLUDED_FROM_PIPELINE = {"Wishlist"}


def render_sankey_section(df: pd.DataFrame) -> None:
    """
    Render a Sankey diagram showing movement OUT of Applied,
    without drawing an Applied -> Applied loop.

    Applications still in Applied are shown in the caption and in the
    hover text for the Applied node.
    """
    if df is None or df.empty or "status" not in df.columns:
        return

    st.subheader("Application Pipeline")

    statuses = df["status"].fillna("Unknown").replace("", "Unknown")
    statuses = statuses[~statuses.isin(EXCLUDED_FROM_PIPELINE)]

    total_apps = len(statuses)
    if total_apps == 0:
        st.caption("No submitted applications yet.")
        return

    applied_only_count = int((statuses == "Applied").sum())
    moved_counts = statuses[statuses != "Applied"].value_counts()

    if moved_counts.empty:
        st.caption(
            f"All {total_apps} applications are still in Applied. No movement yet to display."
        )
        return

    moved_apps = int(moved_counts.sum())

    labels = ["Applied", *moved_counts.index]
    source = [0] * len(moved_counts)
    target = list(range(1, len(labels)))
    value = [int(c) for c in moved_counts.values]

    applied_hover = (
        f"Applied<br>"
        f"Still waiting: {applied_only_count}<br>"
        f"Moved on: {moved_apps}"
    )
    node_hover = [applied_hover] + [
        f"{status}<br>Applications: {int(count)}" for status, count in moved_counts.items()
    ]

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    label=labels,
                    pad=15,
                    thickness=20,
                    customdata=node_hover,
                    hovertemplate="%{customdata}<extra></extra>",
                ),
                link=dict(
                    source=source,
                    target=target,
                    value=value,
                ),
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
    )

    st.caption(f"{applied_only_count} of {total_apps} applications are still in Applied.")
    st.plotly_chart(fig, width="stretch")