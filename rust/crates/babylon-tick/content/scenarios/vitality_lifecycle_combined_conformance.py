"""Conformance vectors for ``vitality`` + ``lifecycle`` run TOGETHER, from
the frozen engine (Program 28 B2, Phase A Task 5).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/multi_rule_conformance.rs``. It builds ONE
ten-node world (the union of ``vitality-conformance.bscn``'s six social
classes and ``lifecycle-conformance.bscn``'s four territories, values
transcribed byte-for-byte from both scripts) and runs the frozen
``VitalitySystem`` and ``LifecycleSystem`` against it TWICE, on two
independently-built copies of the same state: once in the frozen engine's
own tick-position order (Vitality @1, then Lifecycle @7 — "engine order"),
and once in the REVERSE order (Lifecycle, then Vitality — the order the
Rust driver actually runs in, since it sorts by ascending rule-id byte
order, and ``'l' < 'v'``).

The two runs' post-tick fields are compared field-for-field. They must
match EXACTLY, because this is the empirical proof (not just an inference
from reading the bindings) that the two rules' domains are disjoint:
``VitalitySystem`` touches only ``social-class/*`` fields,
``LifecycleSystem`` touches only ``territory/*`` fields, so which one runs
first cannot matter. If the two runs ever disagree, the disjoint-domain
premise this whole task's byte-order-is-safe-here argument rests on is
false, and this script exits loudly rather than printing vectors that
would silently paper over that.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/vitality_lifecycle_combined_conformance.py
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.lifecycle import LifecycleSystem
from babylon.engine.systems.vitality import VitalitySystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

#: The four territories, values transcribed byte-for-byte from
#: lifecycle_conformance.py's own SUBJECTS/RATES.
RATES: dict[str, float] = {
    "rate_d_to_p": 0.0556,
    "rate_p_to_d_prime": 0.0213,
    "rate_d_prime_to_death": 0.039,
    "birth_rate": 0.0107,
}

TERRITORY_SUBJECTS: list[tuple[str, dict[str, Any]]] = [
    (
        "core-county",
        {
            "dpd_state": {
                "pop_d": 2150.0,
                "pop_p": 6050.0,
                "pop_d_prime": 1800.0,
                "wealth_d_prime": 10_000_000.0,
                **RATES,
            },
            "legitimation_crisis": "stable",
        },
    ),
    (
        "growing-county",
        {
            "dpd_state": {
                "pop_d": 3000.0,
                "pop_p": 5000.0,
                "pop_d_prime": 1500.0,
                "wealth_d_prime": 5_000_000.0,
                **RATES,
            },
            "legitimation_crisis": "unstable",
        },
    ),
    (
        "recovering-county",
        {
            "dpd_state": {
                "pop_d": 2000.0,
                "pop_p": 7000.0,
                "pop_d_prime": 2000.0,
                "wealth_d_prime": 20_000_000.0,
                **RATES,
            },
            "legitimation_crisis": "crisis",
        },
    ),
    (
        "young-county",
        {
            "dpd_state": {
                "pop_d": 4000.0,
                "pop_p": 5500.0,
                "pop_d_prime": 0.0,
                "wealth_d_prime": 0.0,
                **RATES,
            },
            "legitimation_crisis": "stable",
        },
    ),
]

#: The six social classes, values transcribed byte-for-byte from
#: vitality_conformance.py's own SUBJECTS.
SOCIAL_CLASS_SUBJECTS: list[tuple[str, dict[str, Any]]] = [
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

#: This pack's own crisis-classification encoding (see lifecycle.bsl's
#: header): 0 = STABLE, 1 = UNSTABLE, 2 = CRISIS.
CRISIS_CODE = {"stable": 0, "unstable": 1, "crisis": 2}


def build_graph() -> BabylonGraph:
    """Build the ten-node world: four territories, six social classes."""
    graph = BabylonGraph()
    for node_id, attrs in TERRITORY_SUBJECTS:
        graph.add_node(node_id, NodeType.TERRITORY, **attrs)
    for node_id, attrs in SOCIAL_CLASS_SUBJECTS:
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **attrs)
    return graph


def territory_vector(graph: BabylonGraph, node_id: str) -> dict[str, Any]:
    """The post-tick territory fields this pack's Rust rule also writes."""
    node = graph.get_node(node_id)
    if node is None:
        raise SystemExit(f"node {node_id} vanished during the tick")
    a = node.attributes
    dpd = a["dpd_state"]
    crisis_str = a["legitimation_crisis"]
    return {
        "pop_d": dpd["pop_d"],
        "pop_p": dpd["pop_p"],
        "pop_d_prime": dpd["pop_d_prime"],
        "wealth_d_prime": dpd["wealth_d_prime"],
        "dependency_ratio": a["dependency_ratio"],
        "legitimation_index": a["legitimation_index"],
        "legitimation_crisis_code": CRISIS_CODE[crisis_str],
        "transmitted_ideology": a["transmitted_ideology"],
    }


def social_class_vector(graph: BabylonGraph, node_id: str) -> dict[str, Any]:
    """The post-tick social-class fields this pack's Rust rule also writes."""
    node = graph.get_node(node_id)
    if node is None:
        raise SystemExit(f"node {node_id} vanished during the tick")
    a = node.attributes
    return {
        "active": a["active"],
        "population": a["population"],
        "wealth": a["wealth"],
    }


def run(services: ServiceContainer, *, lifecycle_first: bool) -> dict[str, dict[str, Any]]:
    """Run one tick against a FRESH ten-node graph, in the requested order.

    Returns every node's post-tick vector, keyed by node id.
    """
    graph = build_graph()
    ctx = TickContext(tick=1)
    if lifecycle_first:
        LifecycleSystem().step(graph, services, ctx)
        VitalitySystem().step(graph, services, ctx)
    else:
        VitalitySystem().step(graph, services, ctx)
        LifecycleSystem().step(graph, services, ctx)

    vectors: dict[str, dict[str, Any]] = {}
    for node_id, _ in TERRITORY_SUBJECTS:
        vectors[node_id] = territory_vector(graph, node_id)
    for node_id, _ in SOCIAL_CLASS_SUBJECTS:
        vectors[node_id] = social_class_vector(graph, node_id)
    return vectors


def main() -> None:
    """Run both orderings, diff them, and print the agreed vectors."""
    services = ServiceContainer.create()
    try:
        engine_order = run(services, lifecycle_first=False)
        reverse_order = run(services, lifecycle_first=True)

        print("disjoint-domain check (engine order vs. reverse order):")
        mismatches = []
        for node_id in engine_order:
            if engine_order[node_id] != reverse_order[node_id]:
                mismatches.append(node_id)
                print(f"  MISMATCH {node_id}:")
                print(f"    engine order:  {engine_order[node_id]!r}")
                print(f"    reverse order: {reverse_order[node_id]!r}")
        if mismatches:
            raise SystemExit(
                f"disjoint-domain premise is FALSE for: {mismatches!r} — "
                "the byte-order-is-safe-here argument does not hold for "
                "this pair; STOP and revisit the Multi-Rule Decision "
                "section rather than proceeding."
            )
        print("  MATCH — every node's post-tick vector is order-invariant.")
        print()

        print("post-tick state (either order — proven identical above):")
        for node_id, _ in TERRITORY_SUBJECTS:
            v = engine_order[node_id]
            print(
                f"  {node_id:<18} pop_d={v['pop_d']!r} pop_p={v['pop_p']!r} "
                f"pop_d_prime={v['pop_d_prime']!r} "
                f"wealth_d_prime={v['wealth_d_prime']!r} "
                f"dependency_ratio={v['dependency_ratio']!r} "
                f"legitimation_index={v['legitimation_index']!r} "
                f"legitimation_crisis={v['legitimation_crisis_code']} "
                f"transmitted_ideology={v['transmitted_ideology']!r}"
            )
        for node_id, _ in SOCIAL_CLASS_SUBJECTS:
            v = engine_order[node_id]
            print(
                f"  {node_id:<18} active={v['active']!r:<6} "
                f"population={v['population']!r:<4} wealth={v['wealth']!r}"
            )
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
