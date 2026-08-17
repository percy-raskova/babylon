"""Conformance vectors for the `control-ratio/*` rule pack (Pack B, Material
Base @12.0), from the frozen engine.

This script is the PROVENANCE — the STRUCTURE and ORDERING oracle, NOT a
correctness oracle (ADR183) — for Task 5 of the Decomposition+ControlRatio
port train (`docs/superpowers/plans/2026-08-17-decomposition-controlratio-
port.md`). It builds the four `control-ratio-*-conformance.bscn` worlds node
for node, pre-seeds a `TickContext` whose `persistent_data` carries only the
frozen coupling key (`_class_decomposition_tick = 0` — the "post-decomposition
carrier state, seeded directly" design §5 requires so a zero
`control_ratio_delay` is safe with no co-loaded `decomposition/*` pack), runs
the frozen `ControlRatioSystem` (@12.0) for one `step()` against each with
`carceral.control_ratio_delay`/`carceral.terminal_decision_delay` overridden
to 0 (matching every `.bscn` sibling's own `defconst` companion-variation),
and prints the post-tick census plus the full event history.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" UV_FROZEN=1 uv run python \\
        rust/crates/babylon-tick/content/scenarios/control_ratio_conformance.py

Task 5 ships only `c01`/`c02` (the unconditional census publication) — no
`c03`/`c04` BSL rule exists yet, so this run's own `CONTROL_RATIO_CRISIS`/
`TERMINAL_DECISION` events (fired by the FROZEN engine, which has no
Task-boundary) are printed for completeness and for Tasks 6-7's own future
provenance, but this task's Rust tests assert only against the census
numbers (`_count_enforcer_population`/`_count_prisoner_population_and_org`'s
own outputs), which is all `c01`/`c02` compute.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import CarceralDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.control_ratio import (
    ControlRatioSystem,
    _count_enforcer_population,
    _count_prisoner_population_and_org,
)
from babylon.models.enums import NodeType, SocialRole
from babylon.topology.graph import BabylonGraph

#: `control_ratio_delay`/`terminal_decision_delay` overridden to 0 — every
#: `.bscn` sibling's own `defconst` companion-variation (§5's "MAY vary a
#: delay/fraction to make a branch reachable at tick 1"); `control_capacity`/
#: `revolution_threshold` stay at their shipped defaults (4 / 0.5,
#: `defines.yaml:294,297`).
BYPASS_DEFINES = CarceralDefines(control_ratio_delay=0, terminal_decision_delay=0)

#: The six social classes of `control-ratio-conformance.bscn` (primary,
#: GENOCIDE) and `control-ratio-revolution-conformance.bscn` (identical
#: except `organization`), in declaration order.
PRIMARY_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "enforcer-active",
        {
            "role": SocialRole.CARCERAL_ENFORCER,
            "active": True,
            "population": 10,
            "organization": 0.0,
        },
    ),
    (
        "enforcer-inactive",
        {
            "role": SocialRole.CARCERAL_ENFORCER,
            "active": False,
            "population": 999,
            "organization": 0.0,
        },
    ),
    (
        "prisoner-ip",
        {
            "role": SocialRole.INTERNAL_PROLETARIAT,
            "active": True,
            "population": 30,
            "organization": 0.2,
        },
    ),
    (
        "prisoner-lumpen",
        {
            "role": SocialRole.LUMPENPROLETARIAT,
            "active": True,
            "population": 20,
            "organization": 0.2,
        },
    ),
    (
        "prisoner-inactive",
        {
            "role": SocialRole.INTERNAL_PROLETARIAT,
            "active": False,
            "population": 888,
            "organization": 0.9,
        },
    ),
    (
        "bourgeois",
        {
            "role": SocialRole.CORE_BOURGEOISIE,
            "active": True,
            "population": 50,
            "organization": 0.0,
        },
    ),
]

#: `control-ratio-revolution-conformance.bscn` — identical to
#: `PRIMARY_CLASSES` except the two active prisoner nodes' `organization`
#: (0.2 -> 0.6).
REVOLUTION_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        node_id,
        {**attrs, "organization": 0.6}
        if node_id in ("prisoner-ip", "prisoner-lumpen")
        else dict(attrs),
    )
    for node_id, attrs in PRIMARY_CLASSES
]

#: `control-ratio-within-capacity-conformance.bscn` — prisoner population
#: (20 + 20 = 40) EXACTLY at `enforcer_pop (10) * control_capacity (4)` = 40,
#: the `<=` boundary — no crisis.
WITHIN_CAPACITY_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "enforcer",
        {
            "role": SocialRole.CARCERAL_ENFORCER,
            "active": True,
            "population": 10,
            "organization": 0.0,
        },
    ),
    (
        "prisoner-ip",
        {
            "role": SocialRole.INTERNAL_PROLETARIAT,
            "active": True,
            "population": 20,
            "organization": 0.3,
        },
    ),
    (
        "prisoner-lumpen",
        {
            "role": SocialRole.LUMPENPROLETARIAT,
            "active": True,
            "population": 20,
            "organization": 0.3,
        },
    ),
]

#: `control-ratio-zero-enforcer-conformance.bscn` — BLOCKER-4's branch:
#: `enforcer`'s `population` is seeded 0 (a real, active, empty
#: CARCERAL_ENFORCER class, not the absence of one).
ZERO_ENFORCER_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "enforcer",
        {
            "role": SocialRole.CARCERAL_ENFORCER,
            "active": True,
            "population": 0,
            "organization": 0.0,
        },
    ),
    (
        "prisoner-ip",
        {
            "role": SocialRole.INTERNAL_PROLETARIAT,
            "active": True,
            "population": 15,
            "organization": 0.4,
        },
    ),
    (
        "prisoner-lumpen",
        {
            "role": SocialRole.LUMPENPROLETARIAT,
            "active": True,
            "population": 10,
            "organization": 0.4,
        },
    ),
]

#: Task 7 (`c04-terminal`, ADR070-RESERVED) ad-hoc fixture #1 — the exact
#: `>=` boundary the frozen `TestControlRatioMutationKillers` class itself
#: targets: `organization` exactly 0.5 on both active prisoner nodes (same
#: population split as `PRIMARY_CLASSES`/`REVOLUTION_CLASSES`, 30 + 20),
#: giving a population-weighted average of EXACTLY 0.5 — AT the threshold,
#: which must route to REVOLUTION (`>=`, not `>`).
EXACT_THRESHOLD_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "enforcer",
        {
            "role": SocialRole.CARCERAL_ENFORCER,
            "active": True,
            "population": 10,
            "organization": 0.0,
        },
    ),
    (
        "prisoner-ip",
        {
            "role": SocialRole.INTERNAL_PROLETARIAT,
            "active": True,
            "population": 30,
            "organization": 0.5,
        },
    ),
    (
        "prisoner-lumpen",
        {
            "role": SocialRole.LUMPENPROLETARIAT,
            "active": True,
            "population": 20,
            "organization": 0.5,
        },
    ),
]

#: Task 7 ad-hoc fixture #2 — the intensive-aggregation guard
#: (`the_avg_organization_is_population_weighted_not_a_bare_mean`): a SMALL
#: population at HIGH organization (5 @ 0.9) and a LARGE population at LOWER
#: organization (95 @ 0.4). The population-weighted average is
#: (5*0.9 + 95*0.4) / 100 = 0.425 -> GENOCIDE; the UNWEIGHTED bare mean of
#: the two organization values, (0.9 + 0.4) / 2 = 0.65, would route
#: REVOLUTION instead — proving the routing decision depends on the
#: population-weighted computation, not a bare mean of per-class values.
POPULATION_WEIGHTED_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "enforcer",
        {
            "role": SocialRole.CARCERAL_ENFORCER,
            "active": True,
            "population": 10,
            "organization": 0.0,
        },
    ),
    (
        "prisoner-ip",
        {
            "role": SocialRole.INTERNAL_PROLETARIAT,
            "active": True,
            "population": 5,
            "organization": 0.9,
        },
    ),
    (
        "prisoner-lumpen",
        {
            "role": SocialRole.LUMPENPROLETARIAT,
            "active": True,
            "population": 95,
            "organization": 0.4,
        },
    ),
]

WORLDS: list[tuple[str, list[tuple[str, dict[str, Any]]]]] = [
    ("control-ratio-conformance (PRIMARY, genocide)", PRIMARY_CLASSES),
    ("control-ratio-revolution-conformance", REVOLUTION_CLASSES),
    ("control-ratio-within-capacity-conformance", WITHIN_CAPACITY_CLASSES),
    ("control-ratio-zero-enforcer-conformance", ZERO_ENFORCER_CLASSES),
    ("control-ratio-exact-threshold (Task 7 ad-hoc #1)", EXACT_THRESHOLD_CLASSES),
    ("control-ratio-population-weighted (Task 7 ad-hoc #2)", POPULATION_WEIGHTED_CLASSES),
]


def build_graph(classes: list[tuple[str, dict[str, Any]]]) -> BabylonGraph:
    """Build a world's social classes, in its own scenario's declaration order.

    Mirrors `decomposition_conformance.py::build_graph`'s own note: the BSL
    scenario also mints a `carceral-register` `INSTITUTION` carrier node
    (§2's reformulation); the frozen engine has no graph-node counterpart for
    `persistent_data` at all, so this mirror builds none.
    """
    graph = BabylonGraph()
    for node_id, attrs in classes:
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **attrs)
    return graph


def main() -> None:
    """Run one tick of the frozen ControlRatioSystem against all four worlds."""
    services = ServiceContainer.create()
    try:
        object.__setattr__(services.defines, "carceral", BYPASS_DEFINES)
        c = services.defines.carceral
        print("defines (src/babylon/data/defines.yaml, carceral: section, delays OVERRIDDEN to 0):")
        for name in (
            "control_capacity",
            "revolution_threshold",
            "control_ratio_delay",
            "terminal_decision_delay",
        ):
            print(f"  carceral.{name} = {getattr(c, name)!r}")
        print()

        for label, classes in WORLDS:
            print(f"=== {label} ===")
            services.event_bus.clear_history()
            graph = build_graph(classes)

            # The census math directly (§2's own two-step design: sum first,
            # divide second — NOT a weighted-mean fold), independent of the
            # gated step() below, so this task's own c01/c02 numbers are
            # provenanced even though the frozen step() may return early
            # before printing anything else interesting for this world.
            enforcer_pop = _count_enforcer_population(graph)
            prisoner_pop, prisoner_org_sum = _count_prisoner_population_and_org(graph)
            print(
                f"  census: enforcer_population={enforcer_pop!r} "
                f"prisoner_population={prisoner_pop!r} "
                f"prisoner_org_weighted_sum={prisoner_org_sum!r}"
            )

            context = TickContext(tick=1)
            context.persistent_data["_class_decomposition_tick"] = 0
            ControlRatioSystem().step(graph, services, context)

            print("  post-tick persistent_data:")
            for key in sorted(context.persistent_data):
                print(f"    {key} = {context.persistent_data[key]!r}")

            events = services.event_bus.get_history()
            print("  events:")
            for event in events:
                print(f"    {event.type} {event.payload!r}")
            if not events:
                print("    (none)")
            print()
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
