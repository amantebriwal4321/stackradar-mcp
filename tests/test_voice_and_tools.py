import pytest

from stackradar_mcp.catalog import TOOLS_BY_SLUG
from stackradar_mcp.service import compare_tools, tool_score, trending_tools, weekly_digest
from stackradar_mcp.signals import load_seed_file
from stackradar_mcp.voice import speak_score

BANNED = ("*", "#", "`", "{", "}", "[", "]", "—", "–", "--")


def _assert_spoken(text: str) -> None:
    assert text
    assert len(text) < 700
    for token in BANNED:
        assert token not in text
    assert "\n" not in text


@pytest.mark.anyio
async def test_seed_covers_every_catalog_slug():
    blob = load_seed_file()
    assert set(blob["tools"]) == set(TOOLS_BY_SLUG)


@pytest.mark.anyio
async def test_tool_score_fastapi_uses_snapshot_and_breakdown():
    payload = await tool_score("FastAPI")
    assert payload["ok"] is True
    assert payload["slug"] == "fastapi"
    assert payload["data_source"] == "seed"
    assert payload["breakdown"]["parts"]["github_stars"]["weight"] == 0.60
    assert 0 <= payload["score"] <= 100
    _assert_spoken(payload["spoken"])
    assert "FastAPI" in payload["spoken"]
    assert "out of 100" in payload["spoken"]


@pytest.mark.anyio
async def test_window_changes_mention_counts():
    day = await tool_score("react", "24h")
    month = await tool_score("react", "30d")
    assert day["breakdown"]["parts"]["community"]["total_mentions"] < month["breakdown"]["parts"]["community"]["total_mentions"]


@pytest.mark.anyio
async def test_unknown_tool_is_spoken_not_raised():
    payload = await tool_score("not-a-real-library")
    assert payload["ok"] is False
    _assert_spoken(payload["spoken"])
    assert "don't have a tool" in payload["spoken"]


@pytest.mark.anyio
async def test_compare_names_a_gap():
    payload = await compare_tools("fastapi", "next.js")
    assert payload["ok"] is True
    assert payload["a"]["slug"] == "fastapi"
    assert payload["b"]["slug"] == "nextjs"
    _assert_spoken(payload["spoken"])
    assert "FastAPI" in payload["spoken"]
    assert "Next.js" in payload["spoken"]


@pytest.mark.anyio
async def test_trending_ai_is_sorted_and_short():
    payload = await trending_tools("ai", "week", 3)
    assert payload["ok"] is True
    assert payload["category"] == "AI / ML"
    assert payload["window"] == "7d"
    scores = [tool["score"] for tool in payload["tools"]]
    assert scores == sorted(scores, reverse=True)
    assert len(payload["tools"]) == 3
    _assert_spoken(payload["spoken"])
    assert "AI and ML" in payload["spoken"]


@pytest.mark.anyio
async def test_bad_category_and_window():
    bad_category = await trending_tools("underwater basket weaving")
    assert bad_category["ok"] is False
    assert "category" in bad_category["spoken"]
    bad_window = await tool_score("react", "fortnight")
    assert bad_window["ok"] is False
    assert "24h" in bad_window["spoken"]


@pytest.mark.anyio
async def test_weekly_digest_names_ollama_as_the_loudest_snapshot_riser():
    payload = await weekly_digest()
    assert payload["ok"] is True
    assert payload["window"] == "7d"
    assert len(payload["leaders"]) == 3
    assert payload["riser"]["slug"] == "ollama"
    assert payload["riser"]["mention_delta"] > 0
    _assert_spoken(payload["spoken"])
    assert "Ollama" in payload["spoken"]
    assert "digest" in payload["spoken"].lower()


def test_speak_score_mentions_the_snapshot_when_seeded():
    text = speak_score(
        {
            "name": "Vite",
            "score": 61.2,
            "stage": "Growing",
            "trend": "stable",
            "conversation": "steady",
            "data_source": "seed",
        }
    )
    assert "saved snapshot" in text
    assert "61 out of 100" in text
