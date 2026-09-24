"""
Live web search for alternative suppliers, used only when nothing in
the local supplier directory matches the disrupted item.

Uses DuckDuckGo via the `ddgs` package since it needs no API key or
account signup - good for a student project you want to run today.
It's a free, scraped service, so it can occasionally rate-limit or
return thin results; treat its output as a starting point for manual
follow-up (real leads to click into and contact), not a verified,
guaranteed-accurate vendor list.
"""

from __future__ import annotations

from typing import Optional


class WebSearchError(Exception):
    """Raised when the live supplier search can't complete."""


def search_alternative_suppliers(
    item_name: str,
    avoid_terms: Optional[list[str]] = None,
    max_results: int = 8,
) -> list[dict]:
    """Search the web for companies that supply the given item.

    Args:
        item_name: the item to search for, e.g. "Industrial Sensors".
        avoid_terms: optional list of terms to exclude from results,
            e.g. the disrupted supplier's name or the affected region.
        max_results: how many results to fetch.

    Returns:
        A list of dicts with 'title', 'href', and 'body' (snippet).

    Raises:
        WebSearchError: if the ddgs package is missing, the search
            fails (e.g. rate-limited), or nothing is found.
    """
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise WebSearchError(
            "The 'ddgs' package isn't installed. Run: pip install ddgs"
        ) from exc

    query = f"{item_name} supplier manufacturer wholesale"
    for term in avoid_terms or []:
        if term:
            query += f" -{term}"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        raise WebSearchError(
            f"Web search failed ({exc}). DuckDuckGo's free search "
            "occasionally rate-limits automated queries — wait a "
            "minute and try again."
        ) from exc

    if not results:
        raise WebSearchError(
            "No web results found for that item. Try a more general "
            "item name (e.g. 'sensors' instead of a specific model number)."
        )

    return results