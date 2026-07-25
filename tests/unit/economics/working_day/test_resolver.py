"""Tests for the working_day resolvers (Vol I U4 + U6).

Feature: 021-capital-volume-i / vol1-value-production program U4 -- the first
production reader of ``services.productivity_data_source``. Feeds
:class:`~babylon.domain.economics.working_day.classifier
.DefaultWorkingDayClassifier` from real FRED-adapter data (OPHNFB + HOANBS,
via ``create_vol1_services``'s ``_FredProductivityAdapter``) and resolves the
Ch. 10 visibility modifier for :class:`~babylon.engine.systems.ideology
.ConsciousnessSystem` to consume. U6 adds
``resolve_absolute_relative_surplus_ratio``, sharing the same fetch to feed
the ``absolute_relative_surplus`` opposition (Chs. 10, 12, 15).
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines, WorkingDayDefines
from babylon.domain.economics.working_day.resolver import (
    resolve_absolute_relative_surplus_ratio,
    resolve_working_day_visibility_modifier,
)
from babylon.domain.economics.working_day.types import WorkingDayState
from babylon.engine.services import ServiceContainer
from babylon.topology.graph import BabylonGraph

_ABSOLUTE_STATE = WorkingDayState(
    fips_code="26163",
    naics_sector="48",
    year=2019,
    avg_weekly_hours=50.0,
    labor_intensity_index=0.9,
)
_RELATIVE_STATE = WorkingDayState(
    fips_code="26163",
    naics_sector="51",
    year=2019,
    avg_weekly_hours=37.0,
    labor_intensity_index=2.0,
)


class _FixedProductivitySource:
    """Test double: returns a fixed ``WorkingDayState`` regardless of args,
    while recording the arguments it was called with (for call-contract
    pins)."""

    def __init__(self, state: WorkingDayState | None) -> None:
        self._state = state
        self.calls: list[tuple[str, str, int]] = []

    def get_working_day_state(
        self, fips_code: str, naics_sector: str, year: int
    ) -> WorkingDayState | None:
        self.calls.append((fips_code, naics_sector, year))
        return self._state


@pytest.mark.unit
class TestResolveWorkingDayVisibilityModifier:
    """resolve_working_day_visibility_modifier: services + graph + tick ->
    Ch. 10 visibility modifier, or an honest ``None``."""

    def test_unwired_source_returns_none(self) -> None:
        """Default ``ServiceContainer.create()`` leaves
        ``productivity_data_source`` unwired -- an explicit "no data",
        never a fabricated default modifier."""
        services = ServiceContainer.create()
        graph = BabylonGraph()

        result = resolve_working_day_visibility_modifier(graph, services, tick=1)

        assert result is None

    def test_source_returning_none_propagates_none(self) -> None:
        """The data source itself may have no data for this year -- also
        an honest ``None``, not a fabricated fallback."""
        source = _FixedProductivitySource(state=None)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_working_day_visibility_modifier(graph, services, tick=1)

        assert result is None

    def test_absolute_dominant_state_returns_absolute_visibility(self) -> None:
        """A long-hours/low-intensity state classifies ABSOLUTE_DOMINANT ->
        the (default 1.0) absolute_visibility modifier."""
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_working_day_visibility_modifier(graph, services, tick=1)

        assert result == pytest.approx(WorkingDayDefines().absolute_visibility)

    def test_relative_dominant_state_returns_relative_visibility(self) -> None:
        """Short-hours/high-intensity state classifies RELATIVE_DOMINANT ->
        the (default 0.3) relative_visibility modifier -- exploitation via
        productivity gains is much less visible."""
        source = _FixedProductivitySource(state=_RELATIVE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_working_day_visibility_modifier(graph, services, tick=1)

        assert result == pytest.approx(WorkingDayDefines().relative_visibility)

    def test_uses_run_scoped_working_day_defines(self) -> None:
        """A custom ``GameDefines.working_day`` override must be threaded
        through to the classifier -- not the hardcoded schema default."""
        custom_defines = GameDefines(working_day=WorkingDayDefines(absolute_visibility=0.42))
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(defines=custom_defines, productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_working_day_visibility_modifier(graph, services, tick=1)

        assert result == pytest.approx(0.42)

    def test_year_derived_from_tick_and_base_year(self) -> None:
        """year = base_year (graph attr) + tick // weeks_per_year -- the
        SAME convention ``engine/systems/production.py`` already uses."""
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()
        graph.set_graph_attr("base_year", 2015)
        weeks_per_year = services.defines.timescale.weeks_per_year

        resolve_working_day_visibility_modifier(graph, services, tick=weeks_per_year * 3)

        assert source.calls, "the data source must have been called"
        _, _, queried_year = source.calls[0]
        assert queried_year == 2015 + 3

    def test_default_base_year_is_2022_when_unset(self) -> None:
        """No ``base_year`` graph attr -> the 2022 default, matching
        ``engine/systems/production.py``'s convention exactly (both read
        the same graph attribute within one tick)."""
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        resolve_working_day_visibility_modifier(graph, services, tick=0)

        _, _, queried_year = source.calls[0]
        assert queried_year == 2022

    def test_no_county_sector_geography_is_fabricated(self) -> None:
        """No per-class county/sector identity exists to honestly vary the
        call by (the wired FRED adapter is itself national-uniform,
        program prompt §2c) -- the placeholder args must not silently
        impersonate real per-county/sector data."""
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        resolve_working_day_visibility_modifier(graph, services, tick=0)

        fips_code, naics_sector, _ = source.calls[0]
        assert fips_code == "00000"
        assert naics_sector == "00"

    def test_deterministic(self) -> None:
        """Identical inputs must produce an identical result every time
        (Constitution III.7)."""
        services_a = ServiceContainer.create(
            productivity_data_source=_FixedProductivitySource(state=_RELATIVE_STATE)
        )
        services_b = ServiceContainer.create(
            productivity_data_source=_FixedProductivitySource(state=_RELATIVE_STATE)
        )
        graph_a = BabylonGraph()
        graph_b = BabylonGraph()

        result_a = resolve_working_day_visibility_modifier(graph_a, services_a, tick=5)
        result_b = resolve_working_day_visibility_modifier(graph_b, services_b, tick=5)

        assert result_a == result_b


@pytest.mark.unit
class TestResolveAbsoluteRelativeSurplusRatio:
    """resolve_absolute_relative_surplus_ratio: services + graph + tick ->
    Chs. 10/12/15 surplus-strategy ratio, or an honest ``None``.

    Feature: vol1-value-production program U6. Shares
    ``resolve_working_day_state``'s one FRED fetch with
    ``resolve_working_day_visibility_modifier`` (U4) -- same source, same
    year derivation, same "national placeholder, never fabricated
    geography" discipline.
    """

    def test_unwired_source_returns_none(self) -> None:
        services = ServiceContainer.create()
        graph = BabylonGraph()

        result = resolve_absolute_relative_surplus_ratio(graph, services, tick=1)

        assert result is None

    def test_source_returning_none_propagates_none(self) -> None:
        source = _FixedProductivitySource(state=None)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_absolute_relative_surplus_ratio(graph, services, tick=1)

        assert result is None

    def test_absolute_dominant_state_reads_below_parity(self) -> None:
        """hours=50, intensity=0.9, relative_hours_threshold=40 (default):
        ratio = 0.9 * 40/50 = 0.72 -- below the 1.0 parity point, matching
        the state's own ABSOLUTE_DOMINANT classification."""
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_absolute_relative_surplus_ratio(graph, services, tick=1)

        assert result == pytest.approx(0.72)

    def test_relative_dominant_state_reads_above_parity(self) -> None:
        """hours=37, intensity=2.0, relative_hours_threshold=40 (default):
        ratio = 2.0 * 40/37 ~= 2.162 -- above the 1.0 parity point, matching
        the state's own RELATIVE_DOMINANT classification."""
        source = _FixedProductivitySource(state=_RELATIVE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_absolute_relative_surplus_ratio(graph, services, tick=1)

        assert result == pytest.approx(2.0 * 40.0 / 37.0)

    def test_zero_hours_is_a_degenerate_none(self) -> None:
        """A ratio cannot honestly answer a zero-hours reading -- absence,
        never a fabricated division."""
        zero_hours_state = WorkingDayState(
            fips_code="26163",
            naics_sector="48",
            year=2019,
            avg_weekly_hours=0.0,
            labor_intensity_index=1.0,
        )
        source = _FixedProductivitySource(state=zero_hours_state)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_absolute_relative_surplus_ratio(graph, services, tick=1)

        assert result is None

    def test_uses_run_scoped_working_day_defines(self) -> None:
        """A custom ``relative_hours_threshold`` override must be threaded
        through -- not the hardcoded schema default."""
        custom_defines = GameDefines(working_day=WorkingDayDefines(relative_hours_threshold=50.0))
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(defines=custom_defines, productivity_data_source=source)
        graph = BabylonGraph()

        result = resolve_absolute_relative_surplus_ratio(graph, services, tick=1)

        # ratio = 0.9 * 50/50 = 0.9, exactly at the (custom) threshold.
        assert result == pytest.approx(0.9)

    def test_shares_the_same_year_derivation_as_the_visibility_modifier(self) -> None:
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        graph = BabylonGraph()
        graph.set_graph_attr("base_year", 2015)
        weeks_per_year = services.defines.timescale.weeks_per_year

        resolve_absolute_relative_surplus_ratio(graph, services, tick=weeks_per_year * 3)

        assert source.calls, "the data source must have been called"
        _, _, queried_year = source.calls[0]
        assert queried_year == 2015 + 3

    def test_deterministic(self) -> None:
        """Identical inputs must produce an identical result every time
        (Constitution III.7)."""
        services_a = ServiceContainer.create(
            productivity_data_source=_FixedProductivitySource(state=_RELATIVE_STATE)
        )
        services_b = ServiceContainer.create(
            productivity_data_source=_FixedProductivitySource(state=_RELATIVE_STATE)
        )
        graph_a = BabylonGraph()
        graph_b = BabylonGraph()

        result_a = resolve_absolute_relative_surplus_ratio(graph_a, services_a, tick=5)
        result_b = resolve_absolute_relative_surplus_ratio(graph_b, services_b, tick=5)

        assert result_a == result_b
