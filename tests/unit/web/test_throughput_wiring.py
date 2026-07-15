"""Wave 2 Round 2 owner ruling 1: wire ``throughput_position`` for real.

Before this fix, ``throughput_position``/``supply_chain_depth`` were
fabricated: hardcoded ``1.0``/``2.0`` at seed
(``domain/economics/tick/initializer.py:170-177``), carried forward forever
because ``_bridge_economics_overrides`` never constructed a
``throughput_calculator`` and ``_carry_tick_dynamics_flows`` never carried
``tick_throughput_position``/``tick_supply_chain_depth`` across the
``WorldState`` round-trip. Both gaps were engineering, not data — the BEA/QCEW
adapters read the same reference DB Φ already uses.

This suite pins three things (matching the pattern of
``test_carry_group_a_b.py``/``test_carry_derived_rates.py``):

1. ``_bridge_economics_overrides`` now constructs a real
   ``throughput_calculator`` and includes it in the overrides dict. NOTE:
   despite the empty ``fips_codes`` gate on ``_build_capital_calculator``,
   this call is NOT reference-DB-free — it eagerly builds the Leontief rent
   services, which load the BEA industry dimension (``dim_bea_industry``)
   regardless of fips. So these three wiring assertions carry
   ``@pytest.mark.requires_reference_db``: deselected on the DB-free dev CI
   tier (``test:unit-ci`` filters ``not requires_reference_db``), run locally
   and in main/nightly against the ci-data-v1 subset. They assert DI object
   identity, not query results.
2. ``_carry_tick_dynamics_flows`` re-stamps
   ``tick_throughput_position``/``tick_supply_chain_depth`` at a year
   boundary AND carries them forward between boundaries — the exact
   evaporation-on-``WorldState``-round-trip bug Group A/B were fixed for.
3. ``_serialize_territory`` emits ``throughput_position``/``supply_chain_depth``
   as honest ``None`` when the graph has no attr yet, and the real value when
   it does.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.types import (
    BifurcationRiskMetric,
    ClassDistribution,
    CountyEconomicState,
    CrisisPhase,
    CrisisState,
    NationalTickParameters,
)
from babylon.models.entities.territory import Territory
from babylon.models.enums import OperationalProfile, SectorType
from babylon.models.world_state import WorldState

pytestmark = pytest.mark.unit

WAYNE_FIPS = "26163"


@pytest.mark.requires_reference_db
class TestBridgeEconomicsOverridesWiresThroughputCalculator:
    """``_bridge_economics_overrides`` must construct a real throughput_calculator."""

    def test_overrides_include_a_real_throughput_calculator(self) -> None:
        from babylon.domain.economics.throughput.calculator import DefaultThroughputCalculator
        from game.engine_bridge import _bridge_economics_overrides

        # Empty fips_codes: no reference-DB hydration is triggered (mirrors
        # _build_capital_calculator's own no-fips gate) — safe at unit scope,
        # never touches the reference DB / babylon-data drive.
        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            assert "throughput_calculator" in overrides
            assert isinstance(overrides["throughput_calculator"], DefaultThroughputCalculator)
        finally:
            if leontief_session is not None:
                leontief_session.close()

    def test_throughput_calculator_reuses_the_qcew_source_wired_for_employment(self) -> None:
        """DRY: one QCEWCountyNAICSSource instance backs both employment_source
        and the throughput calculator's own QCEW dependency."""
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            throughput_calculator = overrides["throughput_calculator"]
            # Private attr introspection is the only way to assert reuse
            # without invoking a real query (Constitution III.11 test scope:
            # never touch the reference DB in this lane's tests).
            assert throughput_calculator._qcew_source is overrides["employment_source"]
        finally:
            if leontief_session is not None:
                leontief_session.close()

    def test_throughput_calculator_is_wired_with_the_melt_calculator(self) -> None:
        """π = τ_through / τ_national needs MELT — must not be left None."""
        from game.engine_bridge import _bridge_economics_overrides

        overrides, leontief_session = _bridge_economics_overrides(())
        try:
            throughput_calculator = overrides["throughput_calculator"]
            assert throughput_calculator._melt_calculator is overrides["melt_calculator"]
        finally:
            if leontief_session is not None:
                leontief_session.close()


def _boundary_county_and_params(
    *, throughput_position: float = 0.72, supply_chain_depth: float = 3.4
) -> tuple[CountyEconomicState, NationalTickParameters]:
    """A post-boundary county carrying a real (non-default) π/D pair."""
    dist = ClassDistribution(
        fips=WAYNE_FIPS,
        year=2011,
        bourgeoisie_share=0.02,
        petit_bourgeoisie_share=0.08,
        labor_aristocracy_share=0.30,
        proletariat_share=0.40,
        lumpenproletariat_share=0.20,
    )
    county = CountyEconomicState(
        fips=WAYNE_FIPS,
        year=2011,
        capital_stock=1e9,
        throughput_position=throughput_position,
        supply_chain_depth=supply_chain_depth,
        unemployment_rate=0.081,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=dist,
        phi_hour=3.50,
        crisis_state=CrisisState(
            phase=CrisisPhase.NORMAL,
            consecutive_below=0,
            crisis_start_period=None,
            crisis_duration=0,
            cumulative_wage_compression=0.0,
        ),
        bifurcation_risk=BifurcationRiskMetric(
            score=0.0,
            solidarity_density=0.4,
            legitimation=0.3,
            class_burden_ratio=0.5,
        ),
    )
    params = NationalTickParameters(
        year=2011,
        tau=62.0,
        gamma_basket=0.68,
        gamma_basket_raw=0.68,
        gamma_III=0.33,
        gamma_III_raw=0.33,
        tau_effective=42.16,
        v_reproduction=12.0,
        estimated=True,
    )
    return county, params


def _wayne_graph() -> object:
    """A one-territory graph whose node carries the real Wayne FIPS."""
    territory = Territory(
        id="T001",
        name="Wayne County",
        sector_type=SectorType.INDUSTRIAL,
        profile=OperationalProfile.LOW_PROFILE,
        biocapacity=500.0,
        county_fips=WAYNE_FIPS,
    )
    state = WorldState(tick=0, entities={}, territories={"T001": territory}, relationships=[])
    return state.to_graph()


class TestCarryThroughputPositionAtBoundary:
    def test_carry_stamps_throughput_position_and_supply_chain_depth(self) -> None:
        from game.engine_bridge import _carry_tick_dynamics_flows

        county, params = _boundary_county_and_params(
            throughput_position=0.72, supply_chain_depth=3.4
        )
        new_graph = _wayne_graph()
        old_graph = _wayne_graph()
        ctx = {
            "_tick_dynamics": {
                "county_states": {WAYNE_FIPS: county},
                "national_params": params,
            }
        }

        _carry_tick_dynamics_flows(old_graph, new_graph, ctx)

        node = new_graph.nodes["T001"]
        assert node["tick_throughput_position"] == pytest.approx(0.72)
        assert node["tick_supply_chain_depth"] == pytest.approx(3.4)


class TestCarryThroughputPositionBetweenBoundaries:
    def test_carry_forwards_throughput_position_between_boundaries(self) -> None:
        """Between year boundaries no new π/D is computed, but the last
        boundary's values must persist (like tick_phi_hour does) rather than
        evaporate — the exact bug owner ruling 1 calls out."""
        from game.engine_bridge import _carry_tick_dynamics_flows

        old_graph = _wayne_graph()
        old_graph.update_node(
            "T001",
            tick_phi_hour=3.50,
            tick_median_wage=21.0,
            tick_employment=500_000.0,
            tick_year=2011,
            tick_throughput_position=0.72,
            tick_supply_chain_depth=3.4,
        )
        new_graph = _wayne_graph()
        ctx: dict[str, object] = {}  # no _tick_dynamics => not a boundary

        _carry_tick_dynamics_flows(old_graph, new_graph, ctx)

        node = new_graph.nodes["T001"]
        assert node["tick_throughput_position"] == pytest.approx(0.72)
        assert node["tick_supply_chain_depth"] == pytest.approx(3.4)

    def test_no_boundary_ever_run_leaves_throughput_position_absent(self) -> None:
        """A session with no boundary state yet (no tick_phi_hour carried)
        skips the territory entirely — an honest empty domain, not a
        fabricated 1.0/2.0."""
        from game.engine_bridge import _carry_tick_dynamics_flows

        old_graph = _wayne_graph()  # no tick_* attrs at all yet
        new_graph = _wayne_graph()
        ctx: dict[str, object] = {}

        _carry_tick_dynamics_flows(old_graph, new_graph, ctx)

        node = new_graph.nodes["T001"]
        assert "tick_throughput_position" not in node
        assert "tick_supply_chain_depth" not in node


class TestSerializeTerritoryThroughputPosition:
    def _territory(self) -> Territory:
        return Territory(
            id="T001",
            name="Wayne County",
            sector_type=SectorType.INDUSTRIAL,
            profile=OperationalProfile.LOW_PROFILE,
            biocapacity=500.0,
            county_fips=WAYNE_FIPS,
        )

    def test_absent_from_graph_serializes_as_honest_none(self) -> None:
        from game.engine_bridge import _serialize_territory

        territory = self._territory()
        state = WorldState(tick=0, entities={}, territories={"T001": territory}, relationships=[])
        graph = state.to_graph()

        result = _serialize_territory(territory, graph=graph)

        assert result["throughput_position"] is None
        assert result["supply_chain_depth"] is None

    def test_present_on_graph_is_read_through(self) -> None:
        from game.engine_bridge import _serialize_territory

        territory = self._territory()
        state = WorldState(tick=0, entities={}, territories={"T001": territory}, relationships=[])
        graph = state.to_graph()
        graph.update_node("T001", tick_throughput_position=0.72, tick_supply_chain_depth=3.4)

        result = _serialize_territory(territory, graph=graph)

        assert result["throughput_position"] == pytest.approx(0.72)
        assert result["supply_chain_depth"] == pytest.approx(3.4)

    def test_no_graph_supplied_serializes_as_none(self) -> None:
        from game.engine_bridge import _serialize_territory

        territory = self._territory()

        result = _serialize_territory(territory, graph=None)

        assert result["throughput_position"] is None
        assert result["supply_chain_depth"] is None
