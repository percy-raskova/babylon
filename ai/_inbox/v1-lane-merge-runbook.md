# v1.0.0 lane merge runbook (controller working notes, 2026-07-21)

Live integration order + cross-lane checkpoints for the six parallel lanes forked off the
T1.0 contract commit (84d8405a). Fast-dev mode: lanes commit locally; heavy ceremony
(qa:regression byte gate, vault regression, baseline blessing) fires at MERGE time only,
single-flight in this controller. This file is my scratch — supersede freely.

## LANE STATUS (live — controller poll 2026-07-21 ~18:25)

| Lane | Branch | HEAD | Workflow | Merge gate |
|---|---|---|---|---|
| T1.1 seam-severity | lane/t11-seam-severity | c0c9a731 | **✓ DONE** (17/17, 0 err; U1–U7, mutation-verified) | merges 1st — READY |
| T1.2 keel | lane/t12-keel | c4dc2f0c | **✓ DONE** (20/20, 0 err; K1–K5 verified in-code) | **HELD** behind T1.1; clean, merge-ready |
| Vol I | lane/vol1-value-production | 18c2e2d9 | RUNNING (U8 done 20:0x, ADR114; U7 a80616f2 + vocab fix c435d3a6 done; ONLY U9 monitoring + ceremony remain) | 3rd |
| Vol II | lane/vol2-circulation | d694928d | RUNNING (U6a vocab-allowlist narrowing 20:27; U4 lit step 19:29 ADR120/123; U6b seam-rows DEFERRED→rebase; U5 = Vol I's) | 4th (rebase on Vol I) |
| T4 core | lane/t4-campaign-core | 1e4fbe2c | **✓ DONE** (18/18, 0 err; C1–C6, no blockers) | **HELD** behind all; merges last |
| T7 installer | lane/t7-installer | df41a963 | alpha (separate) | post-Gate-3 (T7-beta) |

**DEPENDENCY HEAD CLEARED.** T1.1 done. THREE lanes home (T1.1, T1.2, T4); only Vol I + Vol II
still building. The merge cascade is UNBLOCKED — but held for single-flight safety: no heavy
gate fires while >1 lane workflow is live (Vol I + Vol II = 2 live). **Trigger: when Vol I +
Vol II both complete, run the full cascade single-flight** in order T1.1 → T1.2 → Vol I → Vol
II → T4, `mise run check` + (where drift) qa:regression/baseline per merge. Merging T1.1/T1.2
early buys nothing — Vol I/II forked from 84d8405a and rebase at THEIR merge time regardless.
T1.2 verified units: K1 stdout-contract + default_level, K2 DSN seam (production.py HOST
clobber + vault_regression bypass closed), K3 5-var RAYON pin == canonical, K4 severity pins
restored, K5 ledger.

### T1.1 merge notes (adversarial review, mutation-verified)
U1 derived severity catalog (`models/event_severity.py`): drift-guard reds on any un-rationaled
tier change; reconciliation pin independent; 16 principled drifts (8 warn→crit, 8 warn→info)
each rationaled. U2 single-source. U3 ∂L seam-algebra (`sentinels/seam_algebra/`): disconnected-
subsystem check wired into `check:seam-algebra` → `check:sentinels-static` → fast CI gate;
mutation-verified non-vacuous (reds on `anisotropic_observation_error`, the F-EC-1 witness).
U7 wall-clock-call-site check + F-* closeout. Non-blocking, carry to merge/ceremony:
- **[ceremony]** the §7 severity ceremony note must record the **37-member unclassified→warning
  floor flip** (when U2's `resolve_severity` lands) ALONGSIDE the 16-row drift table — it's
  design-sanctioned (III.11) and matches the Archive/TUI successor (already warns-on-miss); only
  the legacy/disposable web client changes. Don't let the ceremony disclose only 16 of the picture.
- **[owed → U6]** Amendment-S grep-gate scans only `engine|domain`; `formulas/` (feeds the hash)
  is uncovered. No live violation exists; U6 chartered to widen to the full physics surface.
- cosmetic: `.mise.toml:132` parent `check` desc still says "ALL 14 sentinels" (now 15+) — 1-char fix.

### T4-core merge notes (adversarial review, 2026-07-21)
C1–C6 present: composition root + real boot (C1 `02550de9`); lobby→briefing→campaign shell
(C2 `6cf0d50f`) + record_progress writeback (`a846528d`); paced tick driver wired into boot
(C3 `53cfca4b`+`ab360493` — CLOSES C1's "no advance in production" finding); chronicle
adapter → production (C4); incremental dirty-entity baker (C5 `9243dd35` — nationwide);
autosave-cadence save wire (C6). Gates green (lint:imports 9/9, mypy strict, 19 tests on the
REAL 30-system engine). Non-blocking, verify/file at merge:
- **[design-relevant]** campaign-runtime envelope carries EMPTY `audit_log_rows` → `babylon
  play` persists only the identity-stamp `determinism_hash` (sha256 session:tick:seed), NOT
  the ConservationAudit CONTENT hash the headless/bridge path computes. Consistent with the
  known "hash chain aspirational / III.13 PENDING" fact. **Consequence for the interface-shell
  BDD gate (layer 3):** the determinism assertion is REPLAY-IDENTITY for v1.0; true content-
  determinism waits on III.13. The plan must state which hash the gate asserts on.
- advance_tick non-atomic ordering (persist before mark_turns_resolved + bake) — crash
  window, low severity, undriven path.
- coverage gap: real ArchiveTickBaker × real Wayne tick-0 bake only inspection-verified.
- uncommitted `ai/_inbox/PROGRAM_v1_0_0_playable_archive.md` edit left in the t4 worktree —
  reconcile (commit or discard) at merge.
- doc nit: runner.py `_advance_tick` says "21 systems" (should be 30).

## Merge order (dependency-forced)

1. **T1.1 seam-severity** merges FIRST among the reflective/keel lanes — it publishes the
   derived `event_severity` catalog + `resolve_severity` single-source that T4's autopause
   and the chronicle consume. Physics-neutral (G∘P projection); no baseline drift expected.
2. **T1.2 keel** next — Observability Spine + DSN unification + launcher determinism seal +
   WO-52b ports + assumptions ledger. DSN seam is a precondition for T7-beta and the Vol II
   rebase's runner wiring. No baseline drift expected.
3. **Vol I** before **Vol II** (§10 tie-break) — both edit
   `domain/economics/tick/system/__init__.py` (their room-partition banners keep them
   disjoint, but the file still merges). Vol I owns the runner-parity fix both service
   families need. Vol I ceremony = REAL value drift expected (declare it). Vol II rebases
   on merged Vol I, reruns its battery; Vol II ceremony = likely all-zero-with-reason
   (vol2_step still gated until its U4 lights it).
4. **T4-core** merges after T1.1 (needs the severity seam) — the composition root + paced
   driver + chronicle adapter + dirty baker + save wire. Snapshot goldens may re-bake
   (ArchiveApp layout change → all goldens; that's render-tier, regenerate freely, NOT a
   ceremony). Vault manifest goldens ARE ceremony — bless if they move.
5. **T7-beta** (not yet built) after T1.2's DSN seam — embedded PG cluster manager.

## Cross-lane checkpoints to verify AT merge review (do not let these slip)

- [ ] **ADR renumbers executed**: Vol I → 110/111 (was 108/109), Vol II → 120/121. Both got
      binding controller notices prepended to their prompts + block allocation in index meta
      (df087dce). If a lane didn't renumber, do it mechanically before its merge; mainline
      ADR108 = Amendment AA is immovable.
- [ ] **DSN TCP-loopback fallback** (Windows/AA disclosure, keel K2): resolver documents a
      TCP-loopback point beside the unix-socket default. Confirm present; it's the one-line
      Windows optionality seam the AA amendment named.
- [ ] **PostgresRuntime ⊇ GameRuntimeStore protocol** (T4): verify `create_session` grew the
      `session_id` kwarg on BOTH the protocol and PostgresRuntime (C2 identity unification),
      and `persist_tick_atomic`/`get_last_committed_tick` structurally satisfy the protocol.
      In-flight Pyright noise during the build; must be mypy-clean at merge (it will be, or
      the lane's pre-commit blocked the commit).
- [ ] **Severity single-source**: after T1.1 merges, the web `_EVENT_SEVERITY` and Archive
      `EVENT_SEVERITY` twin dicts are DEAD (both route through `resolve_severity`). Grep to
      confirm no third hand-copy survives; the equality sentinel should enforce it.
- [ ] **Vol II LODES artifact determinism**: gzip MTIME pinned (432ea99a) — confirm the
      committed artifact is byte-stable across regenerations (CI-no-drive).
- [ ] **Vol II U6b — seam-algebra registry rows owed AT REBASE**: correctly deferred
      (T1.1's `sentinels/seam_algebra/` doesn't exist in the vol2 tree pre-cascade).
      When Vol II rebases onto merged Vol I + T1.1, it MUST contribute its circulation
      seam rows (gate-satisfaction/stub-vs-calculator entries for the lit vol2_step) and
      rerun its battery — track it as part of the rebase, not a new unit.
- [ ] **THIRD live hex-query citation** (Vol II U6a finding, d694928d):
      `engine/simulation_engine.py:235` — the determinism-hash hex-row collector still
      queries `hex` with no production stamper (empty-set fold in the hash path;
      deterministic but dead). The hex allowlist entry was NARROWED, not retired.
      Feeds Material Triad W1 item 5's disposition (now three citations, not two).
- [ ] **§10.2 dormancy-sentinel hoist**: lives in T1.1 keel, NOT the Vol lanes (recorded
      ADR103). Confirm neither Vol lane also built one (dedupe).
- [x] **U5 runner-parity — LANDED by Vol I** (commit `4627fc23`, peer report
      a3fac268ce84b6d82, 2026-07-21 18:xx). Per §10.3/ADR103 §10.2 the shared runner-parity
      unit is Vol I's; the lane reached it first and, per the "whoever-reaches-it-first lands
      BOTH families" contract, wired BOTH `create_vol1_services` (reserve_army/productivity/
      dispossession/transition_engine) AND `create_circulation_services` (turnover/inventory/
      depreciation) inside `_build_economics_overrides`'s existing `if scope_fips:` branch,
      reusing the already-loaded fred_cache — mirrors `web/game/engine_bridge.py` Task 20b/21b.
      New test `tests/unit/engine/headless_runner/test_vol1_vol2_parity_wiring.py` (RED→GREEN);
      163-test headless_runner suite green; mypy/ruff clean.
      **MERGE-TIME DISPOSITION:** (a) if the Vol II lane ALSO wired create_circulation_services
      into its own runner.py copy, resolve the conflict toward Vol I's version (identical
      intent) — harmless dedupe, NOT a re-wire; (b) do NOT re-run this unit. **VOL II LANE:
      treat U5/runner-parity as SATISFIED — verify + scoped-test only, never re-touch
      `_build_economics_overrides`.**
- [x] **Vol I vocabulary RED — RESOLVED in-lane 19:43** (`c435d3a6`): U6's fixture stamped
      `subsistence_threshold` on a `territory` node; fix dropped the fabricated attribute
      (proven non-load-bearing — production filters by node type alone). check:vocabulary +
      48-test file + full 15-sentinel static battery verified green by the lane. No
      exemption added. U7 itself landed as `a80616f2` (new `check:formula-registration`
      sentinel, counts 14→15 static; ADR113).
- [ ] **Vol I U5 ADR is MISSING** (lane's own report, 19:43): the runner-parity unit
      (`4627fc23`) never wrote its ADR. Write it mechanically at merge review if U8/U9
      don't — it's the shared-unit disposition record both volumes cite (ADR103 §10.3).
- [ ] **Vol I U8 (18c2e2d9, ADR114) merge obligations**: (a) ACCEPTED deviation — no
      CapitalVolumeIDefines built (zero parameter-bearing coefficients existed to home;
      empty file = placeholder violation; ADR114 records it — don't re-litigate at review);
      (b) **confirm zero drift from `min_employed_fraction` wiring** at the single-flight
      qa:regression run — lane argues it only bites at reserve_ratio=1.0, outside the 6
      scenarios' range, but did NOT run the gate (correct per single-flight rule); if drift
      appears it joins the U5-activation attribution table, not a surprise; (c) the Vol I
      ceremony/PR disclosure must note the **3 removed defines.yaml keys**
      (DispossessionDefines weight_wage_theft/weight_incarceration_seizure/
      weight_pension_default — dead-code removal, zero consumers, no proxy existed) since
      defines.yaml is the player-facing moddable surface.
- [ ] **Baseline drift now has a NAMED cause (Vol I ceremony)**: U5 genuinely ACTIVATES
      `_compute_vol1_layer` (median_wage wage-pressure) AND `_compute_circulation_layer`
      (circulation_state) for every headless run whose `scope_fips` is non-empty (always, in
      real runs) at any year boundary with FRED coverage. median_wage / circulation_state /
      downstream phi_hour / wealth channels move in EVERY scenario. This is the "Vol I = real
      value drift expected" ceremony line — attribute the drift table to U5 activation at
      blessing time; do NOT let it read as a surprise. (Vol II's own ceremony stays "likely
      all-zero-with-reason" until vol2_step is lit by its U4.)

## Post-cascade queue (order among these decided at fork time; none gate Gate 3)

1. **Wiring-doctrine enforcement train** (ADR109 §7, 8 units) — FIRST of the queue: it
   extends the just-merged T1.1 seam_algebra + T1.2 spine estates, and every later wiring
   unit (Material Triad W1, interface-shell drivers) then lands under its registry.
2. **Material Triad W1** (territory repair + `metabolic` registration) — needs merged
   catalog + T1.1 stub-vs-calculator.
3. **Interface-shell plan** (11 tasks, BD-queued behind cascade + T3's EconomyView).

## Post-merge cleanup units (from the fork's research passes — file as small PRs, not blockers)

- **Choropleth re-sum anti-pattern**: state-tier choropleth re-sums hex rows in Python when a
  SQL view already computes the identical SUM (SYSTEM_DECOMPOSITION_OPTIONS.md finding). Small
  fix, real intensive-aggregation-adjacent smell. **This is the type case for the ruling below.**

### BD ruling 2026-07-21 — a Python-loop bottleneck is a signal to fix the ENGINE, never to relax correctness

BD: "if pythonic looping is a bottleneck thats another sign that whatever engine is running
that needs to be rewritten in a better language that can handle that, or that method should be
refactored." Binding disposition of the nationwide-perf question:

- A hot-loop bottleneck has exactly TWO legitimate responses — **refactor** the method or
  **rewrite** it in a faster language. Relaxing determinism to hide it is NOT one (the fork
  already proved it buys nothing: the bottleneck is pure-Python O(territory) loops with no
  BLAS/numpy in them, so BLAS=1 stays, Tier A stays untouched).
- **Diagnose per loop before touching it** (profile first, the machine-safety "catch loudly"
  discipline applied to CPU): (a) *accidentally-Python* loops — ones that should be a SQL
  aggregate or a vectorized op (the choropleth re-sum is exactly this) — get REFACTORED, no
  new language needed; (b) *irreducibly per-node* loops — linear, per-node graph reads +
  branching that don't vectorize — get REWRITTEN in Rust via the paused hypergraph-rs PyO3
  lane, under the III.12b tolerance leg the Constitution already pre-authorizes.
- Never blanket-rewrite (most loops refactor) and never blanket-relax (correctness is not the
  variable). v1.0 impact: NONE on the critical path — Wayne (the shipping default) is small;
  the bottleneck only bites nationwide, which is gated advanced mode. The rewrite-or-refactor
  sweep is a post-1.0 program, profiled and diagnosed loop by loop.
- **County-count discrepancy**: repo says 3,153 counties, plan/memory say 3,191. Reconcile the
  canonical number (affects the nationwide-scale honesty note + the ~22h full-campaign figure).
- **Nationwide = gated advanced mode**: Wayne is the shipping default + CI golden scenario;
  nationwide (~22h full campaign at real scale) stays behind the explicit resource gate with
  the incremental dirty-entity baker. Confirm T4's baker is scenario-bounded.

## Standing BD-disposition items (NOT lane work — surfaced by the fork's research, BD rules when ready)

- Ratify "Rust-only compiled lane, Haskell excluded" as a standing ADR (closes the reopened
  algebra-language question). Algebra stays Python/Pydantic for v1.0 regardless.
- pgrx `babylon_graph` extension: committed post-1.0 direction or shelved seed? (plrust is
  dead — that door's closed; AGE is healthy but post-1.0-only.)
- ConceptCard `$$` math construct (BFM positioning open question).
- Tick-compressor / narrative-vector-space (research seed — post-1.0 AI phase).

## Gate 3 assembly (the actual goal)

T4 (C1–C6) + T1.1 + T1.2 merged → `babylon play` boots a real campaign → paced driver +
chronicle + autopause + dossier + save/resume. THAT is the full-TUI-campaign-session gate the
PR #241 cutover waits on. T3 gap projections gate on Vol I's runner-parity specifically. T5
narrator + T6 tutorial follow. Then Gate 3 → #241 → T7 → T8.
