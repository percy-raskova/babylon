"""The frozen composition oracle for the joint carceral arc — Task 8 of the
Decomposition (@11.0) + ControlRatio (@12.0) port train
(`docs/superpowers/plans/2026-08-17-decomposition-controlratio-port.md`).

This script is the STRUCTURE and ORDERING oracle (ADR183), NOT a
correctness oracle — it exists to derive and cross-check the arc's tick schedule and to
prove the frozen engine's own cross-system composition (`DecompositionSystem`
@11.0 THEN `ControlRatioSystem` @12.0, called in that order every tick,
sharing ONE `TickContext.persistent_data`), which
`carceral-arc-conformance.bscn` + the concatenated `decomposition.bsl` +
`control-ratio.bsl` sources are the ported analogue of (`carceral_arc_
conformance.rs`'s own module doc explains the cross-pack BYTE-ORDER
INVERSION the port introduces and why it is benign here).

The world mirrors `decomposition-delay-conformance.bscn`'s DELAY-PATH LA
vector (wealth 515, strictly between `subsistence + 1*consumption` (510) and
`subsistence + 2*consumption` (520) — "approaching, not dying") plus
`control-ratio-conformance.bscn`'s prisoner/enforcer seeding, combined into
ONE five-class world so both packs' rules compose over the SAME nodes:

  la-approaching   LABOR_ARISTOCRACY, active, population 600, wealth 515 —
                    the delay-path trigger (SUPERWAGE_CRISIS at tick 1,
                    CLASS_DECOMPOSITION 52 ticks later).
  enforcer-seed    CARCERAL_ENFORCER, seeded INACTIVE, population 20,
                    wealth 100 — the BLOCKER-1 seeding obligation; becomes
                    active via the ADDITIVE p04 intake at the decomposition
                    fire tick.
  ip-seed          INTERNAL_PROLETARIAT, seeded INACTIVE, population 77,
                    wealth 33, organization 0.0 — becomes active via the
                    OVERWRITE p05 intake; organization is UNTOUCHED by
                    decomposition (p04/p05 never write it), so it stays 0.0
                    after intake — the "no organization" default outcome
                    vector.
  lumpen           LUMPENPROLETARIAT, active from tick 1, population 200,
                    organization 0.2 — the SECOND prisoner role, present
                    throughout so the prisoner census is never zero once
                    ip-seed activates.
  bourgeois        CORE_BOURGEOISIE, active — the non-participant vector for
                    BOTH packs.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" UV_FROZEN=1 uv run python \\
        rust/crates/babylon-tick/content/scenarios/carceral_arc_conformance.py
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.control_ratio import ControlRatioSystem
from babylon.engine.systems.decomposition import DecompositionSystem
from babylon.models.enums import NodeType, SocialRole
from babylon.topology.graph import BabylonGraph

#: The five social classes, in `carceral-arc-conformance.bscn`'s own
#: declaration order.
SOCIAL_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "la-approaching",
        {
            "role": SocialRole.LABOR_ARISTOCRACY,
            "active": True,
            "population": 600,
            "wealth": 515.0,
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

#: The tick range to run — comfortably past the derived TERMINAL_DECISION
#: tick (see the module doc's own arithmetic: 1 / 53 / 105 / 106), with a
#: small margin to prove no fifth event fires afterward.
MAX_TICK = 112


def build_graph() -> BabylonGraph:
    """Build the five-class world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SOCIAL_CLASSES:
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **attrs)
    return graph


def main() -> None:
    """Run the frozen DecompositionSystem then ControlRatioSystem for each
    tick in `1..=MAX_TICK`, sharing ONE `TickContext.persistent_data`
    (matching the frozen engine's own single `context` threaded through
    every system every tick), printing every event with its tick."""
    services = ServiceContainer.create()
    try:
        c = services.defines.carceral
        print("defines (src/babylon/data/defines.yaml, carceral: section, SHIPPED values):")
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
        print()

        graph = build_graph()
        context = TickContext(tick=1)
        decomposition = DecompositionSystem()
        control_ratio = ControlRatioSystem()

        milestones: dict[str, int] = {}
        for tick in range(1, MAX_TICK + 1):
            context.tick = tick
            services.event_bus.clear_history()

            decomposition.step(graph, services, context)
            control_ratio.step(graph, services, context)

            events = services.event_bus.get_history()
            for event in events:
                print(f"tick {tick}: {event.type} {event.payload!r}")
                milestones.setdefault(event.type, tick)

        print()
        print("milestone ticks (first occurrence):")
        for name in (
            "superwage_crisis",
            "class_decomposition",
            "control_ratio_crisis",
            "terminal_decision",
        ):
            print(f"  {name} = {milestones.get(name, 'NEVER FIRED')!r}")
        print()

        print(f"post-tick (tick {MAX_TICK}) social classes:")
        for node_id, seed in SOCIAL_CLASSES:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the session")
            a = node.attributes
            print(
                f"  {node_id:<15} active={a.get('active')!r} "
                f"population={a.get('population')!r} (seed {seed['population']!r}) "
                f"wealth={a.get('wealth')!r} (seed {seed['wealth']!r})"
            )
        print()

        print(f"post-tick (tick {MAX_TICK}) persistent_data:")
        for key in sorted(context.persistent_data):
            print(f"  {key} = {context.persistent_data[key]!r}")
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
