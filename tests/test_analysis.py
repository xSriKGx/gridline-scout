from nfl_assistant.analysis import build_context, infer_filters
from nfl_assistant.data import load_plays


def test_infers_third_and_long_for_selected_defense():
    filters = infer_filters("What does the defense do on 3rd and long?", "KC")
    assert filters["side"] == "defense"
    assert filters["defteam"] == "KC"
    assert filters["down"] == 3
    assert filters["ydstogo_min"] == 7


def test_context_is_transparent_and_grounded_in_evidence():
    plays = load_plays("data/play_by_play_2025.csv.gz")
    context = build_context(plays, "What does KC defense do on 3rd and long?", "KC")
    assert context["meta"]["filter_labels"] == ["defense=KC", "down=3", "distance≥7"]
    assert context["stats"]["sample_size"] > 0
    assert all(item["citation"].startswith("play_id=") for item in context["evidence"])
    assert all("DEMO" not in item["citation"] for item in context["evidence"])


def test_red_zone_filter_reduces_sample():
    plays = load_plays("data/play_by_play_2025.csv.gz")
    context = build_context(plays, "How does KC defend in the red zone?", "KC")
    assert context["meta"]["filters"]["yardline_100_max"] == 20
    assert context["stats"]["sample_size"] < len(plays)


def test_real_nflverse_file_covers_all_32_teams():
    plays = load_plays("data/play_by_play_2025.csv.gz")
    teams = {str(play.get("posteam", "")) for play in plays} | {str(play.get("defteam", "")) for play in plays}
    teams.discard("")
    assert len(teams) == 32
    assert {play.get("season") for play in plays} == {2025}


def test_offense_and_late_game_filters_work_on_real_data():
    plays = load_plays("data/play_by_play_2025.csv.gz")
    context = build_context(
        plays,
        "What happens when BUF trails in the 4th quarter?",
        selected_team="BUF",
        team_side="offense",
    )
    assert context["meta"]["filters"]["posteam"] == "BUF"
    assert context["meta"]["filters"]["qtr"] == 4
    assert context["meta"]["filters"]["score_state"] == "trailing"
    assert context["stats"]["sample_size"] > 0
