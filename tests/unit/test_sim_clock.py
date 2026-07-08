"""Tests for the deterministic simulation clock (Constitution III.7).

``sim_datetime`` maps a weekly tick to a canonical in-world datetime so
timestamps are a pure function of tick, never of wall clock. Year mapping
mirrors FR-013 (``year = start_year + tick // 52``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from babylon.sim_clock import SIM_EPOCH_YEAR, UNSET_TIMESTAMP, WEEKS_PER_YEAR, sim_datetime

pytestmark = pytest.mark.unit


class TestSimDatetime:
    """Contract for the tick -> datetime mapping."""

    def test_tick_zero_is_epoch(self) -> None:
        """Tick 0 maps to the FR-013 epoch (2010-01-01 UTC)."""
        assert sim_datetime(0) == datetime(2010, 1, 1, tzinfo=UTC)

    def test_tick_52_advances_one_year(self) -> None:
        """FR-013 alignment: ``year = start_year + tick // 52``."""
        assert sim_datetime(52).year == 2011
        assert sim_datetime(52) == datetime(2011, 1, 1, tzinfo=UTC)

    def test_purity_same_tick_same_datetime(self) -> None:
        """The mapping is a pure function of tick (no wall-clock leakage)."""
        assert sim_datetime(7) == sim_datetime(7)

    def test_intra_year_ticks_advance_by_weeks(self) -> None:
        """Ticks within a year advance in whole weeks from Jan 1."""
        delta = sim_datetime(3) - sim_datetime(0)
        assert delta.days == 21

    def test_negative_tick_raises_value_error(self) -> None:
        """Negative ticks are a caller bug and must fail loud."""
        with pytest.raises(ValueError, match="tick must be >= 0"):
            sim_datetime(-1)

    def test_result_is_timezone_aware_utc(self) -> None:
        """All sim datetimes are tz-aware UTC (stable serialization)."""
        assert sim_datetime(5).tzinfo is UTC

    def test_constants_exposed(self) -> None:
        """Epoch constants are public and match FR-013 conventions."""
        assert SIM_EPOCH_YEAR == 2010
        assert WEEKS_PER_YEAR == 52

    def test_unset_sentinel_is_min_utc(self) -> None:
        """The UNSET sentinel is a fixed, tz-aware minimum datetime."""
        assert datetime.min.replace(tzinfo=UTC) == UNSET_TIMESTAMP
