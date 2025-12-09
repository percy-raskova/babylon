# Graph Persistence Strategy: KuzuDB Evaluation

**Status:** DEFERRED
**Phase:** VI (The Fractal)
**Created:** 2025-12-09
**Core Insight:** Databases optimize for retrieval; simulations optimize for mutation. Keep the physics in RAM.

---

## 1. The Contender: KuzuDB

[KuzuDB](https://kuzudb.com/) bills itself as the "SQLite of Graph Databases":

| Property | Value |
|----------|-------|
| Deployment | Embedded, serverless (single file) |
| Query Language | Cypher (same as Neo4j) |
| Persistence | Disk-backed with page cache |
| Transactions | Full ACID compliance |
| License | MIT |

**Theoretical Appeal:**
- Our simulation is fundamentally graph-based (NetworkX topology)
- Cypher queries are more expressive than SQL JOINs for path-finding
- Embedded = no server overhead, fits the "Embedded Trinity" philosophy
- Could unify graph storage with graph processing

**Why We Considered It:**
The promise of a single abstraction handling both storage AND computation is seductive. Query your history with Cypher instead of painful recursive SQL. Persist your graph without serialization/deserialization.

---

## 2. The Comparison: Simulation vs. Database

### NetworkX (Current Choice)
**Optimized for:** Mutation and Physics

```
┌─────────────────────────────────────────────────────────┐
│                     RAM ($O(1)$ access)                 │
│                                                         │
│  graph.nodes[node_id]['wealth'] += delta               │
│  graph.edges[u, v]['strength'] *= decay                │
│                                                         │
│  → Every node touched every tick                        │
│  → Every edge weight mutated                           │
│  → Zero I/O latency during computation                  │
└─────────────────────────────────────────────────────────┘
```

**Characteristics:**
- In-memory: All operations are RAM pointer traversals
- Mutable: Direct attribute modification on nodes/edges
- No transaction overhead: No ACID guarantees needed during simulation
- Perfect for `step()` functions that touch 100% of entities per tick

### KuzuDB (Alternative)
**Optimized for:** Retrieval and Querying

```
┌─────────────────────────────────────────────────────────┐
│               Disk + Page Cache                         │
│                                                         │
│  MATCH (c:Class) WHERE c.wealth < threshold             │
│  SET c.wealth = c.wealth + delta                        │
│                                                         │
│  → Each mutation = disk page write                      │
│  → ACID overhead per transaction                        │
│  → Optimized for selective queries, not bulk updates    │
└─────────────────────────────────────────────────────────┘
```

**The Problem:**
A game loop that updates **every node, every edge, every tick** pays the full ACID overhead on every operation. KuzuDB is optimized for:
- "Find all nodes matching X" (selective reads)
- "Update 5% of nodes based on query" (targeted writes)

It is NOT optimized for:
- "Touch every single node and edge" (bulk mutation)
- "Do this 1000 times per second" (high-frequency updates)

### Performance Reality

| Operation | NetworkX | KuzuDB |
|-----------|----------|--------|
| Read single node attribute | $O(1)$ dict lookup | Page cache hit (fast) or disk seek (slow) |
| Write single node attribute | $O(1)$ dict write | Transaction log + page write |
| Iterate all nodes | $O(n)$ in RAM | $O(n)$ with page cache misses |
| Bulk update all nodes | $O(n)$ in RAM | $O(n)$ with $n$ transaction commits |

For our simulation with ~50-500 entities per tick across 6 systems, NetworkX wins by orders of magnitude.

---

## 3. The "Hydration Pattern" (Our Architecture)

We implement a **Hydration Pattern** that leverages each technology's strengths:

```
┌─────────────────────────────────────────────────────────────────┐
│                        THE HYDRATION CYCLE                      │
│                                                                 │
│   ┌─────────┐      hydrate()       ┌─────────────┐              │
│   │ SQLite  │ ──────────────────→  │  NetworkX   │              │
│   │ (REST)  │                      │  (ACTIVE)   │              │
│   │         │  ←──────────────────  │             │              │
│   │ Ledger  │      dehydrate()     │  Topology   │              │
│   └─────────┘                      └─────────────┘              │
│                                           │                     │
│                                           │ step()              │
│                                           ↓                     │
│                                    ┌─────────────┐              │
│                                    │  Pure Math  │              │
│                                    │  (Systems)  │              │
│                                    └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### Phase Breakdown

| Phase | Technology | State | Operations |
|-------|------------|-------|------------|
| **REST** | SQLite | Persistent | Save/Load between sessions |
| **ACTIVE** | NetworkX | In-Memory | All simulation physics |
| **ARCHIVE** | ChromaDB | Persistent | Semantic history for AI |

### Implementation

```python
# Hydration: Load from SQLite into NetworkX
world_state = WorldState.load_from_db(session)
graph = world_state.to_graph()  # → NetworkX DiGraph

# Simulation: Pure RAM operations
for _ in range(ticks):
    graph = simulation_engine.run_tick(graph, services, context)
    # Zero I/O here - all in RAM

# Dehydration: Persist back to SQLite
world_state = WorldState.from_graph(graph)
world_state.save_to_db(session)
```

### Why This Wins

1. **Zero I/O During Math:** The entire `run_tick()` operates in RAM
2. **Clean Boundaries:** Persistence is a discrete operation, not interleaved with logic
3. **Technology Fit:** Each tool does what it's optimized for
4. **Testability:** Graph operations are pure functions, easily unit-tested
5. **Simplicity:** SQLite is battle-tested, well-understood, zero dependencies

---

## 4. The Trigger for Phase VI: The Chronicle

KuzuDB becomes valuable when we need to **query historical relationships**.

### The Problem (Phase VI)

After 100,000+ turns of simulation history:
- NetworkX can't query history (it only holds current state)
- SQLite requires painful multi-table JOINs for graph questions

**Example Query:**
> "Find all turns where a HIGH_HEAT territory was adjacent to a territory controlled by a Radical Union"

In SQL:
```sql
-- This is a nightmare of recursive CTEs and JOINs
WITH RECURSIVE territory_adjacency AS (...)
SELECT t.turn_number
FROM turns t
JOIN territories t1 ON ...
JOIN adjacency_edges a ON ...
JOIN territories t2 ON ...
JOIN territory_control tc ON ...
JOIN factions f ON ...
WHERE t1.heat >= 0.8
  AND f.type = 'RADICAL_UNION'
-- 50 more lines of JOIN hell
```

In Cypher (KuzuDB):
```cypher
MATCH (t1:Territory)-[:ADJACENT]->(t2:Territory)<-[:CONTROLS]-(f:Faction)
WHERE t1.heat >= 0.8 AND f.type = 'RADICAL_UNION'
RETURN DISTINCT t1.turn_number
```

### The Use Case: The Chronicle

Phase VI introduces "The Chronicle" - a queryable historical graph:

```
┌─────────────────────────────────────────────────────────────────┐
│                     PHASE VI: THE CHRONICLE                     │
│                                                                 │
│  ┌──────────┐                          ┌────────────────────┐   │
│  │ Current  │     append_turn()        │     KuzuDB         │   │
│  │ NetworkX │ ──────────────────────→  │  (Historical)      │   │
│  │  Graph   │                          │                    │   │
│  └──────────┘                          │  Turn 1 snapshot   │   │
│                                        │  Turn 2 snapshot   │   │
│                                        │  ...               │   │
│                                        │  Turn 100,000      │   │
│                                        └────────────────────┘   │
│                                                 │               │
│                                                 │ Cypher        │
│                                                 ↓               │
│                                        ┌────────────────────┐   │
│                                        │ "When did faction  │   │
│                                        │  X first appear in │   │
│                                        │  territory Y?"     │   │
│                                        └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**When This Matters:**
- Longitudinal analysis across thousands of turns
- AI narrative generation querying "pivotal moments"
- Player queries: "How did we get here?"
- Research/debugging: Pattern detection in historical data

---

## 5. Verdict

### Decision: DEFERRED to Phase VI

| Aspect | Current (Phase 3-5) | Future (Phase VI) |
|--------|---------------------|-------------------|
| Primary Concern | Simulation speed | Historical queries |
| Data Volume | Hundreds of entities | Millions of historical records |
| Query Pattern | "Update all" | "Find specific patterns" |
| Best Tool | NetworkX + SQLite | NetworkX + SQLite + KuzuDB |

### The Rule

> **"Databases are for retrieval. Simulations are for mutation. Keep the physics in RAM."**

### Conditions for Adoption

KuzuDB enters the stack when ALL of these are true:

1. **Historical depth:** 10,000+ turns of accumulated history
2. **Query complexity:** Questions that span multiple turns/relationships
3. **User demand:** Players or AI actively querying historical patterns
4. **Performance ceiling:** SQLite JOIN complexity becomes unmanageable

### Architecture Evolution

```
Phase 3-5 (Current):
  SQLite ←→ NetworkX ←→ ChromaDB
  (Ledger)  (Topology)  (Archive)

Phase VI (Future):
  SQLite ←→ NetworkX ←→ ChromaDB
  (Ledger)  (Topology)  (Archive)
              ↓
           KuzuDB
         (Chronicle)
```

The Embedded Trinity remains. KuzuDB becomes the **fourth pillar** when history becomes deep enough to query.

---

## 6. References

- [KuzuDB Documentation](https://docs.kuzudb.com/)
- [NetworkX Documentation](https://networkx.org/documentation/stable/)
- ADR-003: Graph-First Data Model (`ai-docs/decisions.yaml`)
- ADR-007: Embedded Architecture (`ai-docs/decisions.yaml`)
- Four Phase Engine Blueprint (`brainstorm/plans/four-phase-engine-blueprint.md`)
