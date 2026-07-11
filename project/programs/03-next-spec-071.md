# 03 — Next Unit: spec-071 Reactionary Subject

Catalog entry: `reports/aidocs-vs-code-audit-2026-05-16.md` Part 3, Wave 1,
"spec-071 — Reactionary Subject (Entitlement + Chauvinism +
FascistFactionSystem)". Complexity L (~50–70 h catalog estimate).
Dependency: spec-070 Balkanization (DONE — Faction model is live).

## Why this is next (and why it's now buildable)

- Wave-1 completion; critical path `070 → 071 → 075 → 081`.
- It is the OTHER branch of the bifurcation formula: 2026-07-02 built
  hegemony (labor aristocracy, super-wages, P(S|A)→0.995); 071 builds what
  the bribed class does when the bribe decays.
- Its substrate now actually exists in the canonical world (it did not
  before 2026-07-02): LA nodes in all 83 counties, live super-wage flows,
  a wired crisis-gated agitation pathway, and 070's Factions for drifted
  nodes to be assigned to.

## Process

1. Branch `071-reactionary-subject` off `dev` (after Percy merges the
   2026-07-02 branch; if not yet merged, branch off `fix/web-local-play-wireup`
   and rebase later — ask Percy first).
1. Speckit lifecycle: `specify → plan → tasks → implement`, Constitution
   **v2.7.0** gates in plan.md (now incl. II.12 authoring-API and the III.7
   determinism-hash contract; Amendments K+L are the two new foundations).
   NO MVP-scoping — implement the full catalog entry.
1. TDD throughout; commit per task-group; update `ai/state.yaml` + ADR
   at the end; then update `project/01-state-of-the-world.md`.

## Inherited obligations (added 2026-07-03 — both foundations landed)

071 now CONSUMES the shipped dialectics machinery (ADR051) instead of
building alongside it:

- **The OODA hook is ready**: `StanceIntervention` +
  `opposition_interventions` graph attr (designed FOR 071 — see
  `06-lawverian-dialectics.md` Part II §5). Fascist pull should be computed
  as a gap/monad quantity against the opposition registry, not a parallel
  ad-hoc counter.
- **RLF simplex constraints are DEFERRED TO 071** (ADR051 / 06 §9.4 /
  06 Part IV §E7): r+l+f=1 enforcement, the `f→r` ε-gate breaking detailed
  balance, entropy-as-diagnostic-only, `assimilation_ratio`.
- **DecompositionSystem carceral-enforcer gap** (02 §5b) fires exactly in
  071's crisis tests — fix it as part of 071 (seed an inactive
  carceral-enforcer entity per county, or teach the system to create one).
- Level lattices + `classify_regime` + `LEVEL_TRANSITION` exist — 071's
  reactionary dynamics should read the regime, not recompute it.

## What to build (from the catalog, with 2026-07-02 annotations)

1. **New SocialClass fields** (frozen Pydantic, `Intensity` types):
   `entitlement` (defaults by class: P=0.2, L_u=0.0, C_pb=0.7, **C_la=0.8**),
   `volatility` (L_u default 0.8), `fascist_alignment` (0→1 drift counter).
   - Annotation: remember the graph round-trip gotcha — new fields must
     survive `to_graph()`/`from_graph()` (see root CLAUDE.md "Graph Round-Trip
     Can Lose Mutations"; the graph is a **BabylonGraph** since Amendment L —
     `08-graph-substrate.md`). Follow the Phase-D5 transient-attribute
     precedent (`aa2cfab0`: `w_paid`/`v_produced` handling in `from_graph`)
     when deciding persisted-vs-transient. Add round-trip tests.
1. **`chauvinism: Intensity`** on organization member records (LA recruits).
1. **New system `FascistFactionSystem`** at ~position 17.5.
   - ⚠ Position conflict to resolve in `/plan`: spec-070 already landed
     SovereigntySystem at 17.5. The catalog says "coexists"; decide 17.4/17.6
     ordering relative to SovereigntySystem and document in the plan.
   - Per-tick for C_pb and C_la nodes:
     `Fascist_Pull = Agitation × (Entitlement / (Solidarity + 0.1))`;
     if > 1.0 → `fascist_alignment += 0.05`, emit `FASCIST_DRIFT`;
     at ≥ 1.0 alignment → reassign node to the fascist Faction (070's model).
   - LA members of player orgs: chauvinism +0.01/tick base, +0.02 if
     super-waged (the WAGES edge + super_wage_bonus > 0 identifies this —
     wired 2026-07-02); on CRISIS events roll
     `P_defection = sigmoid(chi − D)`; defection fires
     `ORGANIZATIONAL_FRACTURE`; >50% defection fires `RED_BROWN_COUP`.
1. **Volatility integration in StruggleSystem**: L_u peripheral revolt gated
   on `V·(1 − org_discipline)`.
   - Annotation: StruggleSystem is the system that severs EXPLOITATION edges
     on revolt (see `02-engine-truths.md` §3). Any change here MUST keep the
     income-circuit integration suite green
     (`tests/integration/test_bridge_income_circuit.py`, esp.
     `test_hegemony_holds_exploitation_edge_persists`).
1. **Fascist action verbs** in `ActionType` + OODA resolution: `POGROM`,
   `LOCKOUT`, `VIGILANTISM`, `RED_BROWN_COUP` (auto-triggered).
1. **New events** (extend the EventType enum, currently **71** values —
   Phase E added `LEVEL_TRANSITION` — in
   `src/babylon/models/enums/events.py`): `FASCIST_DRIFT`,
   `FASCIST_RECRUITMENT`, `ORGANIZATIONAL_FRACTURE`, `RED_BROWN_COUP`,
   `POGROM`, `LOCKOUT`, `VIGILANTISM`, `SPONTANEOUS_RIOT`.
1. **Formulas in `src/babylon/formulas/reactionary.py`**:
   `calculate_fascist_pull`, `calculate_defection_probability`,
   `calculate_spontaneous_riot_risk`, `calculate_entitlement_effective`.
   All constants into GameDefines (Constitution III.1 — no magic numbers in
   systems), doctests per house docstring standard.

## Acceptance beyond the catalog text

- All existing suites stay green (`mise run check`,
  income-circuit integration suite, `mise run qa:e2e-regression`).
- A canonical 520-tick run completes with 83/83 liveness AND the new events
  visible in the bundle (during the pacified decade, expect near-zero
  FASCIST_DRIFT — agitation is crisis-gated; write a scenario/integration
  test that INDUCES crisis, e.g. wage cut or pool drain, and asserts drift +
  faction reassignment fire).
- Update the engine-pipeline table in root `CLAUDE.md` (system count/order)
  and `ai/state.yaml`; ADR for the position decision.
