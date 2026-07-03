# 08 — Graph Substrate: BabylonGraph / rustworkx (MASTER RECORD)

**Status**: **IMPLEMENTED (2026-07-03, constitution Amendment L, ADR052)**.
18 commits on `refactor/networkx-to-rustworkx` (continues
`refactor/lawverian-dialectics`), ending `a7e98f8d`. Canonical record:
`ai-docs/decisions/ADR052_rustworkx_graph_substrate.yaml`.

## What changed and why

NetworkX (pure Python) was the Topology pillar's substrate. rustworkx
(Qiskit's Rust-core graph library, 0.17.1, mypy-strict stubs) replaced it
1-for-1 for algorithm performance: raw-layer wins 2–5x (dijkstra 5.0x,
components 4.1x, build 4x; CRUD ≈ parity BY DESIGN — see below). The
binding constraint was **constitution III.7**: the determinism hash
depends on graph iteration order, and rustworkx REUSES integer node
indices after removal, so raw index order ≠ insertion order under churn.

## The design (read this before touching engine/graph internals)

`src/babylon/engine/graph.py` — **`BabylonGraph`** (directed world graph)
and **`BabylonUGraph`** (undirected analytics sibling) over a shared
`_GraphCore`. One class is BOTH the GraphProtocol implementation AND the
nx-compat authoring API (constitution **II.12**) — `SystemBase._wrap_graph`
passes it through and **raises TypeError on raw networkx graphs**.

- `_core`: `rx.PyDiGraph(multigraph=False)` — consulted ONLY for
  algorithms, never iterated for ordering.
- `_ids` / `_index_to_id`: insertion-ordered str↔int bimap — index reuse
  is invisible; no surface ever iterates raw index order.
- `_node_payload` / `_edge_payload`: the SAME dict objects held as
  rustworkx payloads (reference semantics — mutations visible everywhere).
- `_adj` / `_pred`: per-source insertion-ordered adjacency mirrors;
  `edges(data=True)` reproduces NetworkX's exact iteration contract —
  this is what kept the determinism baselines **byte-identical**
  (qa:regression 5/5, e2e Δ=0.000%, zero baseline regeneration).
- **Dual edge-type keys**: payloads carry public `edge_type` (~25 raw
  readers) AND internal `_edge_type` (protocol key), synced at insert.
- `add_edge` on an existing (u,v) **MERGES** attributes (nx semantics —
  raw rustworkx would REPLACE the payload).
- `copy()` deep-copies payload dicts; `subgraph()` SHARES them (nx-view
  parity); `to_undirected()` → BabylonUGraph with copied dicts.
- Algorithm seam: `src/babylon/engine/graph_algorithms.py` (components,
  articulation points, centralities, stoer_wagner min-cut, dijkstra).

## rustworkx 0.17 gotchas (pinned in `tests/unit/engine/test_rustworkx_spike.py`)

1. Node indices are REUSED after `remove_node` — never trust index order.
1. `add_edge` on an existing pair REPLACES the payload (we merge).
1. `subgraph()`/`copy()` SHARE payload dicts (we copy in `copy()`).
1. `dijkstra_shortest_path_lengths(goal=)` returns an EMPTY mapping on
   unreachable (no raise); `stoer_wagner_min_cut` returns
   `(cut_value, partition) | None`.
1. No `density` function (inlined); `dfs_edges` lacks `depth_limit`
   (bounded shim).

## Governance

- `networkx` remains in the lockfile **transitively** (xgi, torch) — do
  not "clean it up". The migration is made permanent by semgrep:
  `babylon.layer-boundary.no-networkx-import` (ERROR, src/+web/) and
  `no-raw-rustworkx` (rx.\* banned in systems/formulas/economics — go
  through the seam or the compat surface).
- Two test files DELIBERATELY keep real networkx as differential oracles
  (`test_graph_iteration_order.py`, `test_connectivity_instance.py`) —
  do not "migrate" them.
- Hook-venv vs project-venv mypy diverge on xgi: use
  `# type: ignore[import-untyped, unused-ignore]` (house pattern).

## Storage reality (discovered during acceptance, 2026-07-03)

One canonical 520-tick michigan-canada run writes **~7 GB** into
`babylon_test` — 48,827 H3 res-7 hexes × full state × every tick
(~13 MB/tick; spec-062 hex-as-source-of-truth + III.7 replay-from-any-tick).
**Nothing prunes finished runs**: spec-037's archival pipeline
(`src/babylon/persistence/archival.py`, Parquet→R2 + prune) is still
`NotImplementedError` stubs. A 71 GB accumulation (~10 runs) exhausted
/var and caused psycopg DiskFull failures before this was found.

- Pressure valves: `mise run clean:testdb` (drop/recreate/re-bootstrap
  the disposable test DB) and `mise run clean:docker` (flush leaked
  ephemeral postgis testcontainers + anonymous volumes — killed test
  runs leak them).
- **Open decision for Percy**: implement spec-037 archival (the designed
  fix), or delta-writes (persist only changed hexes — likely an order of
  magnitude smaller, but replay needs snapshot+delta reconstruction).
  Nationwide scale is ~65× the hex count; this stops being optional
  well before that.

## Observability

`mise run sim:status` (tick/520, DB size, liveness, contradiction_field
rows, max_tension trend), `sim:watch` (30s refresh), `sim:e2e-bg`
(daemonized canonical run with pidfile+log), `sim:probe` (single-county
Postgres tick probe, `tools/tick_probe.py`).
