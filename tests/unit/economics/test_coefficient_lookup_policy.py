"""Coefficient-lookup policy dispatch tests (T033 / FR-011/012/013/016)."""

from __future__ import annotations

import warnings
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
    """FR-041 (T038b): below-range fallback clamps to earliest year."""

    def test_below_range_returns_start_year_value(self, lookup: ImmutableReferenceLookup) -> None:
        # Use a custom lookup that starts later than the simulated year.
        bounded = ImmutableReferenceLookup(
            runtime=_StubRuntime(),  # type: ignore[arg-type]
            session_id=uuid4(),
            start_year=2015,
            end_year=2025,
        )
        # tick=0 with start_year=2015 → simulated_year=2015 (exact match);
        # to force below-range we need the year to be < start_year, which
        # happens when the series' own first year is later than the session
        # start_year. We model this by using a smaller start_year on the
        # lookup that REPRESENTS the SERIES coverage (not the session).
        # For this test the lookup IS the series-coverage instance.
        # So we set the lookup's start_year=2015 and simulated_year=2010:
        result = bounded.get(
            "hickel_drain",
            tick=-260 + 260,  # placeholder; below uses negative-year math
            policy="slowly_varying",
            value_provider=_linear_provider,
        )
        # tick=0 → year = 2015 → exact, not clamped.
        assert result.lookup_method == LookupMethod.EXACT_YEAR

        # Build a fake-historical case directly by manipulating start_year:
        backward = ImmutableReferenceLookup(
            runtime=_StubRuntime(),  # type: ignore[arg-type]
            session_id=uuid4(),
            start_year=1995,
            end_year=2025,
        )
        # Now ask for tick where simulated_year < start_year. simulated_year =
        # backward.start_year + tick//52 = 1995 + tick//52. To get year=1990
        # we need tick such that 1995 + tick//52 == 1990, i.e., tick//52 = -5.
        # Negative tick is invalid, so we model the below-range case by
        # constructing a lookup whose series coverage starts AFTER its
        # constructor start_year. In production this happens when the
        # series' first available year is later than the session's
        # start_year (e.g., Hickel begins 1995 but scenario starts 1990).
        # For the unit test, fall back to direct verification via the
        # private method:
        from_method = backward._clamped_to_earliest(
            "hickel_drain", simulated_year=1990, value_provider=_linear_provider
        )
        assert from_method.lookup_method == LookupMethod.CLAMPED_TO_EARLIEST
        assert from_method.value == 1995.0  # value at clamped year
        assert from_method.bracketing_years == (1995,)
