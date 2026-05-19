# Phase 0 Research: Sovereign Topology + Faction Influence + Balkanization

**Branch**: `070-balkanization` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

This document resolves the five research questions identified in
the Constitution Check + plan-phase-deferred clarifications. Each
section follows the Decision / Rationale / Alternatives format.

---

## R-001: Multiplier Provenance + Missing Data Sources (III.1 + III.4)

### Context

The spec inherits eleven numeric multipliers from
`ai-docs/epochs/epoch3/balkanization-spec.yaml` v1.2.0 (2025-12-26):

| Constant | Where | Value |
|---|---|---|
| `metabolic_impact(INTENSIFY)` | FR-004 | −0.02 |
| `metabolic_impact(CONTINUE)` | FR-004 | −0.005 |
| `metabolic_impact(CEASE)` | FR-004 | +0.01 |
| `extraction_modifier(UPHOLD/IGNORE/ABOLISH)` | FR-007 | 1.5 / 0.8 / 0.0 |
| `violence_modifier(UPHOLD/IGNORE/ABOLISH)` | FR-007 | 2.0 / 0.5 / 0.3 |
| `class_reduction(UPHOLD/IGNORE/ABOLISH)` | FR-007 | 0.0 / 0.7 / 0.5 |
| `metabolic_reduction(UPHOLD/IGNORE/ABOLISH)` | FR-007 | −0.5 / 0.0 / +0.8 |

Constitution III.1 forbids magic constants without provenance.
III.4 forbids data sources without catalog entries. FR-039 names
three proxy data sources for INFLUENCES seeding: union density,
AIANNH (TIGER) area boundaries, and recent presidential election
results. The catalog (v2.6.3) contains none of these explicitly.

### Decision

**Multiplier provenance**:

- **Tier 1 (Theoretical Defaults)**: All seven multiplier sets in
  FR-007 + FR-004 are **theoretically-derived defaults**, not
  empirical measurements. Their rationale is the dialectical
  logic of the Three Stances (balkanization-spec.yaml §theory),
  not a calibration against observed habitability decay rates.
  This is acknowledged in `data-model.md` and the
  `BalkanizationDefines` Pydantic model's class docstring.
- **Tier 2 (Per-Faction Overrides)**: `BalkanizationDefines`
  exposes every multiplier as a Pydantic field with the v1.2.0
  default. Per-Faction seed JSON may override individual values
  (FR-007 "with the option for per-Faction overrides via
  initial-state JSON"), enabling sensitivity analysis via
  `tune:sensitivity` (Morris + Sobol) per CLAUDE.md tooling.
- **Tier 3 (Empirical Calibration — Deferred)**: Empirical
  grounding of metabolic_impact rates (e.g., against EPA
  Sustainable Communities Indicator habitability trajectories
  under different extraction regimes) is a future-spec concern.
  Spec-070 ships the theoretical defaults plus the calibration
  infrastructure (Morris/Sobol-runnable on these parameters); a
  follow-up spec calibrates them.

**Missing data source provenance** (FR-039 proxies):

- **Union density (Workers' Congress seeding)**: Derive from
  existing **QCEW** (BLS Quarterly Census of Employment and
  Wages, already in `data-catalog.yaml` v2.6.3, Federal Economic
  category). Union density is computed as `union_employment /
  total_employment` per county-year using QCEW's `own_code='3'`
  (state-government, often unionized) plus LODES jobs-by-NAICS
  filtered to historically unionized industries. **No new catalog
  entry needed.**
- **AIANNH (Decolonial seeding)**: Use **Natural Earth SQLite**
  (already in catalog, Land Cover/Spatial category, Fixture
  class). Natural Earth's `tribal_lands_north_america_admin1`
  layer provides the AIANNH polygon footprint for Detroit
  tri-county scope (Wayne / Oakland / Macomb counties intersect
  with no major AIANNH areas, so initial influence concentration
  for Decolonial is necessarily light at MVP — this is itself an
  empirical finding). **Natural Earth is already cataloged.**
- **Recent presidential election results (Restorationist
  seeding)**: Source from **Census Bureau** (already in catalog,
  Federal Demographic / Federal Economic). The MIT Election Lab
  dataset (county-presidential-1976-2020) is a fixture-class
  derivative of Census Bureau data. **Need to add MIT Election
  Lab county-presidential dataset to the catalog as a Fixture
  source under a new "Election Data" sub-category OR under
  Federal Demographic.** This is a v2.6.4 catalog amendment
  proposal, recorded in `Follow-up TODOs`.

### Rationale

- Treating the multipliers as theoretical defaults rather than
  empirical constants is honest: balkanization-spec.yaml derives
  them from the Three Stances dialectic, not from measurement.
  Pretending otherwise would violate III.1's spirit even while
  satisfying its letter.
- Falling back to existing catalog sources (QCEW + Natural Earth)
  for two of three proxies is correct catalog hygiene; the third
  (MIT Election Lab) is genuinely new and needs explicit
  constitutional addition rather than silent introduction.
- Exposing multipliers via `BalkanizationDefines` with
  Morris/Sobol-runnable structure satisfies III.2 (Falsifiability)
  and gives empirical-calibration future-work a concrete
  attachment point.

### Alternatives Considered

- **(A) Empirically pre-calibrate before shipping**: Rejected.
  No suitable measurement dataset exists at the per-extraction-
  policy-per-habitability-decay-rate granularity. Calibration
  requires a longitudinal study type that doesn't exist for the
  decolonization counterfactual (no historical case study of
  large-scale CEASE policy in the US contiguous footprint).
- **(B) Ship without overrides**: Rejected. Hard-coding the
  theoretical defaults without a Pydantic override path violates
  the project's "Data-Driven Design" coding standard
  (`game/CLAUDE.md` §Coding Standards).
- **(C) Add all three proxy data sources to catalog explicitly**:
  Considered. Only MIT Election Lab is genuinely new — adding
  the other two would be redundant entries pointing at existing
  cataloged sources. Net: minimal-diff catalog amendment.

### Follow-up TODOs

- **CATALOG-AMENDMENT**: Add MIT Election Lab county-presidential
  (1976–2020) dataset to `data-catalog.yaml` v2.6.4 as a
  Fixture-class entry under Federal Demographic (or new "Election
  Data" sub-category). Track as a v2.6.4 PATCH bump (one new
  source, no principle changes).
- **EMPIRICAL-CALIBRATION** (future spec): Calibrate
  metabolic_impact rates against EPA Sustainable Communities
  data + a literature review of post-extractive-economy
  habitability trajectories. Run Morris/Sobol on
  BalkanizationDefines first to identify the dominant
  parameters.

---

## R-002: Canadian Sovereign in Initial Seed (IV.1 Detroit-Windsor)

### Context

Constitution IV.1: "Cross-border labor markets, trade flows, and
imperial rent circuits (automotive supply chain, logistics, water
rights) MUST be modeled. Canada is a first-class territorial
substrate." Spec-070's initial-state seed currently includes
SOV_USA_FED (ruled by FAC_RESTORATIONIST) but no equivalent
Canadian Sovereign. This is a gate-blocker.

### Decision

Initial seed includes **`SOV_CAN_FED`** (Canadian Federal
Government) as a first-class Sovereign with the following
attributes:

```yaml
id: SOV_CAN_FED
name: "Government of Canada"
sovereignty_type: RECOGNIZED_STATE
legitimacy: 0.85
color_hex: "#FF0000"
capital_territory_id: null   # Ottawa not in Detroit MVP scope
founded_tick: 0
ruling_faction_id: FAC_LIBERAL_IMPERIAL   # See below
extraction_policy: CONTINUE   # IGNORE-stance → CONTINUE
```

A fourth canonical Faction, **`FAC_LIBERAL_IMPERIAL`** (`name:
"Liberal Imperial Bloc"`, `ideology: "LIBERAL_IMPERIALISM"`,
`colonial_stance: IGNORE`, `is_settler_formation: true`), is
introduced for SOV_CAN_FED's ruling-faction slot. This Faction
also exists in the US footprint but at lower initial influence
than FAC_RESTORATIONIST (which dominates the US per Q5
clarification's hard-start).

SOV_CAN_FED's CLAIMS:
- The Canadian boundary node (`canada` per spec-062 R4 amendment,
  exists in `external_node.py` as `NodeKind.EXTERNAL`).
- Any Detroit-MVP-scope Territory that has a cross-border edge
  (per LODES OD matrix's `canada` destination).

### Rationale

- IV.1 mandates Canada as first-class substrate. A Sovereign-less
  Canadian boundary node would treat Canada as inert geography —
  exactly the IV.1-violating pattern.
- Choosing `FAC_LIBERAL_IMPERIAL` (IGNORE stance) for Canada
  preserves the spec's theoretical position that Canadian
  settler-colonial liberalism is part of the same imperial
  formation as the US Restorationist project, but with a softer
  ideological gloss (the IGNORE rather than UPHOLD stance).
  Trudeau-era Liberal Party policies on First Nations
  consultation are a real-world analogue: rhetorical
  acknowledgment + maintained extraction.
- A fourth canonical Faction stays within spec-070's seed-Faction
  scope (FR-008 says "at least three"; nothing prevents four).
  Adding `FAC_LIBERAL_IMPERIAL` also gives the US side a softer
  "liberal-imperial" alternative to FAC_RESTORATIONIST that the
  player can support in CAMPAIGN mode without going full
  Decolonial — modelling the historical Democratic-Party
  IGNORE-stance behavior.
- Initial-state `extraction_policy=CONTINUE` for SOV_CAN_FED
  produces `metabolic_impact = −0.005` for Canadian territories,
  contrasting with the US side's `−0.02` (FAC_RESTORATIONIST
  INTENSIFY). The boundary itself is a contradiction surface, as
  IV.1 anticipates.

### Alternatives Considered

- **(A) Treat Canada as closed-loop boundary with NULL
  ruling_faction**: Rejected. Violates IV.1's "first-class
  territorial substrate" requirement and FR-029a's collapse
  predicates (Sovereigns must have a ruling_faction or be the
  exterior fallback).
- **(B) Add `SOV_CAN_FED` ruled by FAC_DECOLONIAL** (interpreting
  Canada as more decolonial than the US): Rejected. Empirically
  false (Canadian state policy on First Nations is structurally
  similar to US Indian Country administration) and theoretically
  off-frame.
- **(C) Add a Canadian-specific Faction `FAC_TRUDEAU_LIBERAL`**:
  Considered. Decided against in favor of `FAC_LIBERAL_IMPERIAL`
  as a *transnational* liberal-imperial Faction rather than a
  Canada-specific one — matches the theoretical frame better
  (liberal imperialism is an imperial formation that spans
  settler-colonial states, not a Canadian peculiarity).

### Follow-up TODOs

- **SEED**: `seed_factions.json` includes 4 canonical
  PoliticalFactions: FAC_RESTORATIONIST, FAC_WORKERS_CONGRESS,
  FAC_DECOLONIAL, FAC_LIBERAL_IMPERIAL.
- **SEED**: `seed_sovereigns.json` includes 2 Sovereigns:
  SOV_USA_FED (ruled by FAC_RESTORATIONIST) and SOV_CAN_FED
  (ruled by FAC_LIBERAL_IMPERIAL).
- **CROSS-BORDER**: The LODES OD matrix's existing `canada`
  destination feeds into SOV_CAN_FED's CLAIMS at game start.
  No new ingestion pipeline.

---

## R-003: FactionInfluenceSystem Partition Placement (FR-042)

### Context

Spec-056 partitions `_DEFAULT_SYSTEMS` into three sets with an
import-time partition-integrity assertion:

- `MATERIAL_BASE_SYSTEMS` (positions 1–13, before player/org
  action): VitalitySystem through MetabolismSystem.
- `ACTION_PHASE_SYSTEMS` (position 14): OODASystem.
- `CONSEQUENCE_SYSTEMS` (positions 15–21): Survival through
  EdgeTransition.

The spec proposes three new Systems:
- `FactionInfluenceSystem` (at position 14.x, after OODA)
- `SovereigntySystem` (at position 17.x, after Consciousness)
- `CollapseTransitionSystem` (at position 19.x, after
  FieldDerivative)

Each must be added to exactly one of the three partition sets.
SovereigntySystem and CollapseTransitionSystem clearly go in
CONSEQUENCE_SYSTEMS (they consume action results and update state).
FactionInfluenceSystem is ambiguous: is it action-phase
(observing/aggregating same-tick player actions) or consequence
(reading already-committed graph state)?

### Decision

**FactionInfluenceSystem → CONSEQUENCE_SYSTEMS** (positioned at
~14.5, immediately after OODASystem at 14).

Rationale: FactionInfluenceSystem READS INFLUENCES edge state
(possibly written by OODA actions in the same tick) and PRODUCES
derived per-Territory winning-Faction state + TERRITORY_TRANSITION
events. It does NOT take player/org actions itself — that's spec-072
Vanguard Economy's job. So it's a consequence of OODA, not an
action phase.

Constitution II.1 partition logic supports this: "consequences"
are the systems that read the committed-action graph state and
produce derived/transitions. ACTION_PHASE is reserved for the
single OODASystem that actually invokes verb resolvers. Adding a
second member to ACTION_PHASE_SYSTEMS would break the
spec-056-implied invariant that there's exactly one action
phase per tick.

### Rationale

- spec-056 currently has exactly one System in
  `ACTION_PHASE_SYSTEMS` (OODASystem). The import-time partition
  assertion doesn't *require* singleton-action-phase, but the
  spec-056 commit history shows the intent was "actions happen
  here, consequences happen after." Adding FactionInfluenceSystem
  to ACTION_PHASE would either share the action phase (creating
  ordering-within-phase ambiguity) or imply a multi-action-phase
  model that wasn't endorsed.
- FactionInfluenceSystem reads OODA outputs but writes nothing
  the same OODA can react to — it's a downstream reader, which is
  the canonical consequence pattern.
- The actual tick-pipeline position is 14.5 (between OODA and
  Survival): plan-phase finalises position at the integration
  point.

### Alternatives Considered

- **(A) ACTION_PHASE_SYSTEMS**: Rejected per the rationale above.
- **(B) MATERIAL_BASE_SYSTEMS** (before OODA): Rejected. Would
  make winning-faction resolution oblivious to same-tick OODA
  actions that change INFLUENCES — but specifically same-tick OODA
  actions ARE the mechanism by which spec-072 actions change
  faction-influence, so reading them is essential.

### Follow-up TODOs

- Tasks-phase wires FactionInfluenceSystem into
  `_DEFAULT_SYSTEMS` at position ~14.5 (between OODA at 14 and
  Survival at 15) and adds to `CONSEQUENCE_SYSTEMS` frozenset.

---

## R-004: ADJACENCY Spatial-Resolution for Contiguity Check (FR-029b)

### Context

FR-029b requires the contiguity check (for active secession) to
use the existing `ADJACENCY` edges. The codebase has ADJACENCY
used in two existing contexts:

- `engine/systems/territory.py:182, 293` — heat spillover
  (territory-level adjacency).
- `bifurcation/ceiling.py:226-272` — adjacency-edge identification.

The Territory entity in spec-062 operates at multiple scales: H3
res-7 hexes (the spatial substrate) AND county-level Territory
entities (the institutional unit). Which scale's ADJACENCY does
contiguity use?

Implication: at H3 res-7, secession can produce neighborhood-sized
breakaway zones (a few-hex contiguous blob). At county-level, the
minimum secession unit is whole counties.

### Decision

**Contiguity check operates at H3 res-7 hex level** (the spatial
substrate), with two refinements:

1. **Threshold normalization**: The `influence_level > 0.5`
   threshold is applied at the H3 hex level — a Faction must
   hold majority influence in a *contiguous block of hexes*, not
   a contiguous block of counties.
2. **Minimum size requirement**: `BalkanizationDefines` exposes
   `min_contiguous_hex_count` (default 12 hexes ≈ 1 county-
   equivalent area at res-7). Below this, the contiguous-majority
   region is too small to constitute a coherent secessionist
   project — no `SECESSION_DECLARED` event fires.

### Rationale

- The Constitution I.20 immutable spatial substrate is the H3
  res-7 hex grid. Counties are derived aggregations (per spec-062
  cross-scale integration). Operating contiguity at the substrate
  level is consistent with I.20's "claims as overlay on
  immutable substrate."
- Operating at H3 res-7 allows fine-grained secession (a single
  metropolitan area, an industrial corridor, a tribal homeland)
  rather than forcing whole-county granularity. This produces
  more theoretically-realistic secession scenarios — actual
  historical secession movements typically operate at sub-county
  scale (urban neighborhoods, ethnic enclaves) before scaling up.
- The minimum-hex-count threshold prevents trivial-scattered-
  influence trolling: a Faction with 50% influence in 1 hex
  doesn't trigger civil war.
- The h3.grid_disk(cell, 1) helper in
  `infrastructure/h3_mesh.py` already provides the per-hex
  adjacency primitive; contiguity = breadth-first traversal over
  res-7 hexes restricted to influence-majority hexes, using
  grid_disk for neighbors. No new infrastructure needed.

### Alternatives Considered

- **(A) County-level adjacency**: Rejected. Loses spatial
  granularity and forces unrealistic whole-county secession
  units. Also creates a county-vs-hex ambiguity at the secession
  boundary (does a county fully secede if just one of its hexes
  has majority influence?).
- **(B) Multi-scale adjacency (try res-7 first, fall back to
  county)**: Rejected. Adds complexity without clear benefit;
  the H3 res-7 + minimum-size-threshold approach handles the
  same scenarios more cleanly.

### Follow-up TODOs

- `BalkanizationDefines` field `min_contiguous_hex_count: int =
  12` (default ≈ 1 county-equivalent at res-7).
- `formulas/balkanization.py` function
  `contiguous_influence_majority_subregion(graph, faction_id,
  sovereign_id, threshold, min_size)` performs BFS over res-7
  hexes via existing h3.grid_disk helpers.

---

## R-005: Audit/Chronicle Schema Realisation (FR-046)

### Context

FR-046 requires that CLAIMS / INFLUENCES mutations be queryable
post-hoc ("who controlled X at tick T?"). The original
`epoch2-persistence.yaml` v1.2.0 §chronicle specified a
KuzuDB-based snapshot table. Per the audit, KuzuDB was replaced
by PostgreSQL (ADR030); the chronicle infrastructure needs
realisation on the new substrate.

Three architectural options:
- **(A) Dedicated audit table per edge type**: Two new tables
  (`claims_audit`, `influences_audit`), each with full edge state
  + tick + operation_type rows.
- **(B) JSON-history column on the edge row**: Each CLAIMS /
  INFLUENCES row in the runtime table gains a
  `history: jsonb` column tracking mutations.
- **(C) Event-stream-only**: All mutations are recorded as
  EventType rows; reconstruction is by replaying events.

### Decision

**Option (A) — Dedicated audit table per edge type**, owned by
the `balkanization` subsystem per II.11.

Concretely:

```sql
-- Per FR-046, II.11 subsystem ownership
CREATE TABLE balkanization_claims_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    tick INTEGER NOT NULL,
    sovereign_id TEXT NOT NULL,
    territory_id TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('CREATE', 'UPDATE', 'DELETE')),
    control_level NUMERIC NOT NULL,
    fiscal_status TEXT NOT NULL,
    legal_status TEXT NOT NULL,
    recognition_level NUMERIC NOT NULL,
    observer_mutation BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_claims_audit_tick ON balkanization_claims_audit (tick);
CREATE INDEX idx_claims_audit_sovereign ON balkanization_claims_audit (sovereign_id, tick);
CREATE INDEX idx_claims_audit_territory ON balkanization_claims_audit (territory_id, tick);

CREATE TABLE balkanization_influences_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    tick INTEGER NOT NULL,
    faction_id TEXT NOT NULL,
    territory_id TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('CREATE', 'UPDATE', 'DELETE')),
    influence_level NUMERIC NOT NULL,
    support_type TEXT NOT NULL,
    cadre_count INTEGER NOT NULL,
    sympathizer_count BIGINT NOT NULL,
    observer_mutation BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_influences_audit_tick ON balkanization_influences_audit (tick);
CREATE INDEX idx_influences_audit_faction ON balkanization_influences_audit (faction_id, tick);
CREATE INDEX idx_influences_audit_territory ON balkanization_influences_audit (territory_id, tick);
```

Writes happen via `persistence/balkanization_history.py` in the
post-tick flush phase (not during tick computation, per II.6 "no
DB I/O during tick").

### Rationale

- **(A) over (B)**: A JSON-history column on the live row mixes
  current state with historical state. Queries like "who
  controlled X at tick T?" require parsing JSON arrays vs simple
  indexed SQL — significantly slower. Also makes WAL-replication
  noisier (every read-modify-write touches the entire JSON
  history).
- **(A) over (C)**: Event-stream-only requires replaying all
  events from tick 0 to reconstruct edge state at tick T. For a
  50,000-tick simulation, this is O(50k) per query — unacceptable
  for routine "current state at tick T" queries.
- **(A) over hybrid**: A hybrid (audit table + event stream)
  would duplicate state; just-audit-table is simpler and
  sufficient.
- Audit-table approach also makes the FR-049 observer_mutation
  flag clean — a column on the audit row, queryable for "show me
  all observer-mode mutations in this run."
- Per II.11, the new tables live in the `balkanization`
  subsystem's migration directory and are NOT accessed directly
  by other subsystems; the spec-070 `balkanization_history.py`
  module exposes the interface.

### Alternatives Considered

- **(B) JSON-history column**: Rejected per query-performance
  rationale above. Useful for low-volume edit tracking (e.g.,
  blog-post editing); wrong shape for high-frequency simulation
  state.
- **(C) Event-stream-only**: Rejected per O(N) replay cost. The
  EventType stream is still useful for narrative reconstruction
  (spec-077 Wire) but is NOT the right substrate for "current
  state at tick T" queries.
- **(D) Temporal-tables / PostgreSQL system-versioning**:
  Considered. PostgreSQL doesn't natively support SQL:2011
  temporal tables; extensions exist (pg_versioning) but require
  Ansible-deployment changes (constitutional X.3 review). Net:
  not worth the deployment-pipeline impact when a plain audit
  table works.

### Follow-up TODOs

- Migration `00XX_balkanization.sql` includes the two audit
  tables.
- `persistence/balkanization_history.py` exposes
  `record_claims_mutation(tick, edge, op, observer=False)` and
  `record_influences_mutation(tick, edge, op, observer=False)`.
- Replay-from-tick-T mechanic: SELECT the most-recent audit row
  per edge before tick T+1; rebuild edge state from those rows.

---

## Summary of Phase 0 Resolutions

| Research ID | Question | Decision |
|---|---|---|
| R-001 | Multiplier provenance + missing data sources | Theoretical defaults via `BalkanizationDefines`; QCEW for union density, Natural Earth for AIANNH, propose MIT Election Lab catalog addition for v2.6.4 PATCH |
| R-002 | Canadian Sovereign at game start | Add `SOV_CAN_FED` ruled by new `FAC_LIBERAL_IMPERIAL` (IGNORE stance); 4 canonical Factions total in seed |
| R-003 | FactionInfluenceSystem partition | `CONSEQUENCE_SYSTEMS`, position ~14.5 (after OODA at 14) |
| R-004 | Contiguity spatial resolution | H3 res-7 hex level with `min_contiguous_hex_count=12` (~ county-equivalent area), using existing `h3.grid_disk` |
| R-005 | Audit/Chronicle schema | Dedicated audit table per edge type (`balkanization_claims_audit`, `balkanization_influences_audit`); writes in post-tick flush; subsystem-owned per II.11 |

All NEEDS CLARIFICATION items resolved. **Phase 1 design may proceed.**

## Cross-References

- Constitutional principles: I.20, II.9, II.11, III.1, III.4, III.7, IV.1
- Internal: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md) (Phase 1)
- External: `ai-docs/epochs/epoch3/balkanization-spec.yaml` v1.2.0, `ai-docs/epochs/epoch3/epoch2-persistence.yaml` v1.2.0, `reports/aidocs-vs-code-audit-2026-05-16.md` Part 3-FULL Wave 1
