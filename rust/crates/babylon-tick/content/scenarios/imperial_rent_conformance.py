"""Frozen-mirror provenance for `imperial-rent-conformance.bscn` (world 1) —
the ImperialRent BSL port train (Material Base @9.0, Checkpoint A campaign;
plan `docs/superpowers/plans/2026-08-18-imperialrent-port.md`, §9's
canonical mirror recipe). This is the STRUCTURE and ORDERING oracle, NOT a
correctness oracle (ADR183) — later Rust-side pins measure their own
expecteds from the BSL engine itself, cross-checked BY HAND against this
mirror's printed values, never copied byte-for-byte.

Builds the five social classes + one `imperial-rent-register` carrier of
`imperial-rent-conformance.bscn` node for node and edge for edge, runs one
`ImperialRentSystem().step()` against them, and prints every vector Task 1's
brief names: the `economy:` defines block, the per-node post-tick
`wealth`/`effective_wealth`/`unearned_increment`/`ppp_multiplier`/`w_paid`/
`v_produced`, every edge's `value_flow`, the post-tick `economy` graph
attribute, and the full event history.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" UV_FROZEN=1 uv run python \\
        rust/crates/babylon-tick/content/scenarios/imperial_rent_conformance.py

Three header facts (plan §9's own discipline — the easiest places to
mis-read this oracle):

(a) **No boundary register is bound.** `ServiceContainer.create()` below is
    called with no `persistence`/register argument, so `services.
    boundary_register` is `None` (BLOCKER-6) — the L-RECEIPTS `if rent > 0.0
    and register is not None and register.session_id is not None:` guard in
    `_process_extraction_phase` (`economic.py:311`) short-circuits on the
    `None` check alone, a pure no-op. `context.persistent_data` is `{}`
    (D192, `TickContext`'s own default) — none of the two spec-063 sub-stages
    (`economic.py:88-156,158-199`) find their required keys, so both are
    silent no-ops too. The stdout below shows this no-op path throughout.
(b) **The printed `economy` is ALREADY DECAYED.** `_save_economy`
    (`economic.py:827-836`) applies `rent_pool_decay` whenever `services is
    not None` — which it always is here — so the post-tick `economy` this
    script prints corresponds to what a later `r09-pool-decay` rule's output
    should match, NOT `r07`'s (the pre-decay pool after wages/subsidy
    outflow).
(c) **`opposition_states` is deliberately elided to `{"gap": ...}`.**
    `_calculate_aggregate_tension` (`economic.py:752-780`) does raw
    `.get()`s with no `model_validate` against the full `OppositionState`
    shape (`domain/dialectics/core/opposition.py:275-297`) — this mirror
    seeds only the sub-shape the reader actually touches, which is
    behaviorally exact for THIS system, and this note records what was left
    out so a later reader is not surprised by the gap.

World 1 is the "all four phases, NO_CHANGE" primary — Phase 4 (Subsidy) is
Director-RESERVED (Constitution IX.5, plan §6) and never runs; no
`CLIENT_STATE` edge exists in this fixture, so `_process_subsidy_phase`'s own
loop is trivially empty regardless.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.enums import EdgeType, NodeType, SocialRole
from babylon.topology.graph import BabylonGraph

#: The five social classes, in the declaration order of
#: `imperial-rent-conformance.bscn`. `revolutionary` (the BSL-side field,
#: B7's re-point target) has no direct frozen counterpart on the node
#: itself — the frozen engine reads consciousness through
#: `class_consciousness_from_node`'s `ideology.class_consciousness` sub-dict
#: (`kernel/node_access.py:15-37`), seeded separately below via the `ideology`
#: attribute, not through this table.
SOCIAL_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "core-bourgeoisie",
        {
            "role": SocialRole.CORE_BOURGEOISIE,
            "active": True,
            "wealth": 10000.0,
            "production_value": 0.0,
        },
    ),
    (
        "periphery-worker",
        {
            "role": SocialRole.PERIPHERY_PROLETARIAT,
            "active": True,
            "wealth": 500.0,
            "production_value": 0.0,
        },
    ),
    (
        "comprador",
        {
            "role": SocialRole.COMPRADOR_BOURGEOISIE,
            "active": True,
            "wealth": 800.0,
            "production_value": 0.0,
        },
    ),
    (
        "labor-aristocracy",
        {
            "role": SocialRole.LABOR_ARISTOCRACY,
            "active": True,
            "wealth": 300.0,
            "production_value": 40.0,
        },
    ),
    (
        "petty-b",
        {
            "role": SocialRole.PETTY_BOURGEOISIE,
            "active": True,
            "wealth": 250.0,
            "production_value": 0.0,
        },
    ),
]

#: `class_consciousness_from_node`'s own `ideology.class_consciousness`
#: seed — only `periphery-worker` carries a non-zero value (the `.bscn`'s
#: `revolutionary 0.2p`, B7's re-point target); every other class is
#: implicitly `0.0` (the accessor's own absent-key default), so this mirror
#: seeds `periphery-worker` explicitly and leaves the rest unset.
IDEOLOGY_SEEDS: dict[str, float] = {"periphery-worker": 0.2}

#: EXPLOITATION (periphery-worker -> core-bourgeoisie), TRIBUTE (comprador ->
#: core-bourgeoisie), WAGES (core-bourgeoisie -> labor-aristocracy) — the
#: `.bscn`'s own three edges, in the same declaration order.
EDGES: list[tuple[str, str, Any]] = [
    ("periphery-worker", "core-bourgeoisie", EdgeType.EXPLOITATION),
    ("comprador", "core-bourgeoisie", EdgeType.TRIBUTE),
    ("core-bourgeoisie", "labor-aristocracy", EdgeType.WAGES),
]


def build_graph() -> BabylonGraph:
    """Build the five-class, three-edge world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SOCIAL_CLASSES:
        seed = dict(attrs)
        if node_id in IDEOLOGY_SEEDS:
            seed["ideology"] = {"class_consciousness": IDEOLOGY_SEEDS[node_id]}
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **seed)
    for source, target, edge_type in EDGES:
        graph.add_edge(source, target, edge_type, value_flow=0.0)
    return graph


def main() -> None:
    """Run one tick of the frozen `ImperialRentSystem` and print every vector."""
    services = ServiceContainer.create()
    try:
        e = services.defines.economy
        t = services.defines.timescale
        print("defines (src/babylon/data/defines.yaml, economy: section):")
        for name in (
            "extraction_efficiency",
            "comprador_cut",
            "super_wage_rate",
            "superwage_multiplier",
            "superwage_ppp_impact",
            "initial_rent_pool",
            "pool_high_threshold",
            "pool_low_threshold",
            "pool_critical_threshold",
            "min_wage_rate",
            "max_wage_rate",
            "negligible_rent",
            "trpf_coefficient",
            "rent_pool_decay",
            "bribery_wage_delta",
            "austerity_wage_delta",
            "iron_fist_repression_delta",
            "crisis_wage_delta",
            "crisis_repression_delta",
            "bribery_tension_threshold",
            "iron_fist_tension_threshold",
            "trpf_efficiency_floor",
        ):
            print(f"  economy.{name} = {getattr(e, name)!r}")
        print(f"  timescale.weeks_per_year = {t.weeks_per_year!r}")
        print()

        graph = build_graph()

        # §9's canonical preamble — world 1's own seed row: pool 100.0, wage
        # rate 0.2, repression 0.5 (matching the frozen `_load_economy`
        # fallback exactly, per the dossier's world-1 correction), and the
        # gap 0.0 non-binding control.
        graph.set_graph_attr(
            "economy",
            GlobalEconomy(
                imperial_rent_pool=100.0,
                current_super_wage_rate=0.2,
                current_repression_level=0.5,
            ).model_dump(),
        )
        graph.set_graph_attr("la_production", {"labor-aristocracy": 40.0})
        graph.set_graph_attr("opposition_states", {"capital_labor": {"gap": 0.0}})

        context = TickContext(tick=1)
        print(f"context.persistent_data (pre-tick) = {context.persistent_data!r}")
        print(f"services.boundary_register = {services.boundary_register!r}")
        print()

        ImperialRentSystem().step(graph, services, context)

        print("post-tick social classes:")
        for node_id, _ in SOCIAL_CLASSES:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<18} wealth={a.get('wealth')!r} "
                f"effective_wealth={a.get('effective_wealth')!r} "
                f"unearned_increment={a.get('unearned_increment')!r} "
                f"ppp_multiplier={a.get('ppp_multiplier')!r} "
                f"w_paid={a.get('w_paid')!r} "
                f"v_produced={a.get('v_produced')!r}"
            )
        print()

        print("post-tick edges (value_flow):")
        for source, target, edge_type in EDGES:
            edge = graph.get_edge(source, target, edge_type)
            if edge is None:
                raise SystemExit(f"edge {edge_type} {source} -> {target} vanished during the tick")
            print(
                f"  {edge_type} {source} -> {target}: "
                f"value_flow={edge.attributes.get('value_flow')!r}"
            )
        print()

        print(f"post-tick context.persistent_data = {context.persistent_data!r}")
        print()

        economy_after = graph.get_graph_attr("economy")
        print(f"post-tick economy (ALREADY DECAYED, see header (b)) = {economy_after!r}")
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
