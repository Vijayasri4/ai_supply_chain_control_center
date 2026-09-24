"""
Disruption & Alternative Sourcing Advisor.

Given an item that can no longer be supplied as planned (a disaster,
a port closure, a supplier outage, a factory fire, etc.), this module:

1. Works out how much runway is left before a stockout.
2. Finds alternative suppliers from a supplier directory, sorted by
   how fast they can deliver.
3. Builds a compact text summary of the scenario for an AI-generated
   recommendation (see utils.ai_engine.recommend_disruption_response).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from utils.analyzer import find_column


def days_until_stockout(
    current_quantity: float, daily_usage_rate: float
) -> Optional[float]:
    """How many days of stock remain at the given usage rate.

    Returns None if the usage rate is zero/unknown (can't divide by it).
    """
    if not daily_usage_rate or daily_usage_rate <= 0:
        return None
    return round(current_quantity / daily_usage_rate, 1)


def find_alternate_suppliers(
    suppliers_df: pd.DataFrame,
    item_name: str,
    exclude_supplier: Optional[str] = None,
) -> pd.DataFrame:
    """Return suppliers who can provide the given item, sorted by lead
    time (fastest first), excluding the disrupted supplier if named.
    """
    item_col = find_column(suppliers_df, ["item", "product", "sku"])
    supplier_col = find_column(suppliers_df, ["supplier", "vendor"])
    lead_time_col = find_column(suppliers_df, ["lead time", "delivery time", "days"])

    if item_col is None or not item_name:
        return pd.DataFrame()

    matches = suppliers_df[
        suppliers_df[item_col]
        .astype(str)
        .str.contains(str(item_name), case=False, na=False)
    ].copy()

    if exclude_supplier and supplier_col:
        matches = matches[
            ~matches[supplier_col]
            .astype(str)
            .str.contains(str(exclude_supplier), case=False, na=False)
        ]

    if lead_time_col and lead_time_col in matches.columns:
        matches = matches.sort_values(lead_time_col)

    return matches


def build_disruption_context(
    item_name: str,
    current_quantity: float,
    daily_usage_rate: float,
    days_left: Optional[float],
    disrupted_supplier: str,
    disruption_reason: str,
    alternatives_df: pd.DataFrame,
    affected_region: str = "",
    web_leads: Optional[str] = None,
) -> str:
    """Build a compact text summary of the disruption scenario, sized
    for inclusion in an AI prompt.

    affected_region and web_leads are optional: pass affected_region
    when the user names the disrupted region (e.g. "Chennai" after a
    flood), and web_leads when a local directory match wasn't found and
    a live web search (see utils.ai_engine.summarize_web_leads) was run
    instead.
    """
    lines = [
        f"ITEM AFFECTED: {item_name}",
        f"CURRENT STOCK: {current_quantity} units",
        f"ESTIMATED DAILY USAGE: {daily_usage_rate} units/day",
        f"DAYS UNTIL STOCKOUT: {days_left if days_left is not None else 'unknown'}",
        f"DISRUPTED SUPPLIER: {disrupted_supplier or 'not specified'}",
        f"REGION AFFECTED: {affected_region or 'not specified'}",
        f"REASON FOR DISRUPTION: {disruption_reason or 'not specified'}",
    ]

    if alternatives_df.empty:
        lines.append("ALTERNATIVE SUPPLIERS FOUND IN DIRECTORY: none")
        if web_leads:
            lines.append(
                "LIVE WEB SEARCH LEADS (found in real time, unverified):\n"
                f"{web_leads}"
            )
    else:
        lines.append("ALTERNATIVE SUPPLIERS FOUND (fastest first):")
        lines.append(alternatives_df.head(5).to_string(index=False))

    return "\n".join(lines)








'''def build_disruption_context(
    item_name: str,
    current_quantity: float,
    daily_usage_rate: float,
    days_left: Optional[float],
    disrupted_supplier: str,
    disruption_reason: str,
    alternatives_df: pd.DataFrame,
) -> str:
    """Build a compact text summary of the disruption scenario, sized
    for inclusion in an AI prompt.
    """
    lines = [
        f"ITEM AFFECTED: {item_name}",
        f"CURRENT STOCK: {current_quantity} units",
        f"ESTIMATED DAILY USAGE: {daily_usage_rate} units/day",
        f"DAYS UNTIL STOCKOUT: {days_left if days_left is not None else 'unknown'}",
        f"DISRUPTED SUPPLIER: {disrupted_supplier or 'not specified'}",
        f"REASON FOR DISRUPTION: {disruption_reason or 'not specified'}",
    ]

    if alternatives_df.empty:
        lines.append("ALTERNATIVE SUPPLIERS FOUND: none in the supplier directory")
    else:
        lines.append("ALTERNATIVE SUPPLIERS FOUND (fastest first):")
        lines.append(alternatives_df.head(5).to_string(index=False))

    return "\n".join(lines)'''