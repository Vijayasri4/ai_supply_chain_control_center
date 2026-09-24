"""
Analysis utilities for the AI Supply Chain Control Center.

These functions turn raw inventory / shipping DataFrames into the
alerts and metrics shown on the dashboard. Column names are matched
loosely (case-insensitive, substring based) so the app keeps working
even if the user's spreadsheet headers don't match the sample data
exactly.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def find_column(df: pd.DataFrame, keywords: list[str]) -> Optional[str]:
    """Return the first column whose name contains any of the given
    keywords (case-insensitive), or None if no match is found.
    """
    for col in df.columns:
        lowered = str(col).lower()
        for kw in keywords:
            if kw in lowered:
                return col
    return None


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def analyze_inventory(df: pd.DataFrame) -> dict:
    """Compute low-stock / overstock alerts and headline metrics.

    Returns a dict with:
        low_stock (DataFrame), overstock (DataFrame),
        total_items (int), total_value (float or None),
        columns_used (dict) - which columns were detected, for transparency
        warnings (list[str])
    """
    warnings: list[str] = []

    qty_col = find_column(df, ["quantity", "qty", "stock"])
    reorder_col = find_column(df, ["reorder", "min stock", "threshold"])
    price_col = find_column(df, ["price", "cost", "unit price"])
    name_col = find_column(df, ["item", "product", "name", "sku"])

    low_stock = pd.DataFrame()
    overstock = pd.DataFrame()
    total_value = None

    if qty_col is None:
        warnings.append(
            "Couldn't find a quantity/stock column, so stock-level alerts "
            "are unavailable."
        )
    elif reorder_col is None:
        warnings.append(
            "Couldn't find a reorder-point column, so low-stock alerts use "
            "a generic threshold (quantity < 20)."
        )
        low_stock = df[df[qty_col] < 20]
    else:
        low_stock = df[df[qty_col] <= df[reorder_col]]
        overstock = df[df[qty_col] > df[reorder_col] * 5]

    if qty_col and price_col:
        try:
            total_value = float((df[qty_col] * df[price_col]).sum())
        except Exception:
            total_value = None

    return {
        "low_stock": low_stock,
        "overstock": overstock,
        "total_items": int(df[qty_col].sum()) if qty_col else None,
        "total_value": total_value,
        "columns_used": {
            "quantity": qty_col,
            "reorder_point": reorder_col,
            "price": price_col,
            "name": name_col,
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Shipping
# ---------------------------------------------------------------------------

def analyze_shipping(df: pd.DataFrame) -> dict:
    """Compute delayed-shipment alerts and on-time performance.

    Returns a dict with:
        delayed (DataFrame), on_time_rate (float or None),
        avg_delay_days (float or None), status_counts (Series or None),
        warnings (list[str])
    """
    warnings: list[str] = []

    expected_col = find_column(df, ["expected delivery", "eta", "expected"])
    actual_col = find_column(df, ["actual delivery", "delivered", "actual"])
    status_col = find_column(df, ["status"])

    delayed = pd.DataFrame()
    on_time_rate = None
    avg_delay_days = None

    if expected_col and actual_col:
        completed = df[df[actual_col].notna()].copy()
        if not completed.empty:
            completed["_delay_days"] = (
                completed[actual_col] - completed[expected_col]
            ).dt.days
            delayed = completed[completed["_delay_days"] > 0]
            on_time_rate = round(
                100 * (1 - len(delayed) / len(completed)), 1
            )
            if not delayed.empty:
                avg_delay_days = round(delayed["_delay_days"].mean(), 1)
    else:
        warnings.append(
            "Couldn't find both an expected and actual delivery date "
            "column, so delay analysis is unavailable."
        )

    status_counts = df[status_col].value_counts() if status_col else None

    return {
        "delayed": delayed,
        "on_time_rate": on_time_rate,
        "avg_delay_days": avg_delay_days,
        "status_counts": status_counts,
        "columns_used": {
            "expected": expected_col,
            "actual": actual_col,
            "status": status_col,
        },
        "warnings": warnings,
    }


def build_data_summary(
    inventory_df: Optional[pd.DataFrame] = None,
    shipping_df: Optional[pd.DataFrame] = None,
    contract_text: Optional[str] = None,
) -> str:
    """Build a compact, text-only summary of the loaded data, sized for
    inclusion in an AI prompt (kept short to control token usage).
    """
    parts: list[str] = []

    if inventory_df is not None:
        result = analyze_inventory(inventory_df)
        parts.append(
            "INVENTORY DATA\n"
            f"- {len(inventory_df)} SKUs loaded. Columns: {list(inventory_df.columns)}\n"
            f"- Low stock items: {len(result['low_stock'])}\n"
            f"- Overstocked items: {len(result['overstock'])}\n"
            f"- Total inventory value: {result['total_value']}\n"
            f"- Sample rows:\n{inventory_df.head(5).to_string(index=False)}"
        )

    if shipping_df is not None:
        result = analyze_shipping(shipping_df)
        parts.append(
            "SHIPPING DATA\n"
            f"- {len(shipping_df)} shipments loaded. Columns: {list(shipping_df.columns)}\n"
            f"- Delayed shipments: {len(result['delayed'])}\n"
            f"- On-time rate: {result['on_time_rate']}%\n"
            f"- Avg delay (days): {result['avg_delay_days']}\n"
            f"- Sample rows:\n{shipping_df.head(5).to_string(index=False)}"
        )

    if contract_text:
        snippet = contract_text[:3000]
        parts.append(f"VENDOR CONTRACT (excerpt)\n{snippet}")

    return "\n\n".join(parts) if parts else "No data has been uploaded yet."