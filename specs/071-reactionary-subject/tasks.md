# Tasks: The Reactionary Subject (spec-071)

**Branch**: `071-reactionary-subject` | TDD mandatory (Red → Green → Refactor).
Each task group is an independently-committable unit. `[P]` = parallelizable.

Legend: **RED** = write failing test first (`@pytest.mark.red_phase` for the
intentional-fail commit if committed separately); **GREEN** = implement to pass.

## Phase A — Foundations (formulas + defines + enums)

- **T001 [RED]** `tests/unit/config/test_reactionary_defines.py`: assert
  `GameDefines().reactionary` exists with every R-001 constant at its default.
- **T002 [GREEN]** Add `ReactionaryDefines` (config/defines) + wire into
  `_assembler.py` + `__init__.py` (`__all__`). → verify T001 green.
- **T003 [RED]** `tests/unit/formulas/test_reactionary.py`: unit tests +
  doctests for `calculate_fascist_pull`, `calculate_defection_probability`
  (sigmoid), `calculate_spontaneous_riot_risk`, `calculate_entitlement_effective`.
- **T004 [GREEN]** `src/babylon/formulas/reactionary.py` with those functions
  (RST docstrings, doctests, constants referenced from defaults). Update
  `formulas/__init__.py` `__all__`. → T003 green.
- **T005 [RED]** Extend `test_reactionary.py` (or a routing test) for
  `assimilation_ratio`, `ideological_contestation`, `apply_fr_gate`.
- **T006 [GREEN]** Add those to `formulas/consciousness_routing.py` (+ `__all__`);
  add a `normalize_to_simplex` sums-to-1 contract test. → T005 green.
- **T007** Commit: `feat(071): reactionary formulas + ReactionaryDefines + RLF helpers`.

## Phase B — Enums (events + actions)

- **T008 [RED]** Test asserting the 8 new EventType + 4 new ActionType values
  exist and round-trip (`.value`).
- **T009 [GREEN]** Add the values (events.py, actions.py). Update any
  count-pinning test (EventType 71 → 79) if present. → T008 green.
- **T010** Commit: `feat(071): fascist EventType + ActionType values`.

## Phase C — SocialClass reactionary fields (P1 substrate)

- **T011 [RED]** `tests/unit/models/test_social_class_reactionary.py`: fields
  exist with correct defaults; role defaulting (entitlement P/L_u/C_pb/C_la,
  volatility L_u); Intensity bounds; model-const == defines-default equality;
  `aligned_faction_id` default None.
- **T012 [RED]** Round-trip test: `to_graph()`/`from_graph()` preserves the
  four new fields (and does not drop them via SOCIAL_CLASS_COMPUTED_FIELDS).
- **T013 [GREEN]** Add fields + `_set_reactionary_defaults_from_role`
  validator to `social_class.py`. → T011/T012 green.
- **T014** Commit: `feat(071): SocialClass entitlement/volatility/fascist_alignment/aligned_faction_id`.

## Phase D — FascistFactionSystem: drift + capture (P1 core)

- **T015 [RED]** `tests/unit/engine/systems/test_fascist_faction_system.py`:
  (a) C_la node, high entitlement, agitation>0, no SOLIDARITY → pull>1,
  `fascist_alignment += step`, FASCIST_DRIFT published;
  (b) SOLIDARITY edge present → suppressed drift;
  (c) alignment reaches ≥1.0 + fascist faction present → `aligned_faction_id`
  set + FASCIST_RECRUITMENT (idempotent);
  (d) agitation 0 → no drift, no intervention (hegemony);
  (e) StanceIntervention appended to `opposition_interventions`;
  (f) reads `dialectical_regime` (does not crash when absent).
- **T016 [GREEN]** `src/babylon/engine/systems/reactionary.py` FascistFactionSystem
  drift+capture+stance path. Register at 17.4 in `_DEFAULT_SYSTEMS` +
  CONSEQUENCE_SYSTEMS (update the partition assertion). → T015 green.
- **T017** Commit: `feat(071): FascistFactionSystem — fascist pull, drift, faction capture, stance hook`.

## Phase E — Chauvinism + defection + coup (P2)

- **T018 [RED]** Extend the system test: org with MEMBERSHIP→LA edges;
  chauvinism accrues (base + super-wage bonus); crisis event → defection roll
  → ORGANIZATIONAL_FRACTURE; >50% → RED_BROWN_COUP; determinism (same seed →
  same outcome).
- **T019 [GREEN]** Implement the chauvinism/defection/coup branch in
  FascistFactionSystem (seed RNG). → T018 green.
- **T020** Commit: `feat(071): LA chauvinism accumulation + crisis defection + RED_BROWN_COUP`.

## Phase F — Volatility → spontaneous riot in StruggleSystem (P2)

- **T021 [RED]** `tests/unit/engine/systems/test_struggle_volatility.py`:
  L_u high volatility + low discipline → SPONTANEOUS_RIOT (no solidarity
  built); high discipline → suppressed; determinism.
- **T022 [GREEN]** Add the L_u spontaneous-riot branch to StruggleSystem
  (constants from ReactionaryDefines/StruggleDefines). → T021 green.
- **T023 [VERIFY]** `poetry run pytest tests/integration/test_bridge_income_circuit.py`
  (esp. `test_hegemony_holds_exploitation_edge_persists`) stays green.
- **T024** Commit: `feat(071): L_u volatility-gated SPONTANEOUS_RIOT in StruggleSystem`.

## Phase G — Fascist OODA verbs (P3)

- **T025 [RED]** Test resolving POGROM/LOCKOUT/VIGILANTISM through OODA emits
  the events with graph effects.
- **T026 [GREEN]** Add resolution + eligibility for the three verbs in
  `ooda.py`; RED_BROWN_COUP stays auto-triggered by the FascistFactionSystem.
  Effect magnitudes from ReactionaryDefines. → T025 green.
- **T027** Commit: `feat(071): POGROM/LOCKOUT/VIGILANTISM OODA resolution`.

## Phase H — Decomposition carceral-enforcer create-on-demand (P3)

- **T028 [RED]** `tests/unit/engine/systems/test_decomposition_enforcer_creation.py`:
  induce SUPERWAGE_CRISIS with no seeded enforcer → enforcer +
  internal-proletariat created with split pop/wealth; CLASS_DECOMPOSITION
  transfers non-zero.
- **T029 [GREEN]** Create-on-demand in `decomposition.py`. → T028 green.
- **T030** Commit: `fix(071): DecompositionSystem creates carceral enforcer/internal-proletariat on demand`.

## Phase I — Crisis-induction integration (SC-001)

- **T031 [RED]** `tests/integration/test_reactionary_crisis.py`: build a
  small world (C_la node + fascist faction), induce crisis (wage cut / drain
  → rising agitation), run N ticks, assert FASCIST_DRIFT then FASCIST_RECRUITMENT
  + reassignment fire; determinism (same seed → identical event stream, SC-007).
- **T032 [GREEN]** Fix any wiring gaps surfaced. → T031 green.
- **T033** Commit: `test(071): induced-crisis integration — drift + faction reassignment`.

## Phase J — Verification + R-PROOF + close-out

- **T034 [VERIFY]** `mise run check` (lint + format + typecheck + unit) green.
- **T035 [VERIFY]** `mise run test:q -- tests/integration/test_bridge_income_circuit.py` green.
- **T036 [VERIFY]** `mise run qa:e2e-regression`. If byte-identical → done. If
  moved → write the proof (what/why/magnitude), regenerate
  `tests/baselines/detroit-tri-county-5t.json`, commit proof + baseline
  (`--no-verify` for the artifact) — R-PROOF.
- **T037** Update root `CLAUDE.md` engine-pipeline table (system count/order,
  add FascistFactionSystem @17.4), `ai-docs/state.yaml`, add an ADR under
  `ai-docs/decisions/` for the position decision + StanceIntervention wiring.
  Update `project/01-state-of-the-world.md` + `09` §2 spec-071 entry.
- **T038** Commit: `docs(071): pipeline table + state.yaml + ADR + kit close-out`.
- **T039** Launch `mise run sim:e2e-bg`; confirm alive via `mise run sim:status`;
  RETURN PARTIAL with the canonical run in flight (orchestrator archives it).

## Dependency notes

- Phase A/B are independent `[P]` foundations.
- Phase C depends on nothing (fields), but D depends on A (formulas/defines),
  B (events), C (fields).
- E depends on D. F depends on A/B (+ StruggleSystem). G depends on B. H is
  independent (only needs the enforcer test). I depends on C/D (+ B).
- J last (verification + baseline + close-out).
