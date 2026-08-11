"""Conformance vectors for `dispossession/territory-transfer`'s remaining
per-input CEILING clamps, from the frozen engine — the ADVERSARIAL-REVIEW
follow-up scenario (F2/F3 of the 2026-08-11 review round on PR #498).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/dispossession_ceiling_matrix_conformance.rs``.

Companion to ``dispossession_negative_input_conformance.py``: that script
covers `foreclosure_rate`'s ceiling plus every OTHER input's floor; this one
covers `eviction_rate`'s ceiling plus every OTHER input's ceiling
(`displacement_rate`, `concentrated_ownership`, `absentee_landlord_share`),
and `foreclosure_rate`'s floor. Between the two, all ten per-input
floor/ceiling clamps `DispossessionEventSystem` applies
(`dispossession_events.py:70-72,84-88`) are individually exercised by a
vector where deleting JUST that one clamp changes the computed intensity —
none of it needs the `DispossessionDefines.model_construct` bypass, since
every value pushed out of domain here is a raw territory-node attribute
(`_get_float` off a plain graph dict), not a `GameDefines`-sourced
coefficient.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/dispossession_ceiling_matrix_conformance.py
"""

from __future__ import annotations

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph


def main() -> None:
    """Run one tick of the frozen DispossessionEventSystem, shipped defines."""
    services = ServiceContainer.create()
    try:
        graph = BabylonGraph()
        # foreclosure_rate=-6 (past the floor); eviction/displacement/
        # concentrated_ownership/absentee_landlord_share all past the
        # ceiling (eviction, being positive, doubles as the gate anchor).
        graph.add_node(
            "ceiling-matrix-county",
            NodeType.TERRITORY,
            foreclosure_rate=-6.0,
            eviction_rate=6.0,
            displacement_rate=8.0,
            concentrated_ownership=9.0,
            absentee_landlord_share=4.0,
            wealth=1_000_000.0,
        )
        DispossessionEventSystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        node = graph.get_node("ceiling-matrix-county")
        if node is None:
            raise SystemExit("ceiling-matrix-county vanished during the tick")
        a = node.attributes
        print("post-tick state:")
        print(
            f"  ceiling-matrix-county  wealth={a['wealth']!r} "
            f"dispossession_intensity={a.get('dispossession_intensity')!r}"
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
