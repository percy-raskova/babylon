"""Tests for the one-off national MELT fixture export script (D4).

Both adapters are monkeypatched — this test never touches the reference DB or
the babylon-data drive; it only pins export_vol3_melt_fixture.main()'s JSON
shape, its sorting, and its honest-absence rule (a year whose source returns
None is omitted, never zero-filled).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import export_vol3_melt_fixture as export_mod  # type: ignore[import-not-found]  # noqa: E402


class _StubGDP:
    def __init__(self, _session_factory: object) -> None:
        self._values = {2011: 1.5295282203e13, 2010: 1.4754993743e13}

    def get_gdp(self, year: int) -> float | None:
        return self._values.get(year)


class _StubEmployment:
    def __init__(self, _session_factory: object) -> None:
        self._values = {2011: 127_933_758, 2010: 126_464_161}

    def get_national_employment(self, year: int) -> int | None:
        return self._values.get(year)


def test_main_writes_a_deterministic_sorted_json_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RED->GREEN: main() writes {"gdp"|"employment": {year_str: value}}, sorted."""
    fixture_path = tmp_path / "vol3_melt_national.json"
    monkeypatch.setattr(export_mod, "FIXTURE_PATH", fixture_path)
    monkeypatch.setattr(export_mod, "get_normalized_session_factory", lambda: object())
    monkeypatch.setattr(export_mod, "SQLiteBEANationalGDPSource", _StubGDP)
    monkeypatch.setattr(export_mod, "SQLiteQCEWNationalEmploymentSource", _StubEmployment)

    exit_code = export_mod.main()

    assert exit_code == 0
    raw = fixture_path.read_text()
    data = json.loads(raw)
    assert data == {
        "employment": {"2010": 126_464_161, "2011": 127_933_758},
        "gdp": {"2010": 1.4754993743e13, "2011": 1.5295282203e13},
    }
    # Order is the contract, not just content: dict == is order-insensitive.
    assert list(data) == ["employment", "gdp"]
    assert list(data["gdp"]) == ["2010", "2011"]
    # III.11: years the stub has no data for are absent, not zero-filled.
    assert "2020" not in data["gdp"]
    assert raw.endswith("\n")


def test_main_refuses_to_write_when_a_source_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """III.11: no resolvable MELT year is a loud failure, never a silent file."""

    class _EmptyEmployment:
        def __init__(self, _session_factory: object) -> None:
            pass

        def get_national_employment(self, _year: int) -> int | None:
            return None

    fixture_path = tmp_path / "vol3_melt_national.json"
    monkeypatch.setattr(export_mod, "FIXTURE_PATH", fixture_path)
    monkeypatch.setattr(export_mod, "get_normalized_session_factory", lambda: object())
    monkeypatch.setattr(export_mod, "SQLiteBEANationalGDPSource", _StubGDP)
    monkeypatch.setattr(export_mod, "SQLiteQCEWNationalEmploymentSource", _EmptyEmployment)

    exit_code = export_mod.main()

    assert exit_code == 1
    assert not fixture_path.exists()
