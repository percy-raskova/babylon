"""Unit tests for ``derive_year_set`` pure function (spec-069 T005 / R3).

The cache's hydrate step needs to enumerate the calendar years touched
by a run before issuing batched SQL. Under the weekly cadence
(``year = start_year + tick // 52``) this is mechanical:

    derive_year_set(start_year, total_ticks) =
        {start_year + i // 52 : i in [0, total_ticks - 1]}
        = {start_year, ..., start_year + (total_ticks - 1) // 52}

Edge case: ``total_ticks <= 0`` yields the empty set (degenerate
zero-tick run; spec-069 spec.md Edge Cases).
"""

from __future__ import annotations

import pytest

from babylon.engine.headless_runner.reference_data_cache import derive_year_set


class TestDeriveYearSet:
    """``derive_year_set(start_year, total_ticks) -> frozenset[int]``."""

    def test_zero_ticks_yields_empty_set(self) -> None:
        """A zero-tick run has no in-scope years (R3 edge case)."""
        assert derive_year_set(2010, 0) == frozenset()

    def test_negative_ticks_yields_empty_set(self) -> None:
        """Negative total_ticks is treated as the degenerate zero case."""
        assert derive_year_set(2010, -1) == frozenset()

    def test_one_tick_yields_start_year_only(self) -> None:
        """Tick 0 alone resolves to start_year."""
        assert derive_year_set(2010, 1) == frozenset({2010})

    def test_fifty_two_ticks_one_year_inclusive(self) -> None:
        """52 ticks (0..51) all map to start_year — one year only."""
        assert derive_year_set(2010, 52) == frozenset({2010})

    def test_fifty_three_ticks_crosses_year_boundary(self) -> None:
        """Tick 52 is the first tick of start_year + 1."""
        assert derive_year_set(2010, 53) == frozenset({2010, 2011})

    def test_canonical_michigan_canada_yields_ten_years(self) -> None:
        """520 ticks (numbered 0..519) from 2010 covers 2010..2019 inclusive.

        Per research.md R3: ``{start_year + t // 52 for t in range(total_ticks)}``.
        For total_ticks=520, max year is 2010 + 519//52 = 2019. Year 2020 would
        require tick 520 to be touched, but the runner only persists ticks 0..519
        for ``config.ticks=520`` (see ``runner.py:819`` — ``range(1, config.ticks)``
        plus the explicit tick 0 persist at line 817).
        """
        result = derive_year_set(2010, 520)
        assert result == frozenset(range(2010, 2020))
        assert len(result) == 10

    def test_returns_frozenset(self) -> None:
        """Return type is frozenset, not set or list."""
        result = derive_year_set(2010, 520)
        assert isinstance(result, frozenset)

    @pytest.mark.parametrize(
        "start_year,total_ticks,expected",
        [
            (2000, 52, {2000}),
            (2000, 104, {2000, 2001}),
            (1999, 105, {1999, 2000, 2001}),
            (2010, 260, set(range(2010, 2015))),
        ],
    )
    def test_parametrized_year_set_arithmetic(
        self, start_year: int, total_ticks: int, expected: set[int]
    ) -> None:
        """Parametrized: full grid of small year-set cases."""
        assert derive_year_set(start_year, total_ticks) == frozenset(expected)
