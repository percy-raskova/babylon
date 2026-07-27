"""L-RECEIPTS — the Third-Worldist ledger's provenance rows (P25 U12 commit F, ADR139).

The-electoral-question.md §4: *no flow without a row*. The social wage has a
supply chain — overlay ← t-claim + Φ slice ← pool ← TRIBUTE ← periphery
EXPLOITATION — and every hop must leave a BoundaryFlowRegister row so the
Archive can render a welfare check's provenance to the terrain the surplus
was extracted from. The rows speak; no editorial voice needed.

Three writers under test: ImperialRentSystem @9 (EXPLOITATION_FLOW, the
chain's source), PolicySystem @17.47 (FISCAL_FUNDING — the Φ slice the
enactment actually consumed, pool → sovereign; SOCIAL_WAGE — sovereign →
class, the delivered units). All are guarded: an absent register (every unit
test, every qa scenario) is a clean no-op.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import uuid4

import pytest

from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegister
from babylon.domain.economics.node_kinds import BoundaryEdgeKind, NodeKind
from babylon.engine.context import TickContext
from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.scenarios.electoral_fixture import create_electoral_fixture_scenario
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.engine.systems.policy import PolicySystem, enqueue_agenda_item
from babylon.models.enums import EdgeType

from .test_policy import _Context, _item

pytestmark = pytest.mark.unit


@pytest.fixture
def services() -> Generator:
    from babylon.engine.services import ServiceContainer

    container = ServiceContainer.create()
    yield container
    container.database.close()


def _rows_of(register: BoundaryFlowRegister, kind: BoundaryEdgeKind) -> list:
    return [row for row in register.query() if row.flow_type is kind]


class TestExploitationRows:
    """The chain's source: every positive rent extraction leaves a row."""

    def test_every_positive_rent_edge_writes_a_row(self, services) -> None:
        state, _config, _defines = create_two_node_scenario()
        graph = state.to_graph()
        register = BoundaryFlowRegister(session_id=uuid4())
        services.boundary_register = register
        ImperialRentSystem().step(graph, services, TickContext(tick=1))
        rows = _rows_of(register, BoundaryEdgeKind.EXPLOITATION_FLOW)
        positive_flows = [
            e
            for e in graph.query_edges(edge_type=EdgeType.EXPLOITATION)
            if (e.attributes.get("value_flow") or 0.0) > 0.0
        ]
        assert len(rows) == len(positive_flows) > 0
        assert all(row.magnitude > 0.0 for row in rows)
        assert all(
            row.source_kind is NodeKind.SOCIAL_CLASS and row.dest_kind is NodeKind.SOCIAL_CLASS
            for row in rows
        )
        assert all(row.session_id == register.session_id for row in rows)

    def test_absent_register_is_a_clean_no_op(self, services) -> None:
        state, _config, _defines = create_two_node_scenario()
        graph = state.to_graph()
        assert services.boundary_register is None
        ImperialRentSystem().step(graph, services, TickContext(tick=1))  # no raise


class TestSocialWageReceipts:
    """The chain's delivery end: the Φ slice consumed and the per-class units."""

    @staticmethod
    def _funded_graph():
        state, _config, defines = create_electoral_fixture_scenario()
        graph = state.to_graph()
        # Measured Φ, share 200/2000 = 0.10 >= floor (core bars). Funding:
        # funded = min(100, 40 + 0.25*200) = 90; borrowed = 5; delivered = 95;
        # taxes absorb first (40) -> Φ slice consumed = 90 - 40 = 50.
        graph.update_node(
            "T001",
            tick_taxes_on_surplus=40.0,
            tick_total_surplus=2000.0,
            tick_phi_hour=5.0,
        )
        graph.set_graph_attr(
            "electoral_governments",
            {"SOV_USA_FED": {"party_id": "org/party-socdem", "formed_tick": 1, "share": 0.6}},
        )
        enqueue_agenda_item(graph, _item(promised=100.0))
        return graph, defines

    def test_delivery_writes_class_rows_and_the_phi_funding_row(self, services) -> None:
        graph, defines = self._funded_graph()
        register = BoundaryFlowRegister(session_id=uuid4())
        services.boundary_register = register
        bus_services = services
        bus_services.defines = defines
        PolicySystem().step(graph, bus_services, _Context(tick=1))

        social_wage = _rows_of(register, BoundaryEdgeKind.SOCIAL_WAGE)
        assert {row.dest_node_id for row in social_wage} == {"C001", "C002"}
        assert all(
            row.source_node_id == "SOV_USA_FED" and row.source_kind is NodeKind.SOVEREIGN
            for row in social_wage
        )
        assert sum(row.magnitude for row in social_wage) == pytest.approx(95.0)

        funding = _rows_of(register, BoundaryEdgeKind.FISCAL_FUNDING)
        assert len(funding) == 1
        assert funding[0].source_kind is NodeKind.NATIONAL
        assert funding[0].dest_node_id == "SOV_USA_FED"
        assert funding[0].magnitude == pytest.approx(50.0)

    def test_the_receipts_chain_is_complete(self, services) -> None:
        """The §4 sentence as an assertion: from a delivered social-wage row,
        the register can walk back to a funding row and an extraction row —
        no flow without a row, end to end."""
        graph, defines = self._funded_graph()
        graph.add_edge(
            "C001",
            "C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
        )
        register = BoundaryFlowRegister(session_id=uuid4())
        services.boundary_register = register
        services.defines = defines
        ImperialRentSystem().step(graph, services, TickContext(tick=1))
        PolicySystem().step(graph, services, _Context(tick=1))

        assert _rows_of(register, BoundaryEdgeKind.SOCIAL_WAGE)
        assert _rows_of(register, BoundaryEdgeKind.FISCAL_FUNDING)
        assert _rows_of(register, BoundaryEdgeKind.EXPLOITATION_FLOW)
