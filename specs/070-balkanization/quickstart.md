# Quickstart: Sovereign Topology + Faction Influence + Balkanization

**Branch**: `070-balkanization` | **Date**: 2026-05-18

This document gives the minimum reproducible sequence to exercise
spec-070's three new Systems on the Detroit tri-county MVP seed.
It assumes the rest of the project's standard setup (`poetry
install`, `mise install`, `mise run web:install`) has already been
done — see project `CLAUDE.md` for that bootstrap.

## 1. Apply the new migration

Spec-070 introduces one new SQL migration that creates Faction /
Sovereign tables, CLAIMS / INFLUENCES / ADMINISTERS edge tables,
and the two audit tables (per FR-046 + R-005).

```bash
# From project root, with Postgres already provisioned per spec-037:
mise run data:db-init  # idempotent — applies all pending migrations
```

The new migration file is
`src/babylon/persistence/migrations/00XX_balkanization.sql`
(exact number assigned in Phase 2). The migration is owned by
the `balkanization` subsystem per Constitution II.11.

## 2. Verify seed factions and sovereigns load

```bash
poetry run python -c "
from babylon.data.game.balkanization import load_seed_factions, load_seed_sovereigns
factions = load_seed_factions()
sovereigns = load_seed_sovereigns()
print(f'Loaded {len(factions)} factions: {[f.id for f in factions]}')
print(f'Loaded {len(sovereigns)} sovereigns: {[s.id for s in sovereigns]}')
"
```

Expected output:

```text
Loaded 4 factions: ['FAC_RESTORATIONIST', 'FAC_WORKERS_CONGRESS', 'FAC_DECOLONIAL', 'FAC_LIBERAL_IMPERIAL']
Loaded 2 sovereigns: ['SOV_USA_FED', 'SOV_CAN_FED']
```

## 3. Smoke test: 5-tick run with Detroit seed

```bash
mise run sim:run -- --scenario detroit_tri_county --ticks 5 --seed 42
```

Expected behavior:

- Tick 0: Seed runs. SOV_USA_FED (ruled by FAC_RESTORATIONIST,
  INTENSIFY policy) holds DE_JURE CLAIMS on all Detroit
  tri-county Territories at control_level=1.0. SOV_CAN_FED holds
  cross-border CLAIMS via LODES Canada-destination edges.
  Habitability starts at the spec-062 baseline.
- Tick 1–5: Each tick applies metabolic_impact=−0.02 to all
  SOV_USA_FED-claimed Territories. By tick 5, aggregate
  habitability has dropped by approximately 0.10 (5 × 0.02).
  INFLUENCES distributions remain stable (no player intervention
  in this smoke test).
- No endgame events fire in 5 ticks — too short for any predicate
  to trigger.

Verification:

```bash
mise run test:summary  # last test run summary
```

Or for direct state inspection:

```bash
poetry run python tools/inspect_run.py --tick 5 --show-claims --show-influences
```

## 4. Deterministic-replay test

Re-run the same seed and assert byte-identical state output:

```bash
mise run sim:run -- --scenario detroit_tri_county --ticks 5 --seed 42 --output /tmp/run_a.json
mise run sim:run -- --scenario detroit_tri_county --ticks 5 --seed 42 --output /tmp/run_b.json
diff /tmp/run_a.json /tmp/run_b.json
# Expected: no output (files identical) — SC-011
```

## 5. Endgame reachability test (scenario, slow)

```bash
mise run test:scenario -- -k "test_five_endgames_reachable"
```

This runs the 100-stochastic-ensemble test (SC-002), which seeds
runs with varying initial player-equivalent inputs and verifies
that each of the five endgames (REVOLUTIONARY_VICTORY, RED_OGV,
ECOLOGICAL_COLLAPSE, FRAGMENTED_COLLAPSE, FASCIST_CONSOLIDATION)
is observed at least once. Given the hard-start
(FAC_RESTORATIONIST rules SOV_USA_FED), `FASCIST_CONSOLIDATION`
is the modal outcome for zero-player-intervention runs; the test
verifies the other four are reachable under stochastic player
intervention.

Expected runtime: ≈ 5–15 minutes depending on hardware.

## 6. Wallclock budget gate

```bash
mise run test:scenario -- -k "test_wallclock_budget"
```

Verifies SC-014 (combined three-system per-tick wallclock ≤5% of
spec-069's canonical-run budget at steady state) and SC-015
(≤15% during fracture spikes). Runs a 1000-tick steady-state
benchmark and a 100-territory active-secession spike benchmark.

## 7. Player-mode switch demo

CAMPAIGN mode (player picks one Faction at game start):

```bash
mise run sim:run -- --scenario detroit_tri_county --ticks 50 --seed 42 \
                    --player-mode campaign --player-faction FAC_DECOLONIAL
```

OBSERVER mode (player has god-mode):

```bash
mise run sim:run -- --scenario detroit_tri_county --ticks 50 --seed 42 \
                    --player-mode observer
```

OBSERVER-mode mutations are flagged in the audit log per FR-049:

```bash
psql -d babylon -c "SELECT tick, sovereign_id, territory_id, operation, observer_mutation
                    FROM balkanization_claims_audit
                    WHERE observer_mutation = TRUE
                    ORDER BY tick LIMIT 20;"
```

## 8. Cleanup

```bash
mise run test:clean  # wipe reports/, .pytest_cache, etc.
```

## Common gotchas

- **`SOV_USA_FED` initial state surprises**: The hard-start
  (ruled by FAC_RESTORATIONIST, INTENSIFY) is intentional per Q5
  clarification. Habitability drops fast in unobserved runs.
  This is the spec's theoretical position; if it produces
  surprising endgame distributions, that's the *finding*, not a
  bug.
- **Empty AIANNH influence**: Detroit tri-county has no major
  AIANNH polygons; FAC_DECOLONIAL starts with low/zero influence
  in this footprint. Statewide expansion (FR-029b — Wayne County
  is the focus) will introduce more meaningful AIANNH-derived
  influence as the seed area expands.
- **Determinism failures**: If a smoke run produces non-byte-
  identical outputs across two invocations of the same seed,
  this is a P0 violation (III.7). Common causes: dict iteration
  order leakage (use sorted iteration in
  FactionInfluenceSystem), and Python set-iteration order in the
  contiguity BFS (use sorted Territory ID at each frontier
  level).
