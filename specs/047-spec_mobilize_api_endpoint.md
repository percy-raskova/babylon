# MOBILIZE Verb: API Endpoint Specification

**Parent Spec**: `043-consciousness-value-integration`, `037-player-verb-resolution`, `038-django-web-application-v3`
**Scope**: GET (populate page) and POST (submit action) for the MOBILIZE verb
**Date**: 2026-04-10

---

## Theoretical Grounding: MOBILIZE and the Value Form

MOBILIZE is the verb where the labor theory of value stops being theory and becomes practice. A strike empirically demonstrates that living labor (v) creates value, not dead labor (c). When workers withdraw their labor power from the production process, the entire M-C-M' circuit freezes — machines sit idle, commodities go unproduced, surplus drops to zero. Capital discovers in real time that its accumulated constant capital is worth nothing without the variable capital that animates it.

This is qualitatively different from the other two "Project Power" verbs:

- **ATTACK** destroys c (constant capital) through force — sabotage, expropriation
- **CAMPAIGN** engages institutions through legitimacy — elections, lawsuits
- **MOBILIZE** withdraws v (labor power) from circulation through collective action — strikes, boycotts, blockades, demonstrations

ATTACK and CAMPAIGN operate on the object side of the value form (destroying things, reshaping institutions). MOBILIZE operates on the subject side — it activates the collective agency of the people whose labor IS variable capital. This is why MOBILIZE has a direct consciousness effect: the workers are not observing a disruption to the value circuit (as bystanders to an ATTACK); they ARE the disruption.

### Four Forms of Mobilization and the Value Circuit

Each form targets a different stage in M → C → P → C' → M':

| Form | Circuit Stage | Value Effect | Heat | Scale |
|------|--------------|-------------|------|-------|
| **Strike** | P (Production) | v withdrawn → s = 0 for duration. c sits idle. Most direct demonstration of labor theory of value | Medium-High | Workplace to sector |
| **Boycott** | C'→M' (Realization) | Commodities produced but unsold. Surplus generated but unrealized. Hits profit rate without stopping production | Medium | Consumer to community |
| **Blockade** | M→C (Circulation) | Capital cannot purchase inputs. Supply chain severed. c cannot be replenished. Effective against logistics-dependent operations | High | Point of chokepoint |
| **Demonstration** | None (political) | No direct value disruption. Projects visibility, builds solidarity, pressures institutions. Consciousness-raising through collective presence | Low-Medium | Territory-wide |

For MVP, these are not sub-verb selections — the form is implied by target type (business → strike/boycott, territory → demonstration, supply chain edge → blockade). Post-MVP, explicit sub-verb selection with different mechanics per form.

### Consciousness Through Practice (Mao)

MOBILIZE has a direct consciousness effect that operates through a different channel than EDUCATE:

- **EDUCATE**: Builds `education_pressure` on community hyperedges. Modifies the routing of agitation through the r/l/f simplex. Conceptual knowledge — theory.
- **MOBILIZE**: Generates agitation AND provides experiential knowledge simultaneously. Workers who strike together experience their collective power directly. This is `practice_agitation` — agitation that arrives pre-interpreted because the practice itself is the lesson.

In spec 043 terms: MOBILIZE generates agitation that inherently routes toward r (revolutionary) because the experience of collective action IS the de-reification of the value form. The workers didn't read about the labor theory of value — they just lived it. The routing doesn't need education_pressure as strongly because the practice provides its own interpretive framework.

This is why EDUCATE + MOBILIZE is more powerful than either alone: EDUCATE builds the conceptual framework, MOBILIZE provides the experiential confirmation. Together, they create the practice → knowledge → practice cycle that Mao described as the engine of correct ideas.

### The Solidarity Multiplier

The effectiveness of MOBILIZE depends on existing SOLIDARISTIC edges. This is the core mechanic:

```
mobilization_size = base_sympathizers × solidarity_multiplier

solidarity_multiplier = 1.0 + (solidaristic_edge_count × solidarity_amplification_per_edge)
```

An atomized population (zero solidarity edges) has a multiplier of 1.0 — only directly recruited sympathizers show up. Each SOLIDARISTIC edge amplifies turnout because solidarity networks activate beyond the org's direct membership. At 5 solidaristic edges with 0.3 amplification each, the multiplier is 2.5 — the mobilization draws 2.5× the org's direct sympathizer base.

This means: you cannot skip AID and EDUCATE and go straight to MOBILIZE. Without solidarity infrastructure, your demonstration is a handful of cadre holding signs. The game mechanically enforces the organizing principle that mass action requires mass organization.

### The Backfire Dynamic (George Floyd / StruggleSystem)

When the state REPRESSes a mobilization, EXCESSIVE_FORCE events may fire. These events generate:

1. **Sympathy agitation** on the target community (people who weren't at the demonstration see the state violence and react)
2. **Solidarity spikes** that strengthen existing SOLIDARISTIC edges and may create new ones
3. **Sympathizer recruitment** — people radicalized by the state's response join the org

This is already implemented in StruggleSystem. The MOBILIZE endpoint needs to surface the backfire probability and projected effects so the player can assess whether provoking state repression is strategically desirable (it often is — the George Floyd dynamic showed that state overreaction can produce larger consciousness shifts than the original action).

### The DDoS Effect

Multiple simultaneous mobilizations across territories overwhelm state attention threads. The state's repressive apparatus has finite thread capacity (spec 036). Each mobilization that requires a response consumes threads. When threads are exhausted, subsequent mobilizations face reduced or no repression — they succeed more fully.

This creates the strategic incentive for coordination: NEGOTIATE alliances with other orgs → coordinate timing → MOBILIZE simultaneously across Wayne, Oakland, and Macomb → the state can only effectively repress one or two, the rest succeed unopposed. The endpoint should show how many state attention threads are currently committed and how many the projected mobilization would consume.

---

## Endpoint 1: GET Available MOBILIZE Targets

### Route

```
GET /api/games/{game_id}/verbs/mobilize/?org_id={org_id}
```

### Response: 200 OK

```json
{
  "status": "ok",
  "tick": 14,
  "verb": "mobilize",
  "acting_org": {
    "id": "org-detroit-freedom-school",
    "name": "Detroit Freedom School",
    "type": "PoliticalFaction",
    "consciousness_strategy": "revolutionary",
    "resources": {
      "cadre_labor": 12.0,
      "sympathizer_labor": 45.0,
      "material": 5.0
    },
    "ooda": {
      "action_points_remaining": 2,
      "action_points_max": 3,
      "cycle_time": 2
    },
    "reputation": 0.42,
    "sympathizer_count": 890,
    "solidarity_edges": {
      "solidaristic": 3,
      "transactional": 5,
      "total": 8
    }
  },
  "cost": {
    "action_points": 1,
    "cadre_labor": 1.0,
    "sympathizer_labor": "variable",
    "material": 0.0,
    "sl_explanation": "MOBILIZE spends Sympathizer Labor. More SL = larger mobilization. Minimum 5.0. You choose how many sympathizers to activate.",
    "can_afford": true
  },
  "solidarity_overview": {
    "solidarity_multiplier": 1.9,
    "multiplier_breakdown": "3 solidaristic edges × 0.3 amplification = 0.9 bonus. Base multiplier: 1.0 + 0.9 = 1.9",
    "effective_mobilization_capacity": 1691,
    "capacity_explanation": "890 sympathizers × 1.9 solidarity multiplier = 1,691 effective mobilization. Solidarity infrastructure nearly doubles your turnout."
  },
  "targets": [
    {
      "target_id": "territory-26163",
      "target_type": "territory",
      "target_name": "Wayne County",
      "implied_form": "demonstration",
      "population_density": 2945,
      "current_heat": 0.18,
      "org_presence_strength": 0.72,
      "mobilization_projection": {
        "sl_options": [
          {
            "sl_spent": 10.0,
            "projected_turnout": 380,
            "turnout_explanation": "200 base participants × 1.9 solidarity multiplier. A neighborhood-scale demonstration.",
            "political_pressure": 0.15,
            "pressure_explanation": "Modest political pressure on local institutions. Visible but not disruptive.",
            "heat_generated": 0.08,
            "consciousness_effect": {
              "practice_agitation_generated": 0.06,
              "agitation_routing": "Practice-generated agitation routes with +0.2 bonus toward r (experience of collective action provides its own interpretive framework). Projected: 65% to r, 20% to f, 15% to l.",
              "education_amplification": "Current education_pressure on NEW_AFRIKAN community is 0.12. MOBILIZE experience amplifies education's effect — participants who have both studied theory AND experienced collective action consolidate both into revolutionary consciousness.",
              "solidarity_edge_effect": "Temporary amplification of 3 existing solidaristic edges for this tick. Dormant solidarity activated."
            },
            "state_response": {
              "likely_response": "Monitor only — below response threshold",
              "repress_probability": 0.10,
              "backfire_if_repressed": {
                "agitation_generated": 0.12,
                "sympathy_radius": "NEW_AFRIKAN community, Wayne County",
                "sympathizer_recruitment": 45
              }
            }
          },
          {
            "sl_spent": 25.0,
            "projected_turnout": 950,
            "turnout_explanation": "500 base × 1.9 multiplier. A significant district-level demonstration. Will attract media attention.",
            "political_pressure": 0.35,
            "pressure_explanation": "Substantial political pressure. Local officials notice. Businesses in the demonstration area experience disruption.",
            "heat_generated": 0.18,
            "consciousness_effect": {
              "practice_agitation_generated": 0.12,
              "agitation_routing": "Larger demonstration = stronger collective experience. Routing bonus +0.25 toward r. Projected: 70% to r, 18% to f, 12% to l.",
              "education_amplification": "Larger scale means more participants with both education exposure and practice. Consciousness consolidation effect scales with turnout.",
              "solidarity_edge_effect": "Temporary amplification + potential for new TRANSACTIONAL edge creation. Demonstration participants who don't have existing relationships form new connections."
            },
            "state_response": {
              "likely_response": "CO-OPT or REPRESS depending on dominant faction",
              "repress_probability": 0.40,
              "excessive_force_probability": 0.15,
              "backfire_if_repressed": {
                "agitation_generated": 0.22,
                "sympathy_radius": "NEW_AFRIKAN community + adjacent communities in Wayne County",
                "sympathizer_recruitment": 120,
                "solidarity_spike_probability": 0.35,
                "solidarity_spike_explanation": "If EXCESSIVE_FORCE fires, a solidarity spike creates new SOLIDARISTIC edges between participants and bystanders. This is the George Floyd dynamic — state violence against demonstrators builds the solidarity infrastructure for future action."
              }
            }
          },
          {
            "sl_spent": 45.0,
            "projected_turnout": 1691,
            "turnout_explanation": "890 base × 1.9 multiplier. Full mobilization — every available sympathizer activated through all solidarity networks. County-scale demonstration.",
            "political_pressure": 0.55,
            "pressure_explanation": "Major political event. County institutions under direct pressure. Business disruption across the demonstration area. Media coverage guaranteed.",
            "heat_generated": 0.30,
            "consciousness_effect": {
              "practice_agitation_generated": 0.20,
              "agitation_routing": "Full mobilization is a transformative collective experience. Routing bonus +0.3 toward r. Projected: 75% to r, 15% to f, 10% to l.",
              "education_amplification": "Maximum consciousness consolidation. The scale of the demonstration itself demonstrates collective power — participants see their numbers and draw conclusions about what's possible.",
              "solidarity_edge_effect": "Significant edge creation. Large demonstrations create dense temporary solidarity networks. Some persist as permanent TRANSACTIONAL edges."
            },
            "state_response": {
              "likely_response": "REPRESS — demonstration of this scale will trigger response regardless of faction balance",
              "repress_probability": 0.75,
              "excessive_force_probability": 0.35,
              "backfire_if_repressed": {
                "agitation_generated": 0.35,
                "sympathy_radius": "All communities in Wayne County + media spillover to Oakland/Macomb",
                "sympathizer_recruitment": 280,
                "solidarity_spike_probability": 0.60,
                "solidarity_spike_explanation": "High probability of state overreaction. If EXCESSIVE_FORCE fires at this scale, the backfire will be massive — potentially the largest consciousness shift in the game so far."
              }
            },
            "ddos_effect": {
              "state_threads_currently_committed": 3,
              "state_threads_total": 5,
              "threads_this_mobilization_would_consume": 2,
              "threads_remaining_after": 0,
              "ddos_explanation": "Full mobilization consumes the state's last 2 available attention threads. If any allied orgs mobilize simultaneously, the state CANNOT respond — its repressive capacity is saturated. Coordinate with allies via NEGOTIATE for maximum effect."
            }
          }
        ]
      }
    },
    {
      "target_id": "org-wayne-auto-parts-inc",
      "target_type": "business",
      "target_name": "Wayne Auto Parts Inc.",
      "implied_form": "strike",
      "description": "Auto parts manufacturer, 340 non-union workers. Department I.",
      "value_tensor_role": {
        "department": "I",
        "s_v_ratio": 1.8,
        "annual_s": 12.0,
        "v_per_tick": 6.67
      },
      "workforce_overlap": {
        "org_members_employed_here": 23,
        "total_workforce": 340,
        "penetration": 0.068,
        "penetration_explanation": "6.8% workforce penetration. Below the critical mass threshold (15%) for an effective strike. A wildcat action is possible but will struggle to sustain."
      },
      "mobilization_projection": {
        "sl_options": [
          {
            "sl_spent": 15.0,
            "projected_strikers": 52,
            "participation_rate": 0.153,
            "strike_effectiveness": 0.25,
            "value_effect": {
              "s_reduction": 3.0,
              "s_reduction_pct": 25.0,
              "v_withdrawn": 1.67,
              "c_utilization_drop": 0.25,
              "explanation": "With 15% participation, production drops ~25%. The factory limps along with scabs and management. Surplus extraction reduced but not halted. Workers experience partial collective power — enough to see the potential, not enough to prove the theory."
            },
            "consciousness_effect": {
              "practice_agitation_generated": 0.15,
              "strike_specific_bonus": "Strikers experience the labor theory of value directly: they stopped working, production dropped 25%. This generates strong r-routing agitation (bonus +0.35) among participants. Non-participating workers see it too — lower bonus (+0.1) but broad reach.",
              "scab_dynamic": "Non-participating workers who scab experience a different consciousness effect: lateral antagonism toward strikers. Potential f-routing if not addressed through education."
            },
            "heat_generated": 0.15,
            "state_response": {
              "likely_response": "Business requests police protection. State allocates attention thread.",
              "repress_probability": 0.30,
              "injunction_probability": 0.45,
              "injunction_explanation": "Court injunction is the institutional response to strikes. If granted, continuing the strike generates additional heat and potential arrests."
            }
          },
          {
            "sl_spent": 35.0,
            "projected_strikers": 170,
            "participation_rate": 0.50,
            "strike_effectiveness": 0.70,
            "value_effect": {
              "s_reduction": 8.4,
              "s_reduction_pct": 70.0,
              "v_withdrawn": 4.67,
              "c_utilization_drop": 0.70,
              "explanation": "Majority strike. Production effectively halted. Constant capital sits idle — the machines that cost millions produce nothing. Surplus extraction drops 70%. Finance capital notices. This is the labor theory of value made material: without workers, capital is dead weight."
            },
            "consciousness_effect": {
              "practice_agitation_generated": 0.30,
              "strike_specific_bonus": "Majority strike is a transformative experience. Participants see unambiguously that THEY are the source of value. c is revealed as dead labor — useless without v. r-routing bonus +0.45. This is the strongest consciousness effect in the game short of an uprising.",
              "solidarity_creation": "Striking together creates dense solidarity bonds. Projected: 4-6 new TRANSACTIONAL edges among participant clusters. If strike succeeds, edges may immediately strengthen toward SOLIDARISTIC."
            },
            "heat_generated": 0.35,
            "state_response": {
              "likely_response": "REPRESS:RAID or REPRESS:PROSECUTE. Business + finance-capital faction demand response.",
              "repress_probability": 0.65,
              "excessive_force_probability": 0.25,
              "backfire_if_repressed": {
                "agitation_generated": 0.28,
                "sympathy_radius": "All PROLETARIAT in Wayne County + media national",
                "solidarity_spike_probability": 0.50
              }
            }
          }
        ]
      }
    }
  ],
  "coordination_opportunities": {
    "allied_orgs_with_ap": [
      {
        "org_id": "org-wayne-mutual-aid-network",
        "name": "Wayne Mutual Aid Network",
        "edge_mode": "TRANSACTIONAL",
        "has_ap": true,
        "sympathizer_count": 340,
        "can_mobilize_simultaneously": true,
        "coordination_benefit": "Simultaneous mobilization by an allied org in the same territory doubles the DDoS pressure on state attention threads. Two mobilizations require 3-4 threads to manage — potentially saturating the state's capacity."
      }
    ],
    "coordination_explanation": "Use NEGOTIATE to formalize coordination with allied orgs. Simultaneous MOBILIZE actions across orgs create compound effects: larger total turnout, shared heat distribution, and attention thread saturation."
  },
  "unavailable_targets": [
    {
      "target_id": "territory-26125",
      "target_name": "Oakland County",
      "reason": "No organizational presence. Use MOVE to establish presence before mobilizing."
    }
  ]
}
```

### Response Field Semantics

**`solidarity_overview`**: Global solidarity state for the acting org. The `solidarity_multiplier` is the headline number — it tells the player how much their solidarity infrastructure amplifies mobilization. This number is the payoff for all those AID + EDUCATE ticks. A multiplier of 1.0 means you're alone. A multiplier of 3.0 means your solidarity network triples your effective reach.

**`sl_options`**: Multiple mobilization scales. The player chooses how much SL to spend. Each option shows a complete projection: turnout, political pressure, value disruption (for strikes), consciousness effects, heat, and state response. The player can see the escalation curve — spending more SL gets more effect but more heat and higher repression probability.

**`consciousness_effect.practice_agitation_generated`**: This is the unique MOBILIZE contribution to spec 043. Unlike agitation from material deterioration (s/v increases, Φ decline), practice-generated agitation arrives with an inherent routing bonus toward r because the collective action itself is the de-reification experience. The `strike_specific_bonus` is even stronger for strikes because the labor theory of value is demonstrated through practice, not taught through theory.

**`value_effect` (strike targets only)**: Shows the value-theoretic consequences in tensor terms. `s_reduction` = how much surplus extraction drops. `v_withdrawn` = how much variable capital is pulled from production. `c_utilization_drop` = how much constant capital sits idle. This is the player seeing the value circuit respond to their action.

**`workforce_overlap`**: For strike targets, shows how many org members work at the target business. Below critical mass threshold, strikes are fragile (low participation, scab risk). Above threshold, strikes are powerful. This incentivizes REPRODUCE (recruit workers at the target) before MOBILIZE (strike the target).

**`ddos_effect`**: Shows state attention thread arithmetic. If the mobilization consumes the state's remaining threads, other activity proceeds unimpeded. This is the quantitative case for coordination.

**`coordination_opportunities`**: Allied orgs that could mobilize simultaneously. Shows who's available, what edge mode connects you, and what the compound benefit would be. This is the NEGOTIATE → MOBILIZE pipeline visualized.

---

## Endpoint 2: POST Submit MOBILIZE Action

### Route

```
POST /api/games/{game_id}/verbs/mobilize/
```

### Request Body

```json
{
  "org_id": "org-detroit-freedom-school",
  "target_id": "territory-26163",
  "params": {
    "sl_committed": 25.0
  }
}
```

**`params.sl_committed`**: How much Sympathizer Labor to spend. More SL = larger mobilization. The player makes the strategic choice about scale. Minimum 5.0 SL.

### Validation

1. `org_id` exists, is player-controlled, has AP remaining
2. `target_id` exists (territory for demonstration, business for strike, edge for blockade)
3. Org has presence in the target territory
4. `sl_committed` ≥ 5.0 and ≤ org's current SL
5. No existing action for this org this tick

### Response: 201 Created

```json
{
  "status": "ok",
  "action": {
    "id": "action-uuid",
    "tick": 14,
    "org_id": "org-detroit-freedom-school",
    "verb": "mobilize",
    "target_id": "territory-26163",
    "params": {"sl_committed": 25.0},
    "queued_at": "2026-04-10T18:15:00Z",
    "cost_estimate": {
      "action_points": 1,
      "cadre_labor": 1.0,
      "sympathizer_labor": 25.0
    }
  },
  "org_status": {
    "action_points_remaining": 1,
    "sympathizer_labor_remaining": 20.0,
    "has_pending_action": true
  },
  "message": "Mobilization ordered. Detroit Freedom School will organize a demonstration in Wayne County, activating approximately 950 people through direct outreach and solidarity networks. The state will notice."
}
```

---

## Resolution Logic

```python
def resolve_mobilize(
    action: PlayerAction,
    graph: GraphProtocol,
    hypergraph: xgi.Hypergraph,
    defines: MobilizeDefines,
) -> VerbResult:
    """Resolve a queued MOBILIZE action.
    
    Graph operations:
    1. Temporarily amplify SOLIDARISTIC edges (boost for this tick)
    2. Apply political pressure to target (territory heat, institutional pressure)
    3. Generate practice-agitation on participating communities
    4. For strikes: reduce s-flow on target business extractive edges
    
    MOBILIZE is unique: it generates agitation that routes with an
    inherent r-bonus because collective action IS de-reification.
    """
    org = graph.get_node(action.org_id)
    target = graph.get_node(action.target_id)
    sl_committed = action.params["sl_committed"]
    
    mutations = []
    events = []
    
    # --- Compute mobilization scale ---
    # Base turnout from SL committed
    base_turnout = sl_committed * defines.turnout_per_sl
    
    # Solidarity multiplier from SOLIDARISTIC edges
    sol_edges = graph.get_edges_from(
        org.id, mode=EdgeMode.SOLIDARISTIC
    )
    solidarity_multiplier = 1.0 + (
        len(sol_edges) * defines.solidarity_amplification_per_edge
    )
    
    effective_turnout = int(base_turnout * solidarity_multiplier)
    
    # Reputation modifier — unknown orgs draw smaller crowds
    reputation_factor = 0.5 + (org.reputation * 0.5)
    effective_turnout = int(effective_turnout * reputation_factor)
    
    # --- Deduct resources ---
    deduct_resources(
        org, 
        sympathizer_labor=sl_committed,
        cadre_labor=defines.mobilize_cl_cost,
        action_points=1,
    )
    
    # --- Determine mobilization form based on target ---
    if target.node_type == "territory":
        form = "demonstration"
    elif target.node_type == "business":
        form = "strike"
    elif target.node_type == "edge":
        form = "blockade"
    else:
        form = "demonstration"  # default
    
    # --- Form-specific value effects ---
    if form == "strike":
        # Compute workforce participation
        workforce = target.workforce
        org_members_employed = count_members_at(org, target)
        participation = min(
            effective_turnout / workforce,
            1.0,
        )
        
        # Value disruption proportional to participation
        s_reduction = target.s_per_tick * participation
        v_withdrawn = target.v_per_tick * participation
        c_idle_fraction = participation
        
        # Apply to target's extractive edges
        for edge in graph.get_edges_from(target.id, mode=EdgeMode.EXTRACTIVE):
            old_flow = edge.s_flow
            edge.s_flow *= (1 - participation)
            edge.strike_disruption_ticks = defines.strike_duration_ticks
            mutations.append(GraphMutation(
                target_type="edge", target_id=edge.id,
                field="s_flow",
                old_value=old_flow, new_value=edge.s_flow,
            ))
        
        # Strike-specific consciousness: the LTV made material
        practice_agitation = (
            participation * defines.strike_practice_agitation
        )
        r_routing_bonus = defines.strike_r_routing_bonus
        
    elif form == "blockade":
        # Sever target edge temporarily
        edge = graph.get_edge_by_id(action.target_id)
        old_flow = edge.s_flow
        edge.s_flow = 0.0
        edge.blockade_ticks = defines.blockade_duration_ticks
        mutations.append(GraphMutation(
            target_type="edge", target_id=edge.id,
            field="s_flow",
            old_value=old_flow, new_value=0.0,
        ))
        practice_agitation = defines.blockade_practice_agitation
        r_routing_bonus = defines.blockade_r_routing_bonus
        s_reduction = old_flow
        
    else:  # demonstration
        # No direct value disruption — political pressure only
        practice_agitation = (
            (effective_turnout / 1000) * defines.demo_practice_agitation_per_k
        )
        r_routing_bonus = defines.demo_r_routing_bonus
        s_reduction = 0.0
    
    # --- Heat generation ---
    visibility = effective_turnout / defines.visibility_scaling_population
    heat_increase = visibility * defines.heat_per_visibility
    org.heat += heat_increase
    
    territory = graph.get_territory(
        target.territory_id if hasattr(target, 'territory_id') else target.id
    )
    territory.heat += heat_increase * defines.territory_heat_fraction
    
    mutations.append(GraphMutation(
        target_type="organization", target_id=org.id,
        field="heat",
        old_value=org.heat - heat_increase, new_value=org.heat,
    ))
    
    # --- Temporary solidarity amplification ---
    for edge in sol_edges:
        edge.attributes["mobilize_amplified"] = True
        edge.attributes["amplification_tick"] = action.tick
        # Amplification decays automatically next tick in Layer 3
    
    # --- Practice agitation on communities ---
    # Distribute practice_agitation across communities present in territory
    participating_communities = get_communities_in_territory(
        territory.id, hypergraph
    )
    for community in participating_communities:
        # Practice agitation routes with r-bonus
        community.practice_agitation_buffer += (
            practice_agitation / len(participating_communities)
        )
        community.practice_r_routing_bonus = max(
            community.practice_r_routing_bonus,
            r_routing_bonus,
        )
    
    # --- New edge creation from demonstration ---
    if effective_turnout > defines.edge_creation_turnout_threshold:
        new_edges_created = int(
            effective_turnout / defines.participants_per_new_edge
        )
        for _ in range(min(new_edges_created, defines.max_new_edges_per_mobilize)):
            # Create TRANSACTIONAL edges between org and population nodes
            # that don't already have edges
            pop_node = find_unconnected_population(org, territory, graph)
            if pop_node:
                graph.create_edge(
                    source=org.id, target=pop_node.id,
                    edge_type=EdgeType.SOLIDARITY,
                    mode=EdgeMode.TRANSACTIONAL,
                    attributes={
                        "established_tick": action.tick,
                        "established_by": "mobilize",
                    },
                )
    
    # --- Events ---
    events.append(SimulationEvent(
        type=EventType.MOBILIZATION,
        payload={
            "org_id": org.id,
            "target_id": target.id,
            "form": form,
            "effective_turnout": effective_turnout,
            "solidarity_multiplier": solidarity_multiplier,
            "practice_agitation": practice_agitation,
            "r_routing_bonus": r_routing_bonus,
            "s_reduction": s_reduction,
            "heat_generated": heat_increase,
        },
    ))
    
    return VerbResult(
        mutations=mutations,
        events=events,
        ap_spent=1,
        resources_spent={
            "sympathizer_labor": sl_committed,
            "cadre_labor": defines.mobilize_cl_cost,
        },
        feedback=VerbFeedback(
            success=True,
            summary=f"{'Strike' if form == 'strike' else 'Demonstration' if form == 'demonstration' else 'Blockade'} mobilized {effective_turnout} people",
            details={
                "form": form,
                "turnout": effective_turnout,
                "solidarity_multiplier": solidarity_multiplier,
                "s_disrupted": s_reduction,
                "heat_increase": heat_increase,
                "practice_agitation": practice_agitation,
                "r_routing_bonus": r_routing_bonus,
                "new_edges_created": new_edges_created if effective_turnout > defines.edge_creation_turnout_threshold else 0,
            },
        ),
    )
```

---

## GameDefines Constants

```python
class MobilizeDefines(BaseModel):
    """MOBILIZE verb coefficients."""
    
    mobilize_cl_cost: float = Field(
        default=1.0,
        description="CL cost. Low — cadre direct, sympathizers march.",
    )
    turnout_per_sl: float = Field(
        default=20.0,
        description="Base participants per SL spent. At 20, spending 10 SL draws 200 base.",
    )
    solidarity_amplification_per_edge: float = Field(
        default=0.3, ge=0.0,
        description=(
            "Multiplier bonus per SOLIDARISTIC edge. At 0.3, 3 edges "
            "give 1.9x multiplier. 10 edges give 4.0x."
        ),
    )
    
    # Form-specific practice agitation
    strike_practice_agitation: float = Field(
        default=0.30, ge=0.0,
        description=(
            "Practice agitation generated by a full strike (participation=1.0). "
            "Scales linearly with participation rate. "
            "Strikes generate the most practice agitation because "
            "withdrawing labor directly demonstrates the LTV."
        ),
    )
    strike_r_routing_bonus: float = Field(
        default=0.35, ge=0.0,
        description=(
            "Bonus toward r-routing for strike practice agitation. "
            "Added to the base routing formula in spec 043. "
            "Strikes provide their own interpretive framework — "
            "the experience of stopping production IS the theory."
        ),
    )
    demo_practice_agitation_per_k: float = Field(
        default=0.05, ge=0.0,
        description=(
            "Practice agitation per 1000 demonstration participants. "
            "Demonstrations generate less practice agitation than strikes "
            "but scale with turnout."
        ),
    )
    demo_r_routing_bonus: float = Field(
        default=0.20, ge=0.0,
        description=(
            "Bonus toward r-routing for demonstration practice agitation. "
            "Lower than strike because demonstrations show collective "
            "presence but don't directly demonstrate the LTV."
        ),
    )
    blockade_practice_agitation: float = Field(
        default=0.20, ge=0.0,
        description="Practice agitation for blockade actions.",
    )
    blockade_r_routing_bonus: float = Field(
        default=0.25, ge=0.0,
        description="r-routing bonus for blockade practice agitation.",
    )
    
    # Duration
    strike_duration_ticks: int = Field(
        default=3,
        description="Ticks a strike disrupts production (unless broken by REPRESS).",
    )
    blockade_duration_ticks: int = Field(
        default=2,
        description="Ticks a blockade severs an edge.",
    )
    
    # Heat and visibility
    visibility_scaling_population: float = Field(
        default=5000.0,
        description="Denominator for visibility calc. At 5000, 5000 turnout = 1.0 visibility.",
    )
    heat_per_visibility: float = Field(
        default=0.35, ge=0.0,
        description="Heat generated per unit of visibility.",
    )
    territory_heat_fraction: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Fraction of org heat applied to territory. Higher than ATTACK (0.5) because mobilizations are more public.",
    )
    
    # Edge creation
    edge_creation_turnout_threshold: int = Field(
        default=200,
        description="Minimum turnout to create new TRANSACTIONAL edges from demonstration.",
    )
    participants_per_new_edge: int = Field(
        default=200,
        description="One new edge per 200 participants above threshold.",
    )
    max_new_edges_per_mobilize: int = Field(
        default=3,
        description="Cap on edges created per mobilization.",
    )
```

---

## Relationship to Other Verbs

| Verb Pairing | Effect | Strategic Meaning |
|-------------|--------|-------------------|
| EDUCATE → MOBILIZE | Maximum consciousness effect. EDUCATE builds interpretive framework, MOBILIZE provides experiential confirmation. Practice-agitation generated by mobilization routes to r with both the practice bonus AND the education routing modifier. Theory + practice = praxis | Mao's epistemological cycle realized in gameplay |
| AID → MOBILIZE | AID builds solidarity edges → solidarity multiplier amplifies MOBILIZE turnout. Material support creates the infrastructure for mass action. But without EDUCATE, the mobilization doesn't consolidate into lasting consciousness change — it's a big event that fades | Building the base before projecting power |
| MOBILIZE → ATTACK | The escalation ladder. MOBILIZE establishes political legitimacy and mass base. If MOBILIZE is repressed, ATTACK becomes more defensible (you tried peaceful means). ATTACK without prior MOBILIZE is perceived (by the population and the state) as terrorism rather than resistance | The question of when demonstrations become insurrections |
| MOBILIZE + MOBILIZE (coordination) | Multiple orgs mobilizing simultaneously = DDoS on state attention threads. State can't REPRESS all mobilizations. Un-repressed mobilizations succeed more fully. This is the payoff for NEGOTIATE (build alliances) → MOBILIZE (deploy them) | The general strike — many hands making the state's job impossible |
| MOBILIZE alone | Effective for immediate pressure but effects are temporary unless paired with EDUCATE (for consciousness consolidation) and AID (for solidarity maintenance). A one-off demonstration is a news story, not a movement | "What are your demands?" — the question that kills movements without theory |
| CAMPAIGN then MOBILIZE | CAMPAIGN reduces state threat assessment → lower starting heat → MOBILIZE faces less repression. But CAMPAIGN channels energy into institutional engagement, which can undermine the radical edge of MOBILIZE. Strategic tension between legitimacy and militancy | Working within the system to create space for action outside it |
