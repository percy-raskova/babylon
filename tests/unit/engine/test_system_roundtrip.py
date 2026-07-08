"""C.1 gate: every engine System's graph mutations must survive
``WorldState.from_graph`` on a minefield-seeded state.

Uses the spec-054 auto-discovery registry
(``tests/property/harness/system_registry.py``) so newly added Systems are
covered automatically, and the bound-harness invocation pattern
(``bound_harness.py`` run-one-system-then-``from_graph``).

The minefield state seeds every node family ``from_graph`` must
reconstruct — two SocialClass entities, a Territory, EXPLOITATION +
SOLIDARITY relationships, and a Sovereign with a CLAIMS edge (spec-070).
All fixtures come from ``WorldState.to_graph()`` — never hand-seeded
``_node_type`` strings — so the gate exercises the exact graph shape the
bridged runner and the Simulation facade produce.

Note on factions: ``balkanization_faction`` nodes have no production
writer and no WorldState field (spec-070 wiring hazard, out of Design B
scope), so the collapse case routes the winning-faction map through
``persistent_data`` and relies on ``_extraction_policy_for_faction``'s
documented ``"continue"`` fallback for absent Faction nodes.
"""

from __future__ import annotations

import pytest

from babylon.engine.context import TickContext
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.collapse_transition import CollapseTransitionSystem
from babylon.engine.systems.protocol import System
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.sovereign import Sovereign
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    EdgeType,
    ExtractionPolicy,
    OperationalProfile,
    SectorType,
    SovereigntyType,
)
from babylon.models.world_state import WorldState
from tests.property.harness.system_registry import all_systems

pytestmark = pytest.mark.unit


def _minefield_state(*, sovereign_legitimacy: float = 1.0) -> WorldState:
    """Seed every node family ``from_graph`` must reconstruct.

    Wayne-County-like shape: worker + owner SocialClass pair, one
    INDUSTRIAL Territory, EXPLOITATION + SOLIDARITY edges on distinct
    (source, target) pairs, and one Sovereign CLAIMS-ing the Territory
    (the CLAIMS edge also keeps CollapseTransitionSystem's
    orphaned-sovereign cleanup from pruning it).

    Args:
        sovereign_legitimacy: Sovereign legitimacy; ``0.0`` arms the
            FR-023 collapse path for the targeted collapse case.

    Returns:
        A fully-populated WorldState ready for ``to_graph()``.
    """
    worker = create_proletariat(id="C000", county_fips="26163")
    owner = create_bourgeoisie(id="C001", county_fips="26163")
    territory = Territory(
        id="T001",
        name="Wayne County",
        sector_type=SectorType.INDUSTRIAL,
        profile=OperationalProfile.LOW_PROFILE,
        biocapacity=500.0,
    )
    sovereign = Sovereign(
        id="SOV_TEST",
        name="Test Sovereign",
        sovereignty_type=SovereigntyType.RECOGNIZED_STATE,
        legitimacy=sovereign_legitimacy,
        color_hex="#112233",
        ruling_faction_id=None,
        extraction_policy=ExtractionPolicy.CONTINUE,
        founded_tick=0,
    )
    relationships = [
        Relationship(
            source_id="C000",
            target_id="C001",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=5.0,
            tension=0.4,
        ),
        Relationship(
            source_id="C001",
            target_id="C000",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.2,
        ),
        Relationship(
            source_id="SOV_TEST",
            target_id="T001",
            edge_type=EdgeType.CLAIMS,
        ),
    ]
    return WorldState(
        tick=0,
        entities={"C000": worker, "C001": owner},
        territories={"T001": territory},
        relationships=relationships,
        sovereigns={"SOV_TEST": sovereign},
    )


@pytest.mark.parametrize("system_cls", all_systems(), ids=lambda c: c.__name__)
def test_single_system_step_round_trips(system_cls: type[System]) -> None:
    """Run one System on a to_graph-shaped graph; from_graph must not raise."""
    state = _minefield_state()
    graph = state.to_graph()
    services = ServiceContainer.create()
    ctx = TickContext(tick=0)

    system_cls().step(graph, services, ctx)

    restored = WorldState.from_graph(graph, tick=1)  # must not raise
    assert restored.tick == 1
    # The Sovereign must survive the system step AND the round-trip.
    assert "SOV_TEST" in restored.sovereigns


def test_full_pipeline_round_trips() -> None:
    """All default Systems in canonical order, then from_graph must not raise."""
    from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine

    state = _minefield_state()
    graph = state.to_graph()
    services = ServiceContainer.create()
    ctx = TickContext(tick=0)

    SimulationEngine(list(_DEFAULT_SYSTEMS)).run_tick(graph, services, ctx)

    restored = WorldState.from_graph(graph, tick=1)  # must not raise
    assert restored.tick == 1
    assert "SOV_TEST" in restored.sovereigns


def test_collapse_transition_successor_sovereign_round_trips() -> None:
    """FR-023/FR-024 collapse: the SOV_AUTO_* successor lands in .sovereigns."""
    state = _minefield_state(sovereign_legitimacy=0.0)
    graph = state.to_graph()
    services = ServiceContainer.create()
    ctx = TickContext(tick=3)
    ctx.persistent_data["balkanization.winning_faction_by_territory"] = {"T001": "FAC_TEST"}

    CollapseTransitionSystem().step(graph, services, ctx)

    restored = WorldState.from_graph(graph, tick=4)  # must not raise
    successor_ids = [sid for sid in restored.sovereigns if sid.startswith("SOV_AUTO_")]
    assert len(successor_ids) == 1, (
        f"expected exactly one SOV_AUTO_* successor, got {sorted(restored.sovereigns)}"
    )
    successor = restored.sovereigns[successor_ids[0]]
    assert successor.id == successor_ids[0]
    assert successor.ruling_faction_id == "FAC_TEST"
    assert successor.founded_tick == 3
    # The collapsed Sovereign was orphan-pruned after its CLAIMS moved.
    assert "SOV_TEST" not in restored.sovereigns
