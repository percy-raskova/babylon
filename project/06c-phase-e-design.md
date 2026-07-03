# 06c — Phase E design (levels, Aufhebung, fixed-point regimes, re-baseline)

Fable's binding design for `project/06` §7 + §9.4 (+ §9.1 edge-modes),
written 2026-07-03 from a full surface recon. Delegate: read `project/06`
§8 + §9.1 first, then this file. Two recon corrections that OVERRIDE
anything older you read: (1) the bridge persist wiring EXISTS —
`bridge.py:561` calls `persist_contradiction_fields` (C1.4, hasattr-
guarded to the Postgres runtime); (2) the canonical 520-tick run is
Postgres-backed (`runner.py` opens `BABYLON_PG_DSN`), so
`contradiction_field` rows flow on the re-baseline run and the §7
criterion is checked by querying the table.

## E0. Repoint the dormant field stack (the §5.3 leftover, prerequisite)

Three Feature-002 systems run every tick as no-ops because they
early-return on `services.field_registry is None`
(`contradiction_field.py:71-73`, `field_derivative.py:68-69`,
`edge_transition/_legacy.py:571-573`). The Lawverian rewire makes the
opposition layer their source. Rulings:

- `ContradictionFieldSystem` (@19): drop the `field_registry` gate.
  Per-node `contradiction_fields` are now sourced LOCALLY: for each
  social_class node, field `"exploitation"` = mean fresh `tension` over
  its incident EXPLOITATION/WAGES/TENANCY edges (the per-edge gaps
  ContradictionSystem @18 just wrote), field `"atomization"` = the
  registry's atomization gap (global, uniform per node this phase).
  Keep the 3-tick rolling history machinery unchanged. `field_registry`
  keeps working when present (tests use it); the gate becomes
  "registry OR opposition source", not an early return.
- `FieldDerivativeSystem` (@20): NO source changes needed — it reads
  `contradiction_fields` node attrs + history, which E0 now populates.
  Delete only the `field_registry is None` early-return (its math needs
  no registry). Its `principal_contradiction` graph attr +
  PRINCIPAL_CONTRADICTION_SHIFT event now fire for real; they must NOT
  fight the registry's principal: rename its output attr to
  `principal_field` (grep consumers first — if any consumer reads
  `principal_contradiction` expecting the field-stack semantics, STOP
  and report).
- `EdgeTransitionSystem` (@21): delete the `field_registry` early-return
  (predicates read node attrs, which now exist). The 17-transition
  table is UNCHANGED.
- Fix the position-drift docstrings while there ("Execution Order:
  14/15/16" → 19/20/21 actual).
- Gate for E0 alone: the C1.6 bridged 50-tick integration test still
  green; a new unit test per system proving it acts without a
  field_registry (edge mode actually transitions under a forced
  predicate; derivatives non-zero after two ticks).

## E1. Level instances — `instances/levels.py`

Spatial chain `hex ≺ county ≺ state ≺ nation` and social chain
`individual ≺ community ≺ class ≺ bloc`, as `LevelLattice` instances
(`core/level.py` — `is_resolved_at` = `sheaf_higher(skeleton_lower(x)) == skeleton_lower(x)`).

The ambient object X for BOTH chains is a **keyed field**
`Mapping[str, float]` (entity id → value, e.g. county fips → capital\_
labor edge tension). Operators come from Phase D's `ScaleAdjunction`:

- `skeleton_at(level)` = `allocate(aggregate(x))` with that level's
  mapping/shares — smooths within-parent variation (the closure);
- `sheaf_at(level)` = the same closure at the NEXT level up. Equality
  (`eq`) is elementwise within 1e-9.
- **Resolution semantics (the earn-its-keep computation)**: a field is
  resolved at level L iff smoothing at L+1 no longer changes the
  L-smoothed field — i.e. within-(L+1)-region variance of the
  L-aggregates is zero: the contradiction now LIVES at or above L+1.
  This is a variance decomposition computed by adjunction operators.
  Law test: a field constant within states but differing between states
  is resolved at county, NOT resolved at hex; a uniform field resolves
  everywhere.
- Spatial mappings: hex→county from node `county_fips`; county→state =
  `fips[:2]`; state→nation = constant. Shares: population-weighted
  where populations exist, else uniform (document).
- Social mappings: individual→community from the XGI membership span
  (`H.nodes.memberships(agent_id)` — an agent in multiple communities
  contributes via NORMALIZED shares, 1/k each, keeping allocate
  stochastic); community→class from dominant `SocialRole` of members;
  class→bloc = {core, periphery} assignment. NoCommunityFanOut is
  untouched — the lattice reads the XGI layer, never adds MEMBERSHIP
  edges (Constitution II.7 / VIII.9).
- The `unity`-free `OppositionSpec.level_name` field (Phase A) now gets
  values in the catalog: capital_labor/wage/tenancy = "county",
  atomization = "class", imperial = "bloc". Pure data, one test.

## E2. Fixed-point regimes — one operator, three outcomes (§9.4)

A tick is one Picard iteration `W_{n+1} = T(W_n)`. Phase E ships the
REGIME CLASSIFIER over the opposition trajectory — no engine loop
changes, no convergence iteration inside a tick (the dormant package
never had one either; recon item 10):

```python
# dialectics/core/regime.py
Regime = Literal["reproduction", "crisis", "sublation"]
def classify_regime(
    states: Sequence[OppositionState],          # this tick, principal marked
    lattice: LevelLattice[Mapping[str, float]] | None,
    field: Mapping[str, float],                 # principal's per-entity gaps
    level_index: int,                           # principal's declared level
    *, rate_epsilon: float,                     # |rate| below = converged
) -> Regime
```

- **reproduction**: principal `|rate| <= rate_epsilon` — the
  self-consistency search converged; the social form reproduces.
- **crisis**: principal `rate > rate_epsilon` (gap developing) and the
  field NOT resolved at the next level — divergence within the level.
  The existing RUPTURE gate (`gap > threshold AND rate > 0`) stays
  byte-identical as the crisis THRESHOLD event: rupture is this regime's
  boiling point, not a separate mechanism.
- **sublation**: gap developing AND `lattice.aufhebung_of` (at
  `level_index`, probing `[field]`) returns a level — the contradiction
  has moved up: it is resolved-at-a-higher-level while diverging below. Publish the NEW
  `EventType.LEVEL_TRANSITION` (add to the enum — 70 → 71 members)
  with payload {opposition, from_level, to_level, gap, rate}.

Wiring: `ContradictionSystem._step_registry` computes the regime after
`_maybe_rupture` (it already has states; build `field` from per-county
capital_labor edge tensions — the same extraction the C1.6 bridged test
uses), stashes `graph attr "dialectical_regime"`, and publishes
LEVEL_TRANSITION on the sublation branch. `rate_epsilon` and the
lattice wiring ship via `services` defaults (`defines.tension. regime_rate_epsilon`, default 1e-4 — ONE new define, documented).
EdgeTransitionSystem's Aufhebung hook: a new `PredicateCondition`
metric `"regime"` usable in transitions (data only — no new transition
added to the 17 this phase; one unit test proves the predicate
evaluates).

## E3. Edge modes as a presented category (§9.1)

The 17 `EdgeModeTransition`s + the ANTAGONISTIC self-loop ARE the
presented category's generating morphisms. No new class. Law tests over
`_TRANSITION_MAP`/`_VALID_TRANSITIONS` as data:

- `test_no_direct_extractive_to_solidaristic` — absent from the 17;
- `test_extractive_reaches_solidaristic_through_transactional` — a path
  exists and every such path transits TRANSACTIONAL (BFS over the
  transition graph, bounded by 5 nodes);
- `test_all_transitions_endpoints_are_edge_modes` (closure of the
  presentation).

## E4. The fractal check (§9.4 — honesty clause)

Test fixture (extends C2's four-node recursion): nation-level imperial
opposition nests {Core,Periphery}; each zone nests its own
capital_labor. Assert: (a) the SAME {Core,Periphery}×{B,P} structure is
expressible at state zoom by rebinding the same specs over a state's
field slice (the lattice's allocate gives the slice); (b) lumpen
appears only on zoom-in: at class level the social lattice's aggregate
folds LUMPENPROLETARIAT into the proletariat pole (population-weighted),
at individual/community zoom the distinct pole is visible. If (b) is
NOT cleanly expressible with the current operators, the test documents
the failure with `pytest.mark.xfail(reason=...)` and the ADR says so
explicitly — per the contract: "say so explicitly rather than fake it."

## E5. Induced-crisis integration test

`tests/integration/test_induced_crisis.py`, gated like the income-
circuit suite. In the bridged income-circuit world: run ~20 ticks of
pacified hegemony (regime == reproduction), then force the crisis —
drain the rent pool / cut the wage flow (set the economy's rent pool to
~0 via the graph metadata the wages phase reads; if there is no clean
lever, use the SUPERWAGE_CRISIS path by exhausting the pool with a tiny
`extraction_efficiency`) — then assert over the following ticks:
(a) wage/capital_labor gap grows (rate > 0 sustained); (b) principal
contradiction SHIFTS (the fast-developing one takes over — assert the
registry's principal key changes); (c) at least one RUPTURE or
LEVEL_TRANSITION event fires. STOP-condition applies: if inducing the
crisis requires touching StruggleSystem's severing logic or the
consciousness gating, stop and report.

## E6. Grundrisse fixed-point test (§9.4 port)

Extend `tests/integration/test_grundrisse_cycle.py` (do not rewrite)
with `TestFixedPointReading`: the 4-moment cycle driven to its
repeating orbit is a fixed point of the COMPOSITE map T⁴ — assert
regime == "reproduction" on the orbit (gaps repeat within epsilon
tick-over-tick at the same moment across turns); a wage-cut
perturbation breaks the orbit → regime == "crisis". (The dormant
package's only fixed-point content was the previous-tick read pattern —
already carried by the graph-attr snapshot; the regime classifier is
the NEW machinery §9.4 demands.)

## E7. TopologyMonitor + consumers (honesty rulings)

- TopologyMonitor has ZERO production call sites (recon) — the headless
  runner has no observer path. Ruling: the PRODUCTION Aufhebung signal
  is the engine-side LEVEL_TRANSITION event (E2), persisted through the
  normal event pipeline. The monitor gains one small hook —
  `classify_phase` may take an optional `lattice_resolved: bool` that
  promotes transitional→solid when the social field resolves at class
  level — exercised in its existing test suites only. Wiring the
  monitor into the runner is OUT of scope; the ADR records this
  honestly ("TopologyMonitor remains a facade/test observer").
- RLF simplex constraints (§9.4): NOT implemented here — they are
  spec-071's. Record them in the ADR's handoff section verbatim from
  §9.4 (f→r ε-gate breaking detailed balance; entropy diagnostic-only;
  assimilation_ratio; balance∈[−1,1] convention already honored).

## E8. Re-baseline + closing docs

1. All gates green FIRST (below).
1. Launch the canonical run **nohup-detached** (harness background
   tasks die on compaction):
   `nohup mise run sim:e2e-michigan > reports/sim-runs/phase-e-rebaseline.log 2>&1 &`
   — expect ~52 min. Poll the log; on completion verify and RECORD:
   (a) `terminal_state.counties_alive == 83 == counties_with_population`;
   (b) `contradiction_field` rows > 0 for the run's session (psql on
   port 5433, `babylon_test`);
   (c) stddev of per-county capital_labor edge tension > 0 at t300
   (from the trace/baseline artifacts);
   (d) `max_tension < 1.0` in the new baseline (non-saturating gaps —
   the OLD baseline's pinned 1.0 is the artifact we are killing).
   Commit the refreshed `tests/baselines/michigan-e2e.json` with these
   four numbers in the commit body. If ANY criterion fails, STOP —
   report with the numbers; do not commit a failing baseline.
1. ADR `ai-docs/decisions/ADR051_lawverian_dialectics_refactor.yaml`
   (+ index.yaml entry, meta.version bump): the whole refactor A→E —
   registry replaces field_registry+tension ratchet; C2 composition/
   coupling/lineage; D adjunctions + Φ tri-decomposition; E levels/
   regimes/LEVEL_TRANSITION; deferrals (observation-relativity frames,
   RLF→071, TopologyMonitor unwired, transformation problem).
1. `ai-docs/state.yaml`: meta.version bump + sprint note.
1. Root `CLAUDE.md`: pipeline-table note — position 18's description
   already updated in C1; add a one-line note that 19-21 are live
   (no longer field_registry-gated) and events gained LEVEL_TRANSITION.
1. `project/01` + `project/06`: completion notes (§7 checked off).

## File plan

| File                                                    | Change                                    |
| ------------------------------------------------------- | ----------------------------------------- |
| `src/babylon/engine/systems/contradiction_field.py`     | E0 repoint (edge-tension source)          |
| `src/babylon/engine/systems/field_derivative.py`        | E0 gate removal + principal_field rename  |
| `src/babylon/engine/systems/edge_transition/_legacy.py` | E0 gate removal + regime predicate metric |
| `src/babylon/dialectics/instances/levels.py`            | NEW — spatial + social lattices           |
| `src/babylon/dialectics/core/regime.py`                 | NEW — classify_regime                     |
| `src/babylon/engine/systems/contradiction.py`           | E2 wiring (regime + LEVEL_TRANSITION)     |
| `src/babylon/models/enums/events.py`                    | +LEVEL_TRANSITION                         |
| `src/babylon/config/defines/...`                        | +tension.regime_rate_epsilon              |
| `src/babylon/dialectics/instances/catalog.py`           | level_name values                         |
| tests                                                   | per E0-E6; extend, never rewrite          |

Commit units: (1) E0 repoint, (2) E1 levels, (3) E2 regimes +
LEVEL_TRANSITION, (4) E3+E4 category laws + fractal, (5) E5+E6
crisis/fixed-point tests, (6) E8 re-baseline + ADR + docs. Mutation
probes required on: the resolution equality (mutant: sheaf==sheaf
instead of sheaf(skeleton)==skeleton), the crisis/sublation branch
order (mutant: sublation checked first unconditionally), and the E0
edge-tension mean (mutant: max instead of mean).

## Gate

Standing four (§8) + `tests/integration/test_grundrisse_cycle.py`,
`test_induced_crisis.py`, income-circuit — all green BEFORE the
re-baseline step. The re-baseline is the LAST act. Then STOP: Fable
review, then the owner's break.
