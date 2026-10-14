"""Write the offline snapshot used when a public API does not answer.

Mention counts are editorial baselines for the voice demo.
Star and fork counts start as round estimates. Run the script with the
word live to replace those two fields from the public GitHub API.
Mentions stay as they are.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

# slug, stars, forks, 7d mentions (hn, devto, reddit, news), previous 7d mentions
ROWS: list[tuple] = [
    ("react", 251010, 51505, (6, 5, 5, 2), (6, 5, 4, 2)),
    ("tailwindcss", 97862, 8492, (2, 3, 2, 1), (2, 3, 2, 1)),
    ("vite", 83287, 8855, (2, 2, 2, 1), (2, 2, 1, 1)),
    ("vuejs", 54617, 9254, (2, 2, 2, 1), (2, 2, 2, 1)),
    ("svelte", 88347, 8208, (3, 2, 2, 1), (2, 1, 1, 0)),
    ("nextjs", 143002, 34915, (4, 4, 3, 1), (4, 3, 3, 1)),
    ("fastapi", 103081, 10042, (3, 4, 2, 1), (2, 3, 2, 1)),
    ("astro", 63230, 3848, (2, 2, 1, 1), (1, 1, 0, 0)),
    ("trpc", 40703, 1710, (1, 1, 1, 0), (1, 1, 1, 0)),
    ("bun", 96233, 5119, (3, 2, 2, 1), (1, 1, 0, 0)),
    ("deno", 108676, 6467, (1, 1, 1, 0), (1, 1, 1, 0)),
    ("prisma", 47692, 2550, (1, 2, 1, 0), (1, 2, 1, 0)),
    ("pytorch", 104664, 32459, (4, 3, 3, 1), (4, 3, 2, 1)),
    ("tensorflow", 200964, 79416, (3, 2, 2, 1), (3, 2, 2, 1)),
    ("transformers", 167674, 34880, (4, 3, 2, 1), (3, 3, 2, 1)),
    ("langchain", 147803, 24797, (4, 3, 3, 1), (3, 2, 2, 1)),
    ("ollama", 183130, 18269, (6, 4, 4, 2), (1, 1, 1, 0)),
    ("supabase", 111532, 16824, (2, 2, 2, 1), (2, 2, 1, 1)),
    ("terraform", 49911, 10642, (2, 1, 2, 1), (2, 1, 2, 1)),
    ("kubernetes", 128211, 47064, (3, 2, 3, 1), (3, 2, 3, 1)),
    ("docker", 72190, 19236, (3, 2, 3, 1), (3, 2, 2, 1)),
    ("grafana", 77269, 14850, (1, 1, 2, 0), (1, 1, 2, 0)),
    ("prometheus", 66547, 10915, (1, 1, 1, 0), (1, 1, 1, 0)),
    ("rust", 119820, 18662, (4, 2, 3, 1), (3, 2, 3, 1)),
    ("go", 139157, 22331, (3, 2, 2, 1), (3, 2, 2, 1)),
    ("wireshark", 10003, 2230, (1, 0, 1, 0), (1, 0, 1, 0)),
    ("metasploit", 39149, 15000, (1, 0, 1, 0), (1, 0, 1, 0)),
    ("owasp-zap", 15933, 2668, (1, 1, 1, 0), (1, 0, 1, 0)),
    ("hardhat", 8514, 1733, (1, 1, 1, 0), (1, 1, 1, 0)),
    ("foundry", 10667, 2671, (2, 1, 1, 0), (1, 1, 1, 0)),
    ("ethersjs", 8717, 2132, (1, 1, 1, 0), (1, 1, 1, 0)),
]


def _window_counts(counts: tuple[int, int, int, int], scale: float, cap: int) -> dict[str, int]:
    keys = ("hn", "devto", "reddit", "news")
    scaled = [min(cap, int(round(value * scale))) for value in counts]
    return dict(zip(keys, scaled, strict=True))


def fetch_stars(repo: str) -> tuple[int, int] | None:
    url = f"https://api.github.com/repos/{repo}"
    request = urllib.request.Request(url, headers={"User-Agent": "stackradar-mcp-seed", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode())
    except Exception as exc:  # noqa: BLE001 - seed refresh should keep going
        print(f"github skip {repo}: {exc}")
        return None
    return int(payload.get("stargazers_count") or 0), int(payload.get("forks_count") or 0)


def build(live_stars: bool) -> dict:
    from stackradar_mcp.catalog import TOOLS_BY_SLUG

    tools = {}
    for slug, stars, forks, current, previous in ROWS:
        repo = TOOLS_BY_SLUG[slug]["github_repo"]
        if live_stars:
            fetched = fetch_stars(repo)
            if fetched and fetched[0] > 0:
                stars, forks = fetched
                print(f"{slug}: {stars} stars, {forks} forks")
        tools[slug] = {
            "stars": stars,
            "forks": forks,
            "windows": {
                "24h": _window_counts(current, 0.25, 8),
                "7d": _window_counts(current, 1, 40),
                "30d": _window_counts(current, 1.6, 40),
            },
            "previous": {
                "stars": stars,
                "forks": forks,
                "windows": {
                    "24h": _window_counts(previous, 0.25, 8),
                    "7d": _window_counts(previous, 1, 40),
                    "30d": _window_counts(previous, 1.6, 40),
                },
            },
        }
    return {
        "as_of": "2026-10-14",
        "note": (
            "Saved snapshot for when GitHub, Hacker News, Dev.to, Reddit, or RSS does not answer. "
            "Star and fork figures are refreshed with: python scripts/build_seed.py live. "
            "Mention counts are baselines so the weekly conversation line has a prior week to compare."
        ),
        "formula": "StackRadar calculate_all_tool_scores",
        "tools": tools,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("refresh", nargs="?", default="keep")
    args = parser.parse_args()
    payload = build(args.refresh == "live")
    destination = Path(__file__).resolve().parents[1] / "stackradar_mcp" / "data" / "seed_signals.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {destination}")


if __name__ == "__main__":
    main()
