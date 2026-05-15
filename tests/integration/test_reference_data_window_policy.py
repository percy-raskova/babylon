"""Spec-065 T025: FR-022 reference-data window preflight policy.

Three modes (verified per the FR-022 spec):

  - **silent**: requested window ⊆ every required table → preflight
    returns the original scenario length and no warnings.
  - **warn-and-clamp**: requested window extends past at least one
    table's coverage → preflight returns a clamped length plus stderr
    warning messages naming the table and year.
  - **hard-refuse**: ``start_year`` predates the earliest year in any
    required table → preflight raises :class:`InitializationError`
    with the FR-022 named-triple ``ERROR REFERENCE_DATA_MISSING:`` prefix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.persistence.postgres_initialization import (
    InitializationError,
    _preflight_reference_data_window,
)

SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")


pytestmark = pytest.mark.skipif(
    not SQLITE_REF.exists(),
    reason=f"SQLite reference DB missing at {SQLITE_REF}",
)


def test_silent_proceed_within_window() -> None:
    """Spec-065 canonical run: 2010 + 10 years (520 ticks) is fully covered."""
    allowed, warnings = _preflight_reference_data_window(
        sqlite_path=SQLITE_REF,
        start_year=2010,
        scenario_length_years=10,
    )
    assert allowed == 10
    assert warnings == []


def test_warn_and_clamp_when_overshooting_window() -> None:
    """Requested 50-year scenario triggers clamp + warnings (Census ends 2023)."""
    allowed, warnings = _preflight_reference_data_window(
        sqlite_path=SQLITE_REF,
        start_year=2010,
        scenario_length_years=50,
    )
    assert allowed < 50
    assert any("WARN REFERENCE_DATA_CLAMP" in msg for msg in warnings)
    # Census income table ends at 2023 → end_year clamped to 2023 →
    # allowed_length = 2023 - 2010 + 1 = 14.
    assert allowed == 14


def test_hard_refuse_predates_window() -> None:
    """start_year=1950 predates QCEW (starts 2010) → InitializationError."""
    with pytest.raises(InitializationError, match="ERROR REFERENCE_DATA_MISSING"):
        _preflight_reference_data_window(
            sqlite_path=SQLITE_REF,
            start_year=1950,
            scenario_length_years=5,
        )


def test_warning_message_names_table_and_year() -> None:
    """Warning message includes the table name and the offending year."""
    _allowed, warnings = _preflight_reference_data_window(
        sqlite_path=SQLITE_REF,
        start_year=2010,
        scenario_length_years=30,
    )
    msg = warnings[0]
    assert "REFERENCE_DATA_CLAMP" in msg
    assert "fact_" in msg  # table name reference
    assert "year=" in msg


def test_missing_sqlite_file_raises_filenotfound(tmp_path: Path) -> None:
    """A non-existent SQLite path raises FileNotFoundError, not InitializationError."""
    with pytest.raises(FileNotFoundError):
        _preflight_reference_data_window(
            sqlite_path=tmp_path / "nonexistent.sqlite",
            start_year=2010,
            scenario_length_years=5,
        )
