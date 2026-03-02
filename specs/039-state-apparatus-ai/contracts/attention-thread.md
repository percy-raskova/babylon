# Contract: Attention Thread System

**Spec**: FR-A01, FR-A02, FR-A03, FR-A04, FR-A05, FR-A06, FR-A07, FR-A08
**Module**: `src/babylon/ooda/attention/thread_manager.py`, `sparrow.py`, `observation.py`, `thread_ooda.py`
**Entity**: `src/babylon/models/entities/attention_thread.py`

---

## Behavioral Contracts

### T-01: Intel Completeness Growth

```
GIVEN an AttentionThread in MONITORING phase targeting a star-topology organization
WHEN 8 ticks elapse with SIGNALS surveillance method active
THEN intel_completeness has increased from its initial value
AND observed_subgraph contains more nodes and edges than at tick 0
```

**Mechanism**: Each tick, the thread's OODA cycle (OBSERVE phase) discovers new nodes and edges based on the active surveillance method. SIGNALS reveals communication edges and org size estimates (R-007 method table). Discovered nodes/edges are added to `G_observed`.

**Monotonicity invariant**: `intel_completeness` MUST be non-decreasing across ticks for a given thread, absent counter-intelligence actions by the target. Counter-intel is the only mechanism that can reduce `intel_completeness`.

---

### T-02: Cell Topology Resistance

```
GIVEN two organizations with identical membership count:
  - Organization A: star topology (single hub, all members connected to hub)
  - Organization B: cell topology (3 cells, max inter-cell degree = 1)
WHEN both are surveilled for 12 ticks with identical methods and apparatus
THEN cell-topology org (B) has intel_completeness at least 30% lower
  than star-topology org (A)
```

**Mechanism** (FR-A07): Cell topology reduces the effective observation ceiling. Compartmentalization limits how much of the network any single surveillance entry point can reveal. The ceiling reduction factor is proportional to the degree of compartmentalization: `effective_ceiling = base_ceiling * (1 - compartmentalization_factor)`.

**Example**: FBI base ceiling = 0.4. Star topology: effective ceiling = 0.4. Cell topology (3 well-compartmented cells): effective ceiling = 0.4 * (1 - 0.3) = 0.28.

**Test** (SC-007): Over 100 seeded runs, the mean `intel_completeness` for cell-topology targets after 12 ticks MUST be at least 30% lower than for star-topology targets. This validates compartmentalization as a defensive gameplay mechanic.

---

### T-03: Observation Ceiling

```
GIVEN an AttentionThread owned by local_pd (observation_ceiling = 0.2)
WHEN intel accumulates through surveillance over many ticks
THEN intel_completeness is capped at 0.2 for that apparatus
AND further surveillance by the same apparatus yields no additional intelligence
```

**Ceilings by apparatus type** (FR-A07, configurable in `StateApparatusAIDefines`):

| Apparatus | Observation Ceiling |
|-----------|-------------------|
| FBI | 0.4 |
| Local PD | 0.2 |
| Fusion Center | 0.5 |

**Ceiling interaction with cell topology**: The ceiling is reduced by compartmentalization BEFORE the cap is applied. Local PD surveilling a cell-topology org: `effective_ceiling = 0.2 * (1 - 0.3) = 0.14`.

**Invariant**: `intel_completeness <= observation_ceiling` for ANY thread, at ANY tick, for ANY target topology.

---

### T-04: Sparrow Singleton Identification

```
GIVEN AttentionThread with intel_completeness > 0.6 on a star-topology organization
WHEN SparrowAnalysis is computed on G_observed
THEN the hub node appears as an identified singleton
  with betweenness_centrality ranking #1 among observed nodes
AND the hub's equivalence class contains exactly 1 node (singleton)
AND peripheral nodes share an equivalence class (identical numerical signatures)
```

**Sparrow analysis components** (FR-A03):
- Centrality computation: degree, betweenness, closeness, eigenvector (via NetworkX on `G_observed`)
- Equivalence classes: nodes grouped by numerical signature (centrality vector rounded to configurable precision)
- Singleton identification: equivalence classes with exactly one member
- Cutset detection: minimal vertex/edge sets whose removal disconnects `G_observed`

**Caveat**: SparrowAnalysis operates on `G_observed`, not `G_actual`. Results may be incorrect if `G_observed` contains distortions (edge type conflation, informant incentive distortion). This is by design: the state makes decisions on imperfect intelligence.

**Test** (SC-006): After 12 ticks of MONITORING a star-topology org, the hub is identified as a singleton with probability > 0.8 over 100 seeded runs.

---

### T-05: Thread Allocation Meta-OODA

```
GIVEN a thread pool of N threads and M potential targets with varying threat levels
WHEN meta-OODA runs thread allocation
THEN higher-threat targets receive threads before lower-threat targets
WHERE threat is computed from:
  - target territory heat level
  - collective_identity of communities the target operates in
  - organization membership size
  - recent player actions generating Heat in target's territory
```

**Allocation priority** (FR-A04): Targets are scored by a threat function and threads are allocated greedily to the highest-scoring targets until the pool is exhausted.

**Stickiness**: Threads resist rapid reallocation. A thread that has been tracking a target for K ticks has a stickiness bonus proportional to K (configurable in `StateApparatusAIDefines`). This prevents thrashing when threat levels fluctuate.

**Saturation edge case**: When all threads are allocated and a new high-priority target emerges, meta-OODA MUST deallocate the lowest-priority thread (the one with the lowest threat score minus stickiness bonus) to free capacity. This is the thread pool saturation mechanic.

---

### T-06: Observation Gap Distortions

```
GIVEN G_actual contains:
  - SOLIDARISTIC edges between org members
  - Face-to-face meeting edges (PHYSICAL only)
  - Cash flow edges (FINANCIAL only)
  - Consciousness levels on nodes
WHEN G_observed is constructed using SIGNALS surveillance method only
THEN G_observed contains:
  - Communication edges (edge existence revealed)
  - Edge types are CONFLATED (SOLIDARISTIC appears as generic COMMUNICATION)
  - Face-to-face meeting edges are ABSENT (SIGNALS cannot detect them)
  - Cash flow edges are ABSENT (SIGNALS cannot detect them)
  - Consciousness levels are ABSENT (SIGNALS cannot detect internal state)
```

**Method-specific distortions** (FR-A02, R-007):

| Distortion | Affected Methods | Effect |
|-----------|-----------------|--------|
| Edge type conflation | SIGNALS, SOCIAL_MEDIA | All detected edges appear as generic type; SOLIDARISTIC/TRANSACTIONAL/ANTAGONISTIC distinction lost |
| Temporal flattening | All methods | `G_observed` merges observations across ticks; cannot distinguish active from dormant edges |
| Informant incentive distortion | INFORMANT | Informants exaggerate threat to maintain relevance; `intel_completeness` inflated, threat assessment biased upward |
| Cash invisibility | SIGNALS, SOCIAL_MEDIA | Cash-based resource flows invisible; only electronic financial flows detectable via FINANCIAL method |
| Face-to-face blindness | SIGNALS, FINANCIAL, SOCIAL_MEDIA | In-person meetings detectable only via PHYSICAL surveillance |

**Test**: Construct `G_actual` with 3 SOLIDARISTIC edges and 2 face-to-face edges. Apply SIGNALS-only observation. Verify `G_observed` contains communication edges (existence only, no type) and zero face-to-face edges.
