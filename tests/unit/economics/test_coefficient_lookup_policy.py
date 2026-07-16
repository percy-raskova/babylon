"""Coefficient-lookup policy dispatch tests (T033 / FR-011/012/013/016)."""

from __future__ import annotations

import warnings
from unittest.mock import patch
from uuid import uuid4

import pytest

from babylon.persistence.postgres_reference import (
    ImmutableReferenceLookup,
    LookupMethod,
)


class _StubRuntime:
    """In-process stand-in for PostgresRuntime in policy-dispatch tests."""

    pass


@pytest.fixture
def lookup() -> ImmutableReferenceLookup:
    return ImmutableReferenceLookup(
        runtime=_StubRuntime(),  # type: ignore[arg-type]
        session_id=uuid4(),
        start_year=2010,
        end_year=2025,
    )


def _linear_provider(series_id: str, year: int) -> float:  # noqa: ARG001
    """Annual values that linearly track the year."""
    return float(year)


def _step_provider(series_id: str, year: int) -> float:  # noqa: ARG001
    """Annual values that step at year boundaries."""
    return float(year) * 100.0


@pytest.mark.cross_scale
class TestSlowlyVaryingInterpolation:
    """FR-012: linear interpolation across 52 weeks."""

    def test_exact_year_at_tick_0(self, lookup: ImmutableReferenceLookup) -> None:
        result = lookup.get(
            "test_series", tick=0, policy="slowly_varying", value_provider=_linear_provider
        )
        assert result.value == 2010.0
        assert result.lookup_method == LookupMethod.EXACT_YEAR

    def test_mid_year_at_tick_26_is_half_of_v_plus_next(
        self, lookup: ImmutableReferenceLookup
    ) -> None:
        result = lookup.get(
            "test_series",
            tick=26,
            policy="slowly_varying",
            value_provider=_linear_provider,
        )
        # FR-012: v(y) + (v(y+1)-v(y)) * (26/52) = 2010 + 1*0.5 = 2010.5
        assert result.value == pytest.approx(2010.5, abs=1e-12)
        assert result.lookup_method == LookupMethod.LINEAR_INTERPOLATED
        assert result.bracketing_years == (2010, 2011)


@pytest.mark.cross_scale
class TestEventDiscrete:
    """FR-013: step-function at year-boundary."""

    def test_tick_51_returns_year_y(self, lookup: ImmutableReferenceLookup) -> None:
        result = lookup.get(
            "step_series",
            tick=51,
            policy="event_discrete",
            value_provider=_step_provider,
        )
        assert result.value == 201000.0
        assert result.lookup_method == LookupMethod.EXACT_YEAR

    def test_tick_52_returns_year_y_plus_1(self, lookup: ImmutableReferenceLookup) -> None:
        result = lookup.get(
            "step_series",
            tick=52,
            policy="event_discrete",
            value_provider=_step_provider,
        )
        assert result.value == 201100.0
        assert result.lookup_method == LookupMethod.EXACT_YEAR


@pytest.mark.cross_scale
class TestFR016ClampToLastWarning:
    """FR-016: warning emitted exactly once per (session_id, series_id)."""

    def test_first_overrange_emits_warning(self, lookup: ImmutableReferenceLookup) -> None:
        # 2026 is one year past end_year=2025 → tick 832.
        over_tick = 832
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = lookup.get(
                "test_series",
                tick=over_tick,
                policy="slowly_varying",
                value_provider=_linear_provider,
            )
        assert result.lookup_method == LookupMethod.CLAMPED_TO_LAST
        assert result.warning_emitted is True
        assert len(w) == 1
        assert "FR-016" in str(w[0].message)

    def test_second_overrange_no_warning(self, lookup: ImmutableReferenceLookup) -> None:
        lookup.get(
            "test_series",
            tick=832,
            policy="slowly_varying",
            value_provider=_linear_provider,
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = lookup.get(
                "test_series",
                tick=900,
                policy="slowly_varying",
                value_provider=_linear_provider,
            )
        assert result.warning_emitted is False
        assert len(w) == 0


@pytest.mark.cross_scale
class TestFR041ClampToEarliest:
    """FR-041 (T038b): below-range fallback clamps to earliest year.

    ``simulated_year = start_year + (tick // 52)`` can never fall below
    ``start_year`` for a valid (non-negative) tick — ``get()`` rejects
    negative ticks outright — so the clamp-to-earliest branch is
    unreachable through ``tick`` alone under the current session-level
    coverage model (a real gap: per-series coverage narrower than the
    session range isn't modeled yet, per FR-041's own doc comment). Each
    test below stubs only the tick-to-year translation so the assertions
    still exercise ``get()``'s real dispatch, clamp value, and one-shot
    warning logic end to end, instead of calling the private clamp helper
    directly.
    """

    def test_first_below_range_emits_warning(self, lookup: ImmutableReferenceLookup) -> None:
        with (
            patch.object(lookup, "_tick_to_year_and_week", return_value=(2005, 0)),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            result = lookup.get(
                "hickel_drain",
                tick=0,
                policy="slowly_varying",
                value_provider=_linear_provider,
            )
        assert result.lookup_method == LookupMethod.CLAMPED_TO_EARLIEST
        assert result.value == pytest.approx(2010.0)  # value at start_year=2010
        assert result.bracketing_years == (2010,)
        assert result.warning_emitted is True
        assert len(w) == 1
        assert "FR-041" in str(w[0].message)

    def test_second_below_range_no_warning(self, lookup: ImmutableReferenceLookup) -> None:
        with patch.object(lookup, "_tick_to_year_and_week", return_value=(2005, 0)):
            lookup.get(
                "hickel_drain",
                tick=0,
                policy="slowly_varying",
                value_provider=_linear_provider,
            )
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = lookup.get(
                    "hickel_drain",
                    tick=0,
                    policy="slowly_varying",
                    value_provider=_linear_provider,
                )
        assert result.lookup_method == LookupMethod.CLAMPED_TO_EARLIEST
        assert result.warning_emitted is False
        assert len(w) == 0
