"""Absolute momentum score ported from StackRadar.

Source:
https://github.com/amantebriwal4321/StackRadar/blob/main/backend/app/services/scoring.py

The function that actually ships in that repo is ``calculate_all_tool_scores``.
An older single-tool helper with different weights is still in the file and is
not used here. Weights and anchors are unchanged:

* GitHub stars: 60 percent, log floor 500, ceiling 300,000
* GitHub forks: 15 percent, log floor 50, ceiling 60,000
* Community mentions: 25 percent, saturating at 25 mentions

Mentions are Hacker News + Dev.to + Reddit + news. The score is absolute: one
tool does not move because an unrelated tool moved.

Mention matching (``classify_text_to_tools``, ``count_mentions``) is the same
word-boundary pass the web app uses, so RSS titles attribute to the same slugs.
"""

from __future__ import annotations

import math
import re
from typing import Any

from stackradar_mcp.catalog import TOOLS

TOOL_REGISTRY = {
    tool["slug"]: {"repo": tool["github_repo"], "keywords": tool["keywords"], "domain": tool["category"]}
    for tool in TOOLS
}

_TOOL_PATTERNS: dict[str, list[re.Pattern[str]]] = {}
for _slug, _data in TOOL_REGISTRY.items():
    _TOOL_PATTERNS[_slug] = [
        re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE) for keyword in _data["keywords"]
    ]


def classify_text_to_tools(text: str) -> set[str]:
    """Return tool slugs whose keywords appear as whole words in ``text``."""
    if not text:
        return set()
    matched: set[str] = set()
    for slug, patterns in _TOOL_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text):
                matched.add(slug)
                break
    return matched


def _item_text(item: dict) -> str:
    title = item.get("title", "") or ""
    tag_list = item.get("tag_list", [])
    tags = " ".join(tag_list) if isinstance(tag_list, list) else (item.get("tags", "") or "")
    subreddit = item.get("subreddit", "") or ""
    description = item.get("description", "") or ""
    return f"{title} {tags} {subreddit} {description}".strip()


def count_mentions(items: list[dict], all_tool_slugs: set[str]) -> dict[str, int]:
    """Count items that mention each slug. One item counts once, not once per hit."""
    counts = {slug: 0 for slug in all_tool_slugs}
    for item in items:
        for slug in classify_text_to_tools(_item_text(item)):
            if slug in counts:
                counts[slug] += 1
    return counts


def _percentile_rank(values: list[float]) -> list[float]:
    """Kept for parity with the source file. The live score does not call it."""
    n = len(values)
    if n <= 1:
        return [50.0] * n
    ranks = []
    for value in values:
        less_than = sum(1 for other in values if other < value)
        equal_to = sum(1 for other in values if other == value)
        rank = less_than + (equal_to / 2.0)
        ranks.append((rank / n) * 100.0)
    return ranks


def _norm_log(val: float, floor: float, ceil: float) -> float:
    """Floor-anchored log scale. At or below ``floor`` is 0, at or above ``ceil`` is 100."""
    if val <= floor:
        return 0.0
    lo, hi = math.log(floor), math.log(ceil)
    return max(0.0, min(100.0, ((math.log(val) - lo) / (hi - lo)) * 100.0))


def calculate_all_tool_scores(tool_data: list[dict[str, Any]]) -> list[float]:
    """Score every row on an absolute 0 to 100 scale. Order matches the input."""
    if not tool_data:
        return []
    scores = []
    for row in tool_data:
        stars = row.get("stars", 0) or 0
        forks = row.get("forks", 0) or 0
        total_mentions = (
            (row.get("hn_count", 0) or 0)
            + (row.get("devto_count", 0) or 0)
            + (row.get("reddit_count", 0) or 0)
            + (row.get("news_count", 0) or 0)
        )
        stars_norm = _norm_log(stars, floor=500, ceil=300_000)
        forks_norm = _norm_log(forks, floor=50, ceil=60_000)
        activity_norm = min(100.0, (total_mentions / 25.0) * 100.0)
        score = stars_norm * 0.60 + forks_norm * 0.15 + activity_norm * 0.25
        scores.append(round(max(0.0, min(score, 100.0)), 1))
    return scores


def score_breakdown(stars: int, forks: int, hn: int, devto: int, reddit: int, news: int) -> dict[str, Any]:
    """Same math as ``calculate_all_tool_scores``, with the parts a voice reply can cite."""
    stars_norm = _norm_log(stars, floor=500, ceil=300_000)
    forks_norm = _norm_log(forks, floor=50, ceil=60_000)
    total = hn + devto + reddit + news
    activity_norm = min(100.0, (total / 25.0) * 100.0)
    parts = {
        "github_stars": {
            "raw": stars,
            "normalized": round(stars_norm, 1),
            "weight": 0.60,
            "points": round(stars_norm * 0.60, 1),
        },
        "github_forks": {
            "raw": forks,
            "normalized": round(forks_norm, 1),
            "weight": 0.15,
            "points": round(forks_norm * 0.15, 1),
        },
        "community": {
            "hn": hn,
            "devto": devto,
            "reddit": reddit,
            "news": news,
            "total_mentions": total,
            "saturation": 25,
            "normalized": round(activity_norm, 1),
            "weight": 0.25,
            "points": round(activity_norm * 0.25, 1),
        },
    }
    score = calculate_all_tool_scores(
        [{"stars": stars, "forks": forks, "hn_count": hn, "devto_count": devto, "reddit_count": reddit, "news_count": news}]
    )[0]
    return {"score": score, "parts": parts}


def classify_growth_stage(score: float) -> str:
    """StackRadar stage cut points for the absolute scale."""
    if score < 20:
        return "Declining"
    if score < 40:
        return "Emerging"
    if score < 70:
        return "Growing"
    return "Mature"


def classify_trend(growth_pct: float) -> str:
    """StackRadar trend labels from score change versus a prior snapshot."""
    if growth_pct > 15:
        return "rising"
    if growth_pct > 5:
        return "growing"
    if growth_pct >= -5:
        return "stable"
    return "declining"


def growth_pct(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100.0, 1)
