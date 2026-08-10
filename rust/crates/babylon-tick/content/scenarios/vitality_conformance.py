"""Conformance vectors for ``vitality/subsistence-and-death``, from the frozen engine.

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/vitality_conformance.rs``. It builds the six
social classes of ``vitality-conformance.bscn`` node for node, runs the frozen
``VitalitySystem`` once against them, and prints the post-tick state plus every
event the tick emitted.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/vitality_conformance.py

The frozen system is the contract source for STRUCTURE and ORDERING, not a
correctness oracle (ADR183). The fixture is chosen so that Grinding Attrition —
the phase the BSL pack does not port, see the ``.bsl`` header — kills nobody
here: every subject satisfies ``int(population * attrition_rate) == 0``. The
script asserts that, so a fixture edit that quietly made the un-ported phase
matter fails loudly instead of drifting the vectors.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.vitality import VitalitySystem
from babylon.formulas import calculate_mortality_rate
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

#: The six classes, in the declaration order of ``vitality-conformance.bscn``.
#: Every value here is an integer, which is the only lane slice 1's scenario
#: loader stores, so the two fixtures agree literally rather than by rounding.
SUBJECTS: list[tuple[str, dict[str, Any]]] = [
    (
        "core",
        {
            "active": True,
            "population": 100,
            "wealth": 1000,
            "subsistence_multiplier": 1,
            "s_bio": 1,
            "s_class": 1,
            "inequality": 0,
        },
    ),
    (
        "bourgeoisie",
        {
            "active": True,
            "population": 4,
            "wealth": 500,
            "subsistence_multiplier": 5,
            "s_bio": 2,
            "s_class": 8,
            "inequality": 0,
        },
    ),
    (
        "hermit",
        {
            "active": True,
            "population": 1,
            "wealth": 100,
            "subsistence_multiplier": 1,
            "s_bio": 1,
            "s_class": 1,
            "inequality": 0,
        },
    ),
    (
        "last-worker",
        {
            "active": True,
            "population": 1,
            "wealth": 1,
            "subsistence_multiplier": 1,
            "s_bio": 1,
            "s_class": 1,
            "inequality": 0,
        },
    ),
    (
        "remnant",
        {
            "active": True,
            "population": 1,
            "wealth": 0,
            "subsistence_multiplier": 1,
            "s_bio": 3,
            "s_class": 1,
            "inequality": 0,
        },
    ),
    (
        "dissolved",
        {
            "active": False,
            "population": 5,
            "wealth": 10,
            "subsistence_multiplier": 1,
            "s_bio": 1,
            "s_class": 1,
            "inequality": 0,
        },
    ),
]


def build_graph() -> BabylonGraph:
    """Build the six-class world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SUBJECTS:
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **attrs)
    return graph


def check_attrition_is_inert(services: ServiceContainer) -> None:
    """Assert the un-ported phase kills nobody in this fixture.

    Recomputes Grinding Attrition exactly as ``VitalitySystem`` would, on the
    POST-drain wealth, and refuses to emit vectors if any subject would lose a
    member. That is what lets the Rust test claim an exact match against the
    FULL frozen system rather than against a subset of it.
    """
    base = services.defines.economy.base_subsistence
    for node_id, attrs in SUBJECTS:
        if not attrs["active"] or attrs["population"] <= 0:
            continue
        population = attrs["population"]
        cost = (base * population) * attrs["subsistence_multiplier"]
        drained = max(0.0, attrs["wealth"] - cost)
        needs = attrs["s_bio"] + attrs["s_class"]
        rate = calculate_mortality_rate(
            wealth_per_capita=drained / population,
            subsistence_needs=needs,
            inequality=attrs["inequality"],
        )
        deaths = int(population * rate)
        if deaths:
            raise SystemExit(
                f"fixture drift: {node_id} loses {deaths} member(s) to Grinding "
                f"Attrition (rate {rate!r}). The BSL pack does not port that "
                f"phase, so a fixture where it fires cannot carry an exact "
                f"conformance vector."
            )
        print(f"  {node_id:<12} attrition_rate={rate!r} deaths={deaths}")


def main() -> None:
    """Run one tick of the frozen VitalitySystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        print("defines (src/babylon/data/defines.yaml):")
        print(f"  economy.base_subsistence = {services.defines.economy.base_subsistence!r}")
        print(f"  economy.death_threshold  = {services.defines.economy.death_threshold!r}")
        print()

        print("Grinding Attrition (the un-ported phase), verified inert here:")
        check_attrition_is_inert(services)
        print()

        graph = build_graph()
        VitalitySystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        print("post-tick state:")
        for node_id, _ in SUBJECTS:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<12} active={a['active']!r:<6} "
                f"population={a['population']!r:<4} wealth={a['wealth']!r}"
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
