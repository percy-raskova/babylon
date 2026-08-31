# Common Gotchas

Lessons from debugging sessions. Read this before implementing engine code.

## WorldState.events is Per-Tick, NOT Cumulative

```python
# WRONG: Accumulating events across ticks
accumulated_events = accumulated_events + new_events
new_state = state.model_copy(update={"events": accumulated_events})

# RIGHT: Each tick gets fresh events
new_state = state.model_copy(update={"events": tick_events})
```

The engine creates fresh `WorldState` each tick. `events` contains ONLY that tick's events. "No events this tick" = `[]`, not duplicates from previous tick.

## Graph Round-Trip Can Lose Mutations

`WorldState.to_graph()` → Systems mutate graph → `WorldState.from_graph()`

**Gotcha**: `from_graph()` excludes computed fields and uses model defaults:

```python
# In from_graph(), these are excluded:
social_class_computed = {"consumption_needs"}
territory_excluded = {"p_acquiescence", "p_revolution"}
```

If you add a field to SocialClass, ensure `to_graph()` serializes it AND `from_graph()` doesn't exclude it.

**Gotcha**: Using `data.get("field", 0.0)` masks missing field bugs:

```python
# This silently uses 0.0 if s_bio missing from graph node
consumption = data.get("s_bio", 0.0) + data.get("s_class", 0.0)
```

## Systems Mutate Shared Graph In-Place

Systems execute in strict order, each seeing previous systems' mutations:

```
ImperialRent → Solidarity → Consciousness → Survival → Struggle → Contradiction → Territory → Metabolism
```

Access node data via `graph.nodes[node_id]["wealth"]`, not model attributes.

## Mypy Misses Pydantic Attribute Errors

```python
# This passes mypy but fails at runtime:
snapshot: TopologySnapshot = monitor.history[-1]
phase = snapshot.phase  # AttributeError: 'TopologySnapshot' has no attribute 'phase'
```

Pydantic models use dynamic attributes that bypass static analysis. **Runtime tests are essential.**

## Immutability via model_copy()

WorldState is frozen. ALL mutations return new instances:

```python
# WRONG
state.tick = state.tick + 1  # Raises ValidationError

# RIGHT
new_state = state.model_copy(update={"tick": state.tick + 1})
```

## Dependency Injection Over Discovery

```python
# WRONG: Discovering dependencies at runtime
def __init__(self):
    self.metrics = self._find_observer(MetricsCollector)

# RIGHT: Explicit injection
def __init__(self, metrics_collector: MetricsCollector):
    self.metrics = metrics_collector
```

## Postgres Data Volumes Are Lineage-Bound

The container default is `babylon-pg-alpine-c-utf8-v1`. Fresh clusters use
Postgres 17's built-in `C.UTF-8` locale provider and receive an exact lineage
marker only after initialization and every init script complete successfully.
Startup accepts an empty data directory or that exact marked lineage. It rejects
every other nonempty directory before changing ownership, mode, or content.
This is an accidental/recoverability lineage fence, not an adversarial
attestation. A process that can write `PGDATA` can forge both the marker and
cluster metadata. The contract protects operators from accidental physical
reuse across incompatible image/libc lineages; it is not a security boundary.
The injected check is deliberately fail-before-chown. No wrapper or fallback is
allowed to run around the digest-pinned upstream entrypoint.

The retired Debian-lineage `babylon-pg-data` volume remains deliberately outside
the Compose file. Keep it unchanged and never attach it to the Alpine image.
`mise run db:nuke` removes only the current Compose volume. It does not remove
the retired volume or a bind-mounted `BABYLON_PG_DATA` directory.

The repository does not automate physical-volume migration. If an old volume
contains valuable data, keep it unchanged. Plan an offline logical dump/restore
with the original Debian-lineage image (`pg_dump`/`pg_restore` or `pg_dumpall`).
Restore into a fresh current-lineage cluster. Check the restored database before
you retire the old volume. `REINDEX`, collation metadata refresh, and in-place
extension updates do not make cross-libc physical reuse a supported migration
path.

The current census v2 fixtures record observations from the digest-pinned
PostGIS image on Alpine 3.24.1 with PostgreSQL 17.11, PostGIS 3.5.7, H3 and
H3/PostGIS 4.5.0, pgvector 0.8.5, and the built-in `C.UTF-8` locale. The image
contract pins the base and source archive checksums plus final runtime package
revisions; builder packages remain repository-resolved, so the contract makes
no byte-reproducibility claim. The exact lineage marker is
`babylon-postgres-lineage-v1|postgres=17|locale-provider=builtin|locale=C.UTF-8|encoding=UTF8|postgis=3.5.7|h3=4.5.0|h3_postgis=4.5.0|vector=0.8.5`.
The v1 census files remain immutable archives, while v2 is the sole current
adoption and fresh-schema path.

One legacy row changed solely because locale collation reversed the first two
members of the otherwise identical `conservation_audit_log` partition-constraint
array. The archived libc `en_US.utf8` payload orders the hex-hash-length check
before the scale check and hashes to
`30ef0e3b7795606b15a35a2f91bcc40dc60be80f0a000d362bc17c5737ff00e2`.
The built-in `C.UTF-8` payload orders the scale check first and hashes to
`5eff9766641285da9cf078e6633f603a3492f2735b6e5dd6f1c9b1fd07b84b50`.
The checked-in canonical JSON receipts hash to those two fixture digests. The
bounded Rust contract parses both complete payloads, swaps the first two
partition-constraint values, and proves the entire remaining JSON equal. The
DDL is unchanged, and every v2 header records the exact census SQL digest.
