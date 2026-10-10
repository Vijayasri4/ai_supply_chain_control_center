"""
Structured Data Profiling Agent.

Combines automated data-quality profiling (fg-data-profiling, formerly
known as pandas-profiling / ydata-profiling) with five custom
business-rule checks specific to shipping logistics - things a
generic profiler has no way to know about, like a delivery date that's
impossible given the ship date.

fg-data-profiling is a fairly heavy dependency (pulls in numba,
matplotlib, statsmodels, etc.), which will add noticeable time to a
fresh `pip install` and to the app's first import. That's the
trade-off for using the exact library named in the project report
rather than a lighter hand-rolled substitute.
"""

from __future__ import annotations

import contextlib
import io

import pandas as pd

from utils.analyzer import find_column


def profile_generic_quality(df: pd.DataFrame) -> list[str]:
    """Run fg-data-profiling's automated checks and return its
    data-quality alerts as plain text (missing values, zeros, high
    cardinality, skew, etc.).
    """
    from data_profiling import ProfileReport

    # ProfileReport writes a progress bar to stderr - discard it so it
    # doesn't clutter the app's server logs.
    with contextlib.redirect_stderr(io.StringIO()):
        report = ProfileReport(df, minimal=True, progress_bar=False, title="Shipping data profile")
        description = report.get_description()

    return [str(alert) for alert in description.alerts]


def check_business_rules(df: pd.DataFrame) -> list[dict]:
    """Five custom business-rule checks specific to shipping logistics.

    Returns a list of dicts, each with:
        rule (str), severity ("warning" | "error"), detail (str)
    """
    issues: list[dict] = []

    id_col = find_column(df, ["shipment id", "order id", "id"])
    ship_col = find_column(df, ["ship date"])
    actual_col = find_column(df, ["actual delivery", "delivered"])
    status_col = find_column(df, ["status"])
    qty_col = find_column(df, ["quantity", "qty"])
    price_col = find_column(df, ["price", "cost"])

    # Rule 1: duplicate shipment/order IDs
    if id_col:
        dupes = df[df[id_col].duplicated(keep=False)]
        if not dupes.empty:
            issues.append({
                "rule": "Duplicate shipment IDs",
                "severity": "error",
                "detail": (
                    f"{dupes[id_col].nunique()} ID(s) appear more than once: "
                    f"{', '.join(map(str, dupes[id_col].unique()[:5]))}"
                ),
            })

    # Rule 2: actual delivery date earlier than ship date (impossible)
    if ship_col and actual_col:
        bad = df[df[actual_col].notna() & (df[actual_col] < df[ship_col])]
        if not bad.empty:
            issues.append({
                "rule": "Delivery date before ship date",
                "severity": "error",
                "detail": f"{len(bad)} row(s) show a delivery date earlier than the ship date.",
            })

    # Rule 3: status says "delivered" but no actual delivery date recorded
    if status_col and actual_col:
        bad = df[
            df[status_col].astype(str).str.contains("deliver", case=False, na=False)
            & df[actual_col].isna()
        ]
        if not bad.empty:
            issues.append({
                "rule": "Delivered with no delivery date",
                "severity": "warning",
                "detail": f"{len(bad)} row(s) are marked delivered but have no actual delivery date.",
            })

    # Rule 4: non-positive quantity or price (likely data entry error)
    for col, label in ((qty_col, "quantity"), (price_col, "price")):
        if col:
            bad = df[df[col] <= 0]
            if not bad.empty:
                issues.append({
                    "rule": f"Non-positive {label}",
                    "severity": "warning",
                    "detail": f"{len(bad)} row(s) have a {label} of zero or less.",
                })

    # Rule 5: unusually long transit time (possible major delay or bad data)
    if ship_col and actual_col:
        transit_days = (df[actual_col] - df[ship_col]).dt.days
        long_transit = df[transit_days > 45]
        if not long_transit.empty:
            issues.append({
                "rule": "Unusually long transit time",
                "severity": "warning",
                "detail": f"{len(long_transit)} row(s) took more than 45 days from ship to delivery.",
            })

    return issues