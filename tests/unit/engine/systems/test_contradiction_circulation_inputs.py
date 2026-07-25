"""ContradictionSystem fills the four Volume II circulation ratios (U5).

All four are RATIOS OF SUMS over the county circulation layer (Feature
023's ``CirculationCrisisState``, U3/U4 wiring), read off
``tick_dynamics.county_states`` the same channel
:meth:`~babylon.engine.systems.contradiction.ContradictionSystem._county_money_ratios`
already reads for the Volume III money fields — never a mean of per-county
ratios (the intensive-aggregation error class).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.circulation.types import (
    CirculationCrisisAssessment,
    CirculationCrisisState,
    DisproportionalityCrisis,
)
from babylon.domain.economics.dynamics.types import ClassDistribution
from babylon.domain.economics.tick.graph_bridge import TICK_DYNAMICS_KEY
from babylon.domain.economics.tick.types import CountyEconomicState
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _class_distribution(fips: str) -> ClassDistribution:
    return ClassDistribution(
        fips=fips,
        year=2015,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )


def _circulation_state(
    fips: str,
    *,
    money_capital: float,
    commodity_capital: float,
    productive_capital: float = 0.0,
    realization_crisis: bool = False,
    reproduction_crisis: bool | None = None,
    dept_i_output: float | None = None,
    dept_ii_output: float | None = None,
) -> CirculationCrisisState:
    base = CirculationCrisisState.initial(fips, 2015)
    circuit = base.circuit_state.model_copy(
        update={
            "money_capital": money_capital,
            "commodity_capital": commodity_capital,
            "productive_capital": productive_capital,
        }
    )
    assessment = CirculationCrisisAssessment(
        fips_code=fips,
        year=2015,
        realization_crisis=realization_crisis,
        turnover_crisis=False,
        reproduction_crisis=reproduction_crisis,
        vulnerabilities=[],
    )
    disproportionality = None
    if dept_i_output is not None and dept_ii_output is not None:
        disproportionality = DisproportionalityCrisis(
            year=2015,
            dept_i_output=dept_i_output,
            dept_ii_output=dept_ii_output,
            dept_i_share_required=0.6667,
        )
    return base.model_copy(
        update={
            "circuit_state": circuit,
            "latest_assessment": assessment,
            "disproportionality": disproportionality,
        }
    )


def _county(fips: str, circulation_state: CirculationCrisisState) -> CountyEconomicState:
    return CountyEconomicState(
        fips=fips,
        year=2015,
        capital_stock=1.0e9,
        throughput_position=0.9,
        supply_chain_depth=2.1,
        unemployment_rate=0.05,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500000.0,
        class_distribution=_class_distribution(fips),
        phi_hour=3.5,
        circulation_state=circulation_state,
    )


def _inputs(graph: BabylonGraph, services: ServiceContainer):  # type: ignore[no-untyped-def]
    return ContradictionSystem()._build_graph_inputs(graph, services)  # noqa: SLF001


class TestAbsence:
    """A bare graph fabricates nothing (Constitution III.11)."""

    def test_all_four_are_none_on_a_bare_graph(self) -> None:
        inputs = _inputs(BabylonGraph(), ServiceContainer.create())
        assert inputs.commodity_overhang_share is None
        assert inputs.realization_crisis_share is None
        assert inputs.reproduction_crisis_share is None
        assert inputs.disproportionality_imbalance is None

    def test_county_states_without_circulation_history_read_absent(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {"county_states": {"26163": _county("26163", CirculationCrisisState.default())}},
        )
        inputs = _inputs(graph, ServiceContainer.create())
        # CirculationCrisisState.default() has circuit_state.total_capital ==
        # 0.0 — the bootstrap/fresh-county placeholder, not real history.
        assert inputs.commodity_overhang_share is None
        assert inputs.realization_crisis_share is None
        assert inputs.reproduction_crisis_share is None
        assert inputs.disproportionality_imbalance is None


class TestCommodityOverhangShare:
    def test_is_commodity_over_total_capital(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163",
                        _circulation_state("26163", money_capital=70.0, commodity_capital=30.0),
                    )
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.commodity_overhang_share == pytest.approx(0.3)

    def test_aggregate_is_a_ratio_of_sums_not_a_mean_of_ratios(self) -> None:
        """A tiny county must NOT swing the national reading as hard as a
        large one. Wayne holds 1000 total capital, 100 stuck as commodity
        (0.1); a 1-total-capital county is fully stuck (1.0). The mean of
        ratios is 0.55; the truth is 101/1001 = 0.1009."""
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163",
                        _circulation_state("26163", money_capital=900.0, commodity_capital=100.0),
                    ),
                    "26001": _county(
                        "26001",
                        _circulation_state("26001", money_capital=0.0, commodity_capital=1.0),
                    ),
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.commodity_overhang_share == pytest.approx(101.0 / 1001.0)
        assert inputs.commodity_overhang_share != pytest.approx(0.55)


class TestRealizationCrisisShare:
    def test_is_capital_weighted_fraction_in_crisis(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163",
                        _circulation_state(
                            "26163",
                            money_capital=25.0,
                            commodity_capital=75.0,
                            realization_crisis=True,
                        ),
                    ),
                    "26001": _county(
                        "26001",
                        _circulation_state(
                            "26001",
                            money_capital=75.0,
                            commodity_capital=25.0,
                            realization_crisis=False,
                        ),
                    ),
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.realization_crisis_share == pytest.approx(0.5)  # 100 / 200


class TestReproductionCrisisShare:
    def test_unknown_counties_are_excluded_from_the_denominator(self) -> None:
        """Honest absence: a county whose reproduction_crisis is None (no
        tensor department data) must not silently count as 'balanced' —
        it is excluded from BOTH the numerator and the denominator."""
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163",
                        _circulation_state(
                            "26163",
                            money_capital=50.0,
                            commodity_capital=50.0,
                            reproduction_crisis=True,
                        ),
                    ),
                    "26001": _county(
                        "26001",
                        _circulation_state(
                            "26001",
                            money_capital=50.0,
                            commodity_capital=50.0,
                            reproduction_crisis=None,
                        ),
                    ),
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        # Only 26163's 100 total_capital is "known"; it is in crisis, so 1.0
        # — not 0.5 (which would result from treating 26001's unknown as
        # "not in crisis" and folding it into the denominator).
        assert inputs.reproduction_crisis_share == pytest.approx(1.0)

    def test_all_unknown_reads_absent(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163",
                        _circulation_state(
                            "26163",
                            money_capital=50.0,
                            commodity_capital=50.0,
                            reproduction_crisis=None,
                        ),
                    )
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.reproduction_crisis_share is None
        # commodity_overhang_share is still real — circuit state exists
        # independently of the reproduction reading's honest absence.
        assert inputs.commodity_overhang_share == pytest.approx(0.5)


class TestDisproportionalityImbalance:
    def test_is_actual_share_minus_required_share(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163",
                        _circulation_state(
                            "26163",
                            money_capital=50.0,
                            commodity_capital=50.0,
                            dept_i_output=6000.0,
                            dept_ii_output=3000.0,
                        ),
                    )
                }
            },
        )
        services = ServiceContainer.create()
        required = services.defines.capital_vol2.dept_i_share_required
        inputs = _inputs(graph, services)
        # actual share = 6000 / 9000 = 0.6667 (Marx's own illustration)
        assert inputs.disproportionality_imbalance == pytest.approx(
            (6000.0 / 9000.0) - required, abs=1e-6
        )

    def test_aggregate_is_a_ratio_of_sums_not_a_mean_of_ratios(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163",
                        _circulation_state(
                            "26163",
                            money_capital=1.0,
                            commodity_capital=1.0,
                            dept_i_output=900.0,
                            dept_ii_output=100.0,
                        ),
                    ),
                    "26001": _county(
                        "26001",
                        _circulation_state(
                            "26001",
                            money_capital=1.0,
                            commodity_capital=1.0,
                            dept_i_output=0.0,
                            dept_ii_output=1.0,
                        ),
                    ),
                }
            },
        )
        services = ServiceContainer.create()
        required = services.defines.capital_vol2.dept_i_share_required
        inputs = _inputs(graph, services)
        # ratio of sums: 900 / 1001, not the mean of (0.9, 0.0) = 0.45
        expected = (900.0 / 1001.0) - required
        assert inputs.disproportionality_imbalance == pytest.approx(expected)

    def test_no_disproportionality_reading_is_absent(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163",
                        _circulation_state("26163", money_capital=50.0, commodity_capital=50.0),
                    )
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.disproportionality_imbalance is None
