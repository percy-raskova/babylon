"""The DISCRIMINATING conformance world for `dispossession/territory-transfer`.

Proves the frozen engine's exact `when`-equivalent gate — `dispossession_events.py:
75-76`: ``if foreclosure_rate <= 0.0 and eviction_rate <= 0.0 and
displacement_rate <= 0.0: continue`` — reads ONLY the three primary rates, not
`concentrated_ownership` / `absentee_landlord_share`. A territory with
nonzero structural factors but all-zero primary rates is skipped WHOLE: no
intensity computed, no state written, no event published, even though the
intensity formula would be nonzero from the structural terms alone if it
ever ran. This is not a defect the port repairs (ADR183 §5.4) — it is the
frozen system's own gate, transcribed exactly.

This scenario is also the Class C reality check
(`reports/bsl-gap-analysis-2026-08-10.md` row 10.0: "Yes (zero-rate
inputs)"): on the canonical run today nothing hydrates non-zero dispossession
rates, so this is the system's actual dormant behavior, not a hypothetical.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/dispossession_zero_rate_conformance.py
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

SUBJECTS: list[tuple[str, dict[str, Any]]] = [
    (
        "dormant-county-1",
        {
            "foreclosure_rate": 0.0,
            "eviction_rate": 0.0,
            "displacement_rate": 0.0,
            # Deliberately NONZERO — proves the gate ignores these two.
            "concentrated_ownership": 0.6,
            "absentee_landlord_share": 0.4,
            "wealth": 1_000_000.0,
        },
    ),
    (
        "dormant-county-2",
        {
            "foreclosure_rate": 0.0,
            "eviction_rate": 0.0,
            "displacement_rate": 0.0,
            "concentrated_ownership": 0.6,
            "absentee_landlord_share": 0.4,
            "wealth": 500_000.0,
        },
    ),
]


def build_graph() -> BabylonGraph:
    """Build the two-territory dormant world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SUBJECTS:
        graph.add_node(node_id, NodeType.TERRITORY, **attrs)
    return graph


def main() -> None:
    """Run one tick of the frozen DispossessionEventSystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        graph = build_graph()
        DispossessionEventSystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        print("post-tick state (must equal the pre-tick seed exactly — no writes):")
        for node_id, seed in SUBJECTS:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<18} "
                f"wealth={a['wealth']!r} "
                f"dispossession_intensity={a.get('dispossession_intensity')!r} "
                f"(seed wealth was {seed['wealth']!r})"
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
