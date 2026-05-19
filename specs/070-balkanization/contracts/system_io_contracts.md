# System I/O Contracts: Balkanization

For each of the three new Systems, this document specifies the
graph state it reads, the graph state it writes, the events it
emits, and the `context.persistent_data` keys it manages.

All Systems are pure transformations on the graph (II.6 State is
Data, Engine is Transformation). No DB I/O during tick. All RNG
draws come from the tick's seed (III.7).

## 1. FactionInfluenceSystem

**Pipeline position**: ~14.5 (after `OODASystem` at 14, before
`SurvivalSystem` at 15).

**Partition (spec-056)**: `CONSEQUENCE_SYSTEMS`.

**Reads**:

| Source | Method | Why |
|---|---|---|
| Graph | `query_nodes(_node_type="political_faction")` | Enumerate active Factions |
| Graph | `query_nodes(_node_type="territory")` | Enumerate active Territories |
| Graph | `query_edges(edge_type=EdgeType.INFLUENCES)` | Compute per-Territory winning-Faction |
| Graph | `query_edges(edge_type=EdgeType.ADJACENCY)` | Contiguity check for active secession (FR-029b) |
| Context | `persistent_data["balkanization.hysteresis_buffer"]` | Per-(faction, sovereign) contiguity-tick counts for hysteresis (FR-029c) |

**Writes**:

| Target | What |
|---|---|
| Graph | New `INFLUENCES` edges from OBSERVER-mode mutations (if any) — though primarily this system reads, not writes, INFLUENCES |
| Context | Update `persistent_data["balkanization.hysteresis_buffer"]` |
| Context | `persistent_data["balkanization.winning_faction_by_territory"]` — per-Territory winning-Faction snapshot (cache for SovereigntySystem to read) |
| Context | `persistent_data["balkanization.secession_eligible"]` — list of `(faction_id, sovereign_id, contiguous_hex_set)` tuples ready to fire SECESSION_DECLARED next tick |

**Events emitted**:

| Event | When |
|---|---|
| `TERRITORY_TRANSITION` | When per-Territory winning-Faction changes from the previous tick's snapshot (FR-022) |
| `FACTION_VICTORY` | When a Faction's aggregate influence crosses the configured supermajority threshold (FR-026) |
| `RED_SETTLER_TRAP_DETECTED` | Per-Faction, when `class_reduction >= 0.6 AND colonial_stance ∈ {UPHOLD, IGNORE}` (FR-034) |
| `SECESSION_DECLARED` | When hysteresis window elapses for a `(faction_id, sovereign_id)` in eligible state (FR-029a (2)) |

**Determinism notes**:

- Winning-Faction `argmax` uses incumbent-priority tiebreaker first, then seed-deterministic RNG (FR-021).
- Contiguity BFS traversal order is deterministic by H3 cell ID lexicographic ordering.
- Hysteresis counters are per `(faction_id, sovereign_id)` pair; no global counter.

## 2. SovereigntySystem

**Pipeline position**: ~17.5 (after `ConsciousnessSystem` at 17,
before `ContradictionSystem` at 18).

**Partition (spec-056)**: `CONSEQUENCE_SYSTEMS`.

**Reads**:

| Source | Method | Why |
|---|---|---|
| Graph | `query_nodes(_node_type="sovereign")` | Enumerate active Sovereigns |
| Graph | `query_edges(edge_type=EdgeType.CLAIMS)` | Compute per-Territory effective controller |
| Context | `persistent_data["balkanization.winning_faction_by_territory"]` | Determine if ruling_faction needs update on any Sovereign |
| Context | `persistent_data["balkanization.secession_eligible"]` | Initiate active-secession workflow on eligible (faction, sovereign) pairs (CIVIL_WAR_DECLARED, then handoff to CollapseTransitionSystem) |

**Writes**:

| Target | What |
|---|---|
| Graph | Sovereign node updates (ruling_faction_id changes per winning-Faction; legitimacy mutations) |
| Graph | CLAIMS edge updates (control_level adjustments per fiscal_status / legal_status transitions) |
| Context | `persistent_data["balkanization.effective_controller_by_territory"]` — per-Territory the Sovereign with highest CLAIMS.control_level (read by MetabolismSystem extension for FR-020 dual-power tiebreak) |
| Context | `persistent_data["balkanization.metabolic_impact_by_territory"]` — per-Territory the metabolic_impact to apply (read by MetabolismSystem extension for FR-019, FR-043) |

**Events emitted**:

| Event | When |
|---|---|
| `DUAL_POWER_ACTIVE` | Per-Territory, when ≥2 CLAIMS edges have `control_level > 0.0` (FR-035) |
| `CIVIL_WAR_DECLARED` | When initiating an active secession from `persistent_data["balkanization.secession_eligible"]` (FR-028) |

**Determinism notes**:

- Effective-controller tiebreak (when two CLAIMS edges have identical `control_level`) uses Sovereign ID lexicographic ordering.

## 3. CollapseTransitionSystem

**Pipeline position**: ~19.5 (after `FieldDerivativeSystem` at 20,
before `EdgeTransitionSystem` at 21).

**Partition (spec-056)**: `CONSEQUENCE_SYSTEMS`.

**Reads**:

| Source | Method | Why |
|---|---|---|
| Graph | `query_nodes(_node_type="sovereign")` | Detect Sovereigns meeting collapse predicates |
| Graph | `query_edges(edge_type=EdgeType.CLAIMS)` | Find claimed territories of collapsing Sovereigns |
| Graph | `query_edges(edge_type=EdgeType.INFLUENCES)` | Compute winning-Faction per claimed Territory for partition step |
| EventBus | Subscribe to `ECOLOGICAL_OVERSHOOT` (existing event from MetabolismSystem) | Trigger collapse predicate per FR-023 |
| EventBus | Subscribe to `NUCLEAR_EXCHANGE` (existing event) | Trigger collapse predicate per FR-023 |
| Context | `persistent_data["balkanization.player_uprising_request"]` | Trigger GENERAL_UPRISING-driven collapse per FR-023 |

**Writes**:

| Target | What |
|---|---|
| Graph | DELETE collapsed Sovereign nodes (after emitting transition events) |
| Graph | DELETE outbound CLAIMS / ADMINISTERS edges of collapsed Sovereigns |
| Graph | CREATE new Sovereign nodes per winning-Faction partition step (FR-024 step 4) |
| Graph | CREATE new CLAIMS edges per partition (control_level=0.8, legal_status=DE_FACTO) |
| Context | Clear `persistent_data["balkanization.secession_eligible"]` entries that were processed |

**Events emitted**:

| Event | When |
|---|---|
| `SOVEREIGN_COLLAPSE` | Per Sovereign meeting collapse predicate (FR-023) |
| `TERRITORY_TRANSITION` | Per claimed Territory of a collapsed Sovereign (FR-025) |

**Determinism notes**:

- Collapse predicate evaluation order is by Sovereign ID lexicographic.
- Partition winning-Faction tiebreak follows FR-021.
- New Sovereign IDs are generated via deterministic format `SOV_AUTO_T{tick}_F{faction_id}_{counter}`.

## 4. MetabolismSystem Extension (FR-043)

**Pipeline position**: 13 (existing — UNCHANGED).

**Existing role**: Computes biocapacity Δ, overshoot ratio,
ecological event emission.

**New role** (additive — FR-043): Apply
`persistent_data["balkanization.metabolic_impact_by_territory"]`
to `territory.habitability` BEFORE computing biocapacity Δ. The
per-tick habitability update sequence becomes:

1. (NEW) For each Territory with an entry in
   `metabolic_impact_by_territory`, apply the additive term:
   `habitability += metabolic_impact`.
2. (EXISTING) Compute biocapacity Δ, overshoot ratio.
3. (EXISTING) Emit `ECOLOGICAL_OVERSHOOT` if overshoot_ratio > 2.0
   for 5+ consecutive ticks (this remains the existing predicate
   per FR-031).

The MetabolismSystem does NOT compute metabolic_impact itself —
that's SovereigntySystem's job. MetabolismSystem only reads and
applies. No new event types are emitted by MetabolismSystem.

## 5. EndgameDetector Extension (FR-031)

**Pipeline position**: Observer (not in `_DEFAULT_SYSTEMS`; runs
post-tick).

**Existing predicates** (UNCHANGED in form, AUGMENTED in
condition):

| Predicate | Existing condition | Augmentation (FR-031) |
|---|---|---|
| `REVOLUTIONARY_VICTORY` | `percolation_ratio >= 0.7 AND avg(class_consciousness) > 0.8` | + `ABOLISH-aligned Sovereign majority (≥0.5 of active Territories) AND aggregate_extraction_policy == CEASE AND habitability_slope_window >= 0` |
| `ECOLOGICAL_COLLAPSE` | `overshoot_ratio > 2.0 for 5 consecutive ticks` | (UNCHANGED — no augmentation) |
| `FASCIST_CONSOLIDATION` | `national_identity > class_consciousness for 3+ nodes` | OR new political-violence route: `UPHOLD-aligned Sovereign majority AND state_violence_index == max AND aggregate_extraction_policy == INTENSIFY` |

**New predicates** (FR-032 + FR-032a):

| Predicate | Condition |
|---|---|
| `RED_OGV` | `IGNORE-aligned Sovereign majority AND class_tension < RED_OGV_CLASS_TENSION_FLOOR AND aggregate_habitability < RED_OGV_HABITABILITY_FLOOR AND habitability_slope_window < 0` |
| `FRAGMENTED_COLLAPSE` | `no_faction_majority AND active_sovereign_count >= 3 AND at_least_one_sovereign_type ∈ {INSURGENT, OCCUPATION, EMERGENCY} AND configuration_duration >= 10 ticks` |

**Priority order** (FR-033): RED_OGV → FRAGMENTED_COLLAPSE →
ECOLOGICAL_COLLAPSE → FASCIST_CONSOLIDATION → REVOLUTIONARY_VICTORY.

**First-match-wins**: Once any endgame fires, EndgameDetector
stops evaluating predicates for the run.
