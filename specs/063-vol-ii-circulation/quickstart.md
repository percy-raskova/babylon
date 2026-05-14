# Quickstart: Vol II Circulation System with LODES OD Integration

**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Date**: 2026-05-13

This walkthrough exercises the full spec 063 surface end-to-end against a live Postgres test pool. Each numbered section corresponds to one user story or critical integration point and produces a verifiable observation.

The matching automated walkthrough script (created during Phase 2 implementation) lives at `tests/scripts/verify_063_circulation_walkthrough.py` and prints `§N OK` per section, mirroring spec 062's `quickstart_062_walkthrough.py` pattern.

## Prerequisites

- `babylon-pg-isolated` Postgres container running on `localhost:5433` (or `BABYLON_TEST_PG_DSN` set)
- Spec 062 migrations applied (`0001_*` through `0013_boundary_flow_register`)
- Spec 063 migration applied (`0014_lodes_od_matrix`)
- LODES dataset present at `/media/user/data/babylon-data/lodes/` (verified by spec 063 research §1)
- Crosswalk file present at `/media/user/data/babylon-data/lodes/us_xwalk.csv.gz`

## §1 — Initialize a Detroit Session and Hydrate LODES Matrix

**Goal**: Confirm session init reads the on-disk LODES files for years 2010–2021 and persists them to `immutable_reference_lodes_od_matrix`. Demonstrates FR-001 / FR-001a / FR-001b / FR-002 / FR-003 / FR-007.

```python
from uuid import uuid4
from babylon.persistence.postgres_initialization import initialize_session
from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.constants import DETROIT_TRI_COUNTY  # Wayne, Oakland, Macomb FIPS codes

session_id = uuid4()
runtime = PostgresRuntime(dsn="dbname=babylon_test host=localhost port=5433 ...")
runtime.initialize()

report = initialize_session(
    runtime=runtime,
    session_id=session_id,
    counties=DETROIT_TRI_COUNTY,
    start_year=2010,
    scenario_length_years=15,  # 2010-2024 → LODES years 2010-2021 (post FR-004 clamp for 2022-2024)
)

assert report.external_node_count == 9             # spec 062 — Canada + 8 international + rest_of_usa
assert report.lodes_year_count == 12               # spec 063 — 2010-2021 cleanly hydrated
assert report.lodes_row_count > 0                  # spec 063 — Detroit tri-county subset is non-empty

print(f"§1 OK — {report.lodes_year_count} LODES years × {report.lodes_row_count:,} rows hydrated")
```

**Expected output**: `§1 OK — 12 LODES years × ~340,000 rows hydrated` (rough estimate for tri-county).

**What this proves**: spec 062's external-node bootstrap already ran; spec 063's hydrator ran on top of it; the FR-026 fail-fast invariant did not fire because Canada is present in the registry.

## §2 — Build the Year Matrix and Inspect the Sparse Shape

**Goal**: Confirm the loader builds a `scipy.sparse.csr_matrix` with the expected dimensions and that the row-sums vector is cached. Demonstrates FR-001 (scipy.sparse representation) / FR-007 (in-study-area pruning).

```python
from babylon.economics.lodes_commute_matrix import LODESCommuteMatrixLoader
from pathlib import Path
from babylon.constants import DETROIT_TRI_COUNTY_HEXES_RES7  # frozenset[str]

loader = LODESCommuteMatrixLoader(
    lodes_root=Path("/media/user/data/babylon-data/lodes"),
    crosswalk_path=Path("/media/user/data/babylon-data/lodes/us_xwalk.csv.gz"),
    study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
    study_area_states=frozenset(["26"]),
)

matrix_2010 = loader.load_year(2010)
print(f"  shape={matrix_2010.matrix.shape}, nnz={matrix_2010.matrix.nnz}")
print(f"  origins={matrix_2010.matrix.shape[0]}, dest cols by kind: {matrix_2010.dest_kind_breakdown_str()}")
print(f"  row_sums: min={matrix_2010.row_sums.min()}, max={matrix_2010.row_sums.max()}, "
      f"zeros={int((matrix_2010.row_sums == 0).sum())}")

assert matrix_2010.matrix.format == "csr"          # GATE-4 — Constitution II.12 sparse representation
assert matrix_2010.matrix.shape[0] >= 1500         # roughly 1,700 study-area hexes ± LODES coverage
assert matrix_2010.matrix.nnz > 10_000             # ~10K-30K nonzeros expected for tri-county
assert matrix_2010.matrix.nnz < 100_000            # bounded matrix: stays well within the < 100ms tick budget per plan.md Performance Goals

print("§2 OK — CSR matrix built with bounded shape; row_sums cached")
```

**What this proves**: GATE-4 (sparse representation) holds; FR-007 pruning is effective (matrix is small enough for fast tick-time multiplication).

## §3 — Run One Tick and Verify Circulation Conservation

**Goal**: Step the engine once and confirm FR-010 conservation — total in-study-area `v` plus the magnitude of all `COMMUTE_OUT` rows added equals the pre-circulation total. Demonstrates User Story 1 / FR-009 / FR-010 / FR-014 / FR-015 / SC-002.

```python
from babylon.engine.simulation_engine import SimulationEngine
from babylon.engine.event_bus import EventBus

bus = EventBus()
engine = SimulationEngine.from_session(runtime=runtime, session_id=session_id, event_bus=bus)

# Capture the pre-circulation v-total via aggregation view
pre_total_v = runtime.fetch_v_total_in_study_area(session_id, tick=0)

# Run one tick (the engine's per-tick transaction wraps the entire pipeline incl. spec 063 sub-stages)
engine.run_tick()

# Capture post-circulation v-total + boundary-out total
post_total_v = runtime.fetch_v_total_in_study_area(session_id, tick=1)
boundary_out_total = runtime.fetch_boundary_register_sum(
    session_id, tick=1, flow_type="commute_out", source_kind="hex",
)

residual = abs(pre_total_v - (post_total_v + boundary_out_total))
tolerance = 1e-9 * pre_total_v
assert residual <= tolerance, f"Conservation violated: residual={residual}, tolerance={tolerance}"

print(f"§3 OK — v conservation: pre={pre_total_v:.2f}, "
      f"post={post_total_v:.2f}, boundary_out={boundary_out_total:.2f}, residual={residual:.2e}")
```

**Expected**: `residual` is ~0 (well below the 1e-9 × pre_total_v tolerance).

## §4 — Verify Φ Distribution Wiring (T079)

**Goal**: Confirm `ImperialRentSystem.step()` invoked `distribute_phi_week_to_counties()` per FR-017 / FR-018 / FR-019. Demonstrates User Story 2 / SC-008.

```python
drain_rows = runtime.fetch_boundary_register(
    session_id,
    tick=1,
    flow_type="drain_edge",
    source_kind="external",
    dest_kind="county",
)

assert len(drain_rows) > 0, "FR-017/018 wiring is dead — no DRAIN_EDGE rows landed at county scale"

# Verify Φ_week-conservation: sum of magnitudes from each external source equals phi_year/52
sums_by_source = {}
for row in drain_rows:
    sums_by_source.setdefault(row.source_node_id, 0.0)
    sums_by_source[row.source_node_id] += row.magnitude

for source_node_id, weekly_sum in sums_by_source.items():
    expected_weekly = runtime.fetch_external_node_phi_year_inflow(session_id, source_node_id) / 52
    residual = abs(weekly_sum - expected_weekly)
    assert residual <= 1e-9, f"FR-021 weekly Φ-distribution residual {residual} exceeds tolerance for {source_node_id}"

print(f"§4 OK — {len(drain_rows)} DRAIN_EDGE rows landed at county scale; "
      f"per-source weekly sums match phi_year/52 within tolerance")
```

**Note**: per research.md §4, only external sources with `phi_year_inflow > 0` for the active simulated year fire DRAIN_EDGE rows. Sources whose Hickel data shows zero contribute zero rows but the loop still completes successfully.

## §5 — Verify Detroit-Windsor Routing (T080) via Synthetic Injection

**Goal**: Confirm the FR-023 Canadian classification rule fires for synthetic Canadian-coded rows and that the FR-026 fail-fast invariant guards against missing-Canada misconfiguration. Demonstrates User Story 3 / SC-004.

Per research.md §4, canonical LODES has no Canadian destinations, so this check uses a synthetic injection at the unit-test layer.

```python
from babylon.engine.systems.cross_border_commute import CrossBorderCommuteClassifier

classifier = CrossBorderCommuteClassifier(
    study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
    study_area_states=frozenset(["26"]),
    domestic_states=frozenset(["01", "02", ..., "78"]),  # all US FIPS state codes
)

# Synthetic Canadian-coded destination (state-prefix 99 — outside US FIPS range)
canada_classification = classifier.classify("990001234567890")
assert canada_classification.dest_kind.value == "external"
assert canada_classification.dest_node_id == "canada"

# Toledo, OH (state 39 — domestic but out-of-study-area)
toledo_classification = classifier.classify("390951234567890")
assert toledo_classification.dest_kind.value == "external"
assert toledo_classification.dest_node_id == "rest_of_usa"

# Detroit hex (in-study-area)
detroit_classification = classifier.classify("260010001001045")
assert detroit_classification.dest_kind.value == "hex"
assert detroit_classification.dest_node_id != "canada"
assert detroit_classification.dest_node_id != "rest_of_usa"

# FR-026 fail-fast: re-init a session with Canada removed from external nodes,
# inject a synthetic Canadian row, expect IntegrityError on initialization
import pytest
from babylon.persistence.postgres_initialization import (
    initialize_session,
    SessionInitializationError,
)
with pytest.raises(SessionInitializationError, match="canada.*not present in external_node registry"):
    initialize_session(
        runtime=runtime,
        session_id=uuid4(),
        counties=DETROIT_TRI_COUNTY,
        start_year=2010,
        scenario_length_years=15,
        external_node_overrides=frozenset(["china", "eu", "rest_of_usa"]),  # NO canada
        synthetic_lodes_canadian_rows=True,                                  # forces FR-026 trigger
    )

print("§5 OK — Windsor → canada, Toledo → rest_of_usa; FR-026 fail-fast invariant holds")
```

## §6 — Verify Paired TRADE_EDGE Emission (FR-030a)

**Goal**: Confirm every cross-boundary `COMMUTE_OUT` is matched by a paired `TRADE_EDGE` row with swapped source/dest and equal magnitude. Demonstrates FR-030a / FR-030c / SC-008.

```python
out_rows = runtime.fetch_boundary_register(
    session_id, tick=1, flow_type="commute_out", source_kind="hex", dest_kind="external",
)
in_rows = runtime.fetch_boundary_register(
    session_id, tick=1, flow_type="trade_edge", source_kind="external", dest_kind="hex",
)

assert len(out_rows) == len(in_rows), \
    f"Paired-emission contract FR-030a violated: {len(out_rows)} COMMUTE_OUT rows but {len(in_rows)} paired TRADE_EDGE rows"

# Index in_rows by (source, dest) for pair lookup; the paired row swaps these
in_by_pair = {(r.source_node_id, r.dest_node_id): r for r in in_rows}

for out in out_rows:
    pair_key = (out.dest_node_id, out.source_node_id)  # paired row swaps source/dest
    assert pair_key in in_by_pair, f"COMMUTE_OUT from {out.source_node_id} to {out.dest_node_id} has no paired TRADE_EDGE"
    paired = in_by_pair[pair_key]
    assert abs(paired.magnitude - out.magnitude) < 1e-9, \
        f"FR-030a magnitude mismatch: COMMUTE_OUT={out.magnitude}, paired TRADE_EDGE={paired.magnitude}"

print(f"§6 OK — {len(out_rows)} COMMUTE_OUT rows each have a paired TRADE_EDGE with equal magnitude")
```

## §7 — Verify Determinism (SC-005)

**Goal**: Re-run the same scenario from a fresh session with the same seed and confirm the per-tick state is bit-identical.

```python
session_id_2 = uuid4()
report_2 = initialize_session(
    runtime=runtime, session_id=session_id_2, counties=DETROIT_TRI_COUNTY,
    start_year=2010, scenario_length_years=15,
)
engine_2 = SimulationEngine.from_session(runtime=runtime, session_id=session_id_2, event_bus=EventBus())
engine_2.run_tick()

# Compare per-tick determinism hash
hash_1 = runtime.fetch_tick_determinism_hash(session_id, tick=1)
hash_2 = runtime.fetch_tick_determinism_hash(session_id_2, tick=1)

assert hash_1 == hash_2, f"Determinism violated: session 1 hash {hash_1} ≠ session 2 hash {hash_2}"

print(f"§7 OK — bit-identical determinism hash across two sessions: {hash_1[:16]}...")
```

## §8 — Border Commute Synthesis (Option B Path)

**Goal**: Verify the optional `BorderCommuteSynthesisLoader` produces non-zero Canadian-bound `COMMUTE_OUT` rows when enabled. Demonstrates FR-031 / FR-032 / FR-033 / FR-034 / FR-035 / FR-036 / SC-011 / SC-012.

**Operator prerequisite** (one-time data acquisition):

```bash
# Download BTS Border Crossing Data
mkdir -p data-trove/border_crossings/
curl -L "https://data.bts.gov/api/views/keg4-3bc2/rows.csv" \
     -o data-trove/border_crossings/bts_border_crossings.csv

# Optional: download StatCan Frontier Counts (for canada_to_us direction)
# Manual export from https://www150.statcan.gc.ca/n1/en/catalogue/71-607-X2023020
# → save as data-trove/border_crossings/statcan_frontier_counts.csv
```

**Walkthrough**:

```python
from babylon.config.defines import GameDefines
from babylon.economics.border_commute_synthesis import BorderCommuteSynthesisLoader

# Construct with synthesis enabled
defines = GameDefines(
    enable_border_commute_synthesis=True,
    border_commute_share=0.50,  # WWE 2017 anchor
)

session_id_synth = uuid4()
report_synth = initialize_session(
    runtime=runtime,
    session_id=session_id_synth,
    counties=DETROIT_TRI_COUNTY,
    start_year=2010,
    scenario_length_years=15,
    defines=defines,
)

assert report_synth.border_synthesis_row_count > 0, "FR-031/035 wiring is dead — no synthesized rows landed"

# Run one tick
engine_synth = SimulationEngine.from_session(runtime=runtime, session_id=session_id_synth, event_bus=EventBus())
engine_synth.run_tick()

# Verify SC-011: non-zero Canada-bound COMMUTE_OUT rows
canada_rows = runtime.fetch_boundary_register(
    session_id_synth, tick=1, flow_type="commute_out", source_kind="hex", dest_kind="external",
)
canada_rows = [r for r in canada_rows if r.dest_node_id == "canada"]
assert len(canada_rows) > 0, "SC-011 violated: no Canada-bound COMMUTE_OUT rows produced"

# Verify FR-035 paired-emission contract holds for synthesized rows too
canada_paired = runtime.fetch_boundary_register(
    session_id_synth, tick=1, flow_type="trade_edge", source_kind="external", dest_kind="hex",
)
canada_paired = [r for r in canada_paired if r.source_node_id == "canada"]
assert len(canada_paired) == len(canada_rows), \
    f"FR-030a violated for synthesized rows: {len(canada_rows)} COMMUTE_OUT vs {len(canada_paired)} TRADE_EDGE"

# Verify SC-011 annual conservation (52-tick aggregate matches BTS-derived annual estimate within 5%)
weekly_synth_total = sum(r.magnitude for r in canada_rows) * 52  # extrapolate one tick × 52
bts_annual_estimate = runtime.fetch_bts_annual_commuter_estimate(session_id_synth, year=2010)
relative_error = abs(weekly_synth_total - bts_annual_estimate) / bts_annual_estimate
assert relative_error <= 0.05, f"SC-011 violated: synth annual={weekly_synth_total:.0f}, BTS={bts_annual_estimate:.0f}, err={relative_error:.1%}"

print(f"§8 OK — synthesis enabled, {len(canada_rows)} Canada-bound rows; annual error {relative_error:.1%}")
```

**Disabled path verification (SC-012)**:

```python
# Default: enable_border_commute_synthesis=False
defines_off = GameDefines(enable_border_commute_synthesis=False)
session_id_off = uuid4()
report_off = initialize_session(
    runtime=runtime, session_id=session_id_off, counties=DETROIT_TRI_COUNTY,
    start_year=2010, scenario_length_years=15, defines=defines_off,
)
assert report_off.border_synthesis_row_count == 0, "SC-012 violated: synth produced rows when flag was False"

# After running one tick, zero canada-bound rows
engine_off = SimulationEngine.from_session(runtime=runtime, session_id=session_id_off, event_bus=EventBus())
engine_off.run_tick()
canada_rows_off = runtime.fetch_boundary_register(
    session_id_off, tick=1, flow_type="commute_out", source_kind="hex",
    dest_node_id="canada",
)
assert len(canada_rows_off) == 0, "SC-012 violated: canada rows in default-disabled path"

print("§8 OK (disabled path) — zero canada-bound rows when synthesis flag is False")
```

## End-to-End Smoke

The script `tests/scripts/verify_063_circulation_walkthrough.py` runs all eight sections above in sequence and prints `§N OK` for each. CI gates on this script returning exit 0 after every spec 063 commit.

```bash
poetry run python tests/scripts/verify_063_circulation_walkthrough.py
# Expected output:
#   §1 OK — 12 LODES years × ~340,000 rows hydrated
#   §2 OK — CSR matrix built with expected shape; row_sums cached
#   §3 OK — v conservation: pre=..., post=..., boundary_out=..., residual=0.00e+00
#   §4 OK — N DRAIN_EDGE rows landed at county scale; per-source weekly sums match phi_year/52
#   §5 OK — Windsor → canada, Toledo → rest_of_usa; FR-026 fail-fast invariant holds
#   §6 OK — N COMMUTE_OUT rows each have a paired TRADE_EDGE with equal magnitude
#   §7 OK — bit-identical determinism hash across two sessions: ...
#   §8 OK — synthesis enabled, N Canada-bound rows; annual error X.X%
#   §8 OK (disabled path) — zero canada-bound rows when synthesis flag is False
```

## Performance Sanity Check

The walkthrough also reports per-tick wall time and verifies SC-007 (Vol II Circulation ≤ 10% of the four-flow-stage budget).

```bash
poetry run python tests/scripts/verify_063_circulation_walkthrough.py --benchmark
# Adds:
#   Per-tick wall-time breakdown (mean over 50 ticks):
#     Production:        125ms
#     Imperial Rent in:   31ms
#     Vol II Circulation: 12ms       ← spec 063 contribution; 12/(125+31+88+155)=3.0% of pipeline
#     Equalization:       88ms
#     Distribution:      155ms
#   SC-007 budget: <= 10% × 399 = 40ms; actual 12ms — PASS
```
