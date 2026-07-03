"""NetworkX vs rustworkx graph-backend micro-benchmark (Amendment L / ADR052).

Times the graph-layer primitives the babylon engine actually exercises,
on a michigan-shaped synthetic graph (~2k nodes, ~8k edges, dict payloads).
Honesty note: the per-tick hot path is CRUD + Pydantic dominated, so
construct/read/sweep rows are expected to be ~parity; the wins concentrate
in the algorithm rows (components, shortest paths). Engine-level wall clock
is measured separately via the canonical run (``mise run sim:e2e-michigan``).

Usage::

    poetry run python tools/benchmarks/graph_backend_bench.py
"""

from __future__ import annotations

import random
import statistics
import time
from collections.abc import Callable
from typing import Any

import networkx as nx
import rustworkx as rx

N_NODES = 2_000
N_EDGES = 8_000
N_ATTR_OPS = 10_000
N_SWEEPS = 20
N_COMPONENT_RUNS = 100
N_SSSP_SOURCES = 200
N_REPS = 5
SEED = 42

NodePayload = dict[str, Any]
EdgeSpec = tuple[str, str, dict[str, Any]]


def make_shape(seed: int = SEED) -> tuple[list[tuple[str, NodePayload]], list[EdgeSpec]]:
    """Build one deterministic node/edge spec shared by both backends."""
    rng = random.Random(seed)
    node_ids = [f"c{i:05d}" for i in range(N_NODES)]
    nodes: list[tuple[str, NodePayload]] = [
        (
            node_id,
            {
                "_node_type": "social_class",
                "wealth": rng.uniform(0.1, 100.0),
                "organization": rng.random(),
                "ideology": rng.uniform(-1.0, 1.0),
            },
        )
        for node_id in node_ids
    ]
    edges: list[EdgeSpec] = []
    seen: set[tuple[str, str]] = set()
    while len(edges) < N_EDGES:
        u, v = rng.sample(node_ids, 2)
        if (u, v) in seen:
            continue
        seen.add((u, v))
        edges.append(
            (
                u,
                v,
                {
                    "edge_type": "SOLIDARITY" if rng.random() < 0.4 else "WAGES",
                    "weight": rng.uniform(0.1, 1.0),
                    "tension": rng.random(),
                },
            )
        )
    return nodes, edges


def build_nx(nodes: list[tuple[str, NodePayload]], edges: list[EdgeSpec]) -> nx.DiGraph[str]:
    graph: nx.DiGraph[str] = nx.DiGraph()
    for node_id, payload in nodes:
        graph.add_node(node_id, **payload)
    for u, v, data in edges:
        graph.add_edge(u, v, **data)
    return graph


def build_rx(
    nodes: list[tuple[str, NodePayload]], edges: list[EdgeSpec]
) -> tuple[rx.PyDiGraph[NodePayload, dict[str, Any]], dict[str, int]]:
    graph: rx.PyDiGraph[NodePayload, dict[str, Any]] = rx.PyDiGraph(multigraph=False)
    ids: dict[str, int] = {}
    for node_id, payload in nodes:
        ids[node_id] = graph.add_node(dict(payload))
    for u, v, data in edges:
        graph.add_edge(ids[u], ids[v], dict(data))
    return graph, ids


def timed(fn: Callable[[], object], reps: int = N_REPS) -> float:
    """Median wall time of ``fn`` over ``reps`` runs, in milliseconds."""
    samples: list[float] = []
    for _ in range(reps):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1_000.0)
    return statistics.median(samples)


def bench_build(nodes: list[tuple[str, NodePayload]], edges: list[EdgeSpec]) -> tuple[float, float]:
    return timed(lambda: build_nx(nodes, edges)), timed(lambda: build_rx(nodes, edges))


def bench_attr_rw(
    g_nx: nx.DiGraph[str],
    g_rx: rx.PyDiGraph[NodePayload, dict[str, Any]],
    ids: dict[str, int],
) -> tuple[float, float]:
    node_ids = list(ids)[:N_ATTR_OPS]

    def run_nx() -> None:
        for node_id in node_ids:
            g_nx.nodes[node_id]["wealth"] = g_nx.nodes[node_id]["wealth"] * 1.0001

    def run_rx() -> None:
        for node_id in node_ids:
            payload = g_rx[ids[node_id]]
            payload["wealth"] = payload["wealth"] * 1.0001

    return timed(run_nx), timed(run_rx)


def bench_sweep(
    g_nx: nx.DiGraph[str],
    g_rx: rx.PyDiGraph[NodePayload, dict[str, Any]],
) -> tuple[float, float]:
    def run_nx() -> None:
        for _ in range(N_SWEEPS):
            total = 0.0
            for _, data in g_nx.nodes(data=True):
                total += data["wealth"]
            for _, _, edata in g_nx.edges(data=True):
                total += edata["weight"]

    def run_rx() -> None:
        for _ in range(N_SWEEPS):
            total = 0.0
            for payload in g_rx.nodes():
                total += payload["wealth"]
            for _, _, edata in g_rx.weighted_edge_list():
                total += edata["weight"]

    return timed(run_nx), timed(run_rx)


def bench_components(
    g_nx: nx.DiGraph[str],
    g_rx: rx.PyDiGraph[NodePayload, dict[str, Any]],
) -> tuple[float, float]:
    undirected_nx = g_nx.to_undirected(as_view=False)

    def run_nx() -> None:
        for _ in range(N_COMPONENT_RUNS):
            _ = [len(c) for c in nx.connected_components(undirected_nx)]

    def run_rx() -> None:
        for _ in range(N_COMPONENT_RUNS):
            _ = [len(c) for c in rx.weakly_connected_components(g_rx)]

    return timed(run_nx), timed(run_rx)


def bench_sssp(
    g_nx: nx.DiGraph[str],
    g_rx: rx.PyDiGraph[NodePayload, dict[str, Any]],
    ids: dict[str, int],
) -> tuple[float, float]:
    sources = list(ids)[:N_SSSP_SOURCES]

    def run_nx() -> None:
        for source in sources:
            _ = nx.single_source_dijkstra_path_length(g_nx, source, weight="weight")

    def run_rx() -> None:
        for source in sources:
            _ = rx.dijkstra_shortest_path_lengths(
                g_rx, ids[source], edge_cost_fn=lambda e: float(e["weight"])
            )

    return timed(run_nx), timed(run_rx)


def main() -> None:
    nodes, edges = make_shape()
    g_nx = build_nx(nodes, edges)
    g_rx, ids = build_rx(nodes, edges)

    rows: list[tuple[str, float, float]] = []
    rows.append(("build (2k nodes / 8k edges)", *bench_build(nodes, edges)))
    rows.append((f"attr r/w ({N_ATTR_OPS} ops)", *bench_attr_rw(g_nx, g_rx, ids)))
    rows.append((f"full sweep x{N_SWEEPS}", *bench_sweep(g_nx, g_rx)))
    rows.append((f"components x{N_COMPONENT_RUNS}", *bench_components(g_nx, g_rx)))
    rows.append((f"dijkstra sssp x{N_SSSP_SOURCES}", *bench_sssp(g_nx, g_rx, ids)))

    print(f"\n{'benchmark':<32} {'networkx':>12} {'rustworkx':>12} {'speedup':>9}")
    print("-" * 69)
    for label, t_nx, t_rx in rows:
        ratio = t_nx / t_rx if t_rx > 0 else float("inf")
        print(f"{label:<32} {t_nx:>10.2f}ms {t_rx:>10.2f}ms {ratio:>8.2f}x")
    print(
        "\nnote: rx rows use raw index access; BabylonGraph adds a dict-mirror\n"
        "layer for id-keyed CRUD, so its CRUD cost ~= the networkx rows."
    )


if __name__ == "__main__":
    main()
