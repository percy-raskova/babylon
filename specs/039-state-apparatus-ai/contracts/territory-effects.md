# Contract: Territory Effects

**Spec**: FR-E01, FR-E02, FR-E03, FR-E06, FR-E07, FR-E08, FR-E09
**Module**: `src/babylon/ooda/state_ai/` (DEVELOP/WITHDRAW resolve functions)
**Applies to**: `src/babylon/models/entities/territory.py` attributes via GraphProtocol

---

## Behavioral Contracts

### TE-01: INVEST Raises Property Values

```
GIVEN a territory with stable economic indicators (property_value_proxy at baseline)
WHEN DEVELOP_INVEST (COMMERCIAL) is applied for 8 consecutive ticks
THEN property_value_proxy has increased by at least
     8 * invest_property_delta (configurable in StateApparatusAIDefines)
AND V_reproduction for existing residents has increased
     (higher property values raise the cost of living)
```

**Mechanism** (FR-E08, R-006): INVEST raises `property_value_proxy` by a configurable delta per tick. The existing economic pipeline already reads `property_value_proxy` from territory nodes to compute `V_reproduction`, so the effect propagates automatically.

**Gentrification circuit**: INVEST is the first stage. Rising property values create displacement pressure. If followed by DISPLACE, the territory undergoes class composition change. This is the gentrification-as-weapon mechanic (US4).

**Test** (SC-008): After 8 ticks of INVEST, `property_value_proxy` MUST have measurably increased. Verify that `V_reproduction` for a test SocialClass node in the territory has also increased.

---

### TE-02: DISPLACE Removes Population

```
GIVEN a territory with population > 0 and TENANCY edges connecting
      population blocks to the territory
WHEN DEVELOP_DISPLACE (RENT_INCREASE) is applied
THEN target population blocks are removed from the territory
AND TENANCY edges between displaced population and territory are severed
AND community infrastructure in the territory degrades
     (community_infrastructure_quality decreases)
AND collective_identity in the affected community decreases
     (displacement scatters organized communities, FR-E06)
```

**Displacement mechanisms** (FR-E08):
- EMINENT_DOMAIN: State-initiated, requires LEGISLATE precondition
- CODE_ENFORCEMENT: Low-visibility, targets specific properties
- RENT_INCREASE: Market-driven, follows INVEST
- DEMOLITION: Direct destruction, high legitimacy cost
- TAX_FORECLOSURE: Financial, targets low-income property owners

**Population destination**: Displaced population blocks do not vanish. They relocate to other territories (determined by adjacency, affordability, and existing community presence). If no affordable adjacent territory exists, population enters a DISPLACED state.

**Test** (SC-008): DISPLACE removes at least 50% of target population from territory (configurable via `displace_population_fraction`).

---

### TE-03: NEGLECT Degrades Infrastructure

```
GIVEN a territory with infrastructure_quality at baseline (e.g., 0.8)
WHEN DEVELOP_NEGLECT is applied for 12 consecutive ticks
THEN infrastructure_quality has decreased
     following exponential decay: quality *= (1 - neglect_decay_rate) per tick
AND infrastructure_quality does NOT fall below neglect_quality_floor
     (configurable, default prevents reaching zero)
AND property_value_proxy has declined (degraded territory loses value)
AND services (education, healthcare, transit) have reduced proportionally
```

**Mechanism** (R-006): Exponential decay models the gradual degradation from sustained disinvestment. The floor prevents quality from reaching zero (abandoned territories retain some baseline infrastructure).

**Cumulative devastation**: NEGLECT is low-visibility (minimal legitimacy cost) but cumulatively devastating. 12 ticks of NEGLECT with `decay_rate=0.05` produces: `0.8 * (0.95)^12 = 0.43`. Infrastructure nearly halved without a single dramatic event.

**Gentrification setup**: NEGLECT followed by INVEST creates the classic disinvestment-reinvestment cycle. NEGLECT lowers property values, making the territory attractive for future INVEST, which then raises values and triggers displacement.

---

### TE-04: STRATEGIC_WITHDRAWAL Hollows Territory

```
GIVEN a territory with state PRESENCE edges (StateApparatus nodes connected
      to territory) and maintained infrastructure
WHEN WITHDRAW_STRATEGIC_WITHDRAWAL is applied with asset_extraction=True
THEN all PRESENCE edges between StateApparatus nodes and the territory
     are removed via graph.remove_edge()
AND infrastructure_quality degrades (accelerated NEGLECT applied)
AND state_investment is set to 0 for the territory
AND V_reproduction increases for remaining population
     (loss of state services raises the cost of self-provision)
```

**Hollowing mechanic** (FR-E09, R-006): The state does not simply leave. It defunds, extracts assets, and lets infrastructure decay BEFORE withdrawing. The player inherits a husk: a territory with no state services, degraded infrastructure, and rising reproduction costs.

**Asset extraction**: When `asset_extraction=True`, the state recovers a fraction of its prior investment as budget. This makes STRATEGIC_WITHDRAWAL partially self-funding.

**Player opportunity**: STRATEGIC_WITHDRAWAL creates a territory the player can occupy, but the territory requires significant investment to become viable. This is a strategic trap: the player may overextend by trying to govern a hollowed territory.

---

### TE-05: SCORCHED_EARTH Destroys Infrastructure

```
GIVEN a territory with infrastructure (infrastructure_quality > 0)
WHEN WITHDRAW_SCORCHED_EARTH is applied
THEN targeted infrastructure is destroyed
     (infrastructure_quality set to neglect_quality_floor or below)
AND legitimacy_cost is proportional to territory visibility
     (high-media-presence territory = extreme cost;
      low-visibility peripheral territory = minimal cost)
AND population in territory suffers immediate V_reproduction spike
```

**Availability constraints**: SCORCHED_EARTH carries massive legitimacy cost in core territories with high media presence. Nearly free in peripheral territories with low international visibility. This mirrors the colonial asymmetry present throughout the spec.

**Distinction from STRATEGIC_WITHDRAWAL**: STRATEGIC_WITHDRAWAL hollows over time; SCORCHED_EARTH destroys immediately. STRATEGIC_WITHDRAWAL extracts assets; SCORCHED_EARTH spends budget to destroy. Both remove state presence, but SCORCHED_EARTH is the kinetic option.

---

### TE-06: Heat Accumulation by Operational Profile

```
GIVEN two organizations in the same territory:
  - Organization A: HIGH_PROFILE operational presence
  - Organization B: LOW_PROFILE operational presence
WHEN 4 ticks elapse
THEN territory heat has increased MORE from Organization A's presence
     than from Organization B's presence
```

**Mechanism** (FR-E01, FR-E02): HIGH_PROFILE presence generates heat at a higher rate. Heat accumulation per tick is proportional to the operational profile weight. Heat decays without activity (if both orgs go dormant, heat decays toward 0).

**Heat consequences**: Territory heat above threshold triggers state response (attention thread allocation, REPRESS verb prioritization). This creates the visibility-security tradeoff: HIGH_PROFILE presence enables faster recruitment and stronger community ties but attracts state attention.

**Test** (US5 Acceptance Scenario 1): After 4 ticks, measure territory heat attributable to each organization. HIGH_PROFILE contribution MUST exceed LOW_PROFILE contribution.

---

### TE-07: PRESENCE Required for Recruitment

```
GIVEN an organization with NO PRESENCE edge to Territory A
     (no EdgeType.PRESENCE connecting org node to territory node)
WHEN the organization attempts RECRUIT targeting population in Territory A
THEN the action fails or has severely reduced effectiveness
     (recruitment success rate reduced to near-zero)
```

**Mechanism** (FR-E07): PRESENCE edges represent an organization's physical footprint in a territory. Without presence, the organization has no access to the territory's population for recruitment purposes.

**Establishing presence**: Organizations must first establish a PRESENCE edge (through a DEPLOY or similar action) before they can recruit in a territory. The operational profile (HIGH_PROFILE or LOW_PROFILE) is set when presence is established.

**Displacement consequence**: When DISPLACE severs community infrastructure and scatters population, organizations that relied on that territory for recruitment lose access. This makes DISPLACE a strategic weapon against organizational growth, distinct from direct repression.

**Test** (US5 Acceptance Scenario 2): Create an organization with no PRESENCE edge to a territory. Attempt RECRUIT targeting population in that territory. Verify action failure or effectiveness below a configurable threshold.
