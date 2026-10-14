"""Load stars, forks, and mention counts from public APIs, with a snapshot fallback."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

from stackradar_mcp.cache import cache_get, cache_set
from stackradar_mcp.catalog import REDDIT_TIME, TOOLS_BY_SLUG, WINDOW_SECONDS
from stackradar_mcp.scoring import count_mentions

logger = logging.getLogger(__name__)

USER_AGENT = "stackradar-mcp/0.1 (Amazon Alexa+ hackathon demo)"
GITHUB_API = "https://api.github.com/repos/{repo}"
HN_API = "https://hn.algolia.com/api/v1/search"
DEVTO_API = "https://dev.to/api/articles"
REDDIT_API = "https://www.reddit.com/search.json"
RSS_FEEDS = (
    "https://hnrss.org/frontpage",
    "https://dev.to/feed",
)

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed_signals.json"


@dataclass
class Signals:
    stars: int
    forks: int
    hn: int
    devto: int
    reddit: int
    news: int
    sources: dict[str, str] = field(default_factory=dict)
    previous_stars: int = 0
    previous_forks: int = 0
    previous_hn: int = 0
    previous_devto: int = 0
    previous_reddit: int = 0
    previous_news: int = 0

    @property
    def data_source(self) -> str:
        used = {self.sources.get(key, "seed") for key in ("github", "hn", "devto", "reddit", "news")}
        if used == {"live"}:
            return "live"
        if used == {"seed"}:
            return "seed"
        return "mixed"


def mode() -> str:
    value = os.environ.get("STACKRADAR_MODE", "auto").strip().lower()
    if value not in {"auto", "live", "seed"}:
        return "auto"
    return value


def live_budget_seconds() -> float:
    raw = os.environ.get("STACKRADAR_LIVE_BUDGET_SECONDS", "8")
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 8.0


def load_seed_file() -> dict[str, Any]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def seed_signals(slug: str, window: str) -> Signals:
    blob = load_seed_file()["tools"][slug]
    current = blob["windows"][window]
    previous = blob["previous"]["windows"][window]
    return Signals(
        stars=int(blob["stars"]),
        forks=int(blob["forks"]),
        hn=int(current["hn"]),
        devto=int(current["devto"]),
        reddit=int(current["reddit"]),
        news=int(current["news"]),
        sources={key: "seed" for key in ("github", "hn", "devto", "reddit", "news")},
        previous_stars=int(blob["previous"]["stars"]),
        previous_forks=int(blob["previous"]["forks"]),
        previous_hn=int(previous["hn"]),
        previous_devto=int(previous["devto"]),
        previous_reddit=int(previous["reddit"]),
        previous_news=int(previous["news"]),
    )


def seed_as_of() -> str:
    return str(load_seed_file().get("as_of", ""))


async def collect_signals(
    slugs: list[str],
    window: str,
    *,
    transport: httpx.BaseTransport | None = None,
    force_live: bool | None = None,
) -> dict[str, Signals]:
    """Return one Signals row per slug. Seed mode never touches the network."""
    rows = {slug: seed_signals(slug, window) for slug in slugs}
    use_live = mode() in {"auto", "live"} if force_live is None else force_live
    if not use_live or not slugs:
        return rows

    timeout = httpx.Timeout(6.0, connect=3.0)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    semaphore = asyncio.Semaphore(6)

    async with httpx.AsyncClient(timeout=timeout, headers=headers, transport=transport, follow_redirects=True) as client:

        async def enrich(slug: str, news_counts: dict[str, int] | None) -> None:
            tool = TOOLS_BY_SLUG[slug]
            keyword = tool["keywords"][0]
            async with semaphore:
                github, hn, devto, reddit = await asyncio.gather(
                    _github(client, tool["github_repo"]),
                    _hn(client, keyword, window),
                    _devto(client, tool["slug"], window),
                    _reddit(client, keyword, window),
                )
            if github is not None:
                rows[slug].stars, rows[slug].forks = github
                rows[slug].sources["github"] = "live"
            if hn is not None:
                rows[slug].hn = hn
                rows[slug].sources["hn"] = "live"
            if devto is not None:
                rows[slug].devto = devto
                rows[slug].sources["devto"] = "live"
            if reddit is not None:
                rows[slug].reddit = reddit
                rows[slug].sources["reddit"] = "live"
            if news_counts is not None:
                rows[slug].news = news_counts.get(slug, 0)
                rows[slug].sources["news"] = "live"

        async def run() -> None:
            news_counts = await _news_counts(client, window)
            await asyncio.gather(*(enrich(slug, news_counts) for slug in slugs))

        try:
            await asyncio.wait_for(run(), timeout=live_budget_seconds())
        except TimeoutError:
            logger.info("live budget exhausted; unfinished tools keep the snapshot")
    return rows


def _recent_failure(key: str) -> bool:
    return cache_get(f"{key}:fail") is True


def _remember_failure(key: str) -> None:
    # A blocked API should not be retried on every spoken question.
    cache_set(f"{key}:fail", True, ttl=900)


async def _github(client: httpx.AsyncClient, repo: str) -> tuple[int, int] | None:
    key = f"github:{repo}"
    if _recent_failure(key):
        return None
    cached = cache_get(key)
    if isinstance(cached, dict) and "stars" in cached:
        return int(cached["stars"]), int(cached["forks"])
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = await client.get(GITHUB_API.format(repo=repo), headers=headers)
        response.raise_for_status()
        payload = response.json()
        value = {"stars": int(payload.get("stargazers_count") or 0), "forks": int(payload.get("forks_count") or 0)}
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.info("github fallback for %s: %s", repo, exc)
        _remember_failure(key)
        return None
    cache_set(key, value)
    return value["stars"], value["forks"]


async def _hn(client: httpx.AsyncClient, keyword: str, window: str) -> int | None:
    key = f"hn:{keyword}:{window}"
    if _recent_failure(key):
        return None
    cached = cache_get(key)
    if isinstance(cached, int):
        return cached
    since = int(datetime.now(timezone.utc).timestamp()) - WINDOW_SECONDS[window]
    try:
        response = await client.get(
            HN_API,
            params={"query": keyword, "tags": "story", "numericFilters": f"created_at_i>{since}", "hitsPerPage": 20},
        )
        response.raise_for_status()
        hits = response.json().get("hits") or []
        # Count stories we actually received. nbHits is the whole index and
        # blows up common words like "react" or "bun".
        count = len(hits) if isinstance(hits, list) else 0
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.info("hn fallback for %s: %s", keyword, exc)
        _remember_failure(key)
        return None
    cache_set(key, count)
    return count


async def _devto(client: httpx.AsyncClient, tag: str, window: str) -> int | None:
    key = f"devto:{tag}:{window}"
    if _recent_failure(key):
        return None
    cached = cache_get(key)
    if isinstance(cached, int):
        return cached
    since = datetime.now(timezone.utc).timestamp() - WINDOW_SECONDS[window]
    try:
        response = await client.get(DEVTO_API, params={"tag": tag, "per_page": 30})
        response.raise_for_status()
        articles = response.json()
        if not isinstance(articles, list):
            return None
        count = 0
        for article in articles:
            published = article.get("published_at") or ""
            try:
                stamp = datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp()
            except ValueError:
                stamp = since
            if stamp >= since:
                count += 1
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.info("devto fallback for %s: %s", tag, exc)
        _remember_failure(key)
        return None
    cache_set(key, count)
    return count


async def _reddit(client: httpx.AsyncClient, keyword: str, window: str) -> int | None:
    key = f"reddit:{keyword}:{window}"
    if _recent_failure(key):
        return None
    cached = cache_get(key)
    if isinstance(cached, int):
        return cached
    try:
        response = await client.get(
            REDDIT_API,
            params={"q": keyword, "sort": "new", "t": REDDIT_TIME[window], "limit": 25, "type": "link"},
        )
        response.raise_for_status()
        children = response.json().get("data", {}).get("children", [])
        count = len(children) if isinstance(children, list) else 0
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.info("reddit fallback for %s: %s", keyword, exc)
        _remember_failure(key)
        return None
    cache_set(key, count)
    return count


async def _news_counts(client: httpx.AsyncClient, window: str) -> dict[str, int] | None:
    key = f"rss:{window}"
    if _recent_failure(key):
        return None
    cached = cache_get(key)
    if isinstance(cached, dict):
        return {str(slug): int(count) for slug, count in cached.items()}
    since = datetime.now(timezone.utc).timestamp() - WINDOW_SECONDS[window]
    items: list[dict[str, str]] = []
    failures = 0
    for url in RSS_FEEDS:
        try:
            response = await client.get(url, headers={"Accept": "application/rss+xml, application/xml, text/xml"})
            response.raise_for_status()
            items.extend(_rss_items(response.text, since))
        except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
            failures += 1
            logger.info("rss fallback for %s: %s", url, exc)
    if failures == len(RSS_FEEDS):
        _remember_failure(key)
        return None
    counts = count_mentions(items, set(TOOLS_BY_SLUG))
    cache_set(key, counts)
    return counts


def _rss_items(xml_text: str, since: float) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    found: list[dict[str, str]] = []
    for node in root.iter():
        if _local(node.tag) != "item":
            continue
        title = ""
        published: float | None = None
        for child in list(node):
            name = _local(child.tag)
            if name == "title" and child.text:
                title = child.text
            elif name in {"pubDate", "published", "updated", "date"} and child.text:
                published = _parse_time(child.text)
        if published is not None and published < since:
            continue
        if title:
            found.append({"title": title})
    return found


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_time(value: str) -> float | None:
    value = value.strip()
    try:
        return parsedate_to_datetime(value).timestamp()
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None
