"""
Chart builders for the dashboard tab. Each function returns a Plotly
figure (or None if it can't be built from the given data) so the
Streamlit layer can decide what to render.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px

from utils.analyzer import find_column


def inventory_quantity_chart(df: pd.DataFrame):
    qty_col = find_column(df, ["quantity", "qty", "stock"])
    name_col = find_column(df, ["item", "product", "name", "sku"])
    reorder_col = find_column(df, ["reorder", "min stock", "threshold"])

    if qty_col is None or name_col is None:
        return None

    plot_df = df[[name_col, qty_col]].copy()
    plot_df["Status"] = "OK"

    if reorder_col:
        low_mask = df[qty_col] <= df[reorder_col]
        plot_df.loc[low_mask.values, "Status"] = "Low stock"

    fig = px.bar(
        plot_df,
        x=name_col,
        y=qty_col,
        color="Status",
        color_discrete_map={"OK": "#2E7D32", "Low stock": "#C62828"},
        title="Inventory Quantity by Item",
    )
    fig.update_layout(xaxis_title="", yaxis_title="Quantity")
    return fig


def shipping_status_chart(df: pd.DataFrame):
    status_col = find_column(df, ["status"])
    if status_col is None:
        return None

    counts = df[status_col].value_counts().reset_index()
    counts.columns = ["Status", "Count"]

    fig = px.pie(
        counts,
        names="Status",
        values="Count",
        title="Shipments by Status",
        hole=0.4,
    )
    return fig


def shipping_delay_chart(df: pd.DataFrame):
    expected_col = find_column(df, ["expected delivery", "eta", "expected"])
    actual_col = find_column(df, ["actual delivery", "delivered", "actual"])
    id_col = find_column(df, ["shipment id", "id", "order"])

    if expected_col is None or actual_col is None:
        return None

    completed = df[df[actual_col].notna()].copy()
    if completed.empty:
        return None

    completed["Delay (days)"] = (
        completed[actual_col] - completed[expected_col]
    ).dt.days

    x_col = id_col if id_col else completed.index

    fig = px.bar(
        completed,
        x=x_col,
        y="Delay (days)",
        title="Delivery Delay by Shipment (negative = early)",
        color="Delay (days)",
        color_continuous_scale=["#2E7D32", "#F9A825", "#C62828"],
    )
    fig.update_layout(xaxis_title="")
    return fig

def alternate_suppliers_chart(df: pd.DataFrame):
    supplier_col = find_column(df, ["supplier", "vendor"])
    lead_col = find_column(df, ["lead time", "delivery time", "days"])
    price_col = find_column(df, ["price", "cost"])
    reliability_col = find_column(df, ["reliability", "rating"])

    if supplier_col is None or lead_col is None or price_col is None:
        return None

    fig = px.scatter(
        df,
        x=lead_col,
        y=price_col,
        text=supplier_col,
        color=reliability_col if reliability_col else None,
        title="Alternative Suppliers: Lead Time vs Price",
        color_continuous_scale="Teal" if reliability_col else None,
    )
    fig.update_traces(textposition="top center", marker=dict(size=14))
    fig.update_layout(xaxis_title="Lead time (days)", yaxis_title="Unit price")
    return fig