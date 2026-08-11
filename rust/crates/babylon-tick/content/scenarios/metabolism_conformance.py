"""Conformance vectors for `metabolism/biocapacity-update`, from the frozen engine.

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/metabolism_conformance.rs``. It builds the
three territories of ``metabolism-conformance.bscn`` node for node, runs the
frozen ``MetabolismSystem`` once against them, and prints the post-tick
state.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/metabolism_conformance.py

The frozen system is the contract source for STRUCTURE and ORDERING, not a
correctness oracle (ADR183). This pack ports only Phase 1 of the frozen
system (per-territory biocapacity delta + hysteresis ratchet + double
clamp) — the spec-070 sovereign pre-pass and Phases 2-3 (global overshoot
aggregate + ``ECOLOGICAL_OVERSHOOT``) are BLOCKED, per
``reports/metabolism-port-assessment-2026-08-11.md``.

All three territories share the PRODUCTION-DEFAULT ``MetabolismDefines``
coefficients (``entropy_factor=1.2``, ``hysteresis_rate=0.005``) and the
production-default per-node ``regeneration_rate=0.02`` (grep-verified
uniform across every scenario builder — the assessment's D-2). They are
discriminated entirely by their per-node ``biocapacity``/``max_biocapacity``/
``extraction_intensity`` seeds:

- ``nominal-county``: a small current stock, full extraction — neither clamp
  binds (regeneration is small and positive, the ecological cost pulls it
  down but not to zero, and the hysteresis damage barely dents the ceiling).
- ``hysteresis-inert-county``: ``extraction_intensity=0`` — the frozen
  formula's ``raw_extraction = extraction_intensity * current_biocapacity``
  is exactly zero, so BOTH the ecological cost AND the hysteresis damage are
  exactly zero: pure regeneration, and ``max_biocapacity`` is unchanged bit
  for bit.
- ``zero-floor-county``: at its ceiling (``biocapacity == max_biocapacity``,
  so regeneration is suppressed per the frozen formula's own
  ``if current_biocapacity >= max_biocapacity: regeneration = 0.0``) with
  full extraction — the ecological cost alone drives ``current + delta``
  deeply negative, and the ``max(0.0, ...)`` floor binds exactly at ``0.0``.
  Its ``max_biocapacity`` also strictly decreases from its seed, proving the
  hysteresis ratchet (``new_max = max(0.0, max_cap - damage)``) is live.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

SUBJECTS: list[tuple[str, dict[str, Any]]] = [
    (
        "nominal-county",
        {
            "biocapacity": 5.0,
            "max_biocapacity": 100.0,
            "extraction_intensity": 1.0,
            "regeneration_rate": 0.02,
        },
    ),
    (
        "hysteresis-inert-county",
        {
            "biocapacity": 50.0,
            "max_biocapacity": 100.0,
            "extraction_intensity": 0.0,
            "regeneration_rate": 0.02,
        },
    ),
    (
        "zero-floor-county",
        {
            "biocapacity": 100.0,
            "max_biocapacity": 100.0,
            "extraction_intensity": 1.0,
            "regeneration_rate": 0.02,
        },
    ),
]


def build_graph() -> BabylonGraph:
    """Build the three-territory world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SUBJECTS:
        graph.add_node(node_id, NodeType.TERRITORY, **attrs)
    return graph


def main() -> None:
    """Run one tick of the frozen MetabolismSystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        d = services.defines.metabolism
        print("defines (src/babylon/data/defines.yaml, metabolism: section):")
        for name in (
            "entropy_factor",
            "overshoot_threshold",
            "hysteresis_rate",
            "max_overshoot_ratio",
        ):
            print(f"  metabolism.{name} = {getattr(d, name)!r}")
        print()

        graph = build_graph()
        MetabolismSystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        print("post-tick state:")
        for node_id, seed in SUBJECTS:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<24} "
                f"biocapacity={a['biocapacity']!r} "
                f"max_biocapacity={a['max_biocapacity']!r} "
                f"(seed biocapacity={seed['biocapacity']!r} "
                f"seed max_biocapacity={seed['max_biocapacity']!r})"
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
