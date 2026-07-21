# v1.0.0 lane merge runbook (controller working notes, 2026-07-21)

Live integration order + cross-lane checkpoints for the six parallel lanes forked off the
T1.0 contract commit (84d8405a). Fast-dev mode: lanes commit locally; heavy ceremony
(qa:regression byte gate, vault regression, baseline blessing) fires at MERGE time only,
single-flight in this controller. This file is my scratch — supersede freely.

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
- [ ] **§10.2 dormancy-sentinel hoist**: lives in T1.1 keel, NOT the Vol lanes (recorded
      ADR103). Confirm neither Vol lane also built one (dedupe).

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
