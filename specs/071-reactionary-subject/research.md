# Research & Provenance: The Reactionary Subject (spec-071)

Phase 0 output. Records the constant provenance (Constitution III.1/III.4),
the resolved design decisions, and the theory grounding (III.8 Aleksandrov).

## R-001 — Constant provenance

All numerics are **theory-derived tunables**, provenance = the catalog entry
`project/03-next-spec-071.md` "What to build" (which itself derives from the
Epoch-3 vision docs). These are STRATEGIC-intervention parameters, not
empirical data — Constitution III.5 explicitly separates strategic
coefficients from data-sourced material conditions, and the existing
`StruggleDefines` / `BalkanizationDefines` follow the identical "theoretical
defaults in a Pydantic model, overridable via YAML" pattern. No new
`data-catalog.yaml` entry is required (no runtime data source added).

| Constant | Default | Source / grounding |
|----------|---------|--------------------|
| `fascist_pull_threshold` | 1.0 | catalog: "if > 1.0 → drift" |
| `fascist_drift_step` | 0.05 | catalog: "fascist_alignment += 0.05" |
| `fascist_recruitment_threshold` | 1.0 | catalog: "at ≥ 1.0 alignment → reassign" |
| `solidarity_pull_epsilon` | 0.1 | catalog formula: "Entitlement / (Solidarity + 0.1)" — the +0.1 both guards div-by-zero and sets the maximal unsuppressed pull |
| `chauvinism_base_rate` | 0.01 | catalog: "chauvinism +0.01/tick base" |
| `chauvinism_superwage_bonus` | 0.02 | catalog: "+0.02 if super-waged" |
| `red_brown_coup_fraction` | 0.5 | catalog: ">50% defection fires RED_BROWN_COUP" |
| `entitlement_default_periphery_proletariat` | 0.2 | catalog: "P=0.2" |
| `entitlement_default_labor_aristocracy` | 0.8 | catalog: "C_la=0.8" |
| `entitlement_default_comprador_bourgeoisie` | 0.7 | catalog: "C_pb=0.7" |
| `entitlement_default_lumpenproletariat` | 0.0 | catalog: "L_u=0.0" |
| `volatility_default_lumpenproletariat` | 0.8 | catalog: "volatility (L_u default 0.8)" |
| `spontaneous_riot_threshold` | 0.5 | NEW — the fire threshold for `volatility×(1−discipline)`; mid-range default (a riot needs both high volatility AND low discipline). Tunable; falsifier is the L_u riot test. |
| `defection_default_discipline` | 0.3 | NEW — org discipline D in `sigmoid(chi − D)` when an org exposes no cadre-derived discipline; matches the default repression/organization scale used elsewhere. |
| `stance_intervention_gain` | 0.05 | NEW — scales `min(pull, cap)` into a bounded shove on the opposition balance ∈ [−1,1]; small so a single tick's reactionary pull nudges, not flips, the balance (I.7 gradualism before the ≥1.0 qualitative jump). |
| `stance_intervention_cap` | 1.0 | NEW — caps the pull magnitude fed to the shove so an extreme agitation spike cannot saturate the balance in one tick. |
| `fr_gate_epsilon` | 0.0 | §9.4: `f→r` forbidden unless (proletarianization ∧ adjacent-r ∧ solidarity); ε=0 = fully forbidden by default (the gate opens only when all three hold). |

## R-002 — Fascist-faction predicate (D2)

A `BalkanizationFaction` graph node is treated as "fascist" (a valid capture
target) iff `is_settler_formation is True and colonial_stance == UPHOLD`
(the settler-restorationist archetype from spec-070's data model), OR its
`ideology` string contains any configured token (default {"fascist",
"reaction", "revanch"}). Deterministic selection = lowest node id among
matches (III.7). If no fascist faction exists, drift still accrues but
capture is deferred (no crash) — matching spec-070's "faction may be absent"
tolerance.

## R-003 — Pipeline position (D1)

Position **17.4**: after ConsciousnessSystem (17), before SovereigntySystem
(17.5). The reactionary subject reads THIS tick's agitation (written by
ConsciousnessSystem @17) and LAST tick's `dialectical_regime`/`opposition_states`
(ContradictionSystem @18 runs after). It writes `opposition_interventions`
consumed by ContradictionSystem @18 the same tick. Classified into
`CONSEQUENCE_SYSTEMS` (spec-056 partition). The spec-056 import-time
partition assertion is updated in lockstep.

## R-004 — StanceIntervention grounding (III.8 + Amendment K)

The pull is a signed shove on the `capital_labor` opposition balance toward
the capital (reactionary) pole. Grounding: the reactionary subject's turn is
a material realignment of the class antagonism's leading aspect — the
labor-aristocratic/petty-bourgeois stratum re-identifies with capital-order.
Expressing it as a `StanceIntervention` (the ADR051 hook designed for 071)
means the reactionary drift moves the LIVE opposition registry, not a
private counter (III.10 earn-its-keep; VIII.11 no add-only ratchet — the
per-tick pull is a fresh measured quantity, and `fascist_alignment` is a
bounded [0,1] accumulator that triggers a discrete qualitative capture, which
I.7 explicitly sanctions as legitimate quantity→quality, distinct from the
banned saturating-tension ratchet).

## R-005 — Determinism (III.7)

Defection and spontaneous-riot rolls use `_resolve_rng(services, tick)`
(spec-070 precedent: `services.rng` if present, else
`random.Random(0xBA1AC1A + tick)`). No module-level `random`. The
FascistFactionSystem's node/edge iteration is lex-sorted by id.

## R-006 — Carceral create-on-demand (D4)

DecompositionSystem currently no-ops the enforcer branch because the bridge
seeds no `CARCERAL_ENFORCER`. Chosen fix: create the enforcer and
internal-proletariat nodes on demand (pattern-valid ids derived from the
decomposing LA id) rather than seeding them per-county. This is
baseline-preserving: the canonical decade never decomposes (rent exhaustion
≈ year 43 ≫ 520 ticks), so no new nodes appear in the base run. Only 071's
induced-crisis tests exercise creation.

## R-007 — Rejected alternatives

- **Reassign via INFLUENCES edges** (faction→territory): rejected — I.20
  keeps INFLUENCES as territory overlays; class capture is a class-level
  attribution (`aligned_faction_id`).
- **Parallel fascist counter fed to nothing**: rejected — violates III.10 /
  the 03 §"Inherited obligations" (use the StanceIntervention hook).
- **Per-county enforcer seeding in the bridge**: rejected — adds 2×83 nodes
  every tick and forces a baseline regeneration for zero canonical benefit.
- **f→r potential/free-energy formulation**: rejected per §9.4 (Kolmogorov
  detailed-balance break — no potential exists).
