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
    Render a clean Sankey diagram showing movement OUT of Applied,
    without drawing an Applied -> Applied loop.

    Applications still in Applied are shown in the caption and in the
    hover text for the Applied node.
    """
    if df.empty or "status" not in df.columns:
        return

    st.subheader("Application Pipeline")

    total_apps = len(df)

    # Count how many apps are still sitting in Applied (current status)
    applied_only_count = int((df["status"] == "Applied").sum())

    # Count flows for statuses OTHER than Applied
    non_applied_df = df[df["status"] != "Applied"]
    non_applied_counts = (
        non_applied_df["status"]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
    )

    if non_applied_counts.empty:
        st.caption(
            f"All {total_apps} applications are still in Applied — no movement yet to display."
        )
        return

    moved_apps = int(non_applied_counts["count"].sum())

    # Labels: Applied + every non-applied status
    labels = ["Applied"] + list(non_applied_counts["status"])

    # Build flow: Applied -> each non-Applied status
    source = []
    target = []
    value = []

    # For node-level hover, we want richer info
    # customdata will be [current_count, moved_from_applied]
    node_customdata = []

    # Applied node customdata
    # current_count = applied_only_count (current Applied),
    # moved_from_applied = moved_apps (apps that have left Applied)
    node_customdata.append([applied_only_count, moved_apps])

    # For each non-applied status, compute "current count" and "moved_from_applied"
    status_to_current_count = (
        df["status"]
        .fillna("Unknown")
        .value_counts()
        .to_dict()
    )
    status_to_flow_count = {
        row["status"]: int(row["count"]) for _, row in non_applied_counts.iterrows()
    }

    for _, row in non_applied_counts.iterrows():
        status = row["status"]
        count = int(row["count"])

        source.append(0)  # Applied index
        target.append(labels.index(status))
        value.append(count)

        current_count = int(status_to_current_count.get(status, 0))
        moved_from_applied = int(status_to_flow_count.get(status, 0))
        node_customdata.append([current_count, moved_from_applied])

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    label=labels,
                    pad=15,
                    thickness=20,
                    customdata=node_customdata,
                    hovertemplate=(
                        # customdata[0] = current_count
                        # customdata[1] = moved_from_applied
                        "Status: %{label}<br>"
                        "Current count in this status: %{customdata[0]}<br>"
                        "Moved here from Applied: %{customdata[1]}<extra></extra>"
                    ),
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