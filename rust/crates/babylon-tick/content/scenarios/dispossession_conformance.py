"""Conformance vectors for the ``dispossession/*`` rule pack, from the frozen engine.

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/dispossession_conformance.rs``. It builds the
two territories of ``dispossession-conformance.bscn`` node for node, runs the
frozen ``DispossessionEventSystem`` once against them, and prints the
post-tick state plus every event the tick emitted.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/dispossession_conformance.py

The frozen system is the contract source for STRUCTURE and ORDERING, not a
correctness oracle (ADR183). This pack ports the WHOLE frozen system — five
territory-level rate/structural inputs feeding a weighted composite
intensity, a value transfer clamped to available wealth, and two events
(``DISPOSSESSION_EVENT`` unconditional once the guard passes,
``VALUE_TRANSFER`` gated on a positive transfer amount) — the gap report's
own "cleanest fit in the estate" verdict (row 10.0,
``reports/bsl-gap-analysis-2026-08-10.md``).

Two territories:

- ``foreclosed-county``: nonzero wealth, exercises the full positive path —
  intensity write, ``DISPOSSESSION_EVENT``, wealth write, ``VALUE_TRANSFER``.
- ``insolvent-county``: SAME rates (dispossession activity exists), but
  ZERO wealth — ``transfer_amount`` computes to exactly ``0.0``, so the
  frozen engine's ``if transfer_amount > 0.0:`` guard does not fire: no
  wealth write, no ``VALUE_TRANSFER``, but the intensity write and
  ``DISPOSSESSION_EVENT`` (both OUTSIDE that guard in the frozen source,
  ``dispossession_events.py:96-133``) still happen.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

#: Shared dispossession-activity rates, applied to both subjects. Real
#: per-county data is not hydrated in the canonical run today (the gap
#: report's Class C: "input-gated / zero-rate" — `dispossession_events.py`
#: fires and produces no writes against current data). These are illustrative
#: conformance fixture values, not read off any real county.
RATES: dict[str, float] = {
    "foreclosure_rate": 0.5,
    "eviction_rate": 0.3,
    "displacement_rate": 0.2,
    "concentrated_ownership": 0.6,
    "absentee_landlord_share": 0.4,
}

SUBJECTS: list[tuple[str, dict[str, Any]]] = [
    ("foreclosed-county", {**RATES, "wealth": 1_000_000.0}),
    ("insolvent-county", {**RATES, "wealth": 0.0}),
]


def build_graph() -> BabylonGraph:
    """Build the two-territory world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SUBJECTS:
        graph.add_node(node_id, NodeType.TERRITORY, **attrs)
    return graph


def main() -> None:
    """Run one tick of the frozen DispossessionEventSystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        d = services.defines.dispossession
        print("defines (src/babylon/data/defines.yaml, dispossession: section):")
        for name in (
            "weight_foreclosure",
            "weight_eviction",
            "weight_displacement",
            "weight_tax_sale",
            "weight_eminent_domain",
            "deadweight_loss_fraction",
            "transfer_scale",
        ):
            print(f"  dispossession.{name} = {getattr(d, name)!r}")
        print()

        graph = build_graph()
        DispossessionEventSystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        print("post-tick state:")
        for node_id, _ in SUBJECTS:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<18} "
                f"wealth={a['wealth']!r} "
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
