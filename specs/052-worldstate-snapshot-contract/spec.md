# WorldState Snapshot Contract (Frontend v0)

**Status:** Draft 1
**Type:** Reference
**Scope:** The JSON payload the Django server emits and the React client consumes for a single tick snapshot. This document defines shape and semantics only. It does not define the engine internals, the Postgres schema, or the WebSocket transport. It does define what the frontend is allowed to assume.

## 1. Purpose

This contract exists so the frontend can be built against a stable shape without locking in concepts the constitution forbids. It replaces the ad-hoc mock currently in use. The numbers in any mock payload conforming to this contract remain fake until the engine computes real ones; the *shape* is load-bearing from day one.

## 2. Non-goals

- TypeScript types (generate after shape stabilizes)
- JSON Schema / OpenAPI (same)
- WebSocket framing, delta encoding, subscription semantics
- Authentication, session lifecycle
- Any engine-side computation detail

## 3. Core invariants

Four rules govern every field in this contract. Violating any of them is a bug in the contract, not the client.

1. **Organizations are the only agents.** Classes, demographics, and identity groups are never top-level entities. They appear as hyperedge memberships or as derived aggregations.
2. **Primitives and derived values are separated.** Anything the engine computes from the ledger lives under `derived`. The client MUST treat `derived` as read-only cache. Primitives live at the top level of their owning object.
3. **Qualities are enums, quantities are floats.** Edge modes, consciousness tendencies, and phase enums never carry a scalar "strength" alongside. If the UI needs visual weight, it derives one from an independent quantity (value flow, tension, cadre labor).
4. **Hyperedges are first-class.** Community membership is never expressed as a pairwise edge or a field on an entity.

## 4. Envelope

```
{
  "status": "ok",
  "tick": <int>,
  "session_id": <uuid>,
  "data": { <snapshot> }
}
```

The envelope is unchanged from the current mock. All subsequent sections describe the contents of `data`.

## 5. Snapshot top level

```
data: {
  tick,
  session_id,
  organizations: [...],
  institutions: [...],
  territories: [...],
  hyperedges: [...],
  edges: [...],
  events: [...],
  traps: {...},
  derived: {...}
}
```

Note what is absent: there is no top-level `entities` array. The five `ent-*` records in the current mock are removed. There is no top-level `economy` block; its contents move under `derived`.

## 6. Organizations

Organizations are the agents. Four subtypes are permitted. No others.

```
{
  "id": "org-peoples-front",
  "name": "People's United Front",
  "org_type": "civil_society_org",     // enum, see below
  "class_character": "proletarian",    // informational label
  "cohesion": 0.6,                     // primitive float [0,1]
  "cadre_level": 0.35,                 // primitive float [0,1]
  "budget": 12.0,                      // primitive float
  "heat": 0.2,                         // primitive float [0,1]
  "territory_ids": ["terr-wayne-01", "terr-wayne-03"],
  "hyperedge_memberships": ["hx-new-afrikan", "hx-women"],
  "consciousness": {
    "liberal": 0.15,
    "fascist": 0.05,
    "revolutionary": 0.80
  },
  "ooda": {
    "observe": 0.6,
    "orient": 0.5,
    "decide": 0.7,
    "act": 0.8,
    "cycle_ticks": 1
  },
  "vanguard": { ... } | null
}
```

**`org_type` enum:** `state_apparatus`, `business`, `political_faction`, `civil_society_org`. The current mock's `paramilitary` is not permitted; a reactionary militia is a `political_faction`.

**`consciousness`:** always a three-vector summing to 1.0. Never a scalar, never a single enum. The `LIBERAL` / `FASCIST` / `REVOLUTIONARY` enum the current mock uses on orgs is removed.

**`ooda`:** required on every org. Nulls not permitted. The frontend will render the OODA profile as a capability bar; the engine will use it to gate action resolution.

**`vanguard`:** optional substructure for orgs that run a cadre pipeline. Retains the current mock's fields (`cadre_labor`, `sympathizer_labor`, `reputation`, caps). State apparatuses and businesses set this to null.

## 7. Institutions

Institutions crystallize social relations and persist across member turnover. Organizations can be housed in them. Institutions are not agents; they do not act. They have fractional composition across state factions.

```
{
  "id": "inst-city-hall",
  "name": "Detroit City Hall",
  "apparatus_type": "executive",       // enum
  "social_function": "governance",
  "class_inscription": "bourgeois-democratic",
  "legitimacy": 0.55,
  "budget": 80.0,
  "housed_org_ids": ["org-state-apparatus"],
  "territory_ids": ["terr-wayne-01"],
  "factional_composition": {
    "liberal_technocratic": 0.45,
    "revanchist_fascist": 0.25,
    "institutionalist_bonapartist": 0.30
  }
}
```

`factional_composition` replaces the three loose fields in the current mock. Values sum to 1.0.

## 8. Territories

Territories are the discretized manifold. H3 resolution 7 is the base unit. Aggregation to resolution 6 and 5 is computed server-side and lives under `derived`, not in the territory object itself.

```
{
  "id": "terr-wayne-01",
  "name": "Downtown Detroit",
  "h3_index": "842a9b7ffffffff",
  "h3_resolution": 7,
  "county_fips": "26163",
  "sector_type": "urban_core",
  "territory_type": "metropolitan",
  "profile": "HIGH_PROFILE",
  "heat": 0.33,                         // primitive, α-smoothed coefficient
  "rent_level": 0.85,                   // primitive
  "biocapacity": 0.2,
  "population": 245000,
  "under_eviction": false,
  "host_id": null,
  "occupant_id": null
}
```

**Removed from the current mock:** floating-point residue like `0.33249999999999996`. The contract requires server-side rounding to 4 decimal places for any field the UI renders as a percentage or bar. Provenance (what coefficient, what α, what source table) is not in the payload — it is in the server's constants provenance audit.

**Added:** `county_fips` so the frontend can group by Wayne / Oakland / Macomb without hardcoding H3 prefix logic. `h3_resolution` so a future aggregation view can mix levels safely.

## 9. Hyperedges (XGI layer)

The category the current mock entirely omits. A hyperedge is a set of member ids (orgs, institutions, or territories) plus a type and a material/ideological distinction.

```
{
  "id": "hx-new-afrikan",
  "category": "contradiction_pair",     // enum, see below
  "label": "NEW_AFRIKAN",
  "contradiction_partner_id": "hx-settler",   // null for non-pair categories
  "member_ids": ["org-peoples-front", "terr-wayne-01", "terr-wayne-02"],
  "material_basis": {
    "description": "Structural position under settler-colonial capital accumulation in Wayne County",
    "indicators": ["residential_segregation", "wealth_gap", "incarceration_rate"]
  },
  "ideological_dimension": {
    "collective_identity_strength": 0.55,
    "organizational_vehicles": ["org-peoples-front"]
  }
}
```

**`category` enum:** exactly three values.

- `contradiction_pair` — both hegemonic and marginalized sides exist as real hyperedges and reference each other via `contradiction_partner_id`. Examples: SETTLER ↔ NEW_AFRIKAN, SETTLER ↔ FIRST_NATIONS, SETTLER ↔ CHICANO, PATRIARCHAL ↔ WOMEN, PATRIARCHAL ↔ TRANS.
- `institutional_exclusion` — only the marginalized side exists; `contradiction_partner_id` is null. Examples: DISABLED, QUEER, UNDOCUMENTED, INCARCERATED. ABLED is not a hyperedge.
- `lifecycle_phase` — D-P-D' circuit phase. Examples: YOUTH, ADULT, ELDER. Not an identity community.

**Material vs ideological:** the gap between `material_basis` (objective structural position) and `ideological_dimension.collective_identity_strength` (subjective for-itself consciousness) is the terrain of political struggle. The frontend should render these as two separate readings on the same hyperedge, not average them.

## 10. Dyadic edges (NetworkX layer)

Edges carry value, tension, and repression flows between two nodes. The type is qualitative. There is no scalar "strength" alongside the type.

```
{
  "id": "edge-bourg-prolet-01",
  "source_id": "org-finance-bloc",
  "target_id": "org-peoples-front",
  "mode": "EXTRACTIVE",                // enum, exactly five values
  "value_flow": 25.0,                  // primitive float, Dept-tagged server-side
  "tension": 0.65,                     // primitive float [0,1]
  "repression_flow": 0.0
}
```

**`mode` enum:** exactly five values.

- `EXTRACTIVE` — replaces `EXPLOITATION` and `TRIBUTE` in the current mock.
- `TRANSACTIONAL` — replaces `WAGES`, market exchange, rent payments.
- `SOLIDARISTIC` — replaces `SOLIDARITY`.
- `ANTAGONISTIC` — open conflict, repression, sabotage.
- `CO_OPTIVE` — absorption, NGO capture, patronage.

**Removed:** `solidarity_strength` field. Entirely. If the renderer needs visual thickness on a solidaristic edge it reads `value_flow`.

**Removed:** `ADJACENCY` edges between territories. Spatial adjacency is implicit in H3 indexing and computed client-side or fetched from a separate adjacency endpoint. It is not a graph edge in the simulation sense.

**Removed:** `HOUSES` edges between institutions and orgs. Replaced by `institution.housed_org_ids` which already exists.

**Edge mode transitions** are governed by a server-side state machine (e.g., EXTRACTIVE → SOLIDARISTIC requires TRANSACTIONAL intermediate). The client never writes to `mode`. The client only reads it.

## 11. Derived block

Everything the engine computes from the ledger. The client treats this as read-only cache. It is permitted to be stale for one tick during recomputation.

```
"derived": {
  "value_tensor": {
    "departments": ["I", "IIa", "IIb", "III"],
    "components": ["c", "v", "s"],
    "values": [
      [<c_I>, <v_I>, <s_I>],
      [<c_IIa>, <v_IIa>, <s_IIa>],
      [<c_IIb>, <v_IIb>, <s_IIb>],
      [<c_III>, <v_III>, <s_III>]
    ],
    "conservation_residual": 0.0
  },
  "imperial_rent": {
    "unequal_exchange": 6.2,
    "externalized_reproductive": 5.1,
    "domestic_shadow": 4.2,
    "total": 15.5
  },
  "dept_iii_visibility": {
    "g33": 0.12
  },
  "class_aggregates": {
    "proletariat": { "population": 850000, "wage_share": 0.38, ... },
    "labor_aristocracy": { "population": 210000, ... },
    "petite_bourgeoisie": { ... },
    "bourgeoisie": { ... },
    "lumpenproletariat": { ... }
  },
  "economy": {
    "gdp": 180.0,
    "gini": 0.62,
    "profit_rate": 0.18,
    "exploitation_rate": 0.55
  },
  "predictions": {
    "per_hyperedge": {
      "hx-new-afrikan": {
        "p_acquiescence": 0.55,
        "p_revolution": 0.18,
        "warsaw_ghetto_corollary_triggered": false
      }
    }
  }
}
```

**Class aggregates live here, not at the top level.** This is the critical shift from the current mock. `ent-proletariat.agitation` becomes `derived.class_aggregates.proletariat.agitation_proxy`, computed from member org states and hyperedge readings. Classes are not agents; they are query results.

**Imperial rent is always three components plus a total.** Never a bare scalar.

**Predictions are per-hyperedge, not per-entity.** `p_revolution` on an "industrial proletariat" entity is a category error. `p_revolution` over the NEW_AFRIKAN hyperedge is a coherent prediction.

## 12. Events

Unchanged from current mock, loose shape:

```
"events": [
  { "type": "TICK_RESOLVED", "tick": 1, "data": { "old_tick": 0 } },
  { "type": "EDGE_MODE_TRANSITION", "tick": 1, "data": { "edge_id": "...", "from": "EXTRACTIVE", "to": "TRANSACTIONAL" } }
]
```

The frontend consumes events for animations and narrative. Event content is not authoritative; the authoritative state is elsewhere in the snapshot.

## 13. Traps

Mostly unchanged, with one requirement: `indicators` must be non-empty whenever `score > 0`. A score without indicators is a contract violation.

```
"traps": {
  "liberal":     { "score": 0.1,  "severity": "none", "indicators": ["electoralism_drift"], "ticks_at_moderate": 0 },
  "ultra_left":  { "score": 0.05, "severity": "none", "indicators": [], "ticks_at_moderate": 0 },
  "rightist":    { "score": 0.08, "severity": "none", "indicators": ["nativist_framing"], "ticks_at_moderate": 0 },
  "active_trap": null,
  "game_over_trap": null
}
```

## 14. Detroit seed requirements

Any mock payload conforming to this contract for the Detroit test case MUST include:

- At least one `state_apparatus` org (Michigan) and one `state_apparatus` org or institution for the city (Detroit).
- At least one proletarian `civil_society_org` in Wayne County.
- At least one reactionary `political_faction` in Macomb or Oakland.
- The SETTLER / NEW_AFRIKAN contradiction pair as two linked hyperedges, with NEW_AFRIKAN members drawn from Wayne territories and at least one org.
- At least one `institutional_exclusion` hyperedge (suggest INCARCERATED, since Wayne's carceral geography is load-bearing for the test case).
- Territories covering at least two H3 cells in each of Wayne (26163), Oakland (26125), Macomb (26099).
- A `derived.value_tensor` with non-zero values in at least Departments I and III.
- A `derived.imperial_rent` with all three components present.

Numbers remain fake at this stage. Shape is not.

## 15. Deferred

Out of scope for this contract version. Do not add to the payload until specified:

- Multi-resolution H3 aggregation views (derived, but not in v0)
- Full LODES commute flow tensor (Volume II circulation)
- Capital migration history (Volume III equalization)
- OODA action queues and per-tick action budgets
- Semantic/narrative layer outputs from the LLM
- Per-org memory, reputation history, faction splits
- Full factional state AI objective functions

When any of these land, they extend this contract via an amendment section. They do not reshape existing fields.

## 16. Open questions

One remaining shape decision I did not make unilaterally: should `hyperedge_memberships` on an org be a list of hyperedge ids (current draft) or should membership live exclusively inside the hyperedge's `member_ids` array and the frontend reverse-index it? The current draft duplicates the relation on both sides for read performance. The alternative is cleaner but forces the client to build a membership index on every snapshot. Flag this before TypeScript types are generated.
