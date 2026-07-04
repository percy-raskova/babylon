# Implementation Plan: The Reactionary Subject

**Branch**: `071-reactionary-subject` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/071-reactionary-subject/spec.md`

## Summary

Build the fascism branch of the George Jackson bifurcation (Constitution
I.4). Add reactionary state to `SocialClass` (entitlement, volatility,
fascist_alignment, aligned_faction_id), a `chauvinism` edge attribute on
Organization MEMBERSHIP edges, and a new `FascistFactionSystem` at pipeline
position 17.4 that: (a) computes `Fascist_Pull` per C_pb/C_la node and drives
`fascist_alignment` drift + fascist-faction capture; (b) accumulates
chauvinism on LA org members and rolls crisis defection →
ORGANIZATIONAL_FRACTURE / RED_BROWN_COUP; (c) expresses the pull as a
`StanceIntervention` on the opposition registry (ADR051 hook) and READS the
`dialectical_regime` attr. Integrate volatility-gated `SPONTANEOUS_RIOT` into
StruggleSystem, add fascist OODA verbs, close the DecompositionSystem
carceral-enforcer gap (create-on-demand), and honor the RLF simplex
constraints. All constants in a new `ReactionaryDefines`. Pure math in
`formulas/reactionary.py` with doctests.

## Technical Context

**Language/Version**: Python 3.12 (worktree venv via `PYTHONPATH=src`)
**Primary Dependencies**: Pydantic 2.x (frozen models), rustworkx via
BabylonGraph (Amendment L), the ADR051 dialectics package
(`babylon.dialectics`). No new third-party dependencies.
**Storage**: In-memory via GraphProtocol. New SocialClass fields persist via
`to_graph()`/`from_graph()`. `chauvinism` is graph edge-state. No new Postgres
tables; the canonical world seeds no orgs/factions so the persistence surface
is unchanged for the base run.
**Testing**: pytest (`mise run test:q`, `mise run check`), doctest
(`test:doctest` known-broken pre-existing), integration
(`tests/integration/test_bridge_income_circuit.py`), 5-tick gate
(`mise run qa:e2e-regression`), canonical (`mise run sim:e2e-bg`).
**Target Platform**: Linux; local sim engine.
**Project Type**: Single project (engine).
**Performance Goals**: The new system reads C_pb/C_la nodes each tick; O(nodes)
per tick, negligible vs existing systems. No hot-loop concerns at Michigan
scope.
**Constraints**: Constitution III.7 determinism (byte-identical baselines or
written proof); frozen models; no magic numbers (III.1).
**Scale/Scope**: Michigan 83 counties (canonical); tri-county 5-tick gate.

## Constitution Check (v2.7.0)

*GATE: Must pass before implementation. Re-checked after design.*

| Principle | Status | How this spec satisfies it |
|-----------|--------|----------------------------|
| **III.1 No Magic Constants** | PASS | Every numeric (drift step 0.05, pull threshold 1.0, chauvinism base 0.01 / super-wage bonus 0.02, riot threshold, defection discipline, ε-gate epsilon) lives in a new `ReactionaryDefines` Pydantic model wired into `GameDefines`. Systems read `services.defines.reactionary.*`. Formula defaults reference the same values; a doctest pins them. |
| **III.2 Falsifiability** | PASS | Each formula names a prediction + distinguishing observable in its docstring (e.g., "drift is zero while agitation is zero → hegemony holds"; "solidarity suppresses pull"). SC-002 is the canonical falsifier: near-zero drift in the pacified decade. |
| **III.7 Determinism Hash / Replayability** | PASS | Frozen `SocialClass`/`ReactionaryDefines`. Stochastic rolls (defection, spontaneous riot) use the seed-deterministic `_resolve_rng(services, tick)` pattern (spec-070 precedent), never module `random`. New always-on reads MUST keep the tri-county gate byte-identical OR take the written-proof path (R-PROOF). Graph round-trip preserves new fields. |
| **III.8 Structural Provenance (Aleksandrov)** | PASS | `Fascist_Pull = Agitation × (Entitlement / (Solidarity + 0.1))` traces to a material relation: entitlement = the stake in imperial rent; solidarity in the denominator = the cross-colonial bridge that reroutes agitation to revolution (I.4). The StanceIntervention is a signed shove on the opposition balance (adjunction defect), not an ungrounded counter. |
| **III.10 Earn-Its-Keep (Amendment K)** | PASS | The fascist pull ships as a running computation that writes a `StanceIntervention` into the live opposition registry (a LAW: the pull moves the balance; a PREDICTION: crisis-gated drift), not category-theory vocabulary. It READS `dialectical_regime` rather than reintroducing a parallel classifier (VIII.11 respected — no add-only ratchet; `fascist_alignment` is a bounded [0,1] accumulator that becomes a QUALITY at ≥1.0 per I.7). |
| **I.4 George Jackson Bifurcation** | PASS | 071 IS the fascism pole of I.4: crisis + absent solidarity → fascist drift; solidarity denominator implements "solidarity across the colonial divide → revolution instead". |
| **I.7 Quantitative → Qualitative** | PASS | `fascist_alignment` (float quantity, [0,1]) accumulates; at the ≥1.0 threshold it transforms discretely into faction capture (`aligned_faction_id` set + FASCIST_RECRUITMENT). Threshold explicit in defines. |
| **I.16 Organization vs Institution** | PASS | Factions/orgs are the agents that recruit; SocialClass is substrate. Reassignment is a class→faction attribution (`aligned_faction_id`), not the class "acting". Fascist verbs (POGROM/LOCKOUT/VIGILANTISM) are org actions via OODA. |
| **I.20 Spatial Substrate / Political Claims Overlay** | PASS | No substrate mutation. `aligned_faction_id` is a class attribution (overlay-like), not a hex/county edit. INFLUENCES edges (faction→territory) are untouched. |
| **II.11 Subsystem Table Ownership** | PASS | No new tables; no cross-subsystem direct table reads. The system reads/writes only graph node/edge attrs and graph attrs (`opposition_interventions`, `dialectical_regime`) it is the declared consumer/producer of. |
| **II.12 Matrix / Authoring API (Amendment L)** | PASS | The system uses the GraphProtocol / BabylonGraph authoring surface (`query_nodes`, `query_edges`, `update_node`, `update_edge`, `get_graph_attr`, `set_graph_attr`) via `SystemBase._wrap_graph`. No raw rustworkx, no networkx imports. |
| **IV Michigan Test Case** | PASS | SC-002/SC-005 run against the Michigan 83-county canonical + the tri-county 5-tick gate (IV.2 backward-compat). |
| **Amendment K — Dialectics** | PASS | Consumes OppositionRegistry via StanceIntervention (the 071 hook), reads `dialectical_regime`; does not recompute regime, does not add a saturating ratchet (VIII.11). |
| **Amendment L — rustworkx** | PASS | All graph access through BabylonGraph/GraphProtocol; determinism preserved via existing insertion-ordered surfaces. |

**No violations → Complexity Tracking table omitted.**

### AI Context Budget tier note (III.9)

Operating with P0 (I.19 dialectic primitive via StanceIntervention, III.7
determinism) + domain P1 (I.4 bifurcation, I.7 quant→qual, I.16 orgs, III.1
no-magic, III.10 earn-its-keep, IV Michigan). P2 principles retained where
relevant (I.5 Dept III not touched; VIII.11 ratchet anti-pattern observed).

## Project Structure

### Documentation (this feature)

```text
specs/071-reactionary-subject/
├── spec.md              # done
├── plan.md              # this file
├── research.md          # decisions + provenance (Phase 0)
├── data-model.md        # entity/field/edge deltas (Phase 1)
├── quickstart.md        # how to exercise the crisis scenario
├── contracts/           # formula + event contracts
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/
├── formulas/reactionary.py                     # NEW — pull/defection/riot/entitlement + RLF helpers
├── config/defines/survival.py or new reactionary.py  # NEW ReactionaryDefines
├── config/defines/__init__.py, _assembler.py   # wire ReactionaryDefines
├── models/entities/social_class.py             # +entitlement/volatility/fascist_alignment/aligned_faction_id
├── models/enums/events.py                       # +8 EventType values
├── models/enums/actions.py                      # +4 ActionType values
├── engine/systems/reactionary.py                # NEW FascistFactionSystem (pos 17.4)
├── engine/simulation_engine.py                  # register system + partition set
├── engine/systems/struggle.py                   # L_u volatility → SPONTANEOUS_RIOT
├── engine/systems/decomposition.py              # create-on-demand enforcer/internal-proletariat
├── engine/systems/ooda.py (+ resolution)        # POGROM/LOCKOUT/VIGILANTISM/RED_BROWN_COUP
└── formulas/consciousness_routing.py            # f→r ε-gate + assimilation_ratio + contestation

tests/
├── unit/formulas/test_reactionary.py            # formula unit + doctest coverage
├── unit/models/test_social_class_reactionary.py # fields + round-trip
├── unit/engine/systems/test_fascist_faction_system.py
├── unit/engine/systems/test_struggle_volatility.py
├── unit/engine/systems/test_decomposition_enforcer_creation.py
├── unit/config/test_reactionary_defines.py
└── integration/test_reactionary_crisis.py       # SC-001 induced-crisis drift + reassignment
```

**Structure Decision**: Single-project engine layout. New code follows the
existing formula/system/defines/enum separation. The FascistFactionSystem
mirrors the SovereigntySystem/FactionInfluenceSystem structure (SystemBase
subclass, deterministic sorted iteration, `_publish` events).

## Design detail (Phase 1 highlights; full record in research.md/data-model.md)

1. **SocialClass fields** — added as real frozen model fields (Intensity
   type + `aligned_faction_id: str | None`). Role defaults applied in the
   existing `_set_*_from_role` model_validator pattern. `model_dump()` in
   `to_graph()` serializes them; `from_graph()` reconstructs them (they are
   NOT added to `SOCIAL_CLASS_COMPUTED_FIELDS`). Round-trip test added.

2. **FascistFactionSystem** — position 17.4 in `_DEFAULT_SYSTEMS`, added to
   `CONSEQUENCE_SYSTEMS`. Per tick, for active nodes with role ∈ {C_la, C_pb}:
   read agitation (this tick's, post-ConsciousnessSystem), entitlement, and
   incident SOLIDARITY strength; compute pull; if > threshold, bump
   `fascist_alignment` and publish FASCIST_DRIFT + push a `StanceIntervention`
   (signed toward the reactionary pole) onto `opposition_interventions`; if
   alignment ≥ 1.0 and a fascist faction exists and node not yet captured,
   set `aligned_faction_id` and publish FASCIST_RECRUITMENT. Then process
   MEMBERSHIP edges (org→LA) for chauvinism accumulation; on crisis events
   (this tick's EventType.ECONOMIC_CRISIS / SUPERWAGE_CRISIS), roll defection
   per member and emit ORGANIZATIONAL_FRACTURE / RED_BROWN_COUP.

3. **Fascist-faction predicate** — a BalkanizationFaction node
   (`_node_type == "balkanization_faction"`) is "fascist" iff
   `is_settler_formation is True and colonial_stance == UPHOLD`, OR its
   `ideology` string matches a configured token set (default {"fascist",
   "reaction"}). Deterministic pick: lowest-ID matching faction.

4. **StanceIntervention target** — the pull shoves the `capital_labor`
   opposition balance toward the reactionary (capital) pole by a
   defines-scaled amount (`stance_gain × min(pull, cap)`), audited
   `source="system:fascist_faction"`. If no such opposition key exists this
   tick, the intervention is skipped (no crash).

5. **StruggleSystem volatility** — add LUMPENPROLETARIAT to a new
   spontaneous-riot branch: `riot_risk = volatility × (1 − discipline)` where
   discipline is read from incident MEMBERSHIP/organization context (default
   0.0 when unorganized). Roll via seed RNG; on fire, destroy wealth
   (existing destruction rate) but build NO solidarity, publish
   SPONTANEOUS_RIOT. Keep the existing periphery/uprising paths intact so the
   income-circuit hegemony test stays green.

6. **Decomposition create-on-demand** — when `_find_entity_by_role(...,
   CARCERAL_ENFORCER)` / `INTERNAL_PROLETARIAT` returns None, create the node
   with a derived, pattern-valid id (`^C[0-9]{3}$`) offset from the LA id, at
   the split population/wealth, `active=True`. Guarded so the canonical decade
   (no decomposition) never creates them.

7. **RLF simplex** — extend `consciousness_routing.py`: keep
   `normalize_to_simplex` (already sums-to-1 with liberal default; add a
   contract test), add `assimilation_ratio(l, f)`,
   `ideological_contestation(r, l, f)` (entropy/log3, DIAGNOSTIC), and an
   `apply_fr_gate(...)` that zeroes an `f→r` flow unless
   (proletarianization ∧ adjacent-r ∧ solidarity) all hold (ε-gate). No
   potential-function formulation (rejected per §9.4).

## R-PROOF plan

The base canonical world has no orgs/factions and (during the pacified
decade) agitation ≈ 0, so `Fascist_Pull ≈ 0`, no drift, no interventions.
Expectation: the tri-county 5-tick gate stays **byte-identical**. Procedure:
(1) confirm green baseline BEFORE changes (DONE — `qa:e2e-regression`
Δ=0.000%); (2) implement; (3) re-run `qa:e2e-regression`; (4a) if
byte-identical → no baseline change needed; (4b) if it moves → write the
proof (what/why/magnitude), regenerate `tests/baselines/detroit-tri-county-5t.json`,
commit proof + baseline together (may use `--no-verify` for the artifact).
Only ONE proof window; 101 does not start until it closes.

## Complexity Tracking

No Constitution violations — table omitted.
