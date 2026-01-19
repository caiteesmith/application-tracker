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


def render_sankey_section(filtered_df: pd.DataFrame) -> None:
    st.markdown("### Sankey Diagram")

    if filtered_df is None or filtered_df.empty:
        st.caption("No applications to visualize yet.")
        return

    flow_type = st.selectbox(
        "Flow type",
        ["Applied → Status"],
        index=0,
    )

    fig = build_sankey_figure(filtered_df, flow_type=flow_type)
    if fig is None:
        st.caption("Not enough data to build a Sankey chart yet.")
    else:
        st.plotly_chart(fig, width="stretch")

    with st.expander("Show SankeyMATIC text export"):
        sankey_text = build_sankey_applied_to_status_text(filtered_df)
        st.caption(
            "Copy this into the **Flows** box on sankeymatic.com "
            "to customize colors/labels or export high-res images."
        )
        st.code(sankey_text or "# No data", language="text")