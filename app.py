"""Flask entry point for Gridline Scout."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from nfl_assistant.analysis import build_context
from nfl_assistant.claude_service import generate_report
from nfl_assistant.data import available_teams, load_plays

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
REAL_DATA_PATH = BASE_DIR / "data" / "play_by_play_2025.csv.gz"
configured_data_path = os.getenv("PLAY_DATA_PATH", "").strip()
if configured_data_path and Path(configured_data_path).name != "plays.csv":
    DATA_PATH = Path(configured_data_path)
else:
    DATA_PATH = REAL_DATA_PATH
if not DATA_PATH.is_absolute():
    DATA_PATH = BASE_DIR / DATA_PATH

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"NFLverse data is missing at {DATA_PATH}. Run `python download_data.py --season 2025` first."
    )

app = Flask(__name__)
PLAYS = load_plays(DATA_PATH)


@app.get("/")
def index():
    teams = available_teams(PLAYS)
    seasons = sorted({play.get("season") for play in PLAYS if play.get("season")})
    season_label = str(seasons[-1]) if seasons else "NFL"
    return render_template(
        "index.html",
        teams=teams,
        data_label=f"{season_label} NFLVERSE · {len(teams)} TEAMS",
    )


@app.get("/api/teams")
def teams():
    return jsonify({"teams": available_teams(PLAYS)})


@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    selected_team = str(payload.get("team", "")).strip().upper() or None
    team_side = str(payload.get("side", "auto")).strip().lower()

    if not question:
        return jsonify({"error": "Ask a football question first."}), 400
    if len(question) > 500:
        return jsonify({"error": "Keep the question under 500 characters."}), 400

    context = build_context(PLAYS, question, selected_team=selected_team, team_side=team_side)
    bundle = generate_report(question, context)
    return jsonify(
        {
            "question": question,
            "report": bundle["report"],
            "mode": bundle["mode"],
            "model": bundle["model"],
            "error": bundle["error"],
            "meta": context["meta"],
            "evidence": context["evidence"],
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "1") == "1")
