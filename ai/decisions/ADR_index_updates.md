# ADR Index Updates

Add these entries to `ai/adr/index.yaml` under the `decisions:` key:

```yaml
  ADR030_unified_sqlite_runtime:
    title: Unified SQLite Runtime Architecture
    status: accepted
    date: '2026-01-30'
    file: ADR030_unified_sqlite_runtime.yaml
    supersedes: ADR029_hybrid_graph_architecture (KuzuDB component)

  ADR031_tick_keyed_temporal_tables:
    title: Tick-Keyed Temporal Tables for State History
    status: accepted
    date: '2026-01-30'
    file: ADR031_tick_keyed_temporal_tables.yaml

  ADR032_networkx_hydration_pattern:
    title: NetworkX Hydration Pattern (Persist to SQLite, Compute in Memory)
    status: accepted
    date: '2026-01-30'
    file: ADR032_networkx_hydration_pattern.yaml

  ADR033_deterministic_simulation:
    title: Deterministic Simulation over Cryptographic Auditability
    status: accepted
    date: '2026-01-30'
    file: ADR033_deterministic_simulation.yaml

  ADR034_deferred_rag_architecture:
    title: Deferred RAG Architecture (ChromaDB When Needed)
    status: accepted
    date: '2026-01-30'
    file: ADR034_deferred_rag_architecture.yaml
```

## Summary of Decisions

| ADR | Decision | Supersedes |
|-----|----------|------------|
| ADR030 | Single SQLite file for runtime (topology, ledger, history) | ADR029 KuzuDB component |
| ADR031 | Tick as temporal primary key, full snapshots per tick | - |
| ADR032 | NetworkX in memory, SQLite for persistence, hydrate once | - |
| ADR033 | Determinism + invariants over Merkle chains | - |
| ADR034 | Defer ChromaDB/RAG until core simulation works | - |

## Note on ADR029

ADR029 proposed NetworkX (Tactical) + KuzuDB (Strategic). ADR030 supersedes
the KuzuDB component—at Detroit scale, the added complexity doesn't earn its
keep. NetworkX + SQLite is sufficient.

If scale increases dramatically (10K+ nodes), revisit ADR030.
