"""Conformance vectors for the `territory/*` rule pack, from the frozen engine.

This script is the PROVENANCE — the STRUCTURE oracle, explicitly NOT a byte
oracle (ADR183) — for the port pinned across
``rust/crates/babylon-tick/tests/territory_conformance.rs``. It builds the
twelve territories and three social classes of
``territory-conformance.bscn`` node for node, runs the frozen
``TerritorySystem`` once against them (all four phases, in the frozen
sequential order), and prints the post-tick state plus every event.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/territory_conformance.py

The frozen system is the contract source for STRUCTURE and ORDERING, not a
correctness oracle (ADR183) — this pack's own BSL rule text diverges from
the frozen engine's float arithmetic in several D-recorded ways (the
scaled-Int rent lane, the directed-vs-any sink/spillover walks, the
same-type multi-sink tiebreak, the two-clamp inconsistency — see
``territory.bsl``'s own header and the Draft-Ruling Register rows this port
adds). What this script proves is that the BSL pack moves the SAME fields
in the SAME direction for the SAME reasons the frozen engine does — the
conformance vectors pinned in the Rust test file are measured from the BSL
engine itself, not copied from this script's printed floats.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.territory import TerritorySystem
from babylon.models.enums import EdgeType, NodeType, OperationalProfile, TerritoryType
from babylon.topology.graph import BabylonGraph

#: The twelve territories, in the declaration order of
#: ``territory-conformance.bscn``. ``rent_level`` and ``population`` mirror
#: the scenario's scaled-Int/plain-Int seeds (rent-level-x1e6 / 1e6).
TERRITORIES: list[tuple[str, dict[str, Any]]] = [
    (
        "sub-threshold-high",
        {
            "profile": OperationalProfile.HIGH_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.3,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 100,
        },
    ),
    (
        "sub-threshold-low",
        {
            "profile": OperationalProfile.LOW_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.4,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 100,
        },
    ),
    (
        "latch-tick-source",
        {
            "profile": OperationalProfile.HIGH_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.68,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 1000,
        },
    ),
    (
        "sink-penal",
        {
            "profile": OperationalProfile.LOW_PROFILE,
            "territory_type": TerritoryType.PENAL_COLONY,
            "heat": 0.1,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 0,
        },
    ),
    (
        "sink-reservation",
        {
            "profile": OperationalProfile.LOW_PROFILE,
            "territory_type": TerritoryType.RESERVATION,
            "heat": 0.1,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 0,
        },
    ),
    (
        "latch-no-sink",
        {
            "profile": OperationalProfile.HIGH_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.68,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 1000,
        },
    ),
    (
        "already-latched-to-camp",
        {
            "profile": OperationalProfile.LOW_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.5,
            "rent_level": 1.0,
            "under_eviction": True,
            "population": 1000,
        },
    ),
    (
        "concentration-camp",
        {
            "profile": OperationalProfile.LOW_PROFILE,
            "territory_type": TerritoryType.CONCENTRATION_CAMP,
            "heat": 0.1,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 500,
        },
    ),
    (
        "chain-1",
        {
            "profile": OperationalProfile.HIGH_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.9,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 1000,
        },
    ),
    (
        "chain-2",
        {
            "profile": OperationalProfile.LOW_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.3,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 100,
        },
    ),
    (
        "chain-3",
        {
            "profile": OperationalProfile.LOW_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.2,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 100,
        },
    ),
    (
        "isolated-fallback",
        {
            "profile": OperationalProfile.LOW_PROFILE,
            "territory_type": TerritoryType.CORE,
            "heat": 0.25,
            "rent_level": 1.0,
            "under_eviction": False,
            "population": 100,
        },
    ),
]

#: The three social classes — two TENANCY-connected to ``sink-penal``, one not.
SOCIAL_CLASSES: list[tuple[str, dict[str, Any]]] = [
    ("tenant-1", {"organization": 0.6}),
    ("tenant-2", {"organization": 0.6}),
    ("non-tenant", {"organization": 0.6}),
]

#: ADJACENCY / TENANCY edges, mirroring the scenario's own edge block.
ADJACENCY_EDGES: list[tuple[str, str]] = [
    ("latch-tick-source", "sink-penal"),
    ("latch-tick-source", "sink-reservation"),
    ("already-latched-to-camp", "concentration-camp"),
    ("chain-1", "chain-2"),
    ("chain-2", "chain-3"),
]
TENANCY_EDGES: list[tuple[str, str]] = [
    ("tenant-1", "sink-penal"),
    ("tenant-2", "sink-penal"),
]


def build_graph() -> BabylonGraph:
    """Build the fifteen-node world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in TERRITORIES:
        graph.add_node(node_id, NodeType.TERRITORY, **attrs)
    for node_id, attrs in SOCIAL_CLASSES:
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **attrs)
    for source, target in ADJACENCY_EDGES:
        graph.add_edge(source, target, EdgeType.ADJACENCY)
    for source, target in TENANCY_EDGES:
        graph.add_edge(source, target, EdgeType.TENANCY)
    return graph


def main() -> None:
    """Run one tick of the frozen TerritorySystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        d = services.defines.territory
        print("defines (src/babylon/data/defines.yaml, territory: section):")
        for name in (
            "heat_decay_rate",
            "high_profile_heat_gain",
            "eviction_heat_threshold",
            "rent_spike_multiplier",
            "displacement_rate",
            "heat_spillover_rate",
            "concentration_camp_decay_rate",
        ):
            print(f"  territory.{name} = {getattr(d, name)!r}")
        print()

        graph = build_graph()
        TerritorySystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        print("post-tick state:")
        for node_id, seed in TERRITORIES:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<26} "
                f"heat={a.get('heat')!r} "
                f"under_eviction={a.get('under_eviction')!r} "
                f"rent_level={a.get('rent_level')!r} "
                f"population={a.get('population')!r} "
                f"(seed heat={seed['heat']!r} seed population={seed['population']!r})"
            )
        print()
        print("post-tick social classes:")
        for node_id, seed in SOCIAL_CLASSES:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<12} organization={a.get('organization')!r} "
                f"(seed organization={seed['organization']!r})"
            )
        print()

        print("events:")
        for event in events:
            print(f"  {event.type} {event.payload!r}")
        if not events:
            print("  (none)")
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
