"""Short lines meant to be read aloud. No markdown, no emoji, no score jargon."""

from __future__ import annotations

from stackradar_mcp.catalog import SPOKEN_CATEGORY, WINDOW_SPOKEN


def _int_score(score: float) -> int:
    return int(round(score))


def _source_clause(data_source: str) -> str:
    if data_source == "live":
        return "This reading is from live public signals."
    if data_source == "seed":
        return "This reading uses the saved snapshot, so it still answers if a public API is down."
    return "This reading mixes live signals with the saved snapshot where a source did not answer."


def speak_score(card: dict) -> str:
    score = _int_score(card["score"])
    stage = card["stage"].lower()
    trend = {
        "rising": "The score itself is rising against the saved baseline.",
        "growing": "The score is up a bit against the saved baseline.",
        "stable": "The score is steady against the saved baseline.",
        "declining": "The score is down against the saved baseline.",
    }.get(card["trend"], "The baseline comparison is unavailable.")
    conversation = card.get("conversation")
    extra = ""
    if conversation == "louder":
        extra = " Developer conversation around it is louder than the baseline."
    elif conversation == "quieter":
        extra = " Developer conversation around it is quieter than the baseline."
    return (
        f"{card['name']} scores {score} out of 100. It sits in the {stage} band. "
        f"{trend}{extra} {_source_clause(card['data_source'])}"
    )


def speak_trending(category_label: str, window: str, cards: list[dict], data_source: str) -> str:
    window_text = WINDOW_SPOKEN.get(window, window)
    if category_label:
        where = SPOKEN_CATEGORY.get(category_label, category_label)
        lead = f"Top {where} tools over {window_text}"
    else:
        lead = f"Top tools over {window_text}"
    if not cards:
        return f"I don't have tools to rank for that filter. {_source_clause(data_source)}"
    bits = [f"{card['name']} at {_int_score(card['score'])}" for card in cards[:3]]
    if len(bits) == 1:
        listing = bits[0]
    elif len(bits) == 2:
        listing = f"{bits[0]} and {bits[1]}"
    else:
        listing = f"{bits[0]}, {bits[1]}, and {bits[2]}"
    return f"{lead}: {listing}. {_source_clause(data_source)}"


def speak_compare(left: dict, right: dict, window: str) -> str:
    window_text = WINDOW_SPOKEN.get(window, window)
    left_score = left["score"]
    right_score = right["score"]
    gap = abs(left_score - right_score)
    if gap < 1:
        leader = f"{left['name']} and {right['name']} are basically tied"
        reason = "neither side has a meaningful lead"
    else:
        winner, loser = (left, right) if left_score > right_score else (right, left)
        reason = _biggest_gap(winner, loser)
        leader = f"{winner['name']} leads {loser['name']} by {_int_score(gap)} points"
    return (
        f"Over {window_text}, {left['name']} scores {_int_score(left_score)} and "
        f"{right['name']} scores {_int_score(right_score)}. {leader}, and {reason}. "
        f"{_source_clause(_mix_source(left['data_source'], right['data_source']))}"
    )


def _biggest_gap(winner: dict, loser: dict) -> str:
    labels = {
        "github_stars": "GitHub stars are the biggest gap",
        "github_forks": "forks are the biggest gap",
        "community": "community mentions are the biggest gap",
    }
    best_key = "github_stars"
    best = -1.0
    for key in labels:
        delta = winner["breakdown"]["parts"][key]["points"] - loser["breakdown"]["parts"][key]["points"]
        if delta > best:
            best = delta
            best_key = key
    return labels[best_key]


def _mix_source(left: str, right: str) -> str:
    sources = {left, right}
    if sources == {"live"}:
        return "live"
    if sources == {"seed"}:
        return "seed"
    return "mixed"


def speak_digest(payload: dict) -> str:
    leaders = payload["leaders"]
    if not leaders:
        return "I don't have a digest for that filter yet."
    names = [f"{card['name']} at {_int_score(card['score'])}" for card in leaders[:3]]
    if len(names) == 1:
        board = names[0]
    elif len(names) == 2:
        board = f"{names[0]} and {names[1]}"
    else:
        board = f"{names[0]}, {names[1]}, and {names[2]}"
    riser = payload.get("riser")
    if riser:
        delta = riser["mention_delta"]
        if delta > 40:
            amount = "a lot more community mentions"
        else:
            amount = f"{delta} more community mentions"
        already_leading = any(card["slug"] == riser["slug"] for card in leaders)
        if already_leading:
            move = f" {riser['name']} is also the loudest new conversation, with {amount} than the saved baseline."
        else:
            move = f" The loudest new conversation is {riser['name']}, with {amount} than the saved baseline."
    else:
        move = " Conversation volume is flat against the saved baseline."
    look = payload.get("worth_a_look")
    look_line = ""
    if look and (not riser or look["slug"] != riser["slug"]):
        look_line = f" Worth a look: {look['name']}, at {_int_score(look['score'])} out of 100."
    return (
        f"Weekly StackRadar digest. The board is led by {board}.{move}{look_line} "
        f"{_source_clause(payload['data_source'])}"
    )


def speak_unknown_tool(query: str, suggestions: list[str]) -> str:
    if suggestions:
        listed = ", ".join(suggestions)
        return f"I don't have a tool called {query}. Closest names I track are {listed}."
    return f"I don't have a tool called {query}. Try React, FastAPI, or PyTorch."


def speak_bad_category(query: str) -> str:
    return (
        f"I don't have a category called {query}. "
        "Try all, web, ai, data, cloud, devops, systems, security, or web3."
    )


def speak_bad_window(query: str) -> str:
    return f"I don't have a window called {query}. Use 24h, 7d, or 30d."
