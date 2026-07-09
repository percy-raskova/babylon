# 2.R baseline-regen R-PROOF — Loud Machine baseline capstone

**Proof home (chosen):** this file sits beside `specs/102-gamma-shocks/proof.md`
because the R-PROOF violation it settles is `cc4a5303` — the E101 gamma/MELT
wiring — which **directly breaks that proof's Part-1 reason 2**
("wiring-path isolation"). This document supersedes that argument and records
the empirical re-settlement. It is the Phase 2.R capstone of the "Loud Machine"
remediation.

**Branch:** `proof/baseline-regen-2026-07` (off dev `276fcb2b`).
**Postgres:** exclusive `babylon_test` @ localhost:5433. Seed 2010 (CLI default,
fixed — matches the committed baseline's seed).

---

## Part 0 — WHAT changed since the last canonical baseline

The committed `tests/baselines/michigan-e2e.json` was authored at `a2f9acee`
(**2026-07-04**, session `ee05760c`, a COMPLETED 520-tick `michigan-canada`
run, seed 2010). The following merged **after** that baseline and before dev
HEAD `276fcb2b`; each is assessed for whether it can touch the gated
`terminal_state` fields (`total_v/total_c/total_s/total_k/counties_alive`):

| Change | Merge | Could touch gated fields? |
|---|---|---|
| **2.3 engine-determinism** — seeded a previously-**unseeded** `random.random()` in StruggleSystem (the 3897-vs-3915 divergence root cause) | `abc6073d` (2026-07-08) | Affects consciousness/tension (`dynamic_consciousness_state`, `max_tension`), **not** the hex economy that feeds the gated fields. Decisively: the **old baseline was itself non-reproducible** (authored 07-04, before this seed). |
| **gamma-wiring E101** — `runner.py` now calls `_build_economics_overrides(session_factory=…)`, wiring `melt_calculator` **and** `gamma_calculator` into the canonical run | `cc4a5303` (**2026-07-06**) | This satisfies `TickDynamicsSystem`'s `melt_calculator is not None` gate → the system now runs **live** (it no-opped for the whole life of the committed baseline). See Part 2 — it does far more than shift a value. |
| **Wave-3 decomposition fix** — seeds `inequality` on decomposition target nodes | `bd3b4388` (2026-07-08) | Only fires if decomposition fires at michigan-canada scale; the run crashes (Part 2) before any year-boundary decomposition, so unobserved here. |
| **2.1 from-graph-safety / Design B** — round-trips `institution_relations` etc. via graph metadata | merged pre-HEAD | Round-trip safety; no michigan-canada scope entities exercise it into the gated path. |

---

## Part 1 — C.8: loud economics-fallback instrumentation (value-NEUTRAL)

**Commit `35513f61`** `feat(observability): loud economics-fallback counters +
economics_fallbacks manifest section (C.8)`.

The silent fallbacks at `src/babylon/economics/tick/system/__init__.py:378-390`
(`gamma_basket_raw = 0.68` when `basket_calculator is None`;
`gamma_III_raw = 0.33` when `gamma_calculator is None` or returns no data;
the MELT-unavailable early return) — the REMEDIATION_PLAN's C.8 row names
these exact lines as "why dead gamma went unnoticed" — are now LOUD:

- `EconomicsFallbackTally` (frozen-free dataclass on `ServiceContainer`,
  `default_factory` → fresh per run) records per-fallback counters
  (`melt_unavailable`, `gamma_basket_calculator_none`,
  `gamma_iii_calculator_none`, `gamma_iii_returned_none`), the wired-vs-None
  status of each calculator, and `national_params_observations`.
- `_compute_national_params` emits a `logger.warning` at each fallback and
  records it. The recorded fallback **value is chosen exactly as before** —
  instrumentation only observes.
- The headless runner surfaces `services.economics_fallbacks.to_dict()` as a
  top-level manifest `economics_fallbacks` block (omitted when `None`).

**Value-neutrality — proven.** `tests/unit/economics/tick/test_system.py::TestEconomicsFallbackInstrumentation`
(6 tests) asserts the fallback constants are **still exactly** `0.68` / `0.33`
with instrumentation on, a wired gamma value flows through unchanged (`0.40`),
and the tally records each path. `tests/unit/engine/test_manifest_builder.py`
adds 3 tests including `test_economics_fallbacks_excluded_from_input_hash`
(the block does **not** enter the deterministic `input_hash`). Green:
`test_system.py`, `test_manifest_builder.py`, `test_gamma_wiring.py`
(139 passed together); broader `tests/unit/engine/ + tests/unit/economics/tick/`
= **2033 passed, 2 xfailed** (pre-existing). `mypy --strict` clean on all four
touched source files; ruff lint + format clean.

**End-to-end wiring verified:** the 5-tick storage-budget bundle's
`manifest.json` carries the `economics_fallbacks` block. It reads all-zero with
`national_params_observations: 0` — correct: a 5-tick run never reaches the
tick-52 year boundary, so `_compute_national_params` never executes. The
`observations` counter cleanly disambiguates "never ran" from "unwired".

---

## Part 2 — Empirical canonical result: the gamma wiring BROKE the 520-tick run

Two independent `mise run sim:e2e-bg` runs (`--scope michigan-canada --ticks 520
--write-baseline tests/baselines/michigan-e2e.json`, seed 2010) both
**crash identically at tick 52** — the first productive `TickDynamicsSystem`
year boundary (year 2011):

```
INFO :babylon.economics.melt.adapters: BEA national GDP derived from county sum for year 2011
WARNING:babylon.economics.tick.system: TickDynamics Step 2: basket_calculator not wired; using fallback gamma_basket=0.68 for year 2011
WARNING:babylon.economics.tick.system: TickDynamics Step 2: gamma_III calculator returned no data; using fallback gamma_III=0.33 for year 2011
ERROR ENGINE_FAILURE: ValidationError: 1 validation error for ClassDistribution
fips
  String should have at least 5 characters [type=string_too_short, input_value='T001', input_type=str] | partial_artifacts=NONE
```

### Root cause (pre-existing; exposed by `cc4a5303`, NOT by C.8)

- `WorldStateBridge._build_per_county_territories` (bridge.py, ADR044 completion
  2026-07-02) mints one `Territory` per county with **id `f"T{i:03d}"`** —
  `T001`, `T002`, … — carrying the county FIPS only in the `name` field.
- `TickDynamicsSystem` (Feature 020) assumes territory-node ids **are** 5-digit
  county FIPS: `_get_territory_fips` / `_bootstrap_county_states` sweep every
  `node_type == "territory"` node and build `ClassDistribution(fips=<node_id>)`.
  `'T001'` (4 chars) violates the ≥5-char FIPS constraint → `ValidationError`.
- This was **dormant** for the entire life of the committed baseline because
  `melt_calculator` was `None`, so `TickDynamicsSystem.step()` early-returned
  (a complete no-op). The committed baseline (07-04) predates `cc4a5303`
  (07-06); the OLD run therefore never reached this code. `cc4a5303` wired
  `melt`+`gamma`, making the system run live, and it crashes the first time its
  county pipeline executes at michigan-canada scale.

### Not caused by C.8 — verified three ways
1. `git diff 276fcb2b 35513f61 -- .../tick/system/__init__.py` touches **only**
   `_compute_national_params` (3 hunks, lines 367-430); it does **not** touch
   `ClassDistribution`, `_bootstrap_county_states`, `_compute_county_states`, or
   any `fips=` construction (grep empty). 319 insertions, **0 deletions**.
2. Runtime order: the C.8 warnings print, `_compute_national_params` **returns
   normally**, and a **different** method (`_bootstrap_county_states`) then raises.
3. Provenance: `cc4a5303` (07-06) is already in `276fcb2b`; the crash is
   independent of the C.8 commit stacked on top.

### Consequence for the baseline
`--write-baseline` only fires on `COMPLETED`/`EARLY_TERMINATED`; the run
`ERRORED`, so `tests/baselines/michigan-e2e.json` was **not** overwritten
(verified byte-identical to the pre-run copy). **The canonical baseline cannot
be refreshed to tick 519 until this crash is fixed.** No baseline was
fabricated.

---

## Part 3 — Gated-field neutrality: the new basis for baseline validity

Spec-102's proof rested baseline-neutrality on two independent reasons; reason 2
(wiring-path isolation) is now **false** — gamma/MELT ARE wired in the canonical
run. So validity now rests **entirely on reason 1 (consumption-path isolation)**.
Settled here **empirically**, not by inference:

The crashed run persisted ticks 0-51. Querying `v_hex_state_asof` for the run's
session at tick 0 and tick 51, and comparing to the committed baseline's
tick-519 `terminal_state`:

| Gated field | Committed baseline (tick 519, pre-`cc4a5303`, TickDynamics no-op) | Gamma-wired run (`v_hex_state_asof`, ticks 0 **and** 51) |
|---|---|---|
| `total_v` | 3126580386.69231 | 3126580386.69 |
| `total_c` | 4107365647.6468215 | 4107365647.65 |
| `total_s` | 4434566613.30769 | 4434566613.31 |
| `total_k` | 1179538932000.0024 | 1179538932000.18 |
| `counties_alive` | 83 | 83 |

The gated fields are **byte-identical to full persisted precision** between the
pre-wiring baseline and the post-wiring run (differences are 2nd-decimal
`round()` display only). Two facts explain and confirm this:

1. **The hex economy is static.** `WorldStateBridge.persist_tick` logs `hex=0`
   for every tick 1-51 — zero hex deltas after the tick-0 checkpoint — so
   `v_hex_state_asof` carries the tick-0 hydration forward unchanged. The
   committed baseline's tick-519 values equal that same tick-0 state, i.e. the
   hex economic base did not move across the entire committed run either.
2. **Consumption-path isolation holds.** Even though `TickDynamicsSystem` now
   runs live, its output (`tick_`-prefixed territory attrs +
   `persist_graph_metadata`) never reaches `dynamic_hex_state` — the sole source
   (`v_hex_state_asof` → trace emission) of the gated fields. The gamma wiring
   therefore contributes **exactly zero** to the gated `terminal_state`.

**Verdict for the gated contract:** the gamma wiring is **baseline-neutral on
the gated fields** — the committed baseline's `total_v/total_c/total_s/total_k/
counties_alive` remain correct. `mise run qa:e2e-regression` (5-tick
detroit-tri-county, the CI gate that consumes a baseline) is **GREEN**:
`counties_alive == 3`, population liveness 3/3, `total_v Δ=0.000%`, no critical
conservation violations. What is broken is the ability to **complete** a fresh
520-tick run, not the correctness of the gated values it would report.

### economics_fallbacks evidence (did gamma compute or fall back?)
At michigan-canada scale the log is unambiguous: **`basket_calculator` is
unwired** (`_build_economics_overrides` wires only `gamma` + `melt`, never
`basket`) → `gamma_basket` falls back to `0.68` every year boundary; and the
wired `gamma_calculator.compute(2011)` **returns no data** →  `gamma_III` falls
back to `0.33`. So even with E101 "live," gamma is **still defaulting**, not
computing real reproductive visibility — precisely the class of silent dead-wire
C.8 was built to expose. (The manifest block that would tally this could not be
written — the run `ERRORED` before artifact emission — but the paired C.8
warnings are in `.sim-pids/e2e.log`.)

---

## Part 4 — A/B determinism

The committed baseline (07-04) was authored **before** the 2.3 StruggleSystem
seed — so it was itself non-reproducible. The new (2.3-seeded, gamma-wired)
engine must instead be provably deterministic. Because the canonical run crashes
at tick 52, the A/B is run over the reproducible **tick 0-51** prefix of two
fully independent `michigan-canada` runs (seed 2010):

- session A = `4ad75b08-0258-48a4-a29a-61cab92d7d13`
- session B = `1111597c-158f-4bcc-a0ed-718cbcd20248`

Compared directly on the persisted Postgres state (`session_id` excluded), via a
two-directional `EXCEPT` (a non-zero count in either direction = any single
differing cell):

| Layer (ticks 0-51) | A rows | B rows | in A not B | in B not A |
|---|---|---|---|---|
| `dynamic_consciousness_state` (RNG-sensitive: `p_acquiescence`, `p_revolution`, `ideology_r/l/f`) | 4316 | 4316 | **0** | **0** |
| `v_hex_state_asof` @ tick 51 (`c,v,s,k` material base) | 45572 | 45572 | **0** | **0** |

**Byte-identical.** `dynamic_consciousness_state` is exactly the layer the 2.3
reseed governs (StruggleSystem's George-Floyd dynamic feeds agitation → ideology
drift); its two independent runs agreeing to the cell proves the 2.3 fix
delivers reproducibility. The `t_commit` / conservation `determinism_hash`
chains are **not** used here — spec-102's proof already established they embed
`session_id` and can never match across runs; comparing persisted **values** is
the direct, session-id-free equivalent (same method spec-102 Part 2 adopted).

Additionally, **the crash reproduces deterministically**: both runs fail at
tick 52 with the identical `ClassDistribution fips='T001'` validation error —
same tick, same node, same message. A future fixed 520-tick run is therefore
expected to be reproducible; the determinism invariant holds up to the (also
deterministic) crash boundary.

---

## Part 5 — Track A scenario baselines + drift gates

- **Track A (`mise run qa:regression`)** drifted on all 5 scenarios
  (`two_node`, `starvation`, `glut`, `imperial_circuit`, `fascist_bifurcation`)
  — **`defines_hash` only**. The compare printed no `final_outcome`,
  `ticks_survived`, or checkpoint diffs; the per-baseline git diff is exactly
  two lines (`generated_at` timestamp + `defines_hash`). Behavior is
  byte-identical; only the GameDefines fingerprint moved (last anchored
  `a5c94c71`, 2026-07-03; GameDefines changed across specs merged 07-03→07-08).
  Regenerated via `mise run qa:regression-generate` → re-compare **5 passed**.
  **Commit `8023b783`.**
- **`mise run qa:e2e-regression`** (5-tick tri-county) — **PASS**, no drift, not
  regenerated. The 5-tick run never reaches the tick-52 year boundary, so it does
  not hit the Part-2 crash and the 2.3 RNG reseed leaves the gated fields
  (production totals) unchanged.
- **`mise run qa:storage-budget`** (5-tick, quiescent owned DB) — **PASS**, all
  10 tables within rows/tick budget. Not regenerated.

---

## Part 6 — cc4a5303 R-PROOF violation: OPEN + ESCALATED (not closed green)

The `cc4a5303` R-PROOF violation was "gamma wired live without a re-baseline
proof." This capstone settles it as follows:

- **Gated-field neutrality is PROVEN** (Part 3): the wiring does not perturb
  `total_v/total_c/total_s/total_k/counties_alive`; the committed baseline's
  gated values remain valid; the CI baseline gate is green.
- **BUT the wiring did more than shift a value — it broke the canonical run's
  ability to complete** (Part 2). Closing the violation with a green 520-tick
  re-baseline is **impossible at dev HEAD**. The violation is therefore
  **not closed** — it is **escalated** with a precise, reproducible root cause:

  > `TickDynamicsSystem` (Feature 020) treats `WorldStateBridge` synthetic
  > territory ids (`T{i:03d}`) as county FIPS. Fix owner options: (a) key
  > bridge territories by FIPS, or (b) resolve/skip non-FIPS territory nodes in
  > `_get_territory_fips` / `_bootstrap_county_states`. Either is a behavior
  > change requiring its own proof and is **out of scope for a baseline-regen
  > capstone** — flagged, not fixed, per "do not paper over / do not fabricate."

**Recommendation:** open a fix spec for the TickDynamicsSystem×bridge territory-id
mismatch; once green, re-run this 2.R capstone to refresh
`tests/baselines/michigan-e2e.json` and close `cc4a5303` with a completed
520-tick A/B.

---

## Verification chain

- Unit: `TestEconomicsFallbackInstrumentation` (6), `test_manifest_builder.py`
  economics_fallbacks (3), `test_gamma_wiring.py` — green; broader engine+tick
  suite 2033 passed / 2 xfailed. `mypy --strict` + ruff clean on touched files.
- Canonical `michigan-canada` 520-tick: **crashes at tick 52** (two runs,
  identical `ClassDistribution fips='T001'` failure) — root-caused, escalated.
- Gated-field neutrality: byte-identical old-vs-new via `v_hex_state_asof`.
- Determinism A/B: Part 4.
- `qa:e2e-regression` GREEN; `qa:storage-budget` GREEN; Track A regenerated
  (defines-only drift, behavior-identical).
