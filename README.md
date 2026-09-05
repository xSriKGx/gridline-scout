# Gridline Scout

Gridline Scout is a grounded NFL film-analysis assistant based on the “AI Scouting Assistant” idea in the linked NFL project document.

It answers natural-language questions such as:

> What does KC defense do on 3rd and long?

The app translates broad film-room questions into transparent filters, retrieves matching play-by-play evidence, calculates a statistical profile, and asks Claude to produce a structured scouting report with exact play citations. It ships with a real 2025 NFLverse season covering all 32 teams and still provides local analysis when no API key is configured.

## Tech stack

| Tool | Why it is used |
| --- | --- |
| Python | Easy data processing and a readable backend for a first portfolio project |
| Flask | Lightweight local web server with no frontend build step |
| Anthropic Python SDK | Calls Claude through the Messages API |
| `csv` and `gzip` from the standard library | Reads both the bundled CSV and NFLverse `.csv.gz` files without a heavy data dependency |
| Vanilla HTML/CSS/JavaScript | Fast, polished UI that runs directly from Flask and is easy to explain in an interview |
| pytest | Small automated evaluation suite for retrieval behavior |
| NFLverse play-by-play | Public football data source; the included 2025 compressed file covers all 32 teams |

## Run it in VS Code

Open this folder in VS Code: `2026-09-04/do`.

### 1. Create a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\\Scripts\\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure Claude

Copy `.env.example` to `.env`.

```bash
cp .env.example .env
```

Add your Anthropic API key to `.env`:

```dotenv
ANTHROPIC_API_KEY=your_key_here
CLAUDE_MODEL=claude-sonnet-5
```

The app does not need a key to launch. Without one, it uses the local retrieval/statistics pipeline. With one, it uses Claude for the report.

### 4. Start the app

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser.

In VS Code, you can also use **Run and Debug → Python: Current File** while `app.py` is open.

### 5. Run the tests

```bash
python -m pytest -q
```

## Change the NFLverse season

The project already includes the 2025 season. To switch to another season:

```bash
python download_data.py --season 2024
```

Then set this in `.env`:

```dotenv
PLAY_DATA_PATH=data/play_by_play_2024.csv.gz
```

Restart `python app.py`. The loader accepts the standard NFLverse play-by-play columns used by the app, including `posteam`, `defteam`, `down`, `ydstogo`, `yardline_100`, `play_type`, `desc`, `epa`, `success`, `qb_hit`, `pass_location`, and `pass_length` when present.

## Project structure

```text
app.py                         Flask routes and app startup
download_data.py               Optional NFLverse downloader
nfl_assistant/data.py          CSV/gzip loading and team discovery
nfl_assistant/analysis.py      Natural-language filters and evidence retrieval
nfl_assistant/claude_service.py Claude prompts, schema, API call, local fallback
data/play_by_play_2025.csv.gz  Real 2025 NFLverse data for all teams
templates/index.html           Film-room UI
static/app.js                  Form submission and report rendering
static/styles.css              Visual design
tests/test_analysis.py         Retrieval/evidence tests
```

## Good portfolio walkthrough

1. Start the app and ask a question about any of the 32 teams.
2. Show the transparent filter labels and evidence ledger.
3. Add your API key and rerun the same question to show Claude mode.
4. Open `nfl_assistant/claude_service.py` and explain the XML grounding, schema-constrained JSON, confidence labels, and citation requirement.
5. Run `python -m pytest -q` to show that the retrieval layer is testable rather than hidden inside a prompt.

## Important limitation

The app uses official NFLverse play-by-play data, not raw video. It can analyze situations, outcomes, pressure, play type, player references, and available tracking fields. It cannot verify a visual coverage shell or route detail unless that information is represented in the loaded data. Treat reports as film-room support—not as a substitute for coaching judgment.
