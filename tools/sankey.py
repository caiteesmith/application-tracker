# tools/sankey.py
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def build_sankey_applied_to_status_text(df: pd.DataFrame) -> str:
    """
    Build SankeyMATIC-friendly flow lines: 'Applied [count] Status'
    """
    if df is None or df.empty or "status" not in df.columns:
        return ""

    counts = df["status"].fillna("Unknown").value_counts()
    lines = []
    for status, count in counts.items():
        status = status.strip() if isinstance(status, str) else status
        if not status:
            status = "Unknown"
        lines.append(f"Applied [{int(count)}] {status}")
    return "\n".join(lines)


def build_sankey_figure(
    df: pd.DataFrame,
    flow_type: str = "Applied → Status",
) -> Optional[go.Figure]:
    """
    Build a Plotly Sankey diagram from the applications dataframe.

    flow_type:
        - "Applied → Status"
        - "Applied → Response"  (if you add response_type later)
    """
    if df is None or df.empty:
        return None

    if flow_type == "Applied → Response":
        target_col = "response_type"
        default_label = "No response yet"
        applied_target_label = None 
    else:
        target_col = "status"
        default_label = "Unknown"
        applied_target_label = "Applied/No update yet"

    if target_col not in df.columns:
        return None

    # Aggregate counts
    counts = (
        df[target_col]
        .fillna(default_label)
        .replace("", default_label)
        .value_counts()
    )

    if counts.empty:
        return None

    source_label = "Applied"

    # Build target labels, renaming "Applied" if needed
    target_labels = []
    for label in list(counts.index):
        if applied_target_label and label == source_label:
            target_labels.append(applied_target_label)
        else:
            target_labels.append(label)

    labels = [source_label] + target_labels
    label_to_idx = {label: i for i, label in enumerate(labels)}

    sources: list[int] = []
    targets: list[int] = []
    values: list[int] = []

    for raw_target_label, count in counts.items():
        if applied_target_label and raw_target_label == source_label:
            target_label = applied_target_label
        else:
            target_label = raw_target_label

        sources.append(label_to_idx[source_label])
        targets.append(label_to_idx[target_label])
        values.append(int(count))

    sankey = go.Sankey(
        node=dict(
            label=labels,
            pad=30,
            thickness=20,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
        ),
    )

    fig = go.Figure(data=[sankey])
    fig.update_layout(
        title_text=flow_type,
        font=dict(size=12),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def render_sankey_section(df: pd.DataFrame) -> None:
    """
    Render a simple Sankey diagram showing flow from 'Applied' to current statuses.

    Assumes df has a 'status' column. No flow-type dropdown; just a single, clean view.
    """
    if df.empty or "status" not in df.columns:
        return

    st.subheader("Application Pipeline")

    status_counts = (
        df["status"]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
    )

    labels = ["Applied"]
    source = []
    target = []
    value = []

    for _, row in status_counts.iterrows():
        status = row["status"]
        count = int(row["count"])

        if status == "Applied":
            continue

        if status not in labels:
            labels.append(status)

        src_idx = 0
        tgt_idx = labels.index(status)

        source.append(src_idx)
        target.append(tgt_idx)
        value.append(count)

    if not value:
        st.caption("Not enough data yet to show an application flow.")
        return

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    label=labels,
                    pad=15,
                    thickness=20,
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

    st.plotly_chart(fig, use_container_width=True)