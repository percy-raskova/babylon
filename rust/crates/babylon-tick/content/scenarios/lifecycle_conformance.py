"""Conformance vectors for the ``lifecycle/*`` rule pack, from the frozen engine.

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/lifecycle_conformance.rs``. It builds the
four territories of ``lifecycle-conformance.bscn`` node for node, runs the
frozen ``LifecycleSystem`` once against them, and prints the post-tick state
plus every event the tick emitted.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/lifecycle_conformance.py

The frozen system is the contract source for STRUCTURE and ORDERING, not a
correctness oracle (ADR183). This pack ports three of the frozen system's
five flat rules (DPD population flow, legitimation index + crisis/recovery,
ideology transmission) — see the ``.bsl`` header for exactly why inheritance
flow and class mobility do not land (director-gate #492, the domain-beyond-
[0,1] construct gap). Unlike Vitality, the un-ported computations here are
STRUCTURALLY isolated, not just fixture-conditionally inert: inheritance
flow writes no graph state at all (event-emission only), and class
mobility's outputs (``adjusted_p_to_d_prime``, ``differential_p_to_d_prime``)
are never read back into ``compute_transitions`` on a later tick (which
reads ``dpd_state.rate_p_to_d_prime``, not the differential field) — so no
fixture envelope is required to keep them from perturbing the ported
fields.

D-5 (see ``.bsl`` header): the frozen engine's crisis/recovery edge check
compares a lowercase ``StrEnum.value`` against the literal ``"CRISIS"``,
which never matches — LEGITIMATION_CRISIS re-fires every tick a territory
is classified CRISIS (not edge-triggered) and LEGITIMATION_RECOVERY is dead
code. This script prints the frozen engine's ACTUAL (buggy) event output
for the record; the Rust conformance test asserts the pack's DELIBERATELY
DIFFERENT, edge-triggered behavior for those two event types only, per the
documented §5.4 repair. Every state field below matches the frozen engine
exactly regardless.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.lifecycle import LifecycleSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

#: The four territories, in the declaration order of
#: lifecycle-conformance.bscn. ``dpd_state`` is supplied explicitly (rather
#: than left absent for lazy defines-derived initialization) so this script
#: can set exactly the pop_d/pop_p/pop_d_prime/wealth_d_prime/rate seeds the
#: .bscn declares, matching them value for value instead of going through
#: the initial_pop_*_frac branch. The four rate fields inside dpd_state are
#: the same values this pack's :const bindings carry
#: (src/babylon/data/defines.yaml:508-511). ``legitimation_state``,
#: ``caregiver_ideology``, ``institutional_hegemony`` and
#: ``community_tendency`` are left ABSENT so the frozen system falls into
#: its defines-derived defaults — matching this pack's D-1 modeling choice
#: (those five/two values never diverge from the defines defaults in the
#: live engine either, per the .bsl header's grep-verified claim).
RATES: dict[str, float] = {
    "rate_d_to_p": 0.0556,
    "rate_p_to_d_prime": 0.0213,
    "rate_d_prime_to_death": 0.039,
    "birth_rate": 0.0107,
}

SUBJECTS: list[tuple[str, dict[str, Any]]] = [
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

#: This pack's own crisis-classification encoding (see the .bsl header):
#: 0 = STABLE, 1 = UNSTABLE, 2 = CRISIS.
CRISIS_CODE = {"stable": 0, "unstable": 1, "crisis": 2}


def build_graph() -> BabylonGraph:
    """Build the four-territory world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SUBJECTS:
        graph.add_node(node_id, NodeType.TERRITORY, **attrs)
    return graph


def main() -> None:
    """Run one tick of the frozen LifecycleSystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        d = services.defines.lifecycle
        print("defines (src/babylon/data/defines.yaml, lifecycle: section):")
        for name in (
            "birth_rate",
            "rate_d_to_p",
            "rate_p_to_d_prime",
            "rate_d_prime_to_death",
            "pension_coverage_rate",
            "home_ownership_rate",
            "ss_replacement_rate",
            "healthcare_security",
            "retirement_confidence",
            "legit_w_home_ownership",
            "legit_w_healthcare_security",
            "legit_w_retirement_confidence",
            "legit_w_pension_coverage",
            "legit_w_ss_replacement",
            "legitimation_crisis_threshold",
            "legitimation_unstable_threshold",
            "ideology_caregiver_weight",
            "ideology_institutional_weight",
            "ideology_regression_coefficient",
        ):
            print(f"  lifecycle.{name} = {getattr(d, name)!r}")
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
