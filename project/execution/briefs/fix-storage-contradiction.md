# Phase 5.4 `fix/storage-contradiction` — Adjudication + Implementation Brief

Scout date: 2026-07-08. Checkout inspected: `/home/user/projects/game/babylon` (HEAD `3293833d`, working tree currently on branch `071-reactionary-subject` — treat anchors as dev; all cited files verified at this checkout). Runner Postgres queried read-only at `localhost:5433/babylon_test` (PG 16.14, `pg_isready` OK).

---

## 1. VERDICT: STALE ACCUMULATION + METRIC ARTIFACT — **NOT** a delta-persistence regression. Plus one NEW live P1 found during adjudication (tick-0 commit-marker collision, spec-101).

### 1a. The "1,295 MB/tick full per-tick hex writes" claim is FALSE. Decisive DB evidence:

| Query (all run 2026-07-08, read-only) | Result | Meaning |
|---|---|---|
| `SELECT count(DISTINCT tick), max(tick) FROM dynamic_hex_state` | **2 distinct ticks, max tick 1** (over 14,990,577 rows / 7,832 MB DB) | Not one hex frame exists beyond tick 0 anywhere. Full per-tick writes never happened. |
| `SELECT tick, count(*) FROM dynamic_hex_state_p_df5b8a79… GROUP BY tick` | `tick 0 → 1,884,347 rows` (only row group) | The "450 MB / 1,884,346-row partitions" are each ONE tick-0 frame (US national res-7 ≈ 1.88 M hexes), not per-tick frames. |
| `SELECT is_checkpoint, count(*), min/max(hex_rows_written) FROM tick_commit GROUP BY 1` | 687 non-ckpt commits: max **1**; 249 ckpt commits: max **1** | No envelope since 0029 landed ever wrote more than 1 hex row. Delta emission is in effect on every committed tick. |
| `game_session`: 197 rows (Jul 4 01:29 → Jul 8 06:01); `tick_commit`: 249 distinct sessions, ALL max_tick ≤ 5 | ~200 abandoned sessions | The 7.8 GB = accumulation of abandoned tick-0 hydration frames, dominated by **seven national-scope attempts on Jul 6** (05:12–18:46 UTC: `6e866011`, `6c2e8f9c`, `91fbef1c`, `74798038`, `dfae0bd6`, `df5b8a79`, `e9623b49` — each 1,884,347 rows ≈ 450 MB, each committing ONLY tick 0) + 2 × 400,210-row frames stranded in `dynamic_hex_state_default` (412 MB) + ~21 michigan-canada 45,572-row frames (11 MB each) + dozens of 1–1,045-hex test sessions. |
| `sim:status` avg formula (`.mise.toml:417-420`) | `pg_database_size / (GREATEST(max(tick_commit.tick), max(hex.tick)) + 1)` = 7,832 MB ÷ 6 ≈ **1,295 MB/tick** | The metric divides the WHOLE multi-session DB by the max tick of ANY session. With ~200 abandoned tick-0 frames and max tick 5 (Jul-4 michigan e2e attempts), it fabricates "1295 MB/tick". |

### 1b. Positive proof delta persistence works at design behavior (part a)

- **Code intact & reachable**: `src/babylon/persistence/delta.py` (99 lines, `CHECKPOINT_EVERY_TICKS = 52` at :32, `select_hex_rows_for_emission` :59-91) is called from the ONLY per-tick hex write path: `src/babylon/engine/headless_runner/bridge.py:480-484` inside `persist_tick` (envelope built :539-551, committed via `persist_tick_atomic` at :552). Full frame still feeds the conservation auditor (`hex_frame` at :479, auditor at :531-537). Runner invokes `bridge.persist_tick` for tick 0 at `runner.py:1290` and per tick via `_advance_tick` (`postgres_runtime/_spec_062.py` has no other hex writer; the hydrator uses COPY, see below).
- **Empirical, full 520-tick scale**: committed bundle `reports/sim-runs/sprint5-michigan-delta/manifest.json` storage block: `dynamic_hex_state 455,720 rows = 876.38/tick` over 520 ticks = **exactly 10 yearly checkpoint frames × 45,572 hexes** (ticks 0,52,…,468); `tick_commit 520 rows = 1.0/tick`; whole run DB 337.9 MiB — the ~100 MB-class claim holds (case closed on "stale pre-089 run vs regression": the bloat is post-089 but is *initialization-frame accumulation across ~200 sessions*, not per-tick writes).
- **Fresh run today** (session `b08c0b44`, 2026-07-08 15:12 UTC, tri-county 1,045 hexes): tick 0 = 1,045 rows (hydrator), ticks 1–4 = **0 rows** each. Perfect delta shape.

### 1c. NEW P1 found (live at HEAD): spec-101 tick-0 commit-marker collision — this is what made the telemetry unreadable

`_bootstrap_external_nodes` (`src/babylon/persistence/postgres_initialization.py:589-597`) persists its init-time external-node envelope like this:

```python
    envelope = PerTickTransactionEnvelope(
        session_id=session_id,
        tick=0,
        external_node_rows=rows,
        determinism_hash="0" * 64,  # init-time bootstrap; real hashes start tick 1
    )
    # persist_tick_atomic is monkey-patched onto PostgresRuntime by
    # _spec_062.py at module load; mypy doesn't see the attachment.
    runtime.persist_tick_atomic(envelope)  # type: ignore[attr-defined]
```

`persist_tick_atomic` (`src/babylon/persistence/postgres_runtime/_spec_062.py:270-275`) defaults `write_commit_marker: bool = True`, so **initialize_session writes the tick-0 `tick_commit` row with the placeholder hash `"0"*64`, `hex_rows_written=0`**. The bridge's real tick-0 re-delivery marker (`runner.py:1287-1290` → `bridge.persist_tick` → `_TICK_COMMIT_INSERT`, `_spec_062.py:145-153`) then dies on `ON CONFLICT (session_id, tick) DO NOTHING`. Because migration `0029_tick_commit.sql` ends with `REVOKE UPDATE, DELETE ON tick_commit FROM PUBLIC`, the poisoned row is **permanent** for the session.

DB proof: `tick_commit WHERE tick=0`: 253 rows, **188 with `determinism_hash = repeat('0',64)`**, 189 with `hex_rows_written=0`; **zero** placeholder hashes at tick>0. (The 65 real-hash tick-0 markers come from tests/sessions that never ran `initialize_session`'s bootstrap.)

Consequences: III.7 hash chain broken at tick 0 for every headless session since spec-101 landed (f1183402, Jul 4); tick-0 `hex_rows_written` telemetry reads 0 (which is exactly what prevented the holistic review from adjudicating via `tick_commit`). The hex hydrator itself is CORRECT — it deliberately writes no marker (`hex_hydrator.py:261-267`, `_persist_hex_rows_bulk` COPY path; spec-089 FR-003 comment).

Note the spec-089 commit `c834e76d` (Jul 3) predates spec-101 (Jul 4); the collision is a spec-101 regression against FR-003, invisible because nothing verifies the tick-0 marker after re-delivery.

### 1d. Latent silent-failure mode confirmed in history (motivates Gate A)

Jul-4 michigan sessions (e.g. `580acbfe`, 45,572 hex rows, commits t0–t4) have **0 `hex_spatial_map` rows for their session_id** and all hex rows carry `county_fips NULL` (spec-088 S3 normalization). The bridge template fetch (`_FETCH_TICK_ZERO_HEX_SQL`, `bridge.py:107-120`) filters `COALESCE(m.county_fips, h.county_fips) = ANY(%s)` — for those sessions it returns **empty**, so `_hex_template` was empty and the whole hex envelope pipeline (checkpoint frames at t52+, auditor frame) silently no-opped. The current hydrator does populate the session-scoped map (`_HEX_SPATIAL_MAP_INSERT`, `hex_hydrator.py:282-286`; verified today: `b08c0b44` map join returns 330 rows for `{26163}`, 1,045 tri-county), so the path is healthy NOW — but nothing is loud if it ever regresses again. The only existing guard is `runner.py:972-975` (`report.hex_count == 0` → `ReferenceDataMissingError`), which checks the HYDRATOR count, not the bridge template.

---

## 2. sim:status implementation — what it measures (part b)

`.mise.toml` `[tasks."sim:status"]` :399-431:
- tick/520: `GREATEST(max(tick_commit.tick), max(dynamic_hex_state.tick))` — cross-session (the "tick 5" was the Jul-4 michigan attempts; today's DB says the same).
- avg/tick (:417-420): `pg_database_size('babylon_test') / (that GREATEST + 1)` — cross-session DB size over one session's tick count. **Structurally cannot be trusted in a multi-session DB**; this line manufactured the P1.
- table sizes (:421-426): `pg_stat_user_tables` top-6 by size — surfaced the per-SESSION partitions (`<table>_p_<uuid.hex>`, `partitioning.py:47-53`) which the holistic review misread as per-tick partitions (review §"six per-tick dynamic_hex_state partitions" — wrong; partitioning is `PARTITION BY LIST (session_id)`, migration 0026 + `partitioning.py:34-44`).

## 3. qa:storage-budget mechanics (part d)

`.mise.toml:580-588`: runs a fresh 5-tick strict tri-county headless run, then `tools/storage_budget.py check --bundle $ARTIFACT_DIR --baseline tests/baselines/storage-budget-5t.json`. The storage block is collected per-session at artifact time (`runner.py:1498` → `storage_probe.query_storage_footprint`, `storage_probe.py:81-140`, `session_rows` exact per session; rows/tick deterministic). Baseline (`tests/baselines/storage-budget-5t.json`): `dynamic_hex_state: 209.0` rows/tick (=1045/5), `tick_commit: 1.0`, tolerance 10 %.

- **Would it catch a delta regression?** YES for re-inflation: full per-tick writes ⇒ 1045 rows/tick ≈ 5× budget ⇒ `check_bundle` fails (`storage_budget.py:114-122`). It is per-session, so abandoned-session accumulation can never false-positive it.
- **Two gaps**: (1) it is manual-only (CI has no Postgres leg; REMEDIATION C.12 plans a wayne 3-tick CI-light smoke); (2) it is **one-sided** — "Under-budget passes (that is the point)" (`storage_budget.py:93-97,123-127`), so the §1d silent-zero-writes failure (hex 0 rows/tick) PASSES today. Fix in Step 3.

## 4. Archival lifecycle state (part e)

Healthy and sufficient for cleanup: `tools/archive_sessions.py discover_sessions` (:54-71) discovers via **partition names** (`dynamic_hex_state_p_%` suffix→UUID) plus DEFAULT-partition strays — so the 7 orphan national sessions (which have **no `game_session` row**; headless sessions never get one, by design per `archival.py:322-323` comment) ARE discoverable. `export_session_to_parquet` (`archival.py:172-247`) exports `EXPORT_TABLES` = 9 partitioned families + `contradiction_field` + `simulation_event` (:46-50); `purge_session` (:272-341) verifies manifest row-counts against live (`_verify_manifest_against_live` :250) before `drop_session_partitions` (O(1) partition drop) + DEFAULT-stray/`immutable_reference_*` DELETE sweep. Archive root `/media/user/data/babylon-archives` exists with prior archived sessions (9.4 MB). `edf07b2e` is already status='archived'.

---

## 5. IMPLEMENTATION (aligned to tasks #24–28; TDD; mypy strict; RST docstrings; conventional commits, one commit per step)

### Step 1 — FR-003 fix: initialize_session must not write the tick-0 marker (RED→GREEN)

**RED test** — add to `tests/integration/test_tick_commit.py` (existing classes at :76-118 give the fixture style — `migrated_pool`, `runtime` fixtures):

```python
    def test_initialize_session_leaves_tick0_marker_slot_free(
        self, migrated_pool: Any, runtime: Any
    ) -> None:
        """Spec-089 FR-003: no init-time envelope may claim the tick-0 marker.

        The bridge's tick-0 re-delivery writes the REAL marker (true
        determinism hash + hex_rows_written); tick_commit is append-only
        (0029 REVOKE UPDATE), so a placeholder here is permanent poison.
        """
        session_id = uuid4()
        initialize_session(
            session_id=session_id,
            sqlite_path=_SQLITE_PATH,
            runtime=runtime,
            defines=GameDefines.load_default(),
            start_year=2010,
            scenario_length_years=1,
            counties=["26163"],
            hex_hydration_counties={"26163"},
        )
        with migrated_pool.connection() as conn:
            row = conn.execute(
                "SELECT count(*) FROM tick_commit WHERE session_id = %s",
                (str(session_id),),
            ).fetchone()
        assert row[0] == 0, "initialize_session stole the tick-0 commit-marker slot"
```

Plus the round-trip assertion (same file): after `initialize_session` + `WorldStateBridge(...)`+`hydrate_initial(...)`+`persist_tick(world, 0, real_hash)`, assert `tick_commit` tick-0 row has `determinism_hash == real_hash` and `hex_rows_written == <template size>` (1045 for tri-county / county-scoped count for wayne). Mirror imports/fixtures from `tests/integration/test_two_phase_initialization.py:55-96`.

**Fix (one line)** — `src/babylon/persistence/postgres_initialization.py:597`:

```python
    # Spec-089 FR-003: init-time bootstrap must NOT claim the tick-0
    # commit-marker slot — the placeholder hash is not part of the III.7
    # chain and tick_commit is append-only (0029 REVOKE UPDATE). The
    # bridge's tick-0 re-delivery writes the real marker.
    runtime.persist_tick_atomic(envelope, write_commit_marker=False)  # type: ignore[attr-defined]
```

(Signature confirmed: `persist_tick_atomic(self, envelope, *, write_commit_marker: bool = True)` at `_spec_062.py:270-275`.) Also update the stale hash comment at :593.

### Step 2 — Loud gates so this class of failure can never run silent (task #25)

**Gate A — hex-template liveness (kills §1d silent no-op).** Add a read-only property to `WorldStateBridge` (near `hydrated` at `bridge.py:230-232`):

```python
    @property
    def hex_template_size(self) -> int:
        """Number of tick-0 hex rows cached for per-tick re-emission.

        0 before :meth:`hydrate_initial`; after hydration it MUST equal the
        hydrator's row count — an empty template silently darkens the entire
        hex envelope pipeline (checkpoint frames, conservation-audit frame).
        """
        return len(self._hex_template)
```

Then in `runner.py` immediately after `world = bridge.hydrate_initial(...)` (call at :1008-1015):

```python
        # Phase 5.4 Gate A: the hydrator wrote report.hex_count tick-0 rows;
        # if the bridge's template fetch resolved fewer, the session-scoped
        # hex_spatial_map join regressed (the Jul-4 silent-no-op failure) and
        # every subsequent checkpoint frame would silently write nothing.
        if bridge.hex_template_size != report.hex_count:
            raise ReferenceDataMissingError(
                f"Bridge hex template resolved {bridge.hex_template_size} rows "
                f"but hex hydration wrote {report.hex_count}; "
                "hex_spatial_map join is broken for this session."
            )
```

**Gate B — tick-0 marker verification (kills marker-slot theft forever).** In `runner.py`, module-level helper next to `_check_strict_alarms` (:285), called right after `bridge.persist_tick(world, 0, determinism_hash_t0)` at :1290:

```python
def _verify_tick0_commit_marker(runtime: Any, session_id: UUID, expected_hash: str) -> None:
    """Assert the tick-0 tick_commit row carries the run's real hash.

    Spec-089 FR-003 regression gate: tick_commit is append-only (0029
    REVOKE UPDATE), so a placeholder written by any init-time envelope
    permanently poisons the III.7 chain. Skipped gracefully on pre-0029
    databases (no tick_commit table).

    Raises:
        RunnerError: If the marker is missing or carries a foreign hash.
    """
    with runtime._pool.connection() as conn:  # noqa: SLF001
        has_table = conn.execute("SELECT to_regclass('tick_commit')").fetchone()
        if has_table is None or has_table[0] is None:
            return
        row = conn.execute(
            "SELECT determinism_hash FROM tick_commit WHERE session_id = %s AND tick = 0",
            (str(session_id),),
        ).fetchone()
    if row is None:
        raise RunnerError("tick-0 commit marker missing after bridge re-delivery")
    if row[0] != expected_hash:
        raise RunnerError(
            "tick-0 commit marker carries a foreign hash "
            f"({row[0][:12]}…, expected {expected_hash[:12]}…): an init-time "
            "envelope wrote the marker before the bridge (spec-089 FR-003)."
        )
```

TDD: integration tests in `test_tick_commit.py` — (i) pre-write a placeholder marker, expect `RunnerError`; (ii) real-hash marker passes; unit-test Gate A's comparison as a pure check if you extract it (`_verify_hex_template(hydrated: int, template: int) -> None`) for DB-free coverage under `tests/unit/engine/headless_runner/`.

### Step 3 — Gate C: two-sided storage budget (task #26)

`tools/storage_budget.py`: today under-budget always passes (:123-127). Add per-table **floors** so silent-zero-writes fail:

- `generate_baseline(...)`: add `"floor_pct": 50.0` top-level (or `--floor-pct` arg) and emit `"floors": {table: rows_per_tick}` for the delta-critical tables `("dynamic_hex_state", "tick_commit")`.
- `check_bundle(...)`: after the ceiling loop, for each floored table: `if actual < floor * (1 - ...)` → `ok = False`, `report.append(f"  ✗ {table}: {actual:g} rows/tick below floor …(silent-write regression?)")`. **Backward-compat**: baselines without a `floors` key check ceilings only (old bundles keep passing).
- Regenerate `tests/baselines/storage-budget-5t.json` via the documented flow (`storage_budget.py:16-18`) after Steps 1–2 land: `dynamic_hex_state` stays 209.0 (=1045/5; the tick-0 envelope re-delivery is idempotent no-op rows, count unchanged), `tick_commit` 1.0 — floors e.g. hex ≥ 104.5, tick_commit ≥ 1.0.
- Unit tests in `tests/unit/tools/test_storage_budget.py` (existing style at :38-91): `test_floor_breach_fails`, `test_at_floor_passes`, `test_baseline_without_floors_is_ceiling_only`.

### Step 4 — Session-scope sim:status (task #27)

Rewrite the tick/avg legs of `.mise.toml:399-431` keyed to the most recently writing session (SELECT-only sketch, keep the `2>/dev/null || true` idiom):

```sql
WITH last AS (
  SELECT session_id, max(tick) AS max_tick, count(*) AS commits
  FROM tick_commit
  WHERE session_id = (SELECT session_id FROM tick_commit
                      ORDER BY created_at_utc DESC LIMIT 1)
  GROUP BY session_id
)
SELECT 'session ' || left(session_id::text, 8)
    || ': tick ' || max_tick || '/520 ('
    || round(100.0 * max_tick / 520, 1) || '%), session bytes '
    || pg_size_pretty((SELECT COALESCE(sum(pg_total_relation_size(c.oid)), 0)
                       FROM pg_class c
                       WHERE c.relname LIKE '%_p_' || replace(session_id::text, '-', ''))::bigint)
    || ', ' || pg_size_pretty(((SELECT COALESCE(sum(pg_total_relation_size(c.oid)), 0)
                       FROM pg_class c
                       WHERE c.relname LIKE '%_p_' || replace(session_id::text, '-', ''))
                      / (max_tick + 1))::bigint) || '/tick (this session)'
FROM last;
```

Plus one loudness line so accumulation is visible instead of laundered into an average:

```sql
SELECT 'sessions holding rows: '
    || count(DISTINCT session_id) || ' — total DB '
    || pg_size_pretty(pg_database_size('babylon_test'))
    || ' (run: mise run sim:archive -- list)'
FROM tick_commit;
```

Keep the whole-DB size line but label it `db (ALL sessions)`.

### Step 5 — Cleanup + record repair (task #28)

- Cleanup (owner-run, not in this branch's diff): `mise run sim:archive -- list` then `mise run sim:archive -- archive --all` — discovery is partition-based (`archive_sessions.py:54-71`) so the 7 orphan national frames ARE covered; purge is verify-before-delete (`archival.py:300`) and drops partitions O(1). Expected recovery ≈ 7.4 GB of the 7,832 MB DB. `mise run clean:testdb` is the blunt alternative; prefer archival (keeps III.7-auditable Parquet).
- Record repair: (i) `project/HOLISTIC_REVIEW-2026-07-07.md` — annotate the P1 at :871-872 (and §857, §893, §1031 item (c)) as ADJUDICATED: partitions are per-session not per-tick; whole-DB÷max-tick artifact; delta verified live; (ii) MEMORY.md storage-scaling ⚠️ line — replace "stale pre-089 run vs regression unresolved" with the verdict + the new marker-collision P1 + fix commit; (iii) note the acceptance in `project/REMEDIATION_PLAN.md` Phase 5 exit (:179-180) — "storage adjudication documented with qa:storage-budget green".

---

## 6. Existing test coverage (verified)

- `tests/unit/persistence/test_delta.py` — checkpoint cadence, value-key fields, first-tick/checkpoint full-frame, changed-row-only, determinism (`:43-113`).
- `tests/integration/test_tick_commit.py` — marker in-transaction, zero-hex ticks advance `get_last_committed_tick`, re-delivery idempotent, hydrator-style skip (`:76-118`). **No test covers initialize_session's marker behavior — that is the Step-1 RED hole.**
- `tests/integration/test_asof_reconstruction.py` — sparse-history reconstruction ≡ dense frame (`_TICKS = 8`).
- `tests/unit/tools/test_storage_budget.py` — ceilings only (`:38-91`); `tests/unit/engine/headless_runner/test_storage_probe.py` — block math.
- `tests/baselines/storage-budget-5t.json` — hex 209/tick, tolerance 10 %.

## 7. Verification commands

```bash
# Step 1 RED first, then GREEN:
poetry run pytest tests/integration/test_tick_commit.py -vv          # needs 5433 up (pg_isready guards)
mise run test:q -- tests/unit/persistence/test_delta.py tests/unit/tools/test_storage_budget.py
poetry run pytest tests/integration/test_two_phase_initialization.py -vv   # no regression in init
# Gates A/B:
poetry run pytest tests/integration/test_tick_commit.py -k marker -vv
# Acceptance (REMEDIATION_PLAN.md:148 — 'qa:storage-budget is the acceptance'):
mise run qa:storage-budget          # 5-tick strict tri-county run + budget check, must be green
mise run check:quick                # ruff + format + mypy strict
# Post-fix DB spot-check (fresh session should now have a REAL tick-0 hash):
mise run db:sql -- "SELECT determinism_hash <> repeat('0',64) AS real_hash, hex_rows_written FROM tick_commit WHERE tick=0 ORDER BY created_at_utc DESC LIMIT 1"
```

Commit sequence (one per step, conventional): `fix(persistence): spec-089 FR-003 — init bootstrap must not claim the tick-0 commit marker` → `feat(runner): Gate A hex-template liveness + Gate B tick-0 marker verification` → `feat(qa): two-sided storage budget floors (spec-087 extension)` → `fix(mise): session-scope sim:status metrics` → `docs(truth): storage-contradiction adjudication record`.
