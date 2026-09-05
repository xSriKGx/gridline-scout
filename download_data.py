"""Download an NFLverse play-by-play CSV for use with the assistant.

Example:
    python download_data.py --season 2024
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Download NFLverse play-by-play data")
    parser.add_argument("--season", type=int, default=2024, help="NFL season to download")
    args = parser.parse_args()

    destination = Path("data") / f"play_by_play_{args.season}.csv.gz"
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{args.season}.csv.gz"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    destination.write_bytes(response.content)
    print(f"Saved {destination} ({len(response.content) / 1_000_000:.1f} MB)")
    print(f"Set PLAY_DATA_PATH={destination} in .env to use it.")


if __name__ == "__main__":
    main()
