# AID Verb: API Endpoint Specification

**Parent Spec**: `043-consciousness-value-integration`, `037-player-verb-resolution`, `038-django-web-application-v3`
**Scope**: GET (populate page) and POST (submit action) for the AID verb
**Date**: 2026-04-10

---

## Theoretical Grounding: AID and the Value Form

AID operates where the player's strategic action meets the value tensor directly. Unlike EDUCATE (which modifies the interpretive layer), AID intervenes in social reproduction — the domain of v (variable capital) and Department III.

### What AID Does to the Value Form

Variable capital (v) represents the value of labor power — the basket of use-values workers must consume to reproduce themselves. Under normal capitalist circulation, workers access this basket through the wage: sell labor power → receive money → purchase commodities (food, housing, care). Every link in this chain is mediated by the commodity form.

AID short-circuits this chain by providing use-values outside the commodity form. When the org transfers material resources to a population — food, medical care, housing defense, childcare — it directly substitutes for what v is supposed to cover, but without the wage relation. This has measurable effects on two subsistence parameters already in the data model:

- **s_bio** (biological minimum): AID covering food/medical directly reduces the population's dependence on wages for biological survival
- **s_class** (social reproduction requirement): AID covering housing/childcare/education reduces dependence on wages for class-specific lifestyle maintenance

The degree to which AID covers these needs determines how much it loosens capital's disciplinary grip on the target population. A worker whose s_bio is met by mutual aid rather than wages has more leverage — they can strike, refuse unsafe work, attend a study circle instead of a second shift.

### The Two Outputs of AID

**Output 1 — Material Transfer (v-domain)**: Resources flow from org to population. Target's effective_wealth increases. Survival metrics improve. Consumption gap narrows. This is a direct, measurable intervention in the reproduction of labor power.

**Output 2 — Edge Creation (topology domain)**: The act of providing aid establishes a concrete, material relationship between org and population. This relationship IS an edge in the graph. If no edge exists, AID creates a TRANSACTIONAL edge. If a TRANSACTIONAL edge already exists, sustained AID (combined with EDUCATE) is the path to SOLIDARISTIC transformation.

### The Economism Trap (Value-Theoretic)

AID without EDUCATE is the economism error expressed as gameplay. It substitutes for v without explaining why v is insufficient. The mechanical consequence:

1. Material conditions improve → agitation DROPS (target's material_conditions_buffer.agitation decreases because the gap between needs and means narrows)
2. Agitation drop → less material to route through consciousness simplex
3. No education_pressure → whatever agitation remains routes to l (liberal) by default
4. Net effect: population is materially better off, ideologically unchanged, and now dependent on the org as a service provider rather than activated as political subjects

This is AID reproducing the logic of Φ (imperial rent) at the organizational scale — distributing material benefits to maintain stability rather than building consciousness. The state's CO-OPT:BRIBE verb does the same thing intentionally.

### The Solidarity Edge Factory (Value-Theoretic)

When AID works correctly (paired with EDUCATE), the material transfer is not charity — it is the construction of non-commodified social relations. The edge it creates represents a relationship that exists outside the M-C-M' circuit. This is significant because:

- SOLIDARISTIC edges are the routing infrastructure for revolutionary consciousness (spec 043: solidarity_factor in the agitation routing formula)
- The more SOLIDARISTIC edges exist, the more agitation routes to r instead of f
- AID builds the material basis for these edges; EDUCATE builds the interpretive framework that transforms them from TRANSACTIONAL to SOLIDARISTIC

The edge mode state machine (Constitution Anti-Pattern VIII.1) enforces this: you cannot skip from no-relationship to SOLIDARISTIC. AID creates TRANSACTIONAL. EDUCATE + sustained AID transforms TRANSACTIONAL → SOLIDARISTIC. The intermediate step is the theory in action: solidarity must be built through practice, not declared.

### AID to Organizations vs. Populations

AID has two target types with different value-theoretic meanings:

**AID → Population (SocialClass node)**: Intervenes in reproduction of labor power. Creates org→population edges. The Panthers' survival programs. Resource transfers affect s_bio/s_class on the population node.

**AID → Allied Organization**: Transfers resources between orgs. Strengthens the org→org edge. Does NOT directly affect population survival metrics — it affects the allied org's capacity to act. This is coalition logistics: sharing cadre labor, material resources, or sympathizer networks with allies. Edge mode between orgs follows the same state machine.

---

## Endpoint 1: GET Available AID Targets

### Route

```
GET /api/games/{game_id}/verbs/aid/?org_id={org_id}
```

### Purpose

Populate the AID page. Returns valid targets (populations and allied orgs), their current material conditions, what the org can transfer, projected effects on survival metrics, edge creation/strengthening projections, and the consciousness trade-off (agitation reduction vs. solidarity infrastructure).

### Response: 200 OK

```json
{
  "status": "ok",
  "tick": 14,
  "verb": "aid",
  "acting_org": {
    "id": "org-detroit-freedom-school",
    "name": "Detroit Freedom School",
    "type": "PoliticalFaction",
    "consciousness_strategy": "revolutionary",
    "resources": {
      "cadre_labor": 12.0,
      "sympathizer_labor": 45.0,
      "material": 8.0
    },
    "ooda": {
      "action_points_remaining": 2,
      "action_points_max": 3,
      "cycle_time": 2
    }
  },
  "cost": {
    "action_points": 1,
    "cadre_labor": 0.0,
    "sympathizer_labor": 0.0,
    "material": "variable",
    "material_explanation": "AID transfers material resources from your org to the target. You choose how much to give. Minimum 1.0, maximum is your current stock (8.0).",
    "can_afford": true
  },
  "population_targets": [
    {
      "target_id": "sc-wayne-proletariat-26163",
      "target_type": "population",
      "class": "PROLETARIAT",
      "territory_name": "Wayne County",
      "territory_id": "territory-26163",
      "population": 482000,
      "material_conditions": {
        "wealth": 3.2,
        "s_bio": 2.0,
        "s_class": 1.8,
        "consumption_needs": 3.8,
        "consumption_gap": 0.6,
        "gap_explanation": "This population's consumption needs (3.8) exceed their wealth (3.2) by 0.6 — they are in deficit. Without intervention, wealth will deplete in ~5 ticks.",
        "effective_wealth": 3.5,
        "ppp_multiplier": 1.09,
        "imperial_rent_received": 0.3,
        "active": true
      },
      "existing_edge": {
        "exists": true,
        "mode": "TRANSACTIONAL",
        "established_tick": 8,
        "transition_history": ["none → TRANSACTIONAL (tick 8, via AID)"],
        "next_possible_transition": "SOLIDARISTIC",
        "transition_requirements": "Sustained AID + EDUCATE within shared community. Education pressure on shared community must exceed 0.15. Current: 0.12."
      },
      "community_overlap": {
        "shared_communities": ["NEW_AFRIKAN", "ADULT"],
        "overlap_score": 0.68,
        "strongest_shared": "NEW_AFRIKAN"
      },
      "aid_projection": {
        "transfer_amount_suggested": 2.0,
        "projected_wealth_after": 5.2,
        "projected_consumption_gap_after": -1.4,
        "gap_interpretation": "Surplus — population would have buffer above subsistence for ~3 ticks",
        "survival_improvement": {
          "p_acquiescence_before": 0.45,
          "p_acquiescence_after": 0.62,
          "interpretation": "Survival through acquiescence improves. This is the economism risk: improving P(S|A) without raising P(S|R) makes revolution less rational for the population."
        },
        "edge_effect": {
          "current_mode": "TRANSACTIONAL",
          "projected_mode": "TRANSACTIONAL",
          "solidaristic_progress": 0.55,
          "solidaristic_threshold": 1.0,
          "ticks_to_solidaristic": 6,
          "explanation": "Edge has accumulated 0.55 solidarity through prior aid. Needs ~6 more ticks of sustained AID + EDUCATE to transition to SOLIDARISTIC."
        },
        "consciousness_trade_off": {
          "agitation_before": 0.45,
          "agitation_reduction": 0.08,
          "agitation_after": 0.37,
          "education_pressure_on_community": 0.12,
          "economism_risk": "moderate",
          "economism_explanation": "AID will reduce agitation by ~0.08. Current education pressure (0.12) is below the routing effectiveness threshold (0.15). Net effect: material conditions improve but consciousness routing capacity decreases. Consider pairing with EDUCATE on the NEW_AFRIKAN community.",
          "solidarity_edge_value": "high",
          "solidarity_explanation": "Despite agitation reduction, this AID strengthens the TRANSACTIONAL edge toward SOLIDARISTIC transition. Solidaristic edges are the routing infrastructure for revolutionary consciousness — they make future EDUCATE more effective."
        }
      },
      "state_ai_response": {
        "visibility": "low",
        "likely_response": "CO-OPT — state may offer to fund your mutual aid program, creating dependency",
        "co_opt_risk": "The finance-capital faction prefers to absorb mutual aid into the NGO-industrial complex. If accepted, your TRANSACTIONAL edge transforms to CO-OPTIVE."
      }
    },
    {
      "target_id": "sc-wayne-lumpen-26163",
      "target_type": "population",
      "class": "LUMPENPROLETARIAT",
      "territory_name": "Wayne County",
      "territory_id": "territory-26163",
      "population": 127000,
      "material_conditions": {
        "wealth": 0.8,
        "s_bio": 2.0,
        "s_class": 0.5,
        "consumption_needs": 2.5,
        "consumption_gap": 1.7,
        "gap_explanation": "Severe deficit. This population's wealth (0.8) covers less than a third of consumption needs (2.5). Active starvation risk.",
        "effective_wealth": 0.8,
        "ppp_multiplier": 1.0,
        "imperial_rent_received": 0.0,
        "active": true
      },
      "existing_edge": {
        "exists": false,
        "mode": null,
        "next_possible_transition": "TRANSACTIONAL (new edge)",
        "transition_requirements": "Any AID action creates a new TRANSACTIONAL edge."
      },
      "community_overlap": {
        "shared_communities": ["NEW_AFRIKAN", "INCARCERATED"],
        "overlap_score": 0.52,
        "strongest_shared": "NEW_AFRIKAN"
      },
      "aid_projection": {
        "transfer_amount_suggested": 3.0,
        "projected_wealth_after": 3.8,
        "projected_consumption_gap_after": -1.3,
        "gap_interpretation": "Closes the starvation gap. Population survives another ~2 ticks.",
        "survival_improvement": {
          "p_acquiescence_before": 0.12,
          "p_acquiescence_after": 0.35,
          "interpretation": "P(S|A) rises significantly. For lumpenproletariat with very low P(S|A), this is less about economism risk and more about preventing entity death. You cannot educate the dead."
        },
        "edge_effect": {
          "current_mode": null,
          "projected_mode": "TRANSACTIONAL",
          "solidaristic_progress": 0.0,
          "solidaristic_threshold": 1.0,
          "ticks_to_solidaristic": 12,
          "explanation": "No existing edge. AID creates a new TRANSACTIONAL edge — the beginning of a relationship. Transformation to SOLIDARISTIC requires sustained engagement + EDUCATE."
        },
        "consciousness_trade_off": {
          "agitation_before": 0.72,
          "agitation_reduction": 0.15,
          "agitation_after": 0.57,
          "education_pressure_on_community": 0.12,
          "economism_risk": "low",
          "economism_explanation": "Even after AID, agitation remains high (0.57) — material conditions are still dire. The agitation reduction is real but the base is so high that there's ample material for consciousness routing. Immediate survival outweighs the economism concern here.",
          "solidarity_edge_value": "critical",
          "solidarity_explanation": "Creating a new edge to the lumpenproletariat opens a solidarity channel that didn't exist. This population has high agitation but zero solidarity edges — agitation is routing entirely to f (fascist). A TRANSACTIONAL edge begins redirecting that routing."
        }
      },
      "state_ai_response": {
        "visibility": "low",
        "likely_response": "None — state largely ignores aid to lumpenproletariat",
        "co_opt_risk": "Low. The state does not compete to provide for populations it has written off."
      }
    }
  ],
  "org_targets": [
    {
      "target_id": "org-wayne-mutual-aid-network",
      "target_type": "organization",
      "name": "Wayne Mutual Aid Network",
      "type": "CivilSocietyOrg",
      "consciousness_strategy": "liberal",
      "territory_name": "Wayne County",
      "existing_edge": {
        "exists": true,
        "mode": "TRANSACTIONAL",
        "established_tick": 5
      },
      "their_resources": {
        "cadre_labor": 3.0,
        "sympathizer_labor": 120.0,
        "material": 2.0
      },
      "aid_projection": {
        "transfer_amount_suggested": 2.0,
        "effect": "Strengthens your TRANSACTIONAL alliance. Increases their material capacity, enabling larger-scale AID operations through their sympathizer network. Risk: they are a liberal org — strengthening them channels resources through a liberal frame unless you also EDUCATE within shared communities.",
        "edge_effect": {
          "current_mode": "TRANSACTIONAL",
          "projected_mode": "TRANSACTIONAL",
          "solidaristic_progress": 0.30,
          "ticks_to_solidaristic": 9
        },
        "strategic_note": "Liberal orgs have large sympathizer bases but low cadre. AID strengthens their capacity to provide services but not their capacity to politicize. Consider whether this alliance serves your strategic goals or reproduces the NGO model."
      }
    }
  ],
  "unavailable_targets": [
    {
      "target_id": "sc-oakland-labor-aristocracy-26125",
      "class": "LABOR_ARISTOCRACY",
      "territory_name": "Oakland County",
      "reason": "Your organization has no presence in Oakland County. Use MOVE to establish presence before providing aid."
    }
  ]
}
```

### Response Field Semantics

**`population_targets`**: Populations (SocialClass nodes) in territories where the org has presence. Each target includes:

- **`material_conditions`**: Current survival state. `consumption_gap` = consumption_needs − wealth. Positive gap = deficit (starvation trajectory). Negative = surplus. `imperial_rent_received` shows how much Φ this population receives — high Φ means the population is buffered from exploitation and less likely to need or politically benefit from aid.

- **`existing_edge`**: Current relationship between org and target. If no edge exists, AID creates TRANSACTIONAL. If TRANSACTIONAL exists, AID + EDUCATE can push toward SOLIDARISTIC. `solidaristic_progress` tracks accumulated solidarity on the edge (float, threshold at 1.0 for mode transition). `transition_history` shows how this relationship evolved.

- **`community_overlap`**: Which communities the org and target population share. Higher overlap = stronger foundation for solidarity. AID to a population with no shared community is possible but less effective — you're an outsider providing charity, not a community member providing mutual support.

- **`aid_projection`**: The core feedforward. Shows `transfer_amount_suggested` (heuristic: enough to close the consumption gap for 2 ticks). Survival metric projections show P(S|A) change — this is the economism indicator. When P(S|A) rises significantly, the rational calculus for revolution shifts: if survival through acquiescence improves, P(S|R) must also improve (via organizing) or the population becomes less revolutionary.

- **`consciousness_trade_off`**: The critical strategic information. Shows how much agitation will be reduced by the material improvement, what the current education_pressure is on shared communities, and an explicit economism risk assessment. This is spec 043 in action: the player sees the tension between "help people survive" and "build revolutionary consciousness." The game doesn't resolve this tension — the player does.

**`org_targets`**: Allied organizations the player can transfer resources to. Different from population targets: no survival metrics, no consciousness trade-off. The effect is on the allied org's capacity, not on any population's material conditions. The `strategic_note` field flags when aiding a liberal org might reproduce dependency rather than build solidarity.

**`cost.material`**: Unlike other verbs, AID has a variable material cost — the player chooses how much to transfer. The endpoint reports the org's current material stock and provides a suggested amount, but the final amount is a parameter in the POST submission.

---

## Endpoint 2: POST Submit AID Action

### Route

```
POST /api/games/{game_id}/verbs/aid/
```

### Request Body

```json
{
  "org_id": "org-detroit-freedom-school",
  "target_id": "sc-wayne-lumpen-26163",
  "params": {
    "transfer_amount": 3.0,
    "resource_type": "material"
  }
}
```

**`target_id`**: Either a population node ID or an organization ID. The serializer determines target type from the ID prefix or by graph lookup.

**`params.transfer_amount`**: How much material to transfer. Must be > 0 and ≤ org's current material stock. This is the player's strategic choice: transfer more for greater immediate impact but deplete your own reserves.

**`params.resource_type`**: For MVP, always "material". Post-MVP: could include cadre_labor or sympathizer_labor transfers to allied orgs.

### Validation

1. `org_id` exists, is player-controlled, has AP remaining
2. `target_id` exists and is in a territory where org has presence
3. `transfer_amount` > 0 and ≤ org's material resources
4. No existing action queued for this org this tick
5. If target is an org, it is not ANTAGONISTIC toward the acting org (can't aid an enemy — use NEGOTIATE first to de-escalate)

### Response: 201 Created

```json
{
  "status": "ok",
  "action": {
    "id": "action-uuid",
    "tick": 14,
    "org_id": "org-detroit-freedom-school",
    "verb": "aid",
    "target_id": "sc-wayne-lumpen-26163",
    "params": {
      "transfer_amount": 3.0,
      "resource_type": "material"
    },
    "queued_at": "2026-04-10T16:45:00Z",
    "cost_estimate": {
      "action_points": 1,
      "material": 3.0
    }
  },
  "org_status": {
    "action_points_remaining": 1,
    "material_remaining": 5.0,
    "has_pending_action": true
  },
  "message": "Mutual aid operation queued. Detroit Freedom School will transfer 3.0 material resources to the lumpenproletariat in Wayne County. This will establish a new relationship with this population."
}
```

---

## Resolution Logic

```python
def resolve_aid(
    action: PlayerAction,
    graph: GraphProtocol,
    hypergraph: xgi.Hypergraph,
    defines: AidDefines,
) -> VerbResult:
    """Resolve a queued AID action.
    
    Two graph mutations:
    1. Transfer resources (org material → target wealth)
    2. Create or strengthen edge (org → target)
    
    Consciousness side-effects computed but applied in Layer 3:
    - Agitation reduction on target (material improvement)
    - Edge creation provides solidarity routing infrastructure
    """
    org = graph.get_node(action.org_id)
    target = graph.get_node(action.target_id)
    transfer = action.params["transfer_amount"]
    
    # --- Mutation 1: Resource Transfer ---
    # Deduct from org
    deduct_resources(org, material=transfer, action_points=1)
    
    # Apply to target
    if target.node_type == "social_class":
        # Population target: increase wealth, affecting survival calculus
        old_wealth = target.wealth
        target.wealth += transfer * defines.aid_efficiency
        # Aid efficiency < 1.0 accounts for logistics overhead
        
        # Compute agitation reduction
        # Material improvement reduces the experiential gap that generates agitation
        consumption_gap_before = max(0, target.consumption_needs - old_wealth)
        consumption_gap_after = max(0, target.consumption_needs - target.wealth)
        gap_reduction = consumption_gap_before - consumption_gap_after
        agitation_reduction = gap_reduction * defines.agitation_relief_per_unit
        
        # Apply agitation reduction to MaterialConditionsBuffer
        target.material_conditions.agitation = max(
            0.0,
            target.material_conditions.agitation - agitation_reduction
        )
        
    elif target.node_type == "organization":
        # Org target: increase their material stock
        target.resources.material += transfer * defines.aid_efficiency
        agitation_reduction = 0.0  # Org-to-org aid doesn't affect population agitation
    
    # --- Mutation 2: Edge Creation / Strengthening ---
    edge = graph.get_edge(org.id, target.id)
    edge_created = False
    edge_strengthened = False
    
    if edge is None:
        # No existing relationship → create TRANSACTIONAL edge
        graph.create_edge(
            source=org.id,
            target=target.id,
            edge_type=EdgeType.SOLIDARITY,  # category
            mode=EdgeMode.TRANSACTIONAL,    # initial mode
            attributes={
                "established_tick": action.tick,
                "established_by": "aid",
                "solidarity_accumulation": defines.aid_solidarity_increment,
            },
        )
        edge_created = True
    else:
        # Existing edge → accumulate solidarity
        old_accumulation = edge.attributes.get("solidarity_accumulation", 0.0)
        new_accumulation = old_accumulation + defines.aid_solidarity_increment
        edge.attributes["solidarity_accumulation"] = new_accumulation
        edge_strengthened = True
        
        # Check for mode transition: TRANSACTIONAL → SOLIDARISTIC
        # Requires: solidarity_accumulation >= threshold AND
        #           education_pressure on shared community >= education_threshold
        if (
            edge.mode == EdgeMode.TRANSACTIONAL
            and new_accumulation >= defines.solidaristic_threshold
        ):
            shared_communities = get_shared_communities(org, target, hypergraph)
            max_education = max(
                (c.education_pressure for c in shared_communities),
                default=0.0,
            )
            if max_education >= defines.education_threshold_for_solidarity:
                # Phase transition: TRANSACTIONAL → SOLIDARISTIC
                edge.mode = EdgeMode.SOLIDARISTIC
                # This is a qualitative transformation (Constitution I.7)
                # Emit a discrete event, not a gradual shift
    
    # --- Consciousness Side-Effect (computed, applied in Layer 3) ---
    # Revolutionary org: aid demonstrates alternative to commodity form
    # Liberal org: aid reinforces dependency
    # Fascist org: aid distributed along exclusionary lines
    tendency_effect = {
        "revolutionary": {"ci_delta": 0.01, "direction": "slight r push"},
        "liberal": {"ci_delta": 0.0, "direction": "neutral"},
        "fascist": {"ci_delta": -0.01, "direction": "slight f push"},
    }[org.consciousness_strategy.value]
    
    return VerbResult(
        mutations=[
            GraphMutation(
                target_type="social_class" if target.node_type == "social_class" else "organization",
                target_id=target.id,
                field="wealth" if target.node_type == "social_class" else "resources.material",
                old_value=old_wealth if target.node_type == "social_class" else None,
                new_value=target.wealth if target.node_type == "social_class" else target.resources.material,
            ),
            GraphMutation(
                target_type="edge",
                target_id=f"{org.id}→{target.id}",
                field="mode" if edge_created else "solidarity_accumulation",
                old_value=None if edge_created else old_accumulation,
                new_value="TRANSACTIONAL" if edge_created else new_accumulation,
            ),
        ],
        events=[
            SimulationEvent(
                type=EventType.SOLIDARITY_SPIKE if edge_created else EventType.CONSCIOUSNESS_TRANSMISSION,
                payload={
                    "org_id": org.id,
                    "target_id": target.id,
                    "transfer_amount": transfer,
                    "edge_created": edge_created,
                    "edge_strengthened": edge_strengthened,
                    "agitation_reduction": agitation_reduction,
                    "tendency_effect": tendency_effect,
                },
            ),
        ],
        ap_spent=1,
        resources_spent={"material": transfer},
        feedback=VerbFeedback(
            success=True,
            summary=f"Mutual aid delivered to {target.display_name}",
            details={
                "transferred": transfer,
                "wealth_improvement": target.wealth - old_wealth if target.node_type == "social_class" else None,
                "agitation_reduced_by": agitation_reduction,
                "edge_created": edge_created,
                "edge_mode": "TRANSACTIONAL" if edge_created else edge.mode.value,
                "solidaristic_progress": edge.attributes.get("solidarity_accumulation", 0.0) if not edge_created else defines.aid_solidarity_increment,
                "economism_warning": agitation_reduction > 0.1 and not has_education_pressure(target, hypergraph),
            },
        ),
    )
```

### Layer 3 Consequences

After AID resolves in Action Phase, Layer 3 processes:

1. **Agitation routing** (spec 043): The reduced agitation on the target population flows through the consciousness routing formula on shared community hyperedges. Less agitation = less to route = less consciousness change this tick. But if a TRANSACTIONAL/SOLIDARISTIC edge now exists, the solidarity_factor in the routing formula increases, meaning future agitation routes more toward r. AID trades immediate agitation for structural routing capacity.

2. **Edge mode transition check**: If solidarity_accumulation crossed the threshold AND education_pressure is sufficient, the TRANSACTIONAL → SOLIDARISTIC transition fires as a discrete event (Constitution I.7: quantitative accumulation → qualitative transformation). This is one of the most important events in the game — a solidarity edge is permanent infrastructure.

3. **State AI signal**: AID generates low visibility. The state's likely response is CO-OPT:BRIBE — offer to fund the aid program. If the player accepts state funding (via NEGOTIATE), the edge may transform to CO-OPTIVE rather than SOLIDARISTIC. If the player refuses, the org remains independent but resource-constrained. This is a genuine strategic dilemma.

4. **Survival calculus update**: The target population's P(S|A) and P(S|R) are recomputed with the new wealth level. If AID significantly raised P(S|A) without corresponding P(S|R) increase, the population is less likely to support revolutionary action (economism in the survival calculus).

---

## GameDefines Constants

```python
class AidDefines(BaseModel):
    """AID verb coefficients."""
    
    aid_efficiency: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description=(
            "Fraction of transferred resources that reach the target. "
            "< 1.0 accounts for logistics overhead. "
            "Game Design Knob."
        ),
    )
    aid_cl_cost: float = Field(
        default=0.0,
        description="CL cost for AID. Zero — aid is logistically simple.",
    )
    aid_solidarity_increment: float = Field(
        default=0.15, ge=0.0,
        description=(
            "Solidarity accumulated per AID action on the org→target edge. "
            "Accumulates toward solidaristic_threshold. "
            "Game Design Knob."
        ),
    )
    solidaristic_threshold: float = Field(
        default=1.0, ge=0.0,
        description=(
            "Solidarity accumulation required for TRANSACTIONAL → SOLIDARISTIC "
            "transition. At 1.0 with increment 0.15, takes ~7 AID actions. "
            "But also requires education_threshold_for_solidarity to be met."
        ),
    )
    education_threshold_for_solidarity: float = Field(
        default=0.15, ge=0.0,
        description=(
            "Minimum education_pressure on a shared community for "
            "TRANSACTIONAL → SOLIDARISTIC transition. "
            "Enforces the 'AID alone is not solidarity' principle. "
            "Without education, the edge stays transactional forever."
        ),
    )
    agitation_relief_per_unit: float = Field(
        default=0.05, ge=0.0,
        description=(
            "Agitation reduction per unit of consumption gap closed by AID. "
            "Higher = AID reduces agitation faster = stronger economism risk. "
            "Calibrate: closing 1.0 consumption gap should reduce agitation "
            "by ~0.05 (noticeable but not overwhelming)."
        ),
    )
    economism_warning_threshold: float = Field(
        default=0.1, ge=0.0,
        description=(
            "Agitation reduction above which the feedforward displays "
            "an economism warning if education_pressure is below "
            "education_threshold_for_solidarity."
        ),
    )
```

---

## Tick Results: AID Feedback

```json
{
  "action_id": "action-uuid",
  "verb": "aid",
  "org_name": "Detroit Freedom School",
  "target_name": "Lumpenproletariat, Wayne County",
  "success": true,
  "costs_paid": {
    "action_points": 1,
    "material": 3.0
  },
  "effects": {
    "transferred": 2.55,
    "transfer_explanation": "3.0 material sent, 2.55 received (85% efficiency — logistics overhead)",
    "wealth_before": 0.8,
    "wealth_after": 3.35,
    "consumption_gap_closed": true,
    "starvation_averted": true,
    "edge_created": true,
    "edge_mode": "TRANSACTIONAL",
    "edge_explanation": "New relationship established. First material connection between your organization and this population.",
    "agitation_change": {
      "before": 0.72,
      "after": 0.63,
      "reduction": 0.09,
      "interpretation": "Material improvement slightly reduced political agitation. Agitation remains high — survival conditions are still precarious."
    },
    "economism_assessment": {
      "risk_level": "low",
      "explanation": "Agitation remains well above education threshold. The immediate survival need justified the intervention. Follow up with EDUCATE to build interpretive framework while agitation is still available."
    },
    "solidarity_progress": {
      "accumulation": 0.15,
      "threshold": 1.0,
      "percent_complete": 15,
      "next_step": "Continue AID and begin EDUCATE within shared communities. Solidarity requires both material support and political education."
    }
  },
  "state_response": {
    "triggered": false,
    "explanation": "State apparatus did not register this action. Aid to lumpenproletariat falls below surveillance thresholds."
  },
  "narrative": "Twenty-three families in the Brightmoor neighborhood received food packages this week. Word spread faster than the supplies — by Thursday, a line stretched around the block before the distribution opened. An elderly woman whose grandson had been killed by police last year grabbed the organizer's hand and said, 'Nobody from the city ever came.' The organizer said, 'We're not from the city.'"
}
```

---

## Relationship to Other Verbs

| Verb Pairing | Effect | Strategic Meaning |
|-------------|--------|-------------------|
| AID + EDUCATE | Optimal combination. AID provides material basis and creates edges. EDUCATE builds interpretive framework. Together they push TRANSACTIONAL → SOLIDARISTIC and route agitation to r | The Panthers model: survival programs + political education |
| AID alone | Economism trap. Material conditions improve, agitation drops, consciousness stagnates. Edges stay TRANSACTIONAL | Charity, not revolution |
| EDUCATE alone | Voluntarism risk. Education without material basis is abstract theory disconnected from practice. Low material_readiness reduces EDUCATE effectiveness | Armchair revolutionaries |
| AID + CAMPAIGN | Liberal trap amplified. AID improves conditions, CAMPAIGN channels energy into institutions. Strongest l attractor | The NGO model |
| AID + ATTACK | Contradictory signals. AID builds trust, ATTACK generates heat and repression. Can work if sequenced carefully (AID builds base, ATTACK targets specific oppressors) but risks destroying the relationships AID built | Robin Hood model — fragile |
| AID → state CO-OPT response → NEGOTIATE | The state offers to fund your program. NEGOTIATE determines whether you accept (resources but dependency) or refuse (independence but scarcity). Genuine strategic dilemma with no right answer | The Ford Foundation question |
