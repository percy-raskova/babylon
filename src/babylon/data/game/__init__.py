"""Game entity JSON data files.

Contains static game data (characters, classes, factions, etc.)
migrated from XML format.

Usage:
    from babylon.data.game import GAME_DATA_DIR, load_json

    characters = load_json("characters.json")
"""

import json
from pathlib import Path
from typing import Any

# Directory containing game JSON files
GAME_DATA_DIR = Path(__file__).parent


def load_json(filename: str) -> dict[str, Any]:
    """Load a JSON file from the game data directory.

    Args:
        filename: Name of the JSON file (e.g., "characters.json")

    Returns:
        Parsed JSON data as a dictionary.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file isn't valid JSON.
    """
    filepath = GAME_DATA_DIR / filename
    with open(filepath, encoding="utf-8") as f:
        result: dict[str, Any] = json.load(f)
        return result


def list_data_files() -> list[str]:
    """List all JSON data files in the game data directory.

    Returns:
        List of JSON filenames.
    """
    return [f.name for f in GAME_DATA_DIR.glob("*.json")]


__all__ = ["GAME_DATA_DIR", "load_json", "list_data_files"]
