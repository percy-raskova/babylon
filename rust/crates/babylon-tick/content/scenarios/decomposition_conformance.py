"""Conformance vectors for the `decomposition/*` + `control-ratio/*` rule
packs, from the frozen engine.

This script is the PROVENANCE — the STRUCTURE and ORDERING oracle, NOT a
correctness oracle (ADR183) — for the Decomposition+ControlRatio port train
(`docs/superpowers/plans/2026-08-17-decomposition-controlratio-port.md`). It
builds the five social classes + one carceral-register world of
`decomposition-conformance.bscn` node for node, runs the frozen
`DecompositionSystem` (@11.0) then `ControlRatioSystem` (@12.0) for one
`step()` each against them, with a `TickContext` whose `persistent_data`
starts empty (matching the BSL carrier's own all-zero seed), and prints the
post-tick state plus the full event history.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" UV_FROZEN=1 uv run python \\
        rust/crates/babylon-tick/content/scenarios/decomposition_conformance.py

`la-dying` (wealth 400 < subsistence_threshold 500) is the frozen
`la_about_to_die` FALLBACK TRIGGER (`decomposition.py:158-159`): decomposition
fires at tick 1 with no 52-tick `decomposition_delay` to wait out, and no
prior `SUPERWAGE_CRISIS` event needed. `ControlRatioSystem` runs the SAME
tick immediately after (this script's own call order), but its own
`persistent_data` gate (`decomposition_tick = persistent.get
("_class_decomposition_tick")`) reads the CURRENT tick's write from
`DecompositionSystem` — both systems share the SAME `persistent` dict here,
exactly as the frozen engine's own `context.persistent_data` is one object
threaded through every system in a tick. `control_ratio_delay` is 52, so
`ControlRatioSystem` at tick 1 sees `tick (1) < decomposition_tick (1) + 52`
and returns immediately — no crisis, no terminal decision. This mirrors
Task 1's own scope: Task 1 ships no `control-ratio/*` rule content yet, so
there is nothing for a later Rust conformance test to assert against
ControlRatio's own event path from this run; that arrives in this train's
Pack B tasks, with a companion scenario that seeds a decomposed world
directly (matching plan §5's byte-order-hazard constraint: a zero-delay
control-ratio companion must SEED `decomposition-fire-tick`, never rely on
Pack A writing it the same tick).
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.control_ratio import ControlRatioSystem
from babylon.engine.systems.decomposition import DecompositionSystem
from babylon.models.enums import NodeType, SocialRole
from babylon.topology.graph import BabylonGraph

#: The five social classes, in the declaration order of
#: `decomposition-conformance.bscn`.
SOCIAL_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "la-dying",
        {
            "role": SocialRole.LABOR_ARISTOCRACY,
            "active": True,
            "population": 1000,
            "wealth": 400.0,
            "subsistence_threshold": 500.0,
            "s_bio": 5.0,
            "s_class": 5.0,
            "organization": 0.0,
        },
    ),
    (
        "enforcer-seed",
        {
            "role": SocialRole.CARCERAL_ENFORCER,
            "active": False,
            "population": 20,
            "wealth": 100.0,
            "subsistence_threshold": 0.0,
            "s_bio": 0.0,
            "s_class": 0.0,
            "organization": 0.0,
        },
    ),
    (
        "ip-seed",
        {
            "role": SocialRole.INTERNAL_PROLETARIAT,
            "active": False,
            "population": 77,
            "wealth": 33.0,
            "subsistence_threshold": 0.0,
            "s_bio": 0.0,
            "s_class": 0.0,
            "organization": 0.0,
        },
    ),
    (
        "lumpen",
        {
            "role": SocialRole.LUMPENPROLETARIAT,
            "active": True,
            "population": 200,
            "wealth": 10.0,
            "subsistence_threshold": 0.0,
            "s_bio": 0.0,
            "s_class": 0.0,
            "organization": 0.2,
        },
    ),
    (
        "bourgeois",
        {
            "role": SocialRole.CORE_BOURGEOISIE,
            "active": True,
            "population": 10,
            "wealth": 9000.0,
            "subsistence_threshold": 0.0,
            "s_bio": 0.0,
            "s_class": 0.0,
            "organization": 0.0,
        },
    ),
]


def build_graph() -> BabylonGraph:
    """Build the five-class world, in scenario declaration order.

    The BSL scenario also mints a `carceral-register` `INSTITUTION` carrier
    node (§2's reformulation) — the frozen engine has no graph-node
    counterpart for `persistent_data` at all (it is a plain dict on
    `TickContext`), so this mirror builds none; `main()` prints
    `persistent_data`'s own contents instead, which is what the carrier
    fields are a per-node reformulation OF.
    """
    graph = BabylonGraph()
    for node_id, attrs in SOCIAL_CLASSES:
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **attrs)
    return graph


def main() -> None:
    """Run one tick of the frozen Decomposition + ControlRatio systems and print the vectors."""
    services = ServiceContainer.create()
    try:
        c = services.defines.carceral
        print("defines (src/babylon/data/defines.yaml, carceral: section):")
        for name in (
            "control_capacity",
            "enforcer_fraction",
            "proletariat_fraction",
            "revolution_threshold",
            "decomposition_delay",
            "control_ratio_delay",
            "terminal_decision_delay",
        ):
            print(f"  carceral.{name} = {getattr(c, name)!r}")
        print(
            "  carceral.<approaching-consumption-multiple> = 2  (bare literal, decomposition.py:155, NO defines backing)"
        )
        print()

        graph = build_graph()
        context = TickContext(tick=1)

        DecompositionSystem().step(graph, services, context)
        ControlRatioSystem().step(graph, services, context)

        print(
            "post-tick persistent_data (the frozen state machine §2 reformulates onto the carrier):"
        )
        for key in sorted(context.persistent_data):
            print(f"  {key} = {context.persistent_data[key]!r}")
        print()

        print("post-tick social classes:")
        for node_id, seed in SOCIAL_CLASSES:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<14} active={a.get('active')!r} "
                f"population={a.get('population')!r} (seed {seed['population']!r}) "
                f"wealth={a.get('wealth')!r} (seed {seed['wealth']!r})"
            )
        print()

        events = services.event_bus.get_history()
        print("events:")
        for event in events:
            print(f"  {event.type} {event.payload!r}")
        if not events:
            print("  (none)")
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
