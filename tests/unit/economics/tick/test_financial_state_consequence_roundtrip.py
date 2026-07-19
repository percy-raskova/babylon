"""Round-trip proof for vol3-money-scissors U3: NATIONAL_FINANCIAL_ATTR is
readable by a CONSEQUENCE-phase System in the same tick TickDynamicsSystem
(MATERIAL_BASE @4.0) publishes it — no WorldState round-trip in between,
matching simulation_engine.run_tick's shared-graph contract (design doc SS3.5).

Feature: 024-capital-volume-iii / vol3-money-scissors U3
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from babylon.domain.economics.tick.graph_bridge import (
    NATIONAL_FINANCIAL_ATTR,
    read_national_financial_state_from_graph,
)
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.domain.economics.tick.types import NationalFinancialParameters
from babylon.engine.context import TickContext
from babylon.kernel.system_base import SystemBase
from babylon.kernel.tick_partition import TickPartition
from tests.unit.economics.tick.conftest import (
    MockFictitiousCapitalCalculator,
    MockInterestRateCalculator,
)
from tests.unit.economics.tick.test_system import _make_graph_with_state, _make_services

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.kernel.system_protocol import ContextType


class _SpyConsequenceSystem(SystemBase):
    """Minimal CONSEQUENCE-phase System that observes the published state.

    Stands in for the real MarketScissorsSystem consumer that U4/U6 wire —
    this class exists only to prove the graph key is readable at a
    CONSEQUENCE-phase position (@17.9, near MarketScissorsSystem's @17.8)
    within the same tick TickDynamicsSystem (@4.0, MATERIAL_BASE) writes it.
    """

    name: ClassVar[str] = "spy_consequence"
    partition: ClassVar[TickPartition] = TickPartition.CONSEQUENCE
    position: ClassVar[float] = 17.9

    def __init__(self) -> None:
        self.observed: NationalFinancialParameters | None = None

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Read NATIONAL_FINANCIAL_ATTR from the shared graph."""
        self.observed = read_national_financial_state_from_graph(graph)


def test_consequence_phase_system_reads_financial_state_same_tick() -> None:
    """A CONSEQUENCE System reads what MATERIAL_BASE published, same tick."""
    services = _make_services(
        interest_calculator=MockInterestRateCalculator(
            base_rate=0.25,
            treasury_10y=2.27,
            baa_spread=2.64,
        ),
        fictitious_capital_calculator=MockFictitiousCapitalCalculator(
            government_debt=18e12,
            corporate_equity=20e12,
            corporate_debt=8e12,
            household_debt=14e12,
        ),
    )
    graph = _make_graph_with_state(year=2015)
    context = TickContext(tick=52)

    material_base_system = TickDynamicsSystem()
    consequence_system = _SpyConsequenceSystem()

    assert NATIONAL_FINANCIAL_ATTR not in graph.graph

    # MATERIAL_BASE (@4.0) runs first — this is where NationalFinancialParameters
    # is instantiated and published (U3.2).
    material_base_system.step(graph, services, context)
    assert NATIONAL_FINANCIAL_ATTR in graph.graph

    # CONSEQUENCE (@17.9) runs later in the SAME tick, on the SAME graph
    # object, with no WorldState round-trip between them.
    consequence_system.step(graph, services, context)

    assert consequence_system.observed is not None
    assert consequence_system.observed.fictitious_capital is not None
    assert consequence_system.observed.fictitious_capital.total_claims == 60e12
    assert consequence_system.observed.interest_rate_state is not None
    assert consequence_system.observed.interest_rate_state.base_rate == 0.25
