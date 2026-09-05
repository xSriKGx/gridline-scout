"""Data loading and normalization for NFL play-by-play files."""

from __future__ import annotations

import csv
import gzip
from pathlib import Path
from typing import Any, Iterable


NUMERIC_FIELDS = {
    "season",
    "week",
    "qtr",
    "game_seconds_remaining",
    "quarter_seconds_remaining",
    "down",
    "ydstogo",
    "yardline_100",
    "yards_gained",
    "epa",
    "air_epa",
    "air_yards",
    "yards_after_catch",
    "success",
    "pass",
    "rush",
    "pass_attempt",
    "rush_attempt",
    "complete_pass",
    "no_play",
    "aborted_play",
    "sack",
    "qb_hit",
    "interception",
    "fumble_lost",
    "first_down",
    "touchdown",
    "shotgun",
    "no_huddle",
    "score_differential",
    "blitz",
    "play_id",
}


def _number(value: str | None) -> int | float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _clean_row(row: dict[str, str]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in row.items():
        normalized_key = key.strip().lower()
        cleaned[normalized_key] = _number(value) if normalized_key in NUMERIC_FIELDS else (value or "")
    return cleaned


def load_plays(path: str | Path) -> list[dict[str, Any]]:
    """Load a normal CSV or gzip-compressed CSV into plain dictionaries."""

    data_path = Path(path)
    if not data_path.exists():
        raise FileNotFoundError(f"Play-by-play file not found: {data_path}")

    opener = gzip.open if data_path.suffix == ".gz" else open
    with opener(data_path, "rt", newline="", encoding="utf-8-sig") as handle:
        return [_clean_row(row) for row in csv.DictReader(handle)]


def available_teams(plays: Iterable[dict[str, Any]]) -> list[str]:
    teams: set[str] = set()
    for play in plays:
        for field in ("posteam", "defteam"):
            team = str(play.get(field, "")).strip().upper()
            if team and team not in {"NAN", "NONE"}:
                teams.add(team)
    return sorted(teams)
