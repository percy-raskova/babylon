"""Conformance vectors for the `production/*` rule pack, from the frozen engine.

This script is the PROVENANCE — the STRUCTURE oracle, explicitly NOT a byte
oracle (ADR183) — for the port pinned across
``rust/crates/babylon-tick/tests/production_conformance.rs``. It builds the
eight social classes and four territories of
``production-conformance.bscn`` node for node, runs the frozen
``ProductionSystem`` once against them, and prints the post-tick state.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/production_conformance.py

The frozen system is the contract source for STRUCTURE and ORDERING, not a
correctness oracle (ADR183) — this pack's own BSL rule text diverges from the
frozen engine's field shape in one deliberate way: the frozen engine keys LA
production by worker node id in a graph-scope ``la_production`` dict
(read only by ``ImperialRentSystem``, out of this port's scope); the BSL pack
widens this into an ordinary per-node field, ``social-class/production-value``,
written by ALL THREE producer rules (not just the employed branch), and read
back by the extraction-intensity fold. What this script proves is that the
BSL pack moves the SAME fields (wealth, extraction_intensity) in the SAME
direction for the SAME reasons the frozen engine does — the conformance
vectors pinned in the Rust test file are measured from the BSL engine itself,
not copied from this script's printed floats.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.production import ProductionSystem
from babylon.models.enums import EdgeType, NodeType, SocialRole
from babylon.topology.graph import BabylonGraph

#: The eight social classes, in the declaration order of
#: ``production-conformance.bscn``.
SOCIAL_CLASSES: list[tuple[str, dict[str, Any]]] = [
    (
        "worker-pp",
        {
            "role": SocialRole.PERIPHERY_PROLETARIAT,
            "active": True,
            "population": 100,
            "wealth": 10.0,
        },
    ),
    (
        "worker-pp-two-lands",
        {
            "role": SocialRole.PERIPHERY_PROLETARIAT,
            "active": True,
            "population": 50,
            "wealth": 10.0,
        },
    ),
    (
        "worker-la-one",
        {
            "role": SocialRole.LABOR_ARISTOCRACY,
            "active": True,
            "population": 40,
            "wealth": 10.0,
        },
    ),
    (
        "worker-la-two",
        {
            "role": SocialRole.LABOR_ARISTOCRACY,
            "active": True,
            "population": 60,
            "wealth": 10.0,
        },
    ),
    (
        "worker-la-orphan",
        {
            "role": SocialRole.LABOR_ARISTOCRACY,
            "active": True,
            "population": 30,
            "wealth": 10.0,
        },
    ),
    (
        "worker-la-idle",
        {
            "role": SocialRole.LABOR_ARISTOCRACY,
            "active": False,
            "population": 80,
            "wealth": 10.0,
        },
    ),
    (
        "comprador",
        {
            "role": SocialRole.COMPRADOR_BOURGEOISIE,
            "active": True,
            "population": 500,
            "wealth": 10.0,
        },
    ),
    (
        "employer",
        {
            "role": SocialRole.CORE_BOURGEOISIE,
            "active": True,
            "population": 10,
            "wealth": 10.0,
        },
    ),
]

#: The four territories, in declaration order.
TERRITORIES: list[tuple[str, dict[str, Any]]] = [
    ("t-alpha", {"biocapacity": 80.0, "max_biocapacity": 100.0}),
    ("t-beta", {"biocapacity": 50.0, "max_biocapacity": 100.0}),
    ("t-dead", {"biocapacity": 0.0, "max_biocapacity": 0.0}),
    ("t-empty", {"biocapacity": 100.0, "max_biocapacity": 100.0}),
]

#: TENANCY edges (worker -> territory), mirroring the scenario's own edge block.
TENANCY_EDGES: list[tuple[str, str]] = [
    ("worker-pp", "t-alpha"),
    ("worker-pp-two-lands", "t-alpha"),
    ("worker-pp-two-lands", "t-beta"),
    ("worker-la-one", "t-beta"),
    ("worker-la-two", "t-beta"),
    ("worker-la-orphan", "t-alpha"),
    ("worker-la-idle", "t-beta"),
    ("comprador", "t-alpha"),
]

#: WAGES edges (employer -> worker), mirroring the scenario's own edge block.
WAGES_EDGES: list[tuple[str, str]] = [
    ("employer", "worker-la-one"),
    ("employer", "worker-la-two"),
    ("employer", "worker-la-idle"),
]


def build_graph() -> BabylonGraph:
    """Build the twelve-node world, in scenario declaration order."""
    graph = BabylonGraph()
    for node_id, attrs in SOCIAL_CLASSES:
        graph.add_node(node_id, NodeType.SOCIAL_CLASS, **attrs)
    for node_id, attrs in TERRITORIES:
        graph.add_node(node_id, NodeType.TERRITORY, **attrs)
    for source, target in TENANCY_EDGES:
        graph.add_edge(source, target, EdgeType.TENANCY)
    for source, target in WAGES_EDGES:
        graph.add_edge(source, target, EdgeType.WAGES)
    return graph


def main() -> None:
    """Run one tick of the frozen ProductionSystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        d = services.defines
        print("defines (src/babylon/data/defines.yaml):")
        print(f"  economy.base_labor_power = {d.economy.base_labor_power!r}")
        print(f"  timescale.weeks_per_year = {d.timescale.weeks_per_year!r}")
        print()

        graph = build_graph()
        ProductionSystem().step(graph, services, TickContext(tick=1))
        la_production = graph.get_graph_attr("la_production", {})

        print("post-tick social classes:")
        for node_id, seed in SOCIAL_CLASSES:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<22} wealth={a.get('wealth')!r} "
                f"(seed wealth={seed['wealth']!r}) "
                f"la_production_entry={la_production.get(node_id)!r}"
            )
        print()

        print("post-tick territories:")
        for node_id, seed in TERRITORIES:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            print(
                f"  {node_id:<10} extraction_intensity={a.get('extraction_intensity')!r} "
                f"(seed biocapacity={seed['biocapacity']!r} "
                f"max_biocapacity={seed['max_biocapacity']!r})"
            )
        print()

        print(f"full la_production dict: {la_production!r}")
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
