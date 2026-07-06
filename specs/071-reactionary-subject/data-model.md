# Data Model Deltas: The Reactionary Subject (spec-071)

Phase 1 output. Concrete field/enum/edge/system additions.

## 1. SocialClass (extend — `src/babylon/models/entities/social_class.py`)

Four new frozen fields (Intensity = `float ∈ [0,1]` + SnapToGrid; the id/None
one is a plain optional str):

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `entitlement` | `Intensity` | 0.0 (role-defaulted) | Stake in the imperial order. Role defaults: PERIPHERY_PROLETARIAT 0.2, LABOR_ARISTOCRACY 0.8, COMPRADOR_BOURGEOISIE 0.7, LUMPENPROLETARIAT 0.0, else 0.0. |
| `volatility` | `Intensity` | 0.0 (role-defaulted) | Disorder propensity. Role default: LUMPENPROLETARIAT 0.8, else 0.0. |
| `fascist_alignment` | `Intensity` | 0.0 | Drift accumulator; ≥1.0 ⇒ capture. |
| `aligned_faction_id` | `str \| None` | None | The faction the node was captured by (D2). |

**Role defaulting**: extend the existing `@model_validator(mode="after")`
pattern (`_set_subsistence_multiplier_from_role`) with an analogous
`_set_reactionary_defaults_from_role` that only fills entitlement/volatility
when they are still at the 0.0 sentinel AND a role default exists. Role→default
maps are module-level dicts (mirroring `_SUBSISTENCE_MULTIPLIERS`), sourced from
`ReactionaryDefines` values at construction is NOT possible (frozen model, no
services) — so the maps are module constants that MUST equal the
`ReactionaryDefines` defaults; a unit test pins the equality (III.1: the model
constants and defines agree, single source verified by test).

**Round-trip**: the four fields are real model fields → `model_dump()` in
`to_graph()` emits them, `from_graph()` reconstructs them. They are NOT added
to `SOCIAL_CLASS_COMPUTED_FIELDS`. Add a round-trip test.

## 2. EventType (extend — `src/babylon/models/enums/events.py`)

Add 8 values (StrEnum, snake_case). Current count 71 → 79:

```
FASCIST_DRIFT = "fascist_drift"
FASCIST_RECRUITMENT = "fascist_recruitment"
ORGANIZATIONAL_FRACTURE = "organizational_fracture"
RED_BROWN_COUP = "red_brown_coup"
POGROM = "pogrom"
LOCKOUT = "lockout"
VIGILANTISM = "vigilantism"
SPONTANEOUS_RIOT = "spontaneous_riot"
```

## 3. ActionType (extend — `src/babylon/models/enums/actions.py`)

Add 4 values:

```
POGROM = "pogrom"
LOCKOUT = "lockout"
VIGILANTISM = "vigilantism"
RED_BROWN_COUP = "red_brown_coup"
```

## 4. ReactionaryDefines (new — `src/babylon/config/defines/survival.py`
or a new `reactionary.py`, wired into `GameDefines` as `.reactionary`)

Frozen Pydantic model with all constants from research.md R-001. Wired in
both `_assembler.py` (`reactionary=ReactionaryDefines(**data.get("reactionary", {}))`)
and re-exported in `defines/__init__.py`.

## 5. MEMBERSHIP edge attribute (graph edge-state; D3)

`chauvinism: float ∈ [0,1]` on MEMBERSHIP edges (Organization → LABOR_ARISTOCRACY
SocialClass). Accumulated in-place by FascistFactionSystem; read on crisis for
defection. Not a Relationship model field (graph edge-state only; the base
canonical world has no MEMBERSHIP edges).

## 6. FascistFactionSystem (new — `src/babylon/engine/systems/reactionary.py`)

SystemBase subclass, `name="Fascist Faction"`, `creates_value=False`
(destroys none; defection/coup mutate org/edge state, not hex c+v+s).
Registered at position 17.4 in `_DEFAULT_SYSTEMS` and in `CONSEQUENCE_SYSTEMS`.

Per tick:
1. For active `social_class` nodes with role ∈ {LABOR_ARISTOCRACY,
   COMPRADOR_BOURGEOISIE}: compute pull; drift; StanceIntervention; capture.
2. For MEMBERSHIP edges org→LA: accumulate chauvinism; on this tick's crisis
   events, roll defection → ORGANIZATIONAL_FRACTURE / RED_BROWN_COUP.

Reads: node `ideology.agitation`, `entitlement`, `fascist_alignment`,
`aligned_faction_id`, incident SOLIDARITY `solidarity_strength`; graph attrs
`dialectical_regime`, `opposition_states`; `balkanization_faction` nodes.
Writes: node `fascist_alignment`, `aligned_faction_id`; MEMBERSHIP
`chauvinism`; graph attr `opposition_interventions` (append). Publishes the
8 new events as applicable.

## 7. StruggleSystem (extend — `src/babylon/engine/systems/struggle.py`)

Add a LUMPENPROLETARIAT spontaneous-riot branch: `riot_risk =
volatility × (1 − discipline)`, roll via seed RNG; on fire, apply the
existing wealth-destruction rate, build NO solidarity, publish
SPONTANEOUS_RIOT. `_STRUGGLING_ROLES` already includes LUMPENPROLETARIAT; the
new branch is additive and must not alter the periphery/uprising paths (keep
income-circuit hegemony green).

## 8. DecompositionSystem (extend — `src/babylon/engine/systems/decomposition.py`)

In `_execute_decomposition`, when `_find_entity_by_role(..., CARCERAL_ENFORCER,
include_inactive=True)` / `INTERNAL_PROLETARIAT` returns None, create the node
via `graph.add_node(new_id, node_type="social_class", ...)` with a
pattern-valid id derived from the LA id, then apply the split. Guarded so the
canonical decade never triggers it.

## 9. OODA resolution (extend — `src/babylon/engine/systems/ooda.py` +
resolution map)

Add POGROM/LOCKOUT/VIGILANTISM to the org-action resolution with materially
grounded effects (POGROM: target community/node repression↑, wealth
destruction on the target; LOCKOUT: sever/attenuate WAGES/EMPLOYMENT flow;
VIGILANTISM: local repression spike). RED_BROWN_COUP is emitted by the
FascistFactionSystem (auto-trigger), not selected by OODA. Exact effect
magnitudes → ReactionaryDefines.

## 10. consciousness_routing.py RLF helpers (extend)

- `normalize_to_simplex(r, l, f)` — exists; add contract test.
- `assimilation_ratio(l, f) -> float` — `f/(l+f)`, 0 when `l+f==0`.
- `ideological_contestation(r, l, f) -> float` — `H(r,l,f)/log 3`, DIAGNOSTIC.
- `apply_fr_gate(delta_fr, *, proletarianizing, adjacent_r, has_solidarity,
  epsilon) -> float` — returns `delta_fr` iff all three preconditions hold,
  else `epsilon` (default 0.0). No potential function.
