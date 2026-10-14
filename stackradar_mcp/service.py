"""Turn catalog rows plus signals into the four tool payloads."""

from __future__ import annotations

import difflib
import re
from typing import Any

import httpx

from stackradar_mcp.catalog import (
    ALIASES,
    CATEGORY_ALIASES,
    TOOLS,
    TOOLS_BY_SLUG,
    WINDOW_ALIASES,
    categories,
)
from stackradar_mcp.scoring import (
    calculate_all_tool_scores,
    classify_growth_stage,
    classify_trend,
    growth_pct,
    score_breakdown,
)
from stackradar_mcp.signals import Signals, collect_signals, seed_as_of
from stackradar_mcp.voice import (
    speak_bad_category,
    speak_bad_window,
    speak_compare,
    speak_digest,
    speak_score,
    speak_trending,
    speak_unknown_tool,
)


def _norm(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def resolve_tool(query: str) -> dict | None:
    cleaned = _norm(query)
    if not cleaned:
        return None
    if cleaned in TOOLS_BY_SLUG:
        return TOOLS_BY_SLUG[cleaned]
    if cleaned in ALIASES:
        return TOOLS_BY_SLUG[ALIASES[cleaned]]
    for tool in TOOLS:
        if _norm(tool["name"]) == cleaned:
            return tool
    keyword_hits = [tool for tool in TOOLS if cleaned in {_norm(keyword) for keyword in tool["keywords"]}]
    if len(keyword_hits) == 1:
        return keyword_hits[0]
    compact = _compact(cleaned)
    for tool in TOOLS:
        if compact and compact in {_compact(tool["slug"]), _compact(tool["name"])}:
            return tool
    return None


def suggest_tools(query: str, limit: int = 3) -> list[str]:
    names = [tool["name"] for tool in TOOLS]
    matches = difflib.get_close_matches(query, names, n=limit, cutoff=0.45)
    if matches:
        return matches
    return ["React", "FastAPI", "PyTorch"]


def resolve_category(query: str | None) -> tuple[str | None, str | None]:
    """Return (canonical category or None for all, error message)."""
    if query is None or not str(query).strip():
        return None, None
    cleaned = _norm(str(query))
    if cleaned in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[cleaned], None
    for name in categories():
        if _norm(name) == cleaned:
            return name, None
    return None, speak_bad_category(query)


def resolve_window(query: str | None) -> tuple[str | None, str | None]:
    if query is None or not str(query).strip():
        return "7d", None
    cleaned = _norm(str(query))
    if cleaned in WINDOW_ALIASES:
        return WINDOW_ALIASES[cleaned], None
    return None, speak_bad_window(str(query))


def _conversation(delta: int) -> str:
    if delta >= 4:
        return "louder"
    if delta <= -4:
        return "quieter"
    return "steady"


def _card(tool: dict, signals: Signals, *, full: bool) -> dict[str, Any]:
    breakdown = score_breakdown(signals.stars, signals.forks, signals.hn, signals.devto, signals.reddit, signals.news)
    previous_score = calculate_all_tool_scores(
        [
            {
                "stars": signals.previous_stars,
                "forks": signals.previous_forks,
                "hn_count": signals.previous_hn,
                "devto_count": signals.previous_devto,
                "reddit_count": signals.previous_reddit,
                "news_count": signals.previous_news,
            }
        ]
    )[0]
    change = growth_pct(breakdown["score"], previous_score)
    mention_delta = (signals.hn + signals.devto + signals.reddit + signals.news) - (
        signals.previous_hn + signals.previous_devto + signals.previous_reddit + signals.previous_news
    )
    card: dict[str, Any] = {
        "name": tool["name"],
        "slug": tool["slug"],
        "category": tool["category"],
        "description": tool["description"],
        "github_repo": tool["github_repo"],
        "score": breakdown["score"],
        "stage": classify_growth_stage(breakdown["score"]),
        "trend": classify_trend(change if change is not None else 0.0),
        "growth_pct": change,
        "mention_delta": mention_delta,
        "conversation": _conversation(mention_delta),
        "data_source": signals.data_source,
        "signal_sources": signals.sources,
    }
    if full:
        card["breakdown"] = breakdown
        card["formula"] = {
            "name": "StackRadar calculate_all_tool_scores",
            "stars_weight": 0.60,
            "forks_weight": 0.15,
            "community_weight": 0.25,
            "community_saturation": 25,
            "source": "https://github.com/amantebriwal4321/StackRadar/blob/main/backend/app/services/scoring.py",
        }
    return card


def _envelope(payload: dict[str, Any]) -> dict[str, Any]:
    payload["as_of"] = seed_as_of()
    payload["ok"] = payload.get("ok", True)
    return payload


async def tool_score(
    name: str,
    window: str = "7d",
    *,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    resolved_window, window_error = resolve_window(window)
    if window_error or resolved_window is None:
        return _envelope({"ok": False, "spoken": window_error or speak_bad_window(window)})
    tool = resolve_tool(name)
    if tool is None:
        return _envelope({"ok": False, "spoken": speak_unknown_tool(name, suggest_tools(name))})
    signals = (await collect_signals([tool["slug"]], resolved_window, transport=transport))[tool["slug"]]
    card = _card(tool, signals, full=True)
    card["window"] = resolved_window
    card["spoken"] = speak_score(card)
    return _envelope(card)


async def compare_tools(
    a: str,
    b: str,
    window: str = "7d",
    *,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    resolved_window, window_error = resolve_window(window)
    if window_error or resolved_window is None:
        return _envelope({"ok": False, "spoken": window_error or speak_bad_window(window)})
    left = resolve_tool(a)
    right = resolve_tool(b)
    if left is None:
        return _envelope({"ok": False, "spoken": speak_unknown_tool(a, suggest_tools(a))})
    if right is None:
        return _envelope({"ok": False, "spoken": speak_unknown_tool(b, suggest_tools(b))})
    if left["slug"] == right["slug"]:
        return _envelope({"ok": False, "spoken": f"{left['name']} is the same tool on both sides. Pick a second one."})
    rows = await collect_signals([left["slug"], right["slug"]], resolved_window, transport=transport)
    left_card = _card(left, rows[left["slug"]], full=True)
    right_card = _card(right, rows[right["slug"]], full=True)
    payload = {
        "window": resolved_window,
        "a": left_card,
        "b": right_card,
        "data_source": "live"
        if left_card["data_source"] == right_card["data_source"] == "live"
        else "seed"
        if left_card["data_source"] == right_card["data_source"] == "seed"
        else "mixed",
    }
    payload["spoken"] = speak_compare(left_card, right_card, resolved_window)
    return _envelope(payload)


def _tools_for_category(category: str | None) -> list[dict]:
    if category is None:
        return list(TOOLS)
    return [tool for tool in TOOLS if tool["category"] == category]


async def trending_tools(
    category: str = "all",
    window: str = "7d",
    limit: int = 5,
    *,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    resolved_window, window_error = resolve_window(window)
    if window_error or resolved_window is None:
        return _envelope({"ok": False, "spoken": window_error or speak_bad_window(window)})
    resolved_category, category_error = resolve_category(category)
    if category_error:
        return _envelope({"ok": False, "spoken": category_error})
    try:
        capped = max(1, min(10, int(limit)))
    except (TypeError, ValueError):
        capped = 5
    chosen = _tools_for_category(resolved_category)
    rows = await collect_signals([tool["slug"] for tool in chosen], resolved_window, transport=transport)
    cards = [_card(tool, rows[tool["slug"]], full=False) for tool in chosen]
    cards.sort(key=lambda card: (-card["score"], card["name"]))
    top = cards[:capped]
    sources = {card["data_source"] for card in top} or {"seed"}
    data_source = sources.pop() if len(sources) == 1 else "mixed"
    payload = {
        "category": resolved_category or "all",
        "window": resolved_window,
        "tools": top,
        "data_source": data_source,
    }
    payload["spoken"] = speak_trending(resolved_category or "", resolved_window, top, data_source)
    return _envelope(payload)


async def weekly_digest(
    category: str = "all",
    *,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Leaders by momentum score, plus who got louder in community mentions."""
    resolved_category, category_error = resolve_category(category)
    if category_error:
        return _envelope({"ok": False, "spoken": category_error})
    chosen = _tools_for_category(resolved_category)
    rows = await collect_signals([tool["slug"] for tool in chosen], "7d", transport=transport)
    cards = [_card(tool, rows[tool["slug"]], full=False) for tool in chosen]
    by_score = sorted(cards, key=lambda card: (-card["score"], card["name"]))
    by_mentions = sorted(cards, key=lambda card: (-card["mention_delta"], -card["score"], card["name"]))
    leaders = by_score[:3]
    riser = by_mentions[0] if by_mentions and by_mentions[0]["mention_delta"] > 0 else None
    worth = next((card for card in by_score if card["stage"] in {"Emerging", "Growing"} and card not in leaders), None)
    sources = {card["data_source"] for card in leaders} or {"seed"}
    data_source = sources.pop() if len(sources) == 1 else "mixed"
    payload: dict[str, Any] = {
        "category": resolved_category or "all",
        "window": "7d",
        "leaders": leaders,
        "riser": riser,
        "worth_a_look": worth,
        "data_source": data_source,
    }
    payload["spoken"] = speak_digest(payload)
    return _envelope(payload)
