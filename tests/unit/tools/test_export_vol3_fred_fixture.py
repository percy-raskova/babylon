"""Tests for the one-off Vol III FRED fixture export script (D4).

Both DB-facing calls are monkeypatched — this test never touches the
reference DB or the babylon-data drive; it only pins export_vol3_fred_fixture
.main()'s JSON shape and determinism (sorted series, sorted years, year keys
stringified for JSON, values passed through untouched).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import export_vol3_fred_fixture as export_mod  # type: ignore[import-not-found]  # noqa: E402


def test_main_writes_a_deterministic_sorted_json_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RED->GREEN: main() writes {series_id: {year_str: value}}, sorted."""
    fixture_path = tmp_path / "vol3_fred_series.json"
    monkeypatch.setattr(export_mod, "FIXTURE_PATH", fixture_path)
    monkeypatch.setattr(export_mod, "get_normalized_session_factory", lambda: object())
    monkeypatch.setattr(
        export_mod,
        "load_fred_series_from_db",
        lambda _session_factory: {
            "GFDEBTN": {2020: 27_000_000_000_000.0},
            "FEDFUNDS": {2020: 0.0038, 2019: 0.0225},
        },
    )

    exit_code = export_mod.main()

    assert exit_code == 0
    raw = fixture_path.read_text()
    data = json.loads(raw)
    assert data == {
        "FEDFUNDS": {"2019": 0.0225, "2020": 0.0038},
        "GFDEBTN": {"2020": 27_000_000_000_000.0},
    }
    # Order is the contract, not just content: dict == is order-insensitive.
    assert list(data) == ["FEDFUNDS", "GFDEBTN"]
    assert list(data["FEDFUNDS"]) == ["2019", "2020"]
    assert raw.index('"FEDFUNDS"') < raw.index('"GFDEBTN"')


def test_main_refuses_to_write_an_empty_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """III.11: an empty query result is a loud failure, never a silent empty file."""
    fixture_path = tmp_path / "vol3_fred_series.json"
    monkeypatch.setattr(export_mod, "FIXTURE_PATH", fixture_path)
    monkeypatch.setattr(export_mod, "get_normalized_session_factory", lambda: object())
    monkeypatch.setattr(export_mod, "load_fred_series_from_db", lambda _session_factory: {})

    exit_code = export_mod.main()

    assert exit_code == 1
    assert not fixture_path.exists()
