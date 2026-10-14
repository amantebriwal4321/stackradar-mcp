import json

import httpx
import pytest

from stackradar_mcp.signals import collect_signals, seed_signals


def _transport() -> tuple[httpx.MockTransport, list[str]]:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        host = request.url.host
        if host == "api.github.com":
            return httpx.Response(200, json={"stargazers_count": 12345, "forks_count": 678})
        if host == "hn.algolia.com":
            return httpx.Response(200, json={"nbHits": 999, "hits": [{}, {}, {}, {}]})
        if host == "dev.to" and request.url.path.startswith("/api/"):
            return httpx.Response(
                200,
                json=[{"published_at": "2026-10-14T00:00:00Z", "title": "FastAPI notes"}],
            )
        if host == "www.reddit.com":
            return httpx.Response(403, json={"message": "blocked"})
        if "hnrss.org" in host or request.url.path == "/feed":
            xml = """<?xml version="1.0"?>
            <rss><channel>
              <item><title>FastAPI ships a new release</title><pubDate>Tue, 14 Oct 2026 12:00:00 GMT</pubDate></item>
            </channel></rss>"""
            return httpx.Response(200, text=xml)
        return httpx.Response(404)

    return httpx.MockTransport(handler), calls


@pytest.mark.anyio
async def test_seed_mode_does_not_call_the_network(monkeypatch):
    monkeypatch.setenv("STACKRADAR_MODE", "seed")
    transport, calls = _transport()
    rows = await collect_signals(["fastapi"], "7d", transport=transport)
    assert calls == []
    assert rows["fastapi"].data_source == "seed"
    assert rows["fastapi"].stars == seed_signals("fastapi", "7d").stars


@pytest.mark.anyio
async def test_live_merges_github_and_falls_back_when_reddit_blocks(monkeypatch):
    monkeypatch.setenv("STACKRADAR_MODE", "live")
    transport, calls = _transport()
    rows = await collect_signals(["fastapi"], "7d", transport=transport, force_live=True)
    row = rows["fastapi"]
    assert row.stars == 12345
    assert row.forks == 678
    assert row.hn == 4
    assert row.devto == 1
    assert row.sources["reddit"] == "seed"
    assert row.sources["github"] == "live"
    assert row.sources["news"] == "live"
    assert row.news >= 1
    assert row.data_source == "mixed"
    assert calls


@pytest.mark.anyio
async def test_live_results_are_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("STACKRADAR_MODE", "live")
    monkeypatch.setenv("STACKRADAR_CACHE_DIR", str(tmp_path / "cache"))
    first, first_calls = _transport()
    await collect_signals(["fastapi"], "7d", transport=first, force_live=True)
    second, second_calls = _transport()
    rows = await collect_signals(["fastapi"], "7d", transport=second, force_live=True)
    assert rows["fastapi"].stars == 12345
    assert second_calls == []
    assert first_calls


def test_rss_parser_reads_titles():
    from stackradar_mcp.signals import _rss_items

    xml = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>Try Ollama locally</title><pubDate>Tue, 14 Oct 2026 12:00:00 GMT</pubDate></item>
      <item><title>Old news</title><pubDate>Tue, 14 Oct 2020 12:00:00 GMT</pubDate></item>
    </channel></rss>"""
    items = _rss_items(xml, since=1_700_000_000)
    assert [item["title"] for item in items] == ["Try Ollama locally"]
    assert json.dumps(items)
