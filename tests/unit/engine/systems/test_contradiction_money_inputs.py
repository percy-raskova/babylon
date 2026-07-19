"""ContradictionSystem fills the four Volume III money ratios (U5).

Three sources, each with an honest-absence path:

- county surplus distributions and debt accumulations, read off
  ``tick_dynamics.county_states`` as a RATIO OF SUMS (never a mean of
  per-county ratios — that is the intensive-aggregation error class);
- the national financial state published under ``national_financial``;
- the scissors' ``fictitious_log``, read in ratio space.
"""

from __future__ import annotations

import math

import pytest

from babylon.domain.economics.distribution.types import (
    DebtAccumulation,
    SurplusValueDistribution,
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


def _county(
    fips: str,
    *,
    surplus: float,
    interest: float,
    rent: float,
    taxes: float,
    debt: float,
) -> CountyEconomicState:
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
        surplus_distribution=SurplusValueDistribution(
            fips_code=fips,
            year=2015,
            total_surplus_produced=surplus,
            interest_payments=interest,
            ground_rent=rent,
            taxes_on_surplus=taxes,
        ),
        debt_accumulation=DebtAccumulation(
            fips_code=fips,
            year=2015,
            accumulated_debt=debt,
            consecutive_deficit_ticks=0,
        ),
    )


def _inputs(graph: BabylonGraph, services: ServiceContainer):  # type: ignore[no-untyped-def]
    return ContradictionSystem()._build_graph_inputs(graph, services)  # noqa: SLF001


class TestAbsence:
    """A bare graph fabricates nothing (Constitution III.11)."""

    def test_all_four_are_none_on_a_bare_graph(self) -> None:
        inputs = _inputs(BabylonGraph(), ServiceContainer.create())
        assert inputs.rentier_share is None
        assert inputs.debt_ratio is None
        assert inputs.credit_fragility is None
        assert inputs.financialization_index is None

    def test_county_states_without_distributions_read_absent(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(TICK_DYNAMICS_KEY, {"county_states": {}})
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.rentier_share is None
        assert inputs.debt_ratio is None


class TestCountyRatios:
    def test_rentier_share_is_claims_over_surplus(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163", surplus=100.0, interest=20.0, rent=10.0, taxes=10.0, debt=0.0
                    )
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.rentier_share == pytest.approx(0.4)  # (20 + 10 + 10) / 100

    def test_aggregate_is_a_ratio_of_sums_not_a_mean_of_ratios(self) -> None:
        """The named intensive-aggregation error: a tiny county must NOT swing
        the national reading as hard as a large one. Wayne produces 1000 of
        surplus with 100 of claims (0.1); a 1-surplus county pays 1 in claims
        (1.0). The mean of ratios is 0.55; the truth is 101/1001 = 0.1009."""
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163", surplus=1000.0, interest=100.0, rent=0.0, taxes=0.0, debt=0.0
                    ),
                    "26001": _county(
                        "26001", surplus=1.0, interest=1.0, rent=0.0, taxes=0.0, debt=0.0
                    ),
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.rentier_share == pytest.approx(101.0 / 1001.0)
        assert inputs.rentier_share != pytest.approx(0.55)

    def test_debt_ratio_is_total_debt_over_total_surplus(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163", surplus=100.0, interest=0.0, rent=0.0, taxes=0.0, debt=75.0
                    ),
                    "26001": _county(
                        "26001", surplus=100.0, interest=0.0, rent=0.0, taxes=0.0, debt=25.0
                    ),
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.debt_ratio == pytest.approx(0.5)  # 100 / 200

    def test_zero_total_surplus_reads_absent_not_infinite(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            TICK_DYNAMICS_KEY,
            {
                "county_states": {
                    "26163": _county(
                        "26163", surplus=0.0, interest=0.0, rent=0.0, taxes=0.0, debt=5.0
                    )
                }
            },
        )
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.rentier_share is None
        assert inputs.debt_ratio is None


class TestNationalRatios:
    def test_credit_fragility_arrives_in_threshold_units(self) -> None:
        from babylon.domain.economics.tick.graph_bridge import NATIONAL_FINANCIAL_ATTR

        graph = BabylonGraph()
        graph.set_graph_attr(
            NATIONAL_FINANCIAL_ATTR,
            {"credit_state": {"credit_fragility": 0.002}},
        )
        services = ServiceContainer.create()
        # 0.002 / 0.001 == 2.0: twice the crisis threshold. (credit_fragility_scale
        # was corrected 0.02 -> 0.001 in HEAD b9433773 for exactly this U5.7 design,
        # so the raw reading twice the threshold must be 2e-3, not the brief's stale 4e-2.)
        assert _inputs(graph, services).credit_fragility == pytest.approx(2.0)

    def test_missing_credit_state_reads_absent(self) -> None:
        from babylon.domain.economics.tick.graph_bridge import NATIONAL_FINANCIAL_ATTR

        graph = BabylonGraph()
        graph.set_graph_attr(NATIONAL_FINANCIAL_ATTR, {"credit_state": None})
        assert _inputs(graph, ServiceContainer.create()).credit_fragility is None

    def test_financialization_index_is_the_fictitious_axis_in_ratio_space(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr("market", {"price_log": 0.0, "fictitious_log": 0.5})
        inputs = _inputs(graph, ServiceContainer.create())
        assert inputs.financialization_index == pytest.approx(math.exp(0.5))

    def test_parity_axis_reads_index_one(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr("market", {"price_log": 0.0, "fictitious_log": 0.0})
        assert _inputs(graph, ServiceContainer.create()).financialization_index == pytest.approx(
            1.0
        )

    def test_exponent_is_clamped_by_the_axis_bound(self) -> None:
        """A corrupt unbounded log must not raise OverflowError inside the
        tick loop; the axis's own max_abs_log is the clamp."""
        graph = BabylonGraph()
        graph.set_graph_attr("market", {"price_log": 0.0, "fictitious_log": 10_000.0})
        services = ServiceContainer.create()
        expected = math.exp(float(services.defines.market.max_abs_log))
        assert _inputs(graph, services).financialization_index == pytest.approx(expected)
