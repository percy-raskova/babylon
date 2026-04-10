# ATTACK Verb: API Endpoint Specification

**Parent Spec**: `043-consciousness-value-integration`, `037-player-verb-resolution`, `038-django-web-application-v3`
**Scope**: GET (populate page) and POST (submit action) for the ATTACK verb
**Date**: 2026-04-10

---

## Theoretical Grounding: ATTACK and the Value Form

ATTACK is the only player verb that directly destroys or disrupts value in the tensor. EDUCATE operates on the interpretive layer. AID operates on v (reproduction). ATTACK operates on c (constant capital) and on the edges through which s (surplus value) flows.

### What ATTACK Does to the Value Form

Capital exists as a circuit: M → C (purchase means of production + labor power) → P (production, where s is generated) → C' (commodities embodying c + v + s) → M' (realization through sale). Every link in this circuit has a physical substrate — factories, supply chains, payroll infrastructure, management offices, extraction sites. All of this is constant capital (c): crystallized past labor that capital deploys to organize production and extract surplus.

ATTACK targets this physical substrate:

- **Sabotage infrastructure** → destroy c. The factory, the pipeline, the server farm — these are dead labor made physical. Destroying them interrupts the production process at the P stage. Capital must reinvest to reconstitute c, which consumes accumulated s.
- **Sever an EXTRACTIVE edge** → interrupt value flow. An EXTRACTIVE edge represents surplus (s) flowing from a population node through a business node to capital. Cutting the edge doesn't change the rate of exploitation (s/v at point of production) but prevents the surplus from being realized. This is intervention in Volume II (circulation).
- **Expropriate assets** → seize accumulated s. Bank expropriations, asset seizures, redistribution of hoarded value. The org converts the target's accumulated surplus into its own material resources.
- **Degrade an enemy org** → destroy organizational capacity. State apparatus nodes, business nodes, rival faction nodes all have attributes (violence_capacity, surveillance_capacity, wealth) that ATTACK can degrade.

### The Dialectic of Repression and Agitation

ATTACK generates heat. Heat triggers state REPRESS. REPRESS generates agitation (spec 043: repression_backfire). This creates a feedback loop:

```
ATTACK → heat ↑ → state REPRESS → repression_backfire → agitation ↑
                                                              ↓
                                            solidarity edges? education pressure?
                                                    ↓                    ↓
                                            YES → agitation routes to r
                                            NO  → agitation routes to f
```

Armed action is therefore never "just" the tactical damage it inflicts. Every ATTACK is simultaneously a consciousness event — it provokes a state response that reshapes the ideological terrain. The question is whether the player has built the interpretive infrastructure (EDUCATE) and solidarity infrastructure (AID + NEGOTIATE) for that agitation to route productively.

### The Ultra-Left Trap (Value-Theoretic)

The Weather Underground pattern: the org attacks capital (destroys c, severs extractive edges), generates heat, triggers repression, but has no mass base (low SL), no solidarity edges, and no education pressure on the communities experiencing the repression backfire. Result:

1. Capital reconstitutes the damaged c (it has reserves; you don't)
2. The state expands its repressive apparatus (your ATTACK justified its budget increase)
3. Repression-generated agitation routes to f (fascist) because there's no solidarity or education infrastructure to route it to r
4. Your org is degraded or destroyed by REPRESS response
5. Net value-tensor effect: approximately zero. Net consciousness effect: negative

The trap EMERGES from ATTACK overuse. It is not a separate mechanic — it is the mechanical consequence of projecting force without political preparation.

### The Warsaw Ghetto Corollary

Constitution I.11: all verbs always available. ATTACK specifically invokes the Warsaw Ghetto principle: when P(S|A) → 0, when acquiescence no longer guarantees survival, revolt happens regardless of organization or strategic calculation. In value terms, when v → 0 (the wage cannot reproduce labor power), the survival calculus flips. This is not a strategic choice — it is the material limit of exploitation producing its own negation.

The endpoint must flag this condition. When the acting org's population base has P(S|A) below a critical threshold, the ATTACK page should frame the action differently: not "what are the strategic costs and benefits" but "survival through acquiescence is no longer viable."

### Collateral Damage as Value Destruction

ATTACK in populated territories destroys wealth on bystander population nodes. You are degrading v — the material conditions of the people you're trying to liberate — in the name of disrupting s extraction. This is the tragic dimension of armed struggle: the means of revolution damage the material base of the people who need the revolution. The feedforward must show this honestly. The game does not moralize, but it does not hide.

### ATTACK Compared to State REPRESS

The player's ATTACK and the state's REPRESS are structural mirrors operating from inverse positions:

| Dimension | Player ATTACK | State REPRESS |
|-----------|--------------|---------------|
| Resources | Scarce (CL/SL) | Abundant (budget, personnel, weapons) |
| Legitimacy | Costs nothing (already outside the law) | Costs legitimacy (violence exposes the state) |
| Target | c (constant capital), extractive edges | Org topology, solidarity edges, cadre |
| Heat effect | Increases heat on player org | Generates repression backfire on target community |
| Value effect | Disrupts s realization | Disrupts organizing capacity |
| Asymmetry | Must choose targets carefully (finite capacity) | Can escalate indefinitely (until legitimacy collapses) |

---

## Endpoint 1: GET Available ATTACK Targets

### Route

```
GET /api/games/{game_id}/verbs/attack/?org_id={org_id}
```

### Response: 200 OK

```json
{
  "status": "ok",
  "tick": 14,
  "verb": "attack",
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
    "combat_readiness": 0.35,
    "coherence": 0.78,
    "current_heat": 0.22,
    "internal_topology": "NETWORK"
  },
  "cost": {
    "action_points": 2,
    "cadre_labor_if_targeted": 4.0,
    "sympathizer_labor_if_mass": 15.0,
    "material": 0.0,
    "can_afford_targeted": true,
    "can_afford_mass": true,
    "over_budget_ap": false,
    "cost_explanation": "ATTACK costs 2 AP — the most expensive verb. Targeted operations spend Cadre Labor (precision). Mass actions spend Sympathizer Labor (numbers). Choose based on your resources and the target."
  },
  "ultra_left_warning": {
    "active": false,
    "trap_score": 0.15,
    "indicators": [],
    "explanation": null
  },
  "warsaw_ghetto_flag": {
    "active": false,
    "population_p_acquiescence": 0.45,
    "threshold": 0.05,
    "explanation": null
  },
  "targets": {
    "organizations": [
      {
        "target_id": "org-wayne-auto-parts-inc",
        "target_type": "Business",
        "name": "Wayne Auto Parts Inc.",
        "territory_name": "Wayne County",
        "territory_id": "territory-26163",
        "defensive_capacity": 0.20,
        "description": "Auto parts manufacturer. Primary employer in Brightmoor neighborhood. 340 workers, non-unionized.",
        "value_tensor_role": {
          "department": "I",
          "c_stock": 45.0,
          "annual_s_extracted": 12.0,
          "s_v_ratio": 1.8,
          "explanation": "Department I (means of production). Exploitation rate 180% — extracts $1.80 surplus for every $1.00 in wages. High OCC (capital-intensive manufacturing)."
        },
        "extractive_edges": [
          {
            "edge_id": "edge-wayne-auto→finance-capital",
            "target_name": "Detroit Financial Holdings",
            "flow_type": "EXTRACTIVE",
            "s_flow_per_tick": 4.5,
            "explanation": "Surplus flows from Wayne Auto to Detroit Financial Holdings — profit extraction from production to finance."
          }
        ],
        "attack_projection": {
          "modes": {
            "targeted_sabotage": {
              "resource_cost": {"cadre_labor": 4.0},
              "damage_to_target": {
                "c_destroyed": 8.0,
                "c_destruction_pct": 17.8,
                "wealth_reduction": 8.0,
                "capacity_degradation": 0.15,
                "recovery_ticks": 6,
                "explanation": "Targeted sabotage destroys 17.8% of constant capital. Factory partially shut down. Production disrupted for ~6 ticks while capital reconstitutes c through reinvestment."
              },
              "value_flow_disruption": {
                "s_flow_interrupted": 2.3,
                "s_flow_interrupt_duration": 4,
                "explanation": "Surplus extraction from this business drops by 2.3/tick for 4 ticks while production recovers. Finance capital absorbs the loss."
              },
              "heat_generated": 0.25,
              "opsec_exposure": 0.15,
              "detection_probability": 0.30,
              "explanation": "Targeted operation. Low visibility, moderate damage. Requires cadre with operational discipline."
            },
            "mass_action": {
              "resource_cost": {"sympathizer_labor": 15.0},
              "damage_to_target": {
                "c_destroyed": 15.0,
                "c_destruction_pct": 33.3,
                "wealth_reduction": 15.0,
                "capacity_degradation": 0.30,
                "recovery_ticks": 12,
                "explanation": "Mass action (occupation, large-scale disruption) destroys 33.3% of constant capital. Major production halt. Recovery requires significant reinvestment."
              },
              "value_flow_disruption": {
                "s_flow_interrupted": 4.5,
                "s_flow_interrupt_duration": 8,
                "explanation": "Surplus extraction halts almost completely for 8 ticks. This is a significant disruption to the extraction circuit."
              },
              "heat_generated": 0.55,
              "opsec_exposure": 0.40,
              "detection_probability": 0.85,
              "explanation": "Mass action. High visibility, high damage, high heat. Your organization will be identified."
            }
          },
          "collateral_damage": {
            "affected_population": "sc-wayne-proletariat-26163",
            "population_name": "Proletariat, Wayne County",
            "workers_affected": 340,
            "wealth_impact": -1.2,
            "wealth_impact_explanation": "Workers at this factory lose income during the disruption. Their wealth decreases by ~1.2, accelerating the consumption gap. You are damaging the material conditions of the people whose labor is being exploited.",
            "agitation_effect": 0.12,
            "agitation_explanation": "Disruption generates agitation among affected workers — both from the material loss and from the visibility of the action. This agitation feeds the consciousness routing formula."
          },
          "state_ai_response": {
            "visibility": "HIGH",
            "immediate_response": "REPRESS:RAID — security-state faction will deploy police/FBI to investigate",
            "escalation_risk": "If heat exceeds 0.5, state may escalate to REPRESS:SWEEP of the territory",
            "repression_backfire": {
              "agitation_generated_on_community": 0.18,
              "affected_community": "NEW_AFRIKAN",
              "routing_analysis": "Community has education_pressure 0.12 and 3 solidaristic edges. Repression backfire agitation will partially route to r (revolutionary) — approximately 60% to r, 25% to f, 15% to l given current routing factors."
            },
            "attention_thread_consumed": 1,
            "thread_diversion_explanation": "The state must allocate 1 attention thread to investigate this attack. That thread is no longer available for surveillance of other organizing activity."
          },
          "coherence_check": {
            "current_coherence": 0.78,
            "coherence_threshold": 0.30,
            "network_collapse_risk": false,
            "explanation": "Coherence (0.78) is well above the collapse threshold (0.30). This org can sustain combat operations without fragmenting."
          }
        }
      }
    ],
    "edges": [
      {
        "target_id": "edge-wayne-auto→finance-capital",
        "target_type": "EXTRACTIVE_edge",
        "edge_description": "Surplus extraction flow: Wayne Auto Parts → Detroit Financial Holdings",
        "source_name": "Wayne Auto Parts Inc.",
        "sink_name": "Detroit Financial Holdings",
        "s_flow_per_tick": 4.5,
        "attack_projection": {
          "modes": {
            "targeted_disruption": {
              "resource_cost": {"cadre_labor": 3.0},
              "edge_effect": "SEVER — edge temporarily destroyed. No surplus flows from source to sink for recovery_duration ticks.",
              "recovery_duration": 8,
              "reconnection_probability": 0.90,
              "explanation": "Severing an extractive edge disrupts value flow but doesn't destroy the underlying relationship. Capital will reconnect the flow (~90% probability) once the disruption is resolved. To permanently sever, the source node must also be degraded.",
              "heat_generated": 0.20,
              "detection_probability": 0.25
            }
          },
          "value_consequence": {
            "s_denied_to_sink": 36.0,
            "s_denied_explanation": "4.5 s/tick × 8 ticks = 36.0 total surplus denied to Detroit Financial Holdings. This degrades their accumulation capacity, potentially triggering capital flight or disinvestment.",
            "trickle_effects": "Finance capital's profit rate declines. If sufficient extractive edges are severed simultaneously, this triggers disinvestment cascading through the value equalization system (Volume III)."
          },
          "collateral_damage": {
            "affected_population": "sc-wayne-proletariat-26163",
            "wealth_impact": -0.5,
            "explanation": "Edge disruption reduces employment/wages at the source business. Workers bear partial cost."
          }
        }
      }
    ],
    "institutions": [
      {
        "target_id": "inst-wayne-county-commission",
        "target_type": "institution",
        "name": "Wayne County Commission",
        "factional_control": {
          "finance_capital": 0.45,
          "security_state": 0.25,
          "settler_populist": 0.30
        },
        "attack_projection": {
          "modes": {
            "targeted_disruption": {
              "resource_cost": {"cadre_labor": 5.0},
              "effect": "Degrade institutional capacity. Factional balance disrupted — security-state may fill the vacuum. This is NOT the same as CAMPAIGN (which shifts factional balance through institutional engagement). ATTACK on institutions is destructive, not constructive.",
              "heat_generated": 0.40,
              "legitimacy_note": "Attacking government institutions generates maximum heat and state response. The state treats this as an existential threat.",
              "detection_probability": 0.70
            }
          }
        }
      }
    ]
  },
  "unavailable_targets": [
    {
      "target_id": "org-oakland-hedge-fund",
      "name": "Oakland Capital Management",
      "territory_name": "Oakland County",
      "reason": "Your organization has no presence in Oakland County. Use MOVE first, or use INVESTIGATE to gather intelligence remotely."
    }
  ]
}
```

### Response Field Semantics

**`cost`**: ATTACK costs 2 AP — the highest of any verb. Two resource modes: `targeted` (spends CL — precision operations, low visibility) and `mass` (spends SL — numbers, high visibility). The player chooses which mode when submitting. Over-budget operations still resolve (Constitution I.11) but with maximum exposure and degraded effectiveness.

**`ultra_left_warning`**: Populated from `detect_ultra_left_trap()` in trap_detection.py. If the player has been ATTACK-heavy in recent ticks, this field shows the trap score, indicators, and an explanation. The warning does not prevent the action — it informs. Indicators include: high attack-to-total-action ratio, high heat, low sympathizer labor, territory losses from repression.

**`warsaw_ghetto_flag`**: Active when the population base's P(S|A) is below the critical threshold (GameDefines: `warsaw_ghetto_threshold`, default 0.05). When active, the framing changes: the feedforward does not calculate strategic costs and benefits. It acknowledges that survival through acquiescence is no longer viable and presents the action as a survival response, not a strategic choice.

**`targets.organizations`**: Enemy org nodes the player can attack. Each includes:

- **`value_tensor_role`**: Which department this business operates in, its c stock, its annual s extraction, and its s/v ratio. This tells the player what they're disrupting in value terms. A Department I business (means of production) disrupted affects the production of capital goods. A Department IIa business disrupted affects wage goods. A Department III business disrupted affects social reproduction.

- **`extractive_edges`**: The value flows emanating from this business. Shows where surplus goes after extraction. Attacking the business disrupts these flows. Attacking the edge directly severs the flow without destroying the business.

- **`attack_projection.modes`**: Targeted vs mass. Each shows resource cost, damage inflicted (c destroyed, capacity degraded, recovery time), value flow disruption (how much s is interrupted and for how long), heat generated, OPSEC exposure, and detection probability.

- **`collateral_damage`**: The population wealth impact. Honest accounting: your attack costs workers income. Shows the agitation this generates — which feeds consciousness routing (potentially beneficial if education/solidarity infrastructure exists).

- **`state_ai_response`**: What the state will likely do. ATTACK always generates a state response — the question is what kind. Shows the repression backfire analysis: how much agitation the state response will generate, on which community, and how that agitation will route through the r/l/f simplex given current solidarity and education conditions. Also shows attention thread diversion — how your attack creates cover for other activity.

- **`coherence_check`**: Ultra-left trap guard. If the org's coherence is near the collapse threshold, this warns that the attack risks fragmenting the org itself.

**`targets.edges`**: EXTRACTIVE edges the player can directly sever. This is the purest value-theoretic operation: cut the pipe through which surplus flows. Shows the total surplus denied to the extraction sink, the recovery probability (capital usually reconnects), and trickle effects on the broader value equalization system.

**`targets.institutions`**: Government bodies, courts, regulatory agencies. Attacking institutions is qualitatively different from attacking businesses — it generates maximum heat and the state treats it as existential. The distinction from CAMPAIGN: CAMPAIGN shifts factional balance within institutions through engagement; ATTACK degrades institutional capacity through force.

---

## Endpoint 2: POST Submit ATTACK Action

### Route

```
POST /api/games/{game_id}/verbs/attack/
```

### Request Body

```json
{
  "org_id": "org-detroit-freedom-school",
  "target_id": "org-wayne-auto-parts-inc",
  "params": {
    "mode": "targeted",
    "specific_target": null
  }
}
```

**`params.mode`**: Either `"targeted"` (spends CL, low visibility, surgical) or `"mass"` (spends SL, high visibility, overwhelming). Determines which resource is consumed and the damage/heat/exposure profile.

**`params.specific_target`**: For edge targets, the edge ID. For org/institution targets, null (the whole target is engaged). Post-MVP: could specify sub-targets (specific infrastructure, specific key figures).

### Validation

1. `org_id` exists, is player-controlled
2. `target_id` exists and is in a territory where org has presence (or is an edge adjacent to such territory)
3. Target is an enemy — cannot attack orgs with SOLIDARISTIC edges to you (use NEGOTIATE to break the alliance first if you want to)
4. `mode` is valid ("targeted" or "mass")
5. No existing action queued for this org this tick
6. AP check: 2 AP required. If only 1 AP remaining, action still resolves but with `over_budget_penalty` (degraded effectiveness, maximum OPSEC exposure)

### Response: 201 Created

```json
{
  "status": "ok",
  "action": {
    "id": "action-uuid",
    "tick": 14,
    "org_id": "org-detroit-freedom-school",
    "verb": "attack",
    "target_id": "org-wayne-auto-parts-inc",
    "params": {"mode": "targeted"},
    "queued_at": "2026-04-10T17:30:00Z",
    "cost_estimate": {
      "action_points": 2,
      "cadre_labor": 4.0
    }
  },
  "org_status": {
    "action_points_remaining": 0,
    "has_pending_action": true,
    "can_queue_more": false
  },
  "message": "Direct action operation queued. Detroit Freedom School will conduct a targeted operation against Wayne Auto Parts Inc. in Wayne County. This will generate significant heat. The state will respond.",
  "warnings": [
    "Heat will increase by approximately 0.25. Current heat: 0.22 → projected: 0.47.",
    "Workers at Wayne Auto Parts will experience income disruption (estimated wealth impact: -1.2).",
    "State security apparatus will likely respond with RAID or SWEEP."
  ]
}
```

---

## Resolution Logic

```python
def resolve_attack(
    action: PlayerAction,
    graph: GraphProtocol,
    hypergraph: xgi.Hypergraph,
    defines: AttackDefines,
) -> VerbResult:
    """Resolve a queued ATTACK action.
    
    Graph operations (may produce multiple mutations):
    1. Degrade target node attributes (wealth, capacity, c_stock)
    2. Potentially sever or weaken extractive edges from target
    3. Increase heat on acting org and territory
    4. Collateral damage to population nodes in territory
    
    Unlike EDUCATE (1 mutation) or AID (2 mutations), ATTACK can
    produce 3-4 mutations because destruction cascades.
    """
    org = graph.get_node(action.org_id)
    target = graph.get_node(action.target_id)
    mode = action.params.get("mode", "targeted")
    
    mutations = []
    events = []
    
    # --- Determine resource cost and effectiveness ---
    if mode == "targeted":
        resource_key = "cadre_labor"
        resource_cost = defines.targeted_cl_cost
        base_effectiveness = org.combat_readiness * org.cadre_level
        visibility_multiplier = defines.targeted_visibility
    else:  # mass
        resource_key = "sympathizer_labor"
        resource_cost = defines.mass_sl_cost
        base_effectiveness = org.combat_readiness * (org.sympathizer_count / 100)
        visibility_multiplier = defines.mass_visibility
    
    # Over-budget degradation
    over_budget_factor = 1.0
    available = getattr(org.resources, resource_key)
    if available < resource_cost:
        over_budget_factor = available / resource_cost
        spent = available
    else:
        spent = resource_cost
    
    # AP over-budget (2 AP required, might only have 1)
    ap_cost = 2
    if org.ooda.action_points_remaining < 2:
        over_budget_factor *= 0.5  # Severely degraded
        # Maximum OPSEC exposure when exhausted
        visibility_multiplier *= 2.0
    
    deduct_resources(org, **{resource_key: spent}, action_points=ap_cost)
    
    # --- Compute damage ---
    effectiveness = base_effectiveness * over_budget_factor
    
    # Effectiveness vs. target's defense
    defense = getattr(target, "defensive_capacity", 0.1)
    damage_ratio = effectiveness / (effectiveness + defense)
    # Lanchester-type: damage scales with ratio, not difference
    
    if target.node_type == "organization" or target.node_type == "business":
        # Damage to org/business: destroy c, reduce wealth, degrade capacity
        c_destroyed = target.c_stock * damage_ratio * defines.c_destruction_rate
        wealth_destroyed = c_destroyed  # c destruction = wealth loss
        capacity_loss = damage_ratio * defines.capacity_degradation_rate
        
        old_c = target.c_stock
        old_wealth = target.wealth
        target.c_stock = max(0, target.c_stock - c_destroyed)
        target.wealth = max(0, target.wealth - wealth_destroyed)
        target.capacity = max(0, target.capacity - capacity_loss)
        
        mutations.append(GraphMutation(
            target_type=target.node_type,
            target_id=target.id,
            field="c_stock",
            old_value=old_c,
            new_value=target.c_stock,
        ))
        mutations.append(GraphMutation(
            target_type=target.node_type,
            target_id=target.id,
            field="wealth",
            old_value=old_wealth,
            new_value=target.wealth,
        ))
        
        # Check if extractive edges should be weakened
        for edge in graph.get_edges_from(target.id, mode=EdgeMode.EXTRACTIVE):
            s_flow_reduction = edge.s_flow * damage_ratio * defines.flow_disruption_rate
            edge.s_flow = max(0, edge.s_flow - s_flow_reduction)
            edge.disruption_ticks = int(defines.base_recovery_ticks / (1 - damage_ratio + 0.01))
            mutations.append(GraphMutation(
                target_type="edge",
                target_id=edge.id,
                field="s_flow",
                old_value=edge.s_flow + s_flow_reduction,
                new_value=edge.s_flow,
            ))
    
    elif target.node_type == "edge":
        # Direct edge severing
        edge = graph.get_edge_by_id(action.target_id)
        old_flow = edge.s_flow
        edge.s_flow = 0.0
        edge.severed = True
        edge.recovery_ticks = defines.edge_sever_recovery_ticks
        mutations.append(GraphMutation(
            target_type="edge",
            target_id=edge.id,
            field="s_flow",
            old_value=old_flow,
            new_value=0.0,
        ))
    
    # --- Heat generation ---
    heat_increase = damage_ratio * visibility_multiplier * defines.heat_per_damage
    old_heat = org.heat
    org.heat += heat_increase
    
    # Territory heat also increases
    territory = graph.get_territory(org.territory_id)
    territory.heat += heat_increase * defines.territory_heat_fraction
    
    mutations.append(GraphMutation(
        target_type="organization",
        target_id=org.id,
        field="heat",
        old_value=old_heat,
        new_value=org.heat,
    ))
    
    # --- Collateral damage ---
    collateral_wealth_loss = 0.0
    collateral_agitation = 0.0
    if target.node_type in ("organization", "business"):
        pop_nodes = graph.get_population_in_territory(target.territory_id)
        for pop in pop_nodes:
            loss = c_destroyed * defines.collateral_fraction * (pop.population / territory.total_population)
            pop.wealth = max(0, pop.wealth - loss)
            collateral_wealth_loss += loss
            
            # Collateral generates agitation (people's lives disrupted)
            agit_increase = loss * defines.collateral_agitation_rate
            pop.material_conditions.agitation += agit_increase
            collateral_agitation += agit_increase
    
    # --- OPSEC exposure ---
    opsec_exposure = visibility_multiplier * defines.opsec_base_exposure
    # State gains intelligence about org structure proportional to exposure
    
    # --- Events ---
    events.append(SimulationEvent(
        type=EventType.ATTACK_CONDUCTED,
        payload={
            "org_id": org.id,
            "target_id": target.id,
            "mode": mode,
            "damage_ratio": damage_ratio,
            "c_destroyed": c_destroyed if target.node_type != "edge" else 0,
            "heat_generated": heat_increase,
            "collateral_wealth_loss": collateral_wealth_loss,
            "collateral_agitation": collateral_agitation,
            "opsec_exposure": opsec_exposure,
        },
    ))
    
    # State AI will process this event and likely respond with REPRESS
    # That response generates repression_backfire (spec 043)
    # which creates agitation that feeds consciousness routing
    
    return VerbResult(
        mutations=mutations,
        events=events,
        ap_spent=ap_cost,
        resources_spent={resource_key: spent},
        feedback=VerbFeedback(
            success=True,
            summary=f"{'Targeted operation' if mode == 'targeted' else 'Mass action'} against {target.display_name}",
            details={
                "damage_inflicted": damage_ratio,
                "c_destroyed": c_destroyed if target.node_type != "edge" else None,
                "s_flow_disrupted": s_flow_reduction if target.node_type != "edge" else old_flow,
                "heat_increase": heat_increase,
                "total_heat": org.heat,
                "collateral_damage": collateral_wealth_loss,
                "opsec_exposure": opsec_exposure,
                "over_budget": over_budget_factor < 1.0,
                "ultra_left_warning": detect_ultra_left_trap(
                    get_recent_actions(org.id),
                    org.heat,
                    org.resources.sympathizer_labor,
                    count_territories(org),
                ).severity.value,
            },
        ),
    )
```

---

## Tick Results: ATTACK Feedback

```json
{
  "action_id": "action-uuid",
  "verb": "attack",
  "org_name": "Detroit Freedom School",
  "target_name": "Wayne Auto Parts Inc.",
  "mode": "targeted",
  "success": true,
  "costs_paid": {
    "action_points": 2,
    "cadre_labor": 4.0
  },
  "effects": {
    "damage": {
      "c_destroyed": 8.0,
      "c_remaining": 37.0,
      "c_destruction_pct": 17.8,
      "wealth_destroyed": 8.0,
      "capacity_degraded_by": 0.15,
      "recovery_estimate": "~6 ticks",
      "value_interpretation": "17.8% of constant capital destroyed. This factory's accumulated dead labor — the machines, inventory, and infrastructure that discipline its 340 workers — is diminished. Production will be partially disrupted while capital reconstitutes through reinvestment."
    },
    "value_flow_disruption": {
      "s_flow_before": 4.5,
      "s_flow_after": 2.2,
      "s_flow_reduction": 2.3,
      "s_denied_to": "Detroit Financial Holdings",
      "disruption_duration": "~4 ticks",
      "interpretation": "Surplus extraction from Wayne Auto to finance capital reduced by 51%. The extraction circuit is wounded but not severed — capital will reconnect."
    },
    "heat": {
      "heat_before": 0.22,
      "heat_after": 0.47,
      "heat_increase": 0.25,
      "territory_heat_increase": 0.12,
      "interpretation": "Your organization is now significantly visible to the state apparatus. Expect a response within 1-2 ticks."
    },
    "collateral": {
      "population_affected": "Proletariat, Wayne County",
      "wealth_impact": -1.2,
      "workers_disrupted": 340,
      "interpretation": "Workers at Wayne Auto Parts experienced income loss from the production disruption. Their material conditions worsened."
    },
    "consciousness_cascade": {
      "collateral_agitation_generated": 0.12,
      "routing_prediction": "Agitation from collateral damage + anticipated repression backfire will feed consciousness routing. Given current education pressure (0.12) and solidarity infrastructure (3 edges), approximately 55% will route to r, 30% to f, 15% to l.",
      "net_assessment": "This operation damaged capital and disrupted extraction, but the consciousness effects depend entirely on whether your political infrastructure can interpret the resulting crisis. Without sustained EDUCATE, this agitation will partially route to fascist tendency."
    },
    "opsec": {
      "exposure": 0.15,
      "interpretation": "Targeted operation limited exposure. The state gained partial intelligence about your organizational structure. Counter-surveillance (INVESTIGATE) can mitigate."
    },
    "state_attention": {
      "threads_diverted": 1,
      "interpretation": "The state must allocate 1 attention thread to investigate this attack. Other organizing activity in the region experiences reduced surveillance pressure this tick."
    }
  },
  "state_response": {
    "triggered": true,
    "response_verb": "REPRESS:RAID",
    "response_description": "FBI Detroit field office initiated a joint investigation with DPD. Two known associates of your organization were detained for questioning and released. Your Brightmoor meeting space was photographed by an unmarked vehicle.",
    "repression_backfire": {
      "agitation_generated": 0.18,
      "affected_community": "NEW_AFRIKAN",
      "routing_result": {
        "r_gained": 0.010,
        "f_gained": 0.005,
        "l_lost": 0.015
      },
      "interpretation": "State repression generated agitation within the New Afrikan community. Because solidarity edges and education pressure exist, most of this agitation routed toward revolutionary consciousness. The state's response partially validated your political framework."
    }
  },
  "ultra_left_assessment": {
    "trap_score_before": 0.15,
    "trap_score_after": 0.22,
    "severity": "none",
    "advisory": "Attack frequency is within sustainable range. Monitor heat levels — sustained operations above 0.5 heat will trigger escalated state response."
  },
  "narrative": "The fire at the Wayne Auto Parts warehouse started at 3:17 AM and burned for six hours. The fire marshal's report listed the cause as 'electrical.' Insurance investigators were less credulous. Production on the Brightmoor line stopped for two weeks. Management announced layoffs. The union — such as it was — didn't contest them. In the parking lot where workers gathered to hear the news, someone had left a stack of pamphlets about wage theft in the auto supply chain. Half of them were picked up. The other half blew across the empty lot like leaves."
}
```

---

## GameDefines Constants

```python
class AttackDefines(BaseModel):
    """ATTACK verb coefficients."""
    
    targeted_cl_cost: float = Field(
        default=4.0,
        description="CL cost for targeted operations. High — precision requires trained cadre.",
    )
    mass_sl_cost: float = Field(
        default=15.0,
        description="SL cost for mass actions. Requires mobilizing the sympathizer base.",
    )
    targeted_visibility: float = Field(
        default=0.4, ge=0.0,
        description="Visibility multiplier for targeted mode. Low — surgical operations.",
    )
    mass_visibility: float = Field(
        default=1.0, ge=0.0,
        description="Visibility multiplier for mass mode. Maximum — everyone sees.",
    )
    c_destruction_rate: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description=(
            "Fraction of target c destroyed per unit damage_ratio. "
            "At 0.3, a perfectly effective attack destroys 30% of c."
        ),
    )
    capacity_degradation_rate: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Capacity degradation per unit damage_ratio.",
    )
    flow_disruption_rate: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description=(
            "Fraction of s-flow disrupted on extractive edges when "
            "the source node is attacked."
        ),
    )
    base_recovery_ticks: int = Field(
        default=8,
        description="Base ticks for target to recover from attack. Scaled by damage.",
    )
    edge_sever_recovery_ticks: int = Field(
        default=10,
        description="Ticks for a severed edge to potentially reconnect.",
    )
    heat_per_damage: float = Field(
        default=1.0, ge=0.0,
        description="Heat generated per unit of damage_ratio × visibility. Game Design Knob.",
    )
    territory_heat_fraction: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Fraction of org heat that also applies to the territory.",
    )
    collateral_fraction: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description=(
            "Fraction of c_destroyed that hits population as collateral "
            "wealth loss. At 0.15, destroying 10 c costs the population 1.5 wealth."
        ),
    )
    collateral_agitation_rate: float = Field(
        default=0.08, ge=0.0,
        description=(
            "Agitation generated per unit of collateral wealth loss. "
            "Collateral damage generates its own agitation, separate "
            "from repression backfire."
        ),
    )
    opsec_base_exposure: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description=(
            "Base OPSEC exposure per attack, scaled by visibility. "
            "State gains intelligence about org structure proportional to exposure."
        ),
    )
    warsaw_ghetto_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description=(
            "P(S|A) below which the Warsaw Ghetto flag activates. "
            "When survival through acquiescence is below 5%, "
            "the action is framed as survival response, not strategy."
        ),
    )
```

---

## Relationship to Other Verbs

| Verb Pairing | Effect | Strategic Meaning |
|-------------|--------|-------------------|
| ATTACK + EDUCATE | Optimal. ATTACK disrupts capital and generates heat → state REPRESS → repression backfire agitation. EDUCATE builds the interpretive framework so that agitation routes to r. The agitation ATTACK provokes is raw material for consciousness change — but only if education infrastructure exists | George Jackson: the dialectic of repression and consciousness |
| ATTACK alone | Ultra-left trap. Damage to capital, massive heat, repression, org degraded or destroyed. Agitation generated but routes to f. Net effect: negative | Weather Underground |
| ATTACK + AID | Contradictory but potentially viable. ATTACK disrupts the oppressor; AID supports the community damaged by the disruption. Sequences matter — AID first (build base) then ATTACK (from a position of solidarity) is stronger than the reverse | Robin Hood — fragile but historically precedented |
| ATTACK + INVESTIGATE | Force multiplier. INVESTIGATE reveals targets and defensive capacity. ATTACK with intelligence is more effective and generates less collateral. The reverse also works: ATTACK forces the state to reveal its repressive capacity (who responds, how fast, with what force), which INVESTIGATE can then map | Sparrow's methodology: offense and intelligence are reciprocal |
| ATTACK + MOBILIZE | Escalation ladder. MOBILIZE is mass action through numbers (strikes, blockades). ATTACK is mass or targeted action through force. MOBILIZE first → ATTACK if needed represents escalation. ATTACK without prior MOBILIZE skips the political justification step | The question of when demonstrations become insurrections |
| CAMPAIGN then ATTACK | Exploit the surveillance gap. CAMPAIGN reduces state threat assessment ("they're playing within the rules"). Then ATTACK catches the state with lowered guard. Cynical but mechanically effective — the state's attention threads are allocated to institutional monitoring, not kinetic threat detection | Working within the system to create openings outside it |
