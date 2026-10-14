"""Lock the momentum math to StackRadar's absolute formula."""

import pytest

from stackradar_mcp import scoring as S
from stackradar_mcp.scoring import classify_text_to_tools, count_mentions

REACT_LIKE = {"stars": 230_000, "forks": 47_000, "hn_count": 3, "devto_count": 4, "reddit_count": 2, "news_count": 1}
SMALL = {"stars": 2_000, "forks": 120}


def test_scores_are_absolute_not_relative():
    alone = S.calculate_all_tool_scores([SMALL])[0]
    beside_giant = S.calculate_all_tool_scores([SMALL, REACT_LIKE])[0]
    beside_nothing = S.calculate_all_tool_scores([SMALL, {"stars": 0}])[0]
    assert alone == beside_giant == beside_nothing


def test_output_order_matches_input_order():
    first, second = S.calculate_all_tool_scores([SMALL, REACT_LIKE])
    assert second > first


def test_no_signal_scores_zero_with_no_flat_base():
    assert S.calculate_all_tool_scores([{}]) == [0.0]


def test_maximum_signal_is_capped_at_100():
    huge = {"stars": 10**9, "forks": 10**9, "hn_count": 1000}
    assert S.calculate_all_tool_scores([huge]) == [100.0]


def test_every_score_is_within_bounds():
    rows = [{}, SMALL, REACT_LIKE, {"stars": 499}, {"hn_count": 10**6}]
    assert all(0.0 <= score <= 100.0 for score in S.calculate_all_tool_scores(rows))


def test_more_stars_never_lowers_the_score():
    scores = S.calculate_all_tool_scores([{"stars": n} for n in (100, 1_000, 10_000, 100_000, 1_000_000)])
    assert scores == sorted(scores)


def test_community_activity_saturates_at_25_mentions_and_weighs_25_percent():
    at_cap = S.calculate_all_tool_scores([{"hn_count": 25}])[0]
    past_cap = S.calculate_all_tool_scores([{"hn_count": 250}])[0]
    assert at_cap == past_cap == 25.0


def test_a_single_mention_registers():
    assert S.calculate_all_tool_scores([{"devto_count": 1}])[0] > 0


def test_empty_input():
    assert S.calculate_all_tool_scores([]) == []


def test_norm_log_floor_and_ceiling():
    assert S._norm_log(500, 500, 300_000) == 0.0
    assert S._norm_log(0, 500, 300_000) == 0.0
    assert S._norm_log(300_000, 500, 300_000) == pytest.approx(100.0)
    assert S._norm_log(10**9, 500, 300_000) == 100.0


def test_norm_log_is_logarithmic():
    mid = (500 * 300_000) ** 0.5
    assert S._norm_log(mid, 500, 300_000) == pytest.approx(50.0)


def test_breakdown_matches_batch_score():
    breakdown = S.score_breakdown(230_000, 47_000, 3, 4, 2, 1)
    assert breakdown["score"] == S.calculate_all_tool_scores([REACT_LIKE])[0]
    points = sum(part["points"] for part in breakdown["parts"].values())
    assert points == pytest.approx(breakdown["score"], abs=0.2)


def test_keywords_match_on_word_boundaries():
    assert classify_text_to_tools("I love React hooks") == {"react"}
    assert classify_text_to_tools("going to the store") == set()
    assert classify_text_to_tools("") == set()


def test_count_mentions_is_one_per_item_not_per_occurrence():
    items = [{"title": "React React React"}, {"title": "react vs everything"}]
    counts = count_mentions(items, {"react", "rust"})
    assert counts["react"] == 2
    assert counts["rust"] == 0


def test_devto_description_and_tags_are_searched():
    assert count_mentions([{"title": "My week", "description": "Moved our API to FastAPI"}], {"fastapi"})["fastapi"] == 1
    assert count_mentions([{"title": "My week", "tag_list": ["docker"]}], {"docker"})["docker"] == 1


@pytest.mark.parametrize(
    ("score", "stage"),
    [
        (0, "Declining"),
        (19.9, "Declining"),
        (20, "Emerging"),
        (39.9, "Emerging"),
        (40, "Growing"),
        (69.9, "Growing"),
        (70, "Mature"),
        (100, "Mature"),
    ],
)
def test_growth_stage_boundaries(score, stage):
    assert S.classify_growth_stage(score) == stage


@pytest.mark.parametrize(
    ("pct", "trend"),
    [
        (15.1, "rising"),
        (15, "growing"),
        (5.1, "growing"),
        (5, "stable"),
        (-5, "stable"),
        (-5.1, "declining"),
    ],
)
def test_trend_boundaries(pct, trend):
    assert S.classify_trend(pct) == trend


def test_growth_pct_handles_a_zero_baseline():
    assert S.growth_pct(10, 0) is None
    assert S.growth_pct(110, 100) == 10.0


def test_percentile_helper_still_matches_the_source_file():
    # The web app keeps this helper and does not use it for the live score.
    assert S._percentile_rank([1]) == [50.0]
    assert S._percentile_rank([]) == []
    ranked = S._percentile_rank([1, 3])
    assert ranked[1] > ranked[0]
