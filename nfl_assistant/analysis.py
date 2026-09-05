"""Retrieval and deterministic statistics for the scouting assistant."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable
from xml.sax.saxutils import escape as xml_escape


TEAM_CODES = {
    "ari", "atl", "bal", "buf", "car", "chi", "cin", "cle", "dal", "den",
    "det", "gb", "hou", "ind", "jax", "kc", "lv", "lac", "la", "lar", "mia", "min",
    "ne", "no", "nyg", "nyj", "phi", "pit", "sf", "sea", "tb", "ten", "was",
}

DEFENSIVE_CUES = (
    "defense", "defensive", "defend", "pressure", "pressures", "sack", "sacks",
    "blitz", "coverage", "cover", "pass rush", "stop", "stops", "turnover",
    "interception", "pick six", "tackle",
)
OFFENSIVE_CUES = (
    "offense", "offensive", "attack", "run", "runs", "rush", "rushing", "pass",
    "passes", "passing", "throw", "throws", "quarterback", "qb", "receiver",
    "route", "drive", "score", "scoring", "touchdown",
)


def _as_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _tokens(text: str) -> set[str]:
    stop_words = {"what", "does", "the", "how", "why", "are", "is", "on", "in", "a", "an", "do", "and", "or", "to", "of", "for"}
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in stop_words and len(token) > 1}


def _resolve_side(question: str, selected_team: str | None, requested_side: str) -> str:
    if requested_side in {"offense", "defense", "both"}:
        return requested_side
    lowered = question.lower()
    if any(cue in lowered for cue in DEFENSIVE_CUES):
        return "defense"
    if any(cue in lowered for cue in OFFENSIVE_CUES):
        return "offense"
    return "defense" if selected_team else "both"


def infer_filters(question: str, selected_team: str | None = None, team_side: str = "auto") -> dict[str, Any]:
    """Turn broad film-room language into transparent retrieval filters."""

    lowered = question.lower()
    filters: dict[str, Any] = {}
    resolved_side = _resolve_side(question, selected_team, team_side)
    filters["side"] = resolved_side

    mentioned = {token.upper() for token in _tokens(question) if token in TEAM_CODES}
    if selected_team:
        if resolved_side == "offense":
            filters["posteam"] = selected_team.upper()
        elif resolved_side == "defense":
            filters["defteam"] = selected_team.upper()
        else:
            filters["team_any"] = selected_team.upper()
    elif mentioned:
        team = sorted(mentioned)[0]
        if resolved_side == "offense":
            filters["posteam"] = team
        elif resolved_side == "defense":
            filters["defteam"] = team
        else:
            filters["team_any"] = team

    down_distance = re.search(r"\b([1-4])(?:st|nd|rd|th)?\s*(?:and|-)\s*(\d+)\b", lowered)
    if down_distance:
        filters["down"] = int(down_distance.group(1))
        filters["ydstogo_exact"] = int(down_distance.group(2))
    elif "third down" in lowered or "3rd down" in lowered or "3rd-and" in lowered or "3rd and" in lowered:
        filters["down"] = 3
    elif "first down" in lowered or "1st down" in lowered:
        filters["down"] = 1
    elif "second down" in lowered or "2nd down" in lowered:
        filters["down"] = 2
    elif "fourth down" in lowered or "4th down" in lowered:
        filters["down"] = 4

    if "long" in lowered:
        filters["ydstogo_min"] = 7
    elif "short" in lowered:
        filters["ydstogo_max"] = 3

    if "red zone" in lowered or "redzone" in lowered:
        filters["yardline_100_max"] = 20
    elif "goal line" in lowered or "inside the 10" in lowered:
        filters["yardline_100_max"] = 10

    quarter_match = re.search(r"(?:quarter|qtr|q)\s*([1-4])\b|\b([1-4])(?:st|nd|rd|th) quarter\b", lowered)
    if quarter_match:
        filters["qtr"] = int(next(group for group in quarter_match.groups() if group))
    elif "fourth quarter" in lowered or "late game" in lowered or "late" in lowered:
        filters["qtr"] = 4

    if "two minute" in lowered or "2-minute" in lowered or "hurry-up" in lowered:
        filters["quarter_seconds_remaining_max"] = 120
    if any(phrase in lowered for phrase in ("trailing", "trail", "behind", "down by")):
        filters["score_state"] = "trailing"
    elif any(phrase in lowered for phrase in ("leading", "ahead", "up by")):
        filters["score_state"] = "leading"
    elif any(phrase in lowered for phrase in ("close game", "one score", "one-score")):
        filters["score_state"] = "close"

    flags: dict[str, Any] = {}
    if "sack" in lowered or "sacked" in lowered:
        flags["sack"] = 1
    if "interception" in lowered or "picked off" in lowered or "pick six" in lowered:
        flags["interception"] = 1
    if "touchdown" in lowered or re.search(r"\btd\b", lowered):
        flags["touchdown"] = 1
    if "turnover" in lowered or "fumble" in lowered:
        flags["turnover"] = 1
    if "first down" in lowered:
        flags["first_down"] = 1
    if "completion" in lowered or "completed" in lowered:
        flags["complete_pass"] = 1
    elif "incomplete" in lowered or "incompletions" in lowered:
        flags["complete_pass"] = 0
    if "shotgun" in lowered:
        flags["shotgun"] = 1
    elif "under center" in lowered:
        flags["shotgun"] = 0
    if "no huddle" in lowered or "hurry up" in lowered:
        flags["no_huddle"] = 1
    if "pressure" in lowered or "pressured" in lowered or "qb hit" in lowered:
        flags["pressure"] = 1
    if flags:
        filters["flags"] = flags

    if any(phrase in lowered for phrase in ("pass", "passing", "dropback", "throw")):
        filters["play_types"] = {"pass", "sack"}
    elif any(phrase in lowered for phrase in ("rush", "rushing", "run", "running")):
        # NFLverse calls rushing plays "run"; the bundled fallback data uses "rush".
        filters["play_types"] = {"run", "rush"}

    if "short pass" in lowered or "underneath" in lowered:
        filters["pass_length"] = "short"
    elif "deep pass" in lowered or "downfield" in lowered:
        filters["pass_length"] = "deep"
    if "middle" in lowered:
        filters["pass_location"] = "middle"
    elif "left side" in lowered or "left hash" in lowered:
        filters["pass_location"] = "left"
    elif "right side" in lowered or "right hash" in lowered:
        filters["pass_location"] = "right"

    description_terms = []
    for phrase in ("play action", "play-action", "screen", "motion", "jet sweep", "rpo", "option", "scramble", "kneel", "spike", "penalty", "no play"):
        if phrase in lowered:
            description_terms.append(phrase.replace("-", " "))
    if description_terms:
        filters["description_terms"] = description_terms
    if "penalty" in lowered or "no play" in lowered or "nullified" in lowered:
        filters["include_no_plays"] = True

    return filters


def _matches(play: dict[str, Any], filters: dict[str, Any]) -> bool:
    if not filters.get("include_no_plays") and (
        _as_int(play.get("no_play")) == 1
        or _as_int(play.get("aborted_play")) == 1
        or str(play.get("play_type", "")).lower() == "no_play"
    ):
        return False
    if filters.get("defteam") and str(play.get("defteam", "")).upper() != filters["defteam"]:
        return False
    if filters.get("posteam") and str(play.get("posteam", "")).upper() != filters["posteam"]:
        return False
    if filters.get("team_any") and filters["team_any"] not in {
        str(play.get("defteam", "")).upper(), str(play.get("posteam", "")).upper()
    }:
        return False
    if filters.get("down") and _as_int(play.get("down")) != filters["down"]:
        return False
    if filters.get("ydstogo_exact") is not None and _as_number(play.get("ydstogo"), 99) != filters["ydstogo_exact"]:
        return False
    if filters.get("ydstogo_min") is not None and _as_number(play.get("ydstogo"), 99) < filters["ydstogo_min"]:
        return False
    if filters.get("ydstogo_max") is not None and _as_number(play.get("ydstogo"), 99) > filters["ydstogo_max"]:
        return False
    if filters.get("yardline_100_max") is not None and _as_number(play.get("yardline_100"), 99) > filters["yardline_100_max"]:
        return False
    if filters.get("qtr") and _as_int(play.get("qtr")) != filters["qtr"]:
        return False
    if filters.get("quarter_seconds_remaining_max") is not None and _as_number(play.get("quarter_seconds_remaining"), 999) > filters["quarter_seconds_remaining_max"]:
        return False
    if filters.get("score_state"):
        score_difference = _as_number(play.get("score_differential"), 0)
        if filters["score_state"] == "close" and abs(score_difference) > 8:
            return False
        if filters["score_state"] == "trailing":
            team_score_difference = -score_difference if filters.get("side") == "defense" else score_difference
            if team_score_difference >= 0:
                return False
        if filters["score_state"] == "leading":
            team_score_difference = -score_difference if filters.get("side") == "defense" else score_difference
            if team_score_difference <= 0:
                return False
    if filters.get("play_types") and str(play.get("play_type", "")).lower() not in filters["play_types"]:
        return False
    for field, expected in filters.get("flags", {}).items():
        if field == "pressure":
            if _as_int(play.get("qb_hit")) != 1 and _as_int(play.get("sack")) != 1:
                return False
        elif field == "turnover":
            if _as_int(play.get("interception")) != 1 and _as_int(play.get("fumble_lost")) != 1:
                return False
        elif field == "complete_pass" and str(play.get("play_type", "")).lower() not in {"pass", "sack"}:
            return False
        elif field == "complete_pass" and play.get(field, "") in {None, ""}:
            return False
        elif _as_int(play.get(field)) != expected:
            return False
    if filters.get("pass_length") and str(play.get("pass_length", "")).lower() != filters["pass_length"]:
        return False
    if filters.get("pass_location") and str(play.get("pass_location", "")).lower() != filters["pass_location"]:
        return False
    if filters.get("description_terms"):
        description = str(play.get("desc", "")).lower()
        if not any(term in description for term in filters["description_terms"]):
            return False
    return True


def _relevance(play: dict[str, Any], question_tokens: set[str]) -> float:
    description_tokens = _tokens(str(play.get("desc", "")))
    overlap = len(question_tokens & description_tokens)
    epa_signal = abs(_as_number(play.get("epa")))
    return overlap * 10 + epa_signal


def _play_kind(play: dict[str, Any]) -> str:
    play_type = str(play.get("play_type", "")).lower()
    if play_type in {"pass", "sack"}:
        return "pass"
    if play_type in {"rush", "run"}:
        return "rush"
    return play_type or "other"


def _mean(values: Iterable[float]) -> float:
    values_list = list(values)
    return round(sum(values_list) / len(values_list), 3) if values_list else 0.0


def _success(play: dict[str, Any]) -> bool:
    success = play.get("success")
    if success not in (None, ""):
        return _as_number(success) == 1
    return _as_number(play.get("epa")) >= 0


def _citation(play: dict[str, Any]) -> str:
    play_id = play.get("play_id", "unknown")
    game_id = play.get("game_id", "unknown game")
    week = play.get("week", "?")
    return f"play_id={play_id} | {game_id} | week {week}"


def build_context(
    plays: list[dict[str, Any]],
    question: str,
    selected_team: str | None = None,
    team_side: str = "auto",
    evidence_limit: int = 12,
) -> dict[str, Any]:
    """Retrieve evidence and compute stats before Claude sees the data."""

    filters = infer_filters(question, selected_team, team_side=team_side)
    candidates = [play for play in plays if _matches(play, filters)]
    fallback_used = False

    # If a very specific query returns nothing, relax only the situation filter while
    # preserving the selected defense. This makes the limitation visible to Claude.
    if not candidates and any(filters.get(key) for key in ("defteam", "posteam", "team_any")):
        relaxed_filters = {
            key: value for key, value in filters.items()
            if key in {"defteam", "posteam", "team_any", "side"}
        }
        candidates = [play for play in plays if _matches(play, relaxed_filters)]
        fallback_used = True

    question_tokens = _tokens(question)
    ranked = sorted(candidates, key=lambda play: _relevance(play, question_tokens), reverse=True)
    evidence_rows = ranked[:evidence_limit]

    play_kinds = Counter(_play_kind(play) for play in candidates)
    epa_values = [_as_number(play.get("epa")) for play in candidates]
    yards_values = [_as_number(play.get("yards_gained")) for play in candidates]
    successful = sum(1 for play in candidates if _success(play))
    blitzes = sum(1 for play in candidates if _as_int(play.get("blitz")) == 1)
    pressure_events = sum(
        1 for play in candidates
        if _as_int(play.get("qb_hit")) == 1 or _as_int(play.get("sack")) == 1
    )

    stats = {
        "sample_size": len(candidates),
        "pass_plays": play_kinds.get("pass", 0),
        "rush_plays": play_kinds.get("rush", 0),
        "pass_rate": round(play_kinds.get("pass", 0) / len(candidates), 3) if candidates else 0.0,
        "success_rate": round(successful / len(candidates), 3) if candidates else 0.0,
        "blitz_rate": round(blitzes / len(candidates), 3) if candidates else 0.0,
        "pressure_rate": round(pressure_events / len(candidates), 3) if candidates else 0.0,
        "average_epa": _mean(epa_values),
        "average_yards": _mean(yards_values),
        "first_downs": sum(1 for play in candidates if _as_int(play.get("first_down")) == 1),
        "completions": sum(1 for play in candidates if _as_int(play.get("complete_pass")) == 1),
        "qb_hits": sum(1 for play in candidates if _as_int(play.get("qb_hit")) == 1),
        "touchdowns": sum(1 for play in candidates if _as_int(play.get("touchdown")) == 1),
        "turnovers": sum(1 for play in candidates if _as_int(play.get("interception")) == 1),
        "fumbles_lost": sum(1 for play in candidates if _as_int(play.get("fumble_lost")) == 1),
        "sacks": sum(1 for play in candidates if _as_int(play.get("sack")) == 1),
    }

    evidence = [
        {
            "citation": _citation(play),
            "play_id": play.get("play_id", "unknown"),
            "game_id": play.get("game_id", "unknown"),
            "week": play.get("week", "?"),
            "offense": play.get("posteam", ""),
            "defense": play.get("defteam", ""),
            "down": play.get("down", ""),
            "distance": play.get("ydstogo", ""),
            "play_type": play.get("play_type", ""),
            "yards_gained": play.get("yards_gained", ""),
            "epa": play.get("epa", ""),
            "blitz": bool(_as_int(play.get("blitz"))),
            "pressure": bool(_as_int(play.get("qb_hit")) or _as_int(play.get("sack"))),
            "quarter": play.get("qtr", ""),
            "score_differential": play.get("score_differential", ""),
            "pass_location": play.get("pass_location", ""),
            "pass_length": play.get("pass_length", ""),
            "run_location": play.get("run_location", ""),
            "passer": play.get("passer_player_name", ""),
            "receiver": play.get("receiver_player_name", ""),
            "rusher": play.get("rusher_player_name", ""),
            "description": play.get("desc", ""),
        }
        for play in evidence_rows
    ]

    filter_labels = []
    if filters.get("defteam"):
        filter_labels.append(f"defense={filters['defteam']}")
    if filters.get("posteam"):
        filter_labels.append(f"offense={filters['posteam']}")
    if filters.get("team_any"):
        filter_labels.append(f"team={filters['team_any']}")
    if filters.get("down"):
        filter_labels.append(f"down={filters['down']}")
    if filters.get("ydstogo_min"):
        filter_labels.append(f"distance≥{filters['ydstogo_min']}")
    if filters.get("ydstogo_max"):
        filter_labels.append(f"distance≤{filters['ydstogo_max']}")
    if filters.get("ydstogo_exact") is not None:
        filter_labels.append(f"distance={filters['ydstogo_exact']}")
    if filters.get("yardline_100_max"):
        filter_labels.append(f"yardline≤{filters['yardline_100_max']}")
    if filters.get("qtr"):
        filter_labels.append(f"quarter={filters['qtr']}")
    if filters.get("quarter_seconds_remaining_max") is not None:
        filter_labels.append("last two minutes")
    if filters.get("score_state"):
        filter_labels.append(f"game={filters['score_state']}")
    if filters.get("play_types"):
        if filters["play_types"] == {"run", "rush"}:
            filter_labels.append("play=rush")
        else:
            filter_labels.append("play=" + "/".join(sorted(filters["play_types"])))
    if filters.get("flags"):
        filter_labels.extend(str(flag).replace("_", " ") for flag in filters["flags"])
    if filters.get("pass_length"):
        filter_labels.append(f"pass length={filters['pass_length']}")
    if filters.get("pass_location"):
        filter_labels.append(f"pass location={filters['pass_location']}")
    if filters.get("description_terms"):
        filter_labels.append("concept=" + "/".join(filters["description_terms"]))
    if filters.get("include_no_plays"):
        filter_labels.append("include nullified plays")

    public_filters = {
        key: sorted(value) if isinstance(value, set) else value
        for key, value in filters.items()
    }
    meta = {
        "filters": public_filters,
        "filter_labels": filter_labels or ["all available plays"],
        "fallback_used": fallback_used,
        "total_plays": len(plays),
        "stats": stats,
    }

    return {"meta": meta, "stats": stats, "evidence": evidence}


def context_as_xml(context: dict[str, Any]) -> str:
    """Serialize retrieved evidence in a prompt-friendly, clearly delimited format."""

    meta = context["meta"]
    stats = context["stats"]
    evidence_text = "\n".join(
        "<play>"
        f"<citation>{xml_escape(str(item['citation']))}</citation>"
        f"<situation>quarter={xml_escape(str(item['quarter']))}, down={xml_escape(str(item['down']))}, distance={xml_escape(str(item['distance']))}, play_type={xml_escape(str(item['play_type']))}, blitz={xml_escape(str(item['blitz']))}, pressure={xml_escape(str(item['pressure']))}</situation>"
        f"<result>yards={xml_escape(str(item['yards_gained']))}, epa={xml_escape(str(item['epa']))}, offense={xml_escape(str(item['offense']))}, defense={xml_escape(str(item['defense']))}, score_differential={xml_escape(str(item['score_differential']))}</result>"
        f"<tracking>pass_location={xml_escape(str(item['pass_location']))}, pass_length={xml_escape(str(item['pass_length']))}, run_location={xml_escape(str(item['run_location']))}, passer={xml_escape(str(item['passer']))}, receiver={xml_escape(str(item['receiver']))}, rusher={xml_escape(str(item['rusher']))}</tracking>"
        f"<description>{xml_escape(str(item['description']))}</description>"
        "</play>"
        for item in context["evidence"]
    )
    return (
        "<retrieved_nfl_context>\n"
        f"<filters>{xml_escape(', '.join(meta['filter_labels']))}</filters>\n"
        f"<sample_stats>{xml_escape(str(stats))}</sample_stats>\n"
        f"<fallback_notice>{xml_escape('The exact filters returned no plays; evidence was relaxed to the selected defense.' if meta['fallback_used'] else 'Exact filters returned evidence.')}</fallback_notice>\n"
        f"<plays>\n{evidence_text}\n</plays>\n"
        "</retrieved_nfl_context>"
    )
