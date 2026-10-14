"""Write the offline snapshot used when a public API does not answer.

Mention counts are editorial baselines for the voice demo, not a scrape.
Star and fork counts start as round estimates. Pass --live-stars to replace
those two fields from the public GitHub API and leave mentions alone.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

# slug, stars, forks, 7d mentions (hn, devto, reddit, news), previous 7d mentions
ROWS: list[tuple] = [
    ("react", 238000, 49000, (6, 5, 5, 2), (6, 5, 4, 2)),
    ("tailwindcss", 86000, 4500, (2, 3, 2, 1), (2, 3, 2, 1)),
    ("vite", 70000, 6500, (2, 2, 2, 1), (2, 2, 1, 1)),
    ("vuejs", 48000, 8000, (2, 2, 2, 1), (2, 2, 2, 1)),
    ("svelte", 80000, 4300, (3, 2, 2, 1), (2, 1, 1, 0)),
    ("nextjs", 130000, 28000, (4, 4, 3, 1), (4, 3, 3, 1)),
    ("fastapi", 80000, 7000, (3, 4, 2, 1), (2, 3, 2, 1)),
    ("astro", 48000, 2600, (2, 2, 1, 1), (1, 1, 0, 0)),
    ("trpc", 35000, 1300, (1, 1, 1, 0), (1, 1, 1, 0)),
    ("bun", 75000, 3000, (3, 2, 2, 1), (1, 1, 0, 0)),
    ("deno", 100000, 5500, (1, 1, 1, 0), (1, 1, 1, 0)),
    ("prisma", 40000, 1600, (1, 2, 1, 0), (1, 2, 1, 0)),
    ("pytorch", 86000, 23000, (4, 3, 3, 1), (4, 3, 2, 1)),
    ("tensorflow", 187000, 74000, (3, 2, 2, 1), (3, 2, 2, 1)),
    ("transformers", 140000, 28000, (4, 3, 2, 1), (3, 3, 2, 1)),
    ("langchain", 95000, 15500, (4, 3, 3, 1), (3, 2, 2, 1)),
    ("ollama", 105000, 8500, (6, 4, 4, 2), (1, 1, 1, 0)),
    ("supabase", 78000, 8000, (2, 2, 2, 1), (2, 2, 1, 1)),
    ("terraform", 44000, 9700, (2, 1, 2, 1), (2, 1, 2, 1)),
    ("kubernetes", 112000, 40000, (3, 2, 3, 1), (3, 2, 3, 1)),
    ("docker", 69000, 18700, (3, 2, 3, 1), (3, 2, 2, 1)),
    ("grafana", 66000, 12300, (1, 1, 2, 0), (1, 1, 2, 0)),
    ("prometheus", 56000, 9300, (1, 1, 1, 0), (1, 1, 1, 0)),
    ("rust", 100000, 13000, (4, 2, 3, 1), (3, 2, 3, 1)),
    ("go", 127000, 18000, (3, 2, 2, 1), (3, 2, 2, 1)),
    ("wireshark", 8000, 1800, (1, 0, 1, 0), (1, 0, 1, 0)),
    ("metasploit", 35000, 14000, (1, 0, 1, 0), (1, 0, 1, 0)),
    ("owasp-zap", 13000, 2300, (1, 1, 1, 0), (1, 0, 1, 0)),
    ("hardhat", 7500, 1500, (1, 1, 1, 0), (1, 1, 1, 0)),
    ("foundry", 8500, 900, (2, 1, 1, 0), (1, 1, 1, 0)),
    ("ethersjs", 8000, 2000, (1, 1, 1, 0), (1, 1, 1, 0)),
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
            "Star and fork figures are refreshed with scripts/build_seed.py --live-stars when the API allows. "
            "Mention counts are baselines so the weekly conversation line has a prior week to compare."
        ),
        "formula": "StackRadar calculate_all_tool_scores",
        "tools": tools,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-stars", action="store_true")
    args = parser.parse_args()
    payload = build(args.live_stars)
    destination = Path(__file__).resolve().parents[1] / "stackradar_mcp" / "data" / "seed_signals.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {destination}")


if __name__ == "__main__":
    main()
