"""Conformance vectors for the DISCRIMINATING `:const` environment, from the
frozen engine — companion to ``lifecycle_conformance.py``.

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/lifecycle_crisis_conformance.rs``. It runs
the frozen ``LifecycleSystem`` against a `:const` environment DIFFERENT from
`defines.yaml`'s shipped values — see
``content/scenarios/lifecycle-crisis-conformance.bscn``'s header for why:
under the shipped defaults, the legitimation index is the same 0.6039 for
every subject and `caregiver-ideology-default`/`institutional-hegemony-
default` are both 0.5, so neither the crisis-classification ladder's CRISIS
branch nor the ideology weights are exercised by ``lifecycle_conformance.py``
alone (an adversarial review of PR #493 caught this: two mutations — an
ideology-weight swap, and collapsing the classification ladder to a
constant — passed the original 8-test suite unnoticed).

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/lifecycle_crisis_conformance.py

Frozen system = contract source for STRUCTURE and ORDERING, not a
correctness oracle (ADR183). D-5 (see the `.bsl` header) applies here too:
`already-crisis` is seeded PRE-crisis `"crisis"` and stays classified
CRISIS this tick, so under a CORRECT edge-triggered check
`LEGITIMATION_CRISIS` must NOT re-fire for it — but the frozen engine's
broken comparison (`prev_crisis != "CRISIS"`, comparing a lowercase
`StrEnum.value` against the uppercase literal) fires it anyway, every tick,
for every CRISIS-classified subject regardless of the previous state. This
script prints the frozen engine's ACTUAL (buggy, over-firing) event output
for the record; the Rust test asserts the pack's deliberately different,
correctly edge-triggered behavior, per the documented §5.4 repair.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.lifecycle import LifecycleSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

RATES: dict[str, float] = {
    "rate_d_to_p": 0.0556,
    "rate_p_to_d_prime": 0.0213,
    "rate_d_prime_to_death": 0.039,
    "birth_rate": 0.0107,
}

#: The DISCRIMINATING legitimation_state — NOT `defines.yaml`'s shipped
#: values. All five components lowered to 0.1 so the weighted index
#: (weights unchanged, still summing to 1.0) is 0.1, below
#: legitimation_crisis_threshold (0.3).
LEGITIMATION_STATE: dict[str, float] = {
    "pension_coverage": 0.1,
    "ss_replacement_rate": 0.1,
    "healthcare_security": 0.1,
    "home_ownership_rate": 0.1,
    "retirement_confidence": 0.1,
}

SUBJECTS: list[tuple[str, dict[str, Any]]] = [
    (
        "entering-crisis",
        {
            "dpd_state": {
                "pop_d": 2150.0,
                "pop_p": 6050.0,
                "pop_d_prime": 1800.0,
                "wealth_d_prime": 10_000_000.0,
                **RATES,
            },
            "legitimation_state": dict(LEGITIMATION_STATE),
            "legitimation_crisis": "stable",
        },
    ),
    (
        "already-crisis",
        {
            "dpd_state": {
                "pop_d": 3000.0,
                "pop_p": 5000.0,
                "pop_d_prime": 1500.0,
                "wealth_d_prime": 5_000_000.0,
                **RATES,
            },
            "legitimation_state": dict(LEGITIMATION_STATE),
            "legitimation_crisis": "crisis",
        },
    ),
]

#: This pack's own crisis-classification encoding (see the .bsl header):
#: 0 = STABLE, 1 = UNSTABLE, 2 = CRISIS.
CRISIS_CODE = {"stable": 0, "unstable": 1, "crisis": 2}


def build_graph() -> BabylonGraph:
    """Build the two-territory world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SUBJECTS:
        graph.add_node(node_id, NodeType.TERRITORY, **attrs)
    return graph


def main() -> None:
    """Run one tick of the frozen LifecycleSystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        # Monkeypatch the ideology defaults the same way `:const`
        # `lifecycle/caregiver-ideology-default`/
        # `institutional-hegemony-default` do — those two values have no
        # `defines.yaml` backing at all (D-2), so LifecycleSystem reads a
        # bare Python literal (`0.5`) that no ServiceContainer field can
        # override. Reading the exact worked example off the frozen
        # `compute_ideology_transmission` doctest instead:
        # `formulas/lifecycle.py:189-194` (`caregiver_ideology=0.3,
        # institutional_hegemony=0.8`).
        import babylon.engine.systems.lifecycle as lifecycle_module

        original_step = lifecycle_module.LifecycleSystem.step

        def patched_step(self: Any, graph: Any, services: Any, context: Any) -> None:  # noqa: ANN401
            for node in graph.query_nodes(node_type=NodeType.TERRITORY):
                graph.update_node(node.id, caregiver_ideology=0.3, institutional_hegemony=0.8)
            original_step(self, graph, services, context)

        lifecycle_module.LifecycleSystem.step = patched_step  # type: ignore[method-assign]

        d = services.defines.lifecycle
        print("defines used (deliberately DISCRIMINATING, not defines.yaml's shipped values):")
        print(f"  legitimation_state components = {LEGITIMATION_STATE!r}")
        print("  caregiver_ideology = 0.3, institutional_hegemony = 0.8 (doctest example)")
        print(f"  lifecycle.legitimation_crisis_threshold = {d.legitimation_crisis_threshold!r}")
        print(f"  lifecycle.ideology_caregiver_weight = {d.ideology_caregiver_weight!r}")
        print(f"  lifecycle.ideology_institutional_weight = {d.ideology_institutional_weight!r}")
        print(
            f"  lifecycle.ideology_regression_coefficient = {d.ideology_regression_coefficient!r}"
        )
        print()

        graph = build_graph()
        LifecycleSystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        print("post-tick state:")
        for node_id, _ in SUBJECTS:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            dpd = a["dpd_state"]
            crisis_str = a["legitimation_crisis"]
            print(
                f"  {node_id:<18} "
                f"pop_d={dpd['pop_d']!r} pop_p={dpd['pop_p']!r} "
                f"pop_d_prime={dpd['pop_d_prime']!r} "
                f"wealth_d_prime={dpd['wealth_d_prime']!r} "
                f"dependency_ratio={a['dependency_ratio']!r} "
                f"legitimation_index={a['legitimation_index']!r} "
                f"legitimation_crisis={crisis_str!r} (code={CRISIS_CODE[crisis_str]}) "
                f"transmitted_ideology={a['transmitted_ideology']!r}"
            )
        print()

        print("events (frozen engine's ACTUAL output, D-5 bug included):")
        for event in events:
            print(f"  {event.type} {event.payload!r}")
        if not events:
            print("  (none)")
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
