"""Frozen-mirror provenance for `imperial-rent-conformance.bscn` (world 1) —
the ImperialRent BSL port train (Material Base @9.0, Checkpoint A campaign;
plan `docs/superpowers/plans/2026-08-18-imperialrent-port.md`, §9's
canonical mirror recipe). This is the STRUCTURE and ORDERING oracle, NOT a
correctness oracle (ADR183) — later Rust-side pins measure their own
expecteds from the BSL engine itself, cross-checked BY HAND against this
mirror's printed values, never copied byte-for-byte.

Builds the five social classes + one `imperial-rent-register` carrier of
`imperial-rent-conformance.bscn` node for node and edge for edge, runs
`ImperialRentSystem`'s one tick of phases (`step()`'s own body, replicated
call-for-call so the pre-quantization pool value is observable — see
header fact (d)) against them, and prints every vector Task 1's brief
names: the `economy:` defines block, the per-node post-tick
`wealth`/`effective_wealth`/`unearned_increment`/`ppp_multiplier`/`w_paid`/
`v_produced`, every edge's `value_flow`, the post-tick `economy` graph
attribute (both quantized and raw), and the full event history.

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
(d) **The `economy` graph attribute is QUANTIZED; BSL's own arithmetic is
    NOT — fix round 1, reviewer Important 1, 2026-08-18.**
    `GlobalEconomy`'s three fields (`imperial_rent_pool: Currency`,
    `current_super_wage_rate: Coefficient`, `current_repression_level:
    Probability`) each carry `SnapToGrid = AfterValidator(quantize)`
    (`models/types.py:26-30,41-44`), and `quantize` (`kernel/math.py:41-56`)
    snaps ROUND_HALF_UP to 6 decimals. `_save_economy` (`economic.py:831-836`)
    constructs a `GlobalEconomy(...)`, so EVERY value `graph.get_graph_attr
    ("economy")` returns post-tick has already been through this validator —
    a frozen-Python-ONLY artifact with no BSL counterpart (BSL has no
    Currency/Coefficient/Probability quantization step; every BSL write is
    raw binary64). This script below prints BOTH the quantized graph
    attribute (what the frozen engine actually stores) AND the RAW,
    pre-quantization pool value (recomputed via the same private phase
    calls `step()` itself makes, not hand-derived) — Task 6/7's `r09-pool-
    decay` BSL rule computes the RAW value, so it is the RAW print, not the
    quantized one, that is the correct oracle line for that comparison.
    Node `wealth`/`effective_wealth`/etc. and edge `value_flow` are NEVER
    quantized (`graph.update_node`/`update_edge` write raw dict attributes,
    no Pydantic validation in that path) — the asymmetry is visible in the
    stdout itself (six-decimal `economy` values beside 15-digit `wealth`
    values).

World 1 is the "all four phases, NO_CHANGE" primary — Phase 4 (Subsidy) is
Director-RESERVED (Constitution IX.5, plan §6) and never runs; no
`CLIENT_STATE` edge exists in this fixture, so `_process_subsidy_phase`'s own
loop is trivially empty regardless.

Task 3 extends this module to ALSO drive world 10
(`imperial-rent-multi-tribute-conformance.bscn`) — a comprador with TWO
TRIBUTE edges to two distinct CORE_BOURGEOISIE recipients, built to measure
D184(b) (the frozen engine's per-edge SOURCE re-read, `economic.py:375`)
against the ported rule-scoped `cut`/`tribute` (D200's repeated-`set`
semantics). **Header fact (e), THIS task: the mirror's own comprador number
on world 10 will NOT match the Rust-side assertion, and that is the whole
point of building world 10 — the frozen engine's `source_attrs["wealth"]`
re-read (`:375`) makes the SECOND TRIBUTE edge see the FIRST edge's
already-applied cut (comprador wealth `800.0 -> 720.0 -> 648.0`), while the
ported `r03-tribute` computes `cut`/`tribute` ONCE from pre-state and applies
the SAME value to both edges (comprador wealth `800.0 -> 720.0`, written
twice). `run_world_10()` below is the frozen engine's own oracle for the
FROZEN-sequential half of that comparison; the Rust conformance test
(`imperial_rent_conformance.rs::the_two_tribute_edges_apply_the_rule_scoped_cut_once`)
publishes both numbers side by side, per the D183 publication discipline.
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
        },
    ),
    (
        "periphery-worker",
        {
            "role": SocialRole.PERIPHERY_PROLETARIAT,
            "active": True,
            "wealth": 500.0,
        },
    ),
    (
        "comprador",
        {
            "role": SocialRole.COMPRADOR_BOURGEOISIE,
            "active": True,
            "wealth": 800.0,
        },
    ),
    (
        "labor-aristocracy",
        {
            "role": SocialRole.LABOR_ARISTOCRACY,
            "active": True,
            "wealth": 300.0,
        },
    ),
    (
        "petty-b",
        {
            "role": SocialRole.PETTY_BOURGEOISIE,
            "active": True,
            "wealth": 250.0,
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


#: World 10 — `imperial-rent-multi-tribute-conformance.bscn`'s own topology:
#: one comprador (wealth 800.0, SAME as world 1's own comprador, for direct
#: comparability), TWO TRIBUTE edges to two DISTINCT CORE_BOURGEOISIE
#: recipients. Declaration order fixes `query_edges` insertion order here —
#: comprador -> recipient-a is processed BEFORE comprador -> recipient-b,
#: which is exactly what makes the SECOND edge see the FIRST edge's
#: already-applied wealth overwrite (D184(b)).
WORLD_10_SOCIAL_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "comprador",
        {
            "role": SocialRole.COMPRADOR_BOURGEOISIE,
            "active": True,
            "wealth": 800.0,
        },
    ),
    (
        "recipient-a",
        {
            "role": SocialRole.CORE_BOURGEOISIE,
            "active": True,
            "wealth": 5000.0,
        },
    ),
    (
        "recipient-b",
        {
            "role": SocialRole.CORE_BOURGEOISIE,
            "active": True,
            "wealth": 2000.0,
        },
    ),
]

WORLD_10_EDGES: list[tuple[str, str, Any]] = [
    ("comprador", "recipient-a", EdgeType.TRIBUTE),
    ("comprador", "recipient-b", EdgeType.TRIBUTE),
]


def build_world_10_graph() -> BabylonGraph:
    """Build world 10's three-class, two-edge topology, in declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in WORLD_10_SOCIAL_CLASSES:
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **dict(attrs))
    for source, target, edge_type in WORLD_10_EDGES:
        graph.add_edge(source, target, edge_type, value_flow=0.0)
    return graph


def run_world_10(services: ServiceContainer) -> None:
    """Run one tick of the frozen `ImperialRentSystem` against world 10 and
    print the tribute-relevant vectors — the FROZEN-sequential oracle half
    of D184(b)'s comparison (this module's own docstring, Task 3 section).
    Reuses the SAME `services` the world-1 run above already constructed
    (one process, §9's canonical recipe), against a fresh graph.
    """
    graph = build_world_10_graph()
    graph.set_graph_attr(
        "economy",
        GlobalEconomy(
            imperial_rent_pool=100.0,
            current_super_wage_rate=0.2,
            current_repression_level=0.5,
        ).model_dump(),
    )
    graph.set_graph_attr("opposition_states", {"capital_labor": {"gap": 0.0}})

    context = TickContext(tick=1)
    system = ImperialRentSystem()
    economy = system._load_economy(graph, services)  # noqa: SLF001
    initial_pool = services.defines.economy.initial_rent_pool
    tick_context: dict[str, Any] = {
        "tribute_inflow": 0.0,
        "wages_outflow": 0.0,
        "subsidy_outflow": 0.0,
        "current_pool": economy.imperial_rent_pool,
        "wage_rate": economy.current_super_wage_rate,
        "repression_level": economy.current_repression_level,
    }
    system._process_extraction_phase(graph, services, context, tick_context)  # noqa: SLF001
    system._process_tribute_phase(graph, services, context, tick_context)  # noqa: SLF001
    system._process_wages_phase(graph, services, context, tick_context)  # noqa: SLF001
    system._process_subsidy_phase(graph, services, context, tick_context)  # noqa: SLF001
    system._process_decision_phase(  # noqa: SLF001
        graph, services, context, tick_context, initial_pool
    )
    system._save_economy(graph, tick_context, services)  # noqa: SLF001

    print("=" * 70)
    print("WORLD 10 — imperial-rent-multi-tribute-conformance.bscn (Task 3)")
    print("=" * 70)
    print(
        "comprador seed wealth = 800.0, economy.comprador_cut = "
        f"{services.defines.economy.comprador_cut!r}"
    )
    print()
    print("post-tick social classes:")
    for node_id, _ in WORLD_10_SOCIAL_CLASSES:
        node = graph.get_node(node_id)
        if node is None:
            raise SystemExit(f"node {node_id} vanished during the tick")
        print(f"  {node_id:<12} wealth={node.attributes.get('wealth')!r}")
    print()
    print("post-tick edges (value_flow), declaration/query_edges order:")
    for source, target, edge_type in WORLD_10_EDGES:
        edge = graph.get_edge(source, target, edge_type)
        if edge is None:
            raise SystemExit(f"edge {edge_type} {source} -> {target} vanished during the tick")
        print(
            f"  {edge_type} {source} -> {target}: value_flow={edge.attributes.get('value_flow')!r}"
        )
    print()
    print(
        "FROZEN SEQUENTIAL comprador wealth: 800.0 -> (edge 1's cut) -> "
        "(edge 2's cut, off the ALREADY-CUT balance) — see the two wealth "
        "lines above for the measured intermediate/final values; the "
        "PORTED (BSL) comprador wealth instead lands at edge 1's cut alone, "
        "written twice (D200/D184(b), see this module's own docstring)."
    )
    print()


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

        # Fix round 1 (Important 1): `step()`'s body is replicated call-for-
        # call, in order, rather than invoked as one opaque `.step()` call —
        # this is the ONLY way to observe `tick_context["current_pool"]`
        # BEFORE `_save_economy` hands it to `GlobalEconomy(...)` and its
        # SnapToGrid validator quantizes it (header fact (d)). Every call
        # below is copy-identical to `ImperialRentSystem.step()`
        # (`economic.py:46-86`) in the same order with the same arguments —
        # this is measurement, not re-derivation: the raw pool value comes
        # from the SAME dict the frozen method itself mutates, not from
        # hand arithmetic.
        system = ImperialRentSystem()
        economy = system._load_economy(graph, services)  # noqa: SLF001
        initial_pool = services.defines.economy.initial_rent_pool
        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": economy.imperial_rent_pool,
            "wage_rate": economy.current_super_wage_rate,
            "repression_level": economy.current_repression_level,
        }
        system._process_extraction_phase(graph, services, context, tick_context)  # noqa: SLF001
        system._process_tribute_phase(graph, services, context, tick_context)  # noqa: SLF001
        system._process_wages_phase(graph, services, context, tick_context)  # noqa: SLF001
        system._process_subsidy_phase(graph, services, context, tick_context)  # noqa: SLF001
        system._process_decision_phase(  # noqa: SLF001
            graph, services, context, tick_context, initial_pool
        )
        # `_save_economy`'s own raw-pool formula (`economic.py:823-829`),
        # BEFORE the `GlobalEconomy(...)` construction that quantizes it —
        # this is the oracle line Task 6/7's r09-pool-decay BSL rule must
        # match, per header fact (d).
        raw_pool_pre_decay = tick_context["current_pool"]
        decay_rate = services.defines.economy.rent_pool_decay
        raw_pool_post_decay = max(0.0, raw_pool_pre_decay * (1.0 - decay_rate))
        system._save_economy(graph, tick_context, services)  # noqa: SLF001
        system._invoke_phi_distribution_if_wired(context, services)  # noqa: SLF001
        system._invoke_vol2_circulation_if_wired(graph, context)  # noqa: SLF001

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
        print(
            f"post-tick economy.imperial_rent_pool RAW (pre-quantization, "
            f"see header (d); THE ORACLE FOR BSL's r09) = {raw_pool_post_decay!r}"
        )
        print()

        events = services.event_bus.get_history()
        print("events:")
        for event in events:
            print(f"  {event.type} {event.payload!r}")
        if not events:
            print("  (none)")
        print()

        # Task 3: world 10, the two-TRIBUTE-edge comprador (D184(b)/D200).
        # Reuses this SAME `services` instance — one process, §9's recipe —
        # against a fresh graph; world 10's own event history is not
        # inspected here (Phase 2 emits nothing, r03_emits_nothing's own
        # claim on the Rust side).
        run_world_10(services)
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
