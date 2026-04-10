# MOVE Verb: API Endpoint Specification

**Parent Spec**: `043-consciousness-value-integration`, `037-player-verb-resolution`
**Date**: 2026-04-10

---

## Theoretical Grounding: MOVE and the Spatial Value Circuit

MOVE is the verb that answers "where do you organize?" — which is a question about where in the value circuit you intervene. Capital is not evenly distributed. s/v ratios, Φ flows, state attention threads, community compositions, and agitation levels all vary by territory. The choice of location is a strategic choice about which segment of the value form to contest.

### Three Strategic Questions MOVE Answers

**1. Where is exploitation most visible?** Territories with high s/v and declining Φ have populations whose material conditions make the value form transparent (spec 043: high exploitation_visibility, low reification_buffer). Wayne County's deindustrializing core. MOVE toward the crisis.

**2. Where is the state weak?** Attention threads concentrate spatially. Territories under active surveillance are dangerous. Territories the state has deprioritized are open terrain. MOVE can exploit gaps in state coverage.

**3. Where are potential allies?** Other orgs occupy specific territories. NEGOTIATE requires proximity or prior intelligence. MOVE opens alliance possibilities.

### The Mao Doctrine: Fish and Water

MOVE into a territory where the org shares community membership with the population is cheap and natural — cadre are embedded, recognized, trusted. MOVE into hostile territory (no community overlap) is expensive and risky. The `community_overlap` score directly modulates presence establishment speed and operational effectiveness.

Crossing contradiction pair boundaries (settler org into colonized territory or vice versa) is near-impossible without prior SOLIDARISTIC edges across the divide. The cross-community penalty mechanically enforces that you can't parachute organizers into communities you have no connection to.

### MOVE and Surveillance Evasion

When the org MOVEs, state attention threads may lose tracking. The evasion probability = base_rate × (1 − heat). High-heat orgs are too visible to evade. Low-heat orgs can break surveillance temporarily, gaining 2-3 ticks of operational freedom in the new territory. This creates the INVESTIGATE → MOVE → exploit-window tactical sequence.

### Two Modes: Expand vs. Relocate

**Expand**: Maintain existing presence + add new territory. Presence strength splits between territories. Existing edges in the origin territory weaken under maintenance strain but don't break immediately. The org operates in multiple territories simultaneously but is spread thinner everywhere.

**Relocate**: Abandon origin territory, full presence to destination. Origin presence drops to 0 over 3 ticks (phased withdrawal). ALL edges in the origin territory dissolve — including SOLIDARISTIC edges that took significant investment. The community you organized loses its revolutionary org. This is a severe strategic cost, justified only when the origin territory is untenable (state repression, economic collapse) or when the destination offers dramatically better prospects.

---

## GET Endpoint

```
GET /api/games/{game_id}/verbs/move/?org_id={org_id}
```

Returns: current territory presence, available destinations with community reception scores, strategic assessments (value circuit position, state surveillance, existing orgs), projected outcomes for both expand and relocate modes, surveillance evasion probability.

Key fields per destination:

- **community_reception.overlap_score**: Float [0,1]. How much the org's community memberships overlap with the destination population. High overlap = fish in water. Low overlap = outsider.
- **community_reception.cross_community_penalty**: Effectiveness penalty for operating across contradiction pair boundaries.
- **strategic_assessment.value_circuit_position**: Where this territory sits in the extraction circuit — core/periphery, s/v level, Φ status, agitation.
- **strategic_assessment.surveillance_evasion**: Probability of breaking state tracking during the move.
- **projected_outcomes**: For both expand and relocate — presence values, edges at risk, ticks to operational viability.

## POST Endpoint

```
POST /api/games/{game_id}/verbs/move/
```

```json
{
  "org_id": "org-detroit-freedom-school",
  "target_id": "territory-26099",
  "params": { "mode": "expand" }
}
```

**Costs**: 1 AP. No CL, SL, or material cost. MOVE is about attention allocation, not material expenditure. Distance surcharge: +1 AP per hex hop beyond adjacent.

**Validation**: Org exists, is player-controlled, has AP, destination territory exists, distance is affordable.

## Resolution Logic

1. Compute community reception (overlap score × reception modifiers)
2. If expand: split presence between origin and destination, add maintenance strain to origin edges
3. If relocate: schedule phased withdrawal from origin, establish full presence at destination (modulated by reception)
4. Surveillance evasion roll: if successful, state attention threads lose tracking for 2-3 ticks
5. If evasion fails, state detects move and updates org location model
6. Emit MOVEMENT_DETECTED or SURVEILLANCE_EVASION event

**Graph mutations**: Territory association changes, presence values, edge maintenance strain (expand), withdrawal schedule (relocate).

**Unique property**: MOVE is the only verb whose primary effect is on the org's relationship to territories rather than to other nodes or edges. It reshapes WHERE the org can act, not WHAT it can do.

## GameDefines

```python
class MoveDefines(BaseModel):
    expand_presence_split: float = Field(default=0.30)
    minimum_reception: float = Field(default=0.05)
    relocation_withdrawal_ticks: int = Field(default=3)
    expansion_edge_strain: float = Field(default=0.1)
    evasion_base_probability: float = Field(default=0.40)
    reacquire_ticks: int = Field(default=2)
    distance_ap_surcharge: int = Field(default=1)
```

---

## Relationship to Other Verbs

| Pairing | Effect |
|---------|--------|
| INVESTIGATE → MOVE | Discover where state is weak, then move there. Intelligence-guided positioning |
| MOVE → AID/EDUCATE | Presence in new territory unlocks new populations. Geographic expansion of solidarity infrastructure |
| NEGOTIATE → MOVE | Allied org in destination territory provides reception bonus. Allies open doors |
| MOVE (evasion) → ATTACK | Break surveillance, strike from unexpected position |
| MOVE (expand) → MOBILIZE | Presence in multiple territories enables multi-territory mobilization, amplifying DDoS effect |
| MOVE (relocate) → state DEVELOP:DISPLACE | When the state gentrifies your territory, relocate to survive. Defensive MOVE preserves the org at the cost of community abandonment |
