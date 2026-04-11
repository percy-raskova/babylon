# Build Org Triad: System Analysis + REPRODUCE & INVESTIGATE Endpoint Specifications

**Parent Spec**: `043-consciousness-value-integration`, `037-player-verb-resolution`
**Scope**: The EDUCATE → REPRODUCE → INVESTIGATE cycle as a system, plus API endpoint specs for REPRODUCE and INVESTIGATE (EDUCATE endpoint already spec'd separately)
**Date**: 2026-04-10

---

## The Build Org Cycle

The three Build Org verbs form a feedback cycle. Each verb produces outputs that feed the other two:

```
EDUCATE (consciousness)
  ├─ raises r on community hyperedges
  ├─ creates politically activated recruitment pool for REPRODUCE
  ├─ builds education_pressure that amplifies MOBILIZE routing
  └─ requires CL (produced by cadre, grown via REPRODUCE)
       ↓
REPRODUCE (organization)
  ├─ recruits from consciousness-raised communities
  ├─ grows cadre → generates CL → fuels more EDUCATE
  ├─ grows sympathizers → generates SL → fuels MOBILIZE, AID
  ├─ builds credibility in communities (membership overlap → EDUCATE effectiveness)
  └─ requires intelligence about recruitment terrain (from INVESTIGATE)
       ↓
INVESTIGATE (information)
  ├─ reveals community consciousness state (where is EDUCATE most effective?)
  ├─ reveals population composition (where is REPRODUCE most productive?)
  ├─ reveals enemy topology (where is ATTACK/MOBILIZE best targeted?)
  ├─ reveals state surveillance (where is your org exposed?)
  └─ requires CL for targeted intelligence (produced by cadre)
       ↓
(back to EDUCATE, now with more cadre, better intelligence, and deeper community roots)
```

This cycle is the organizational metabolism. It's what the org does to stay alive and grow. Without it, the org cannot effectively PROJECT POWER or MANAGE RESOURCES — those verbs depend on the capacity this cycle builds.

### The Organizational Value Circuit

The organization itself is a production unit. It produces political effects: consciousness change, solidarity edges, power projection, intelligence. Like any production unit in the Marxist framework, it has an internal composition:

**Cadre** = skilled labor. High productivity per member. Each cadre generates CL (Cadre Labor) per tick — the scarce resource that fuels EDUCATE, targeted INVESTIGATE, targeted ATTACK, and CAMPAIGN. Cadre are the organic intellectuals Gramsci described: embedded in their community, capable of making common sense critical. Training cadre is slow and expensive (REPRODUCE in cadre mode).

**Sympathizers** = general labor. Lower productivity per member but abundant. Each sympathizer generates SL (Sympathizer Labor) per tick — the mass-action resource that fuels MOBILIZE, mass RECRUIT, and large-scale AID. Sympathizers are the mass base. Recruiting sympathizers is fast and cheap (REPRODUCE in mass mode) but dilutes coherence.

**Coherence** = cadre / total membership. The organizational version of the organic composition of capital. High coherence means a disciplined, ideologically unified org that acts effectively but grows slowly. Low coherence means a large, loose network that projects impressive numbers but fragments under pressure.

**The fundamental trade-off of REPRODUCE**: investing in cadre (slow, expensive, builds CL capacity, maintains coherence) vs. mass recruitment (fast, cheap, builds SL capacity, dilutes coherence). This is the organizational version of the intensive vs. extensive accumulation choice. An org that chooses mass recruitment repeatedly creates the Influencer Trap: high Reputation + low Coherence = a crowd that looks like a movement but shatters at the first real crisis.

### Value-Theoretic Meaning of Each Verb

**EDUCATE**: Operates on the transparency of the value form (spec 043). Makes the invisible visible — the extraction, the exploitation, the imperial rent. Produces a community capable of interpreting its own material conditions. The output (education_pressure + consciousness routing) is the precondition for all other political action.

**REPRODUCE**: Operates on the org's capacity to produce political effects. The org's "v" is its membership's labor power (CL and SL). REPRODUCE grows v. The quality/quantity choice determines WHAT KIND of v: skilled revolutionary labor (cadre) or general political labor (sympathizers). The org's coherence is its internal discipline — the organizational equivalent of the rate at which labor power is productively deployed vs. dissipated.

**INVESTIGATE**: Operates on the org's knowledge of the value circuit. Investigation reveals: where does surplus flow (EXTRACTIVE edges), who benefits (s distribution), where is the state watching (attention threads), what communities are ripe for organizing (high agitation, low education), what enemy orgs are doing (OODA states, verb selections). This is Mao's "scientific experiment" — the analytical leg of the three practices. You cannot intervene effectively in a system you don't understand.

---

## REPRODUCE: Theoretical Grounding

### Recruitment and the Class Composition of the Org

Who you recruit determines what your organization can do. This is not a neutral scaling problem — it's a class composition question.

**Recruiting from proletariat with high r** (consciousness-raised through prior EDUCATE): produces committed cadre who understand the political framework. These recruits generate CL. They strengthen coherence. They increase credibility in their community (membership overlap goes up). But they're scarce — high-r populations are the product of sustained organizing work.

**Recruiting from proletariat with low r** (liberal or unorganized): produces sympathizers who support the org's material programs (AID, MOBILIZE) but lack political commitment. These recruits generate SL. They dilute coherence. They may drift if conditions change or if the state CO-OPTs them. But they're abundant — the mass of the population is low-r.

**Recruiting across contradiction pair boundaries** (settler org recruiting from colonized community, or vice versa): extremely expensive. The community overlap penalty is severe. Cross-line recruitment requires prior SOLIDARISTIC edges across the colonial divide — solidarity that has been built through shared struggle, not just goodwill. This mechanically enforces the principle that revolutionary organizing respects and builds from existing community structures rather than imposing external frameworks.

**D-P-D' lifecycle constraint**: can only recruit from ADULT (P-phase) population. YOUTH receive education (EDUCATE), ELDER provide legitimacy (elder_legitimacy_bonus on consciousness effects), but neither can be recruited as active cadre. This enforces the lifecycle circuit from the constitution.

### The Coherence Crisis

Coherence = cadre_count / total_membership. When an org recruits heavily without cadre training:

1. Total membership grows → denominator increases
2. Cadre count stays flat → numerator unchanged
3. Coherence drops → org becomes less effective per action
4. Low coherence → MOBILIZE produces chaos instead of discipline
5. Low coherence → ATTACK risks NETWORK_COLLAPSE (ultra-left trap)
6. Low coherence → state INFILTRATE is more effective (harder to detect outsiders in a loose network)

The Influencer Trap is the specific failure mode: an org with high Reputation (people know who you are) and low Coherence (but you're not actually organized). This org can MOBILIZE large numbers but cannot sustain a campaign, cannot survive repression, and cannot prevent co-optation of its sympathizer base.

---

## REPRODUCE: API Endpoint

### Route

```
GET /api/games/{game_id}/verbs/reproduce/?org_id={org_id}
```

### Response: 200 OK

```json
{
  "status": "ok",
  "tick": 14,
  "verb": "reproduce",
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
    "membership": {
      "cadre": 47,
      "sympathizers": 890,
      "total": 937,
      "coherence": 0.050,
      "coherence_interpretation": "Low coherence. Cadre are only 5% of total membership. The organization has a large sympathizer base but limited trained leadership. Mass recruitment will dilute coherence further. Cadre training is the strategic priority."
    },
    "ooda": {
      "action_points_remaining": 2,
      "action_points_max": 3
    },
    "resource_generation": {
      "cl_per_tick": 4.7,
      "cl_explanation": "47 cadre × 0.1 CL/cadre/tick = 4.7 CL generated per tick",
      "sl_per_tick": 35.6,
      "sl_explanation": "890 sympathizers × 0.04 SL/sympathizer/tick = 35.6 SL generated per tick. SL decays at 10%/tick without engagement."
    }
  },
  "cost": {
    "action_points": 1,
    "cadre_mode_cost": {"cadre_labor": 5.0},
    "mass_mode_cost": {"sympathizer_labor": 10.0},
    "can_afford_cadre": true,
    "can_afford_mass": true
  },
  "modes": {
    "cadre_training": {
      "description": "Train existing sympathizers into cadre. Slow, expensive, builds CL capacity and maintains coherence. The investment that compounds.",
      "resource_cost": {"cadre_labor": 5.0},
      "projected_effect": {
        "cadre_gained": 3,
        "cadre_gained_explanation": "3 sympathizers promoted to cadre. They undergo political education, operational training, and ideological development.",
        "sympathizers_lost": 3,
        "sympathizers_lost_explanation": "Promoted sympathizers leave the sympathizer pool.",
        "coherence_before": 0.050,
        "coherence_after": 0.054,
        "coherence_direction": "improving",
        "cl_generation_increase": 0.3,
        "cl_generation_new_total": 5.0,
        "sl_generation_decrease": 0.12,
        "net_assessment": "Small but compounding investment. Each new cadre generates 0.1 CL/tick permanently. Over 10 ticks, these 3 cadre produce 3.0 additional CL — recovering the investment. Coherence stabilizes."
      },
      "recruitment_pool": {
        "eligible_sympathizers": 890,
        "community_filter": "Promotion prioritizes sympathizers embedded in communities where the org has presence. Current communities: NEW_AFRIKAN (68% overlap), WOMEN (41% overlap), ADULT (100%).",
        "consciousness_filter": "Sympathizers from communities with higher r are more likely to succeed in cadre training. NEW_AFRIKAN community r=0.25 — modest but sufficient for initial cadre development."
      }
    },
    "mass_recruitment": {
      "description": "Recruit new sympathizers from the population. Fast, cheap, builds SL capacity but dilutes coherence. Numbers without discipline.",
      "resource_cost": {"sympathizer_labor": 10.0},
      "projected_effect": {
        "sympathizers_gained": 85,
        "sympathizers_gained_explanation": "Estimated 85 new sympathizers from Wayne County population. Recruitment effectiveness depends on org's Reputation (0.42) and community overlap.",
        "cadre_gained": 0,
        "coherence_before": 0.050,
        "coherence_after": 0.046,
        "coherence_direction": "declining",
        "coherence_warning": "Coherence drops below 5%. Your organization is approaching the Influencer Trap: high visibility, low discipline. The state will find it easier to infiltrate, co-opt sympathizers, and provoke premature action.",
        "sl_generation_increase": 3.4,
        "net_assessment": "Rapid growth in mass base. SL generation increases significantly, enabling larger MOBILIZE and AID operations. But coherence declines — the org becomes harder to steer and easier to fragment."
      },
      "recruitment_pool": {
        "territory": "Wayne County",
        "population_available": {
          "PROLETARIAT": {
            "population": 482000,
            "community_overlap": ["NEW_AFRIKAN (68%)", "ADULT (100%)"],
            "r_level": 0.25,
            "recruitment_modifier": 1.0,
            "explanation": "Base recruitment rate. Shared community membership and modest consciousness make this the primary recruitment pool."
          },
          "LUMPENPROLETARIAT": {
            "population": 127000,
            "community_overlap": ["NEW_AFRIKAN (52%)", "INCARCERATED (overlap unknown)"],
            "r_level": 0.15,
            "recruitment_modifier": 0.7,
            "explanation": "Lower recruitment rate — lumpenproletariat is harder to organize (unstable material conditions, institutional exclusion). But recruiting from this population builds edges to a community with the highest agitation (0.72)."
          }
        },
        "cross_community_penalty": {
          "SETTLER": {
            "recruitment_modifier": 0.05,
            "explanation": "Recruiting across the SETTLER ↔ NEW_AFRIKAN contradiction pair boundary is near-impossible without prior SOLIDARISTIC edges across the divide. You have zero solidaristic edges with SETTLER communities. Build cross-line solidarity first."
          }
        }
      }
    }
  },
  "state_response": {
    "cadre_mode_visibility": "low",
    "cadre_mode_response": "Internal training is invisible to the state unless the org is already under surveillance.",
    "mass_mode_visibility": "medium",
    "mass_mode_response": "Visible recruitment spike. State RESEARCH likely — will update threat assessment. Large recruitment may trigger CO-OPT:BRIBE (state offers jobs to potential recruits)."
  }
}
```

### POST Submit

```
POST /api/games/{game_id}/verbs/reproduce/
```

```json
{
  "org_id": "org-detroit-freedom-school",
  "target_id": "org-detroit-freedom-school",
  "params": {
    "mode": "cadre_training",
    "recruitment_territory": "territory-26163"
  }
}
```

**`target_id`**: Self-targeted. Always equals `org_id`. REPRODUCE is the only verb whose target is the acting org itself.

**`params.mode`**: `"cadre_training"` or `"mass_recruitment"`. Determines resource cost, effects, and coherence impact.

**`params.recruitment_territory`**: For mass mode, which territory to recruit from. Determines available population pools and community overlap modifiers.

### Resolution Logic (Sketch)

```python
def resolve_reproduce(action, graph, hypergraph, defines):
    org = graph.get_node(action.org_id)
    mode = action.params["mode"]

    if mode == "cadre_training":
        # Promote sympathizers to cadre
        promotions = min(
            defines.cadre_training_rate,
            org.sympathizer_count,
        )
        # Deduct CL cost
        deduct_resources(org, cadre_labor=defines.cadre_cl_cost)
        # Apply promotions
        org.cadre_count += promotions
        org.sympathizer_count -= promotions
        # Coherence improves (cadre ratio increases)
        # CL generation increases
        # Community credibility may increase (more cadre embedded in communities)

    elif mode == "mass_recruitment":
        territory = action.params["recruitment_territory"]
        # Compute recruitment from population pools
        # Filtered by community overlap, consciousness level, D-P-D' lifecycle
        deduct_resources(org, sympathizer_labor=defines.mass_sl_cost)
        recruited = compute_recruitment(org, territory, graph, hypergraph, defines)
        org.sympathizer_count += recruited
        # Coherence declines (denominator grows, numerator unchanged)
        # SL generation increases
        # New TRANSACTIONAL edges to recruited population possible
        # Visibility increases if recruitment is large

    return VerbResult(...)
```

---

## INVESTIGATE: Theoretical Grounding

### Information as Precondition for Effective Action

In Mao's three practices — the struggle for production, the class struggle, and scientific experiment — INVESTIGATE is the scientific experiment. It's the analytical work that transforms raw experience into actionable knowledge.

The value tensor generates numbers at every node and edge. But the player doesn't see all of them. Fog of war obscures:

- **Hidden node attributes**: Enemy org membership, resource levels, OODA state, defensive capacity
- **Hidden edges**: State surveillance attention threads, covert EXTRACTIVE flows, secret alliances
- **Hidden community data**: True agitation levels in territories the org doesn't have presence in, consciousness state of communities the org isn't embedded in
- **Counter-intelligence**: Whether the state has INFILTRATED your org, what the state knows about you

INVESTIGATE makes the invisible visible. Each investigation reveals a slice of hidden information, proportional to the org's intelligence capability and inversely proportional to the target's operational security.

### Intelligence and the Value Circuit

The value tensor is the map of exploitation. INVESTIGATE reads that map. Specifically:

- **Investigating a territory** reveals: economic composition (what departments, what s/v ratios), class distribution, which orgs operate there, heat level, infrastructure state, hidden UseValue profiles. This is the material reconnaissance that informs where to EDUCATE, AID, MOBILIZE, or ATTACK.

- **Investigating an organization** reveals: membership, resources, OODA state, edge relationships, consciousness strategy, defensive capacity. For businesses: their c stock, s extraction rate, extractive edge endpoints. For state apparatus: attention thread allocation, surveillance methods in use, factional alignment. This is the target intelligence that makes ATTACK and NEGOTIATE effective.

- **Investigating an edge** reveals: flow values, mode, transition history. For EXTRACTIVE edges: how much s flows and to whom. For hidden state surveillance edges: that you're being watched, and by what method. This is the structural intelligence that reveals the topology of power.

- **Counter-intelligence (investigating your own org)**: reveals whether the state has INFILTRATED, what your OPSEC exposure is, where your vulnerabilities are. This is the defensive application — the paranoia that keeps you alive, balanced against the coherence cost of suspicion.

### The Intelligence-Action Loop

INVESTIGATE has no direct effect on the value tensor or on consciousness. It changes only what the player knows. But knowledge enables effective action:

```
INVESTIGATE territory → discover high agitation in a community → EDUCATE there (high material_readiness)
INVESTIGATE business → discover extractive edge to finance capital → ATTACK the edge
INVESTIGATE state → discover attention thread on your org → MOVE operations, use counter-intel
INVESTIGATE ally → discover CO-OPTIVE edge from state → warn ally, NEGOTIATE defense
```

The cost of NOT investigating is acting on incomplete information: EDUCATing a community with low agitation (wasted CL), ATTACKing a target with high defensive capacity (ineffective and high heat), MOBILIZing in a territory where the state has concentrated attention threads (guaranteed repression).

---

## INVESTIGATE: API Endpoint

### Route

```
GET /api/games/{game_id}/verbs/investigate/?org_id={org_id}
```

### Response: 200 OK

```json
{
  "status": "ok",
  "tick": 14,
  "verb": "investigate",
  "acting_org": {
    "id": "org-detroit-freedom-school",
    "name": "Detroit Freedom School",
    "type": "PoliticalFaction",
    "resources": {
      "cadre_labor": 12.0,
      "sympathizer_labor": 45.0
    },
    "ooda": {
      "action_points_remaining": 2,
      "observe_capability": 0.55,
      "observe_explanation": "OODA Observe phase rating. Higher = more effective intelligence gathering. Improved by counter-intel training and embedded community networks."
    }
  },
  "cost": {
    "action_points": 1,
    "targeted_cost": {"cadre_labor": 3.0},
    "recon_cost": {"sympathizer_labor": 8.0},
    "cost_explanation": "Targeted intelligence (specific org/edge) costs CL — precision work requires trained cadre. General reconnaissance (territory scan) costs SL — mass observation, many eyes."
  },
  "targets": {
    "territories": [
      {
        "target_id": "territory-26163",
        "target_name": "Wayne County",
        "investigation_type": "reconnaissance",
        "resource_cost": {"sympathizer_labor": 8.0},
        "current_knowledge": {
          "known": ["economic composition (QCEW data)", "class distribution", "own org presence", "communities with membership overlap"],
          "partially_known": ["NPC org presence (some detected)", "heat level (estimated)", "agitation levels (for communities where embedded)"],
          "unknown": ["hidden state attention threads", "enemy org details", "true agitation in communities without presence", "covert extractive flows", "infrastructure vulnerabilities"]
        },
        "projected_reveals": {
          "probability_of_useful_intel": 0.70,
          "likely_reveals": [
            "State attention threads targeting this territory (if any)",
            "NPC organization resource levels and OODA states",
            "True agitation on communities where org has no presence",
            "Hidden infrastructure that could be AID or ATTACK targets"
          ],
          "community_embedding_bonus": "Your org's presence in Wayne County (72% strength) provides significant intelligence advantage. Community members share information naturally — investigation here is augmented by existing social networks."
        },
        "detection_risk": {
          "probability": 0.10,
          "explanation": "Low detection risk — reconnaissance in your own territory is natural activity. Risk increases if the state already has an attention thread here."
        }
      },
      {
        "target_id": "territory-26125",
        "target_name": "Oakland County",
        "investigation_type": "reconnaissance",
        "resource_cost": {"sympathizer_labor": 12.0},
        "current_knowledge": {
          "known": ["economic composition (QCEW data)", "class distribution (Census)"],
          "partially_known": [],
          "unknown": ["almost everything — no organizational presence"]
        },
        "projected_reveals": {
          "probability_of_useful_intel": 0.35,
          "likely_reveals": [
            "Org landscape (who operates here)",
            "Heat level",
            "Broad agitation estimate"
          ],
          "community_embedding_bonus": "No org presence in Oakland County. Investigation is external reconnaissance — less effective, more expensive, higher detection risk. Consider MOVE to establish presence first."
        },
        "detection_risk": {
          "probability": 0.30,
          "explanation": "Moderate risk — investigating territory where you have no presence looks suspicious. If detected, state gains intelligence about YOUR interest in this territory."
        }
      }
    ],
    "organizations": [
      {
        "target_id": "org-wayne-auto-parts-inc",
        "target_name": "Wayne Auto Parts Inc.",
        "target_type": "Business",
        "investigation_type": "targeted",
        "resource_cost": {"cadre_labor": 3.0},
        "current_knowledge": {
          "known": ["exists", "location", "department (I)", "approximate workforce"],
          "unknown": ["exact c stock", "s/v ratio", "extractive edge endpoints and flow values", "defensive capacity", "management structure", "union status"]
        },
        "projected_reveals": {
          "probability_of_useful_intel": 0.65,
          "likely_reveals": [
            "Value tensor details: c stock, s extraction rate, s/v ratio",
            "Extractive edge map: where does surplus flow after extraction",
            "Defensive capacity (relevant if considering ATTACK)",
            "Workforce composition (relevant if considering MOBILIZE strike)"
          ],
          "strategic_value": "Investigating this business reveals the extraction circuit in detail. You'll know exactly how much surplus is extracted, where it goes, and how vulnerable the operation is to disruption. This intelligence makes ATTACK and MOBILIZE:STRIKE significantly more effective."
        },
        "detection_risk": {
          "probability": 0.20,
          "explanation": "Investigating a business from a territory where you have presence. Moderate risk — unusual interest in a company's finances may be noticed."
        }
      },
      {
        "target_id": "org-fbi-detroit",
        "target_name": "FBI Detroit Field Office",
        "target_type": "StateApparatus",
        "investigation_type": "targeted",
        "resource_cost": {"cadre_labor": 5.0},
        "current_knowledge": {
          "known": ["exists", "location"],
          "unknown": ["attention thread allocation", "which orgs/communities are under surveillance", "surveillance methods", "informant network", "factional alignment (security-state assumed)"]
        },
        "projected_reveals": {
          "probability_of_useful_intel": 0.40,
          "likely_reveals": [
            "Whether your org has an active attention thread",
            "Surveillance methods in use against your territory",
            "General threat assessment level for your org"
          ],
          "strategic_value": "Critical defensive intelligence. If the FBI has an attention thread on your org, you need to know — it affects the risk calculus for every other verb. If they're using INFORMANT methods, you may have an infiltrator.",
          "observe_difficulty": "HIGH — state apparatus has the best OPSEC. Your observe_capability (0.55) against their security makes useful intelligence unlikely without sustained investigation over multiple ticks."
        },
        "detection_risk": {
          "probability": 0.45,
          "explanation": "HIGH — investigating the state's repressive apparatus is the most dangerous intelligence operation. If detected, the state immediately opens an attention thread on your org (if one doesn't exist) or escalates existing surveillance."
        }
      }
    ],
    "counter_intelligence": {
      "target_id": "org-detroit-freedom-school",
      "target_name": "Your organization (internal)",
      "investigation_type": "counter_intelligence",
      "resource_cost": {"cadre_labor": 2.0},
      "current_opsec": {
        "heat": 0.22,
        "known_exposure": "2 ATTACK actions in last 10 ticks generated moderate OPSEC exposure",
        "infiltration_probability": "Unknown — this is what counter-intel reveals",
        "last_counter_intel": "Tick 8 (6 ticks ago)"
      },
      "projected_reveals": {
        "probability_of_useful_intel": 0.80,
        "likely_reveals": [
          "Current OPSEC posture assessment",
          "Whether state attention threads target your org specifically",
          "Infiltration probability estimate (based on org topology and state intelligence level)",
          "Recommendations for operational security improvements"
        ],
        "strategic_value": "Defensive hygiene. Counter-intelligence is cheap insurance. The cost of NOT knowing you're infiltrated is catastrophic — a state PROVOCATEUR can trigger the ultra-left trap from inside your org."
      },
      "detection_risk": {
        "probability": 0.0,
        "explanation": "Zero — counter-intelligence is internal. The state cannot detect you investigating yourself."
      }
    }
  }
}
```

### POST Submit

```
POST /api/games/{game_id}/verbs/investigate/
```

```json
{
  "org_id": "org-detroit-freedom-school",
  "target_id": "org-wayne-auto-parts-inc",
  "params": {
    "mode": "targeted"
  }
}
```

**`params.mode`**: `"targeted"` (CL cost, specific org/edge) or `"recon"` (SL cost, territory scan) or `"counter_intel"` (CL cost, self-targeted).

### Resolution Logic (Sketch)

```python
def resolve_investigate(action, graph, hypergraph, defines):
    org = graph.get_node(action.org_id)
    target = graph.get_node(action.target_id)
    mode = action.params["mode"]

    # Intelligence effectiveness
    observe = org.ooda.observe_capability
    if mode == "counter_intel":
        target_opsec = 0.0  # Investigating yourself has no resistance
    else:
        target_opsec = getattr(target, "opsec", 0.5)

    # Community embedding bonus
    if is_same_territory(org, target):
        embedding_bonus = org.presence_strength_in(target.territory_id)
    else:
        embedding_bonus = 0.0

    intel_effectiveness = (observe + embedding_bonus) / (observe + embedding_bonus + target_opsec)

    # Roll for each hidden attribute
    reveals = []
    for attr in get_hidden_attributes(target, graph):
        if random() < intel_effectiveness * attr.reveal_difficulty_modifier:
            reveals.append(attr)
            # Promote from hidden to visible in player's information layer
            promote_to_visible(attr, org.player_id)

    # Detection check
    if random() < compute_detection_probability(mode, target, org, defines):
        # State gains intelligence about YOUR investigation
        events.append(SimulationEvent(
            type=EventType.COUNTER_DETECTION,
            payload={"investigator": org.id, "target": target.id},
        ))
        # May trigger state RESEARCH response

    # Counter-intel specifics
    if mode == "counter_intel":
        infiltration_assessment = compute_infiltration_risk(org, graph, defines)
        reveals.append({"type": "infiltration_assessment", "data": infiltration_assessment})

    return VerbResult(
        mutations=[],  # INVESTIGATE changes only the information layer, not the graph
        events=events,
        feedback=VerbFeedback(
            success=len(reveals) > 0,
            summary=f"Investigation {'revealed {len(reveals)} intelligence items' if reveals else 'yielded no actionable intelligence'}",
            details={"reveals": reveals, "detected": was_detected},
        ),
    )
```

### Key Design Point: INVESTIGATE Produces Zero Graph Mutations

INVESTIGATE is unique among all nine verbs: it does not modify the graph. No node attributes change. No edges are created, destroyed, or transformed. No consciousness shifts. No heat changes (unless detected — then the state's response creates heat).

What changes is the **information layer** — what the player can see. Hidden attributes become visible. Unknown edges become known. Fog of war lifts on the investigated target. This information then makes all other verbs more effective:

- EDUCATE with intelligence: you know which communities have high agitation (material_readiness), so you EDUCATE where it will land
- ATTACK with intelligence: you know the target's defensive capacity and extractive edge endpoints, so you hit where it hurts
- NEGOTIATE with intelligence: you know the ally's true resource state and consciousness, so you propose realistic terms
- MOBILIZE with intelligence: you know the state's attention thread allocation, so you mobilize where they're weakest

---

## The Build Org Triad as Game Strategy

### The Investment Thesis

Every tick spent on Build Org is a tick NOT spent on Project Power or Manage Resources. This is the strategic tension: building capacity vs. deploying it. The game's implicit argument is that most revolutionary failures come from projecting power before building sufficient organizational capacity:

- ATTACK without INVESTIGATE = shooting blind
- MOBILIZE without REPRODUCE = protest without organization
- AID without EDUCATE = charity without politics
- All power projection without Build Org = the ultra-left trap, the liberal trap, or the economism trap

The Build Org cycle is the investment that makes everything else work. But it has diminishing returns — an org that only builds and never acts loses relevance (the rightist trap: organizational conservatism, avoiding conflict, stagnant consciousness despite activity).

### The Cadre Bottleneck

CL (Cadre Labor) is the scarce resource that constrains the Build Org cycle. EDUCATE costs CL. Cadre training in REPRODUCE costs CL. Targeted INVESTIGATE costs CL. The only way to produce more CL is to grow cadre (REPRODUCE in cadre mode) — but that itself costs CL.

This creates a compounding investment dynamic: each cadre you train generates ~0.1 CL/tick permanently. Over 20 ticks, one cadre returns 2.0 CL — recovering the training cost and then some. Early investment in cadre training has outsized returns. Late investment is playing catch-up.

The player who spends early ticks on REPRODUCE (cadre) → EDUCATE → REPRODUCE (cadre) builds an exponentially growing CL base. The player who spends early ticks on MOBILIZE → ATTACK → AID has dramatic early results but runs out of CL and collapses when the state escalates.

### The Information Advantage

INVESTIGATE is the most under-valued verb because its outputs are invisible in the game state — no consciousness changed, no edges created, no heat generated. But information asymmetry is the strongest strategic advantage in the game:

- The state's primary advantage is information (surveillance, intelligence)
- INVESTIGATE is how the player contests that advantage
- Counter-intelligence is how the player protects their own information
- The org that knows and is not known has initiative

The DDoS effect from MOBILIZE works best when you KNOW where the state's attention threads are concentrated. The ATTACK target selection is most effective when you KNOW the target's defensive capacity. The NEGOTIATE alliance formation works best when you KNOW the potential ally's true interests.

---

## Verb Pairing Table: Build Org Triad

| Pairing | Effect | Strategic Meaning |
|---------|--------|-------------------|
| EDUCATE → REPRODUCE (cadre) | Consciousness-raised community produces better cadre. Higher r in recruitment pool → cadre are politically committed, not just organizationally useful | The study circle → party member pipeline |
| REPRODUCE (cadre) → EDUCATE | More cadre → more CL → more EDUCATE capacity. The compounding investment that makes everything else possible | Investing in the means of production of revolutionary labor |
| REPRODUCE (mass) → MOBILIZE | More sympathizers → more SL → larger mobilizations. Mass recruitment builds the numerical base for mass action | Building the army before the battle |
| INVESTIGATE → EDUCATE | Intelligence reveals which communities have high material_readiness. EDUCATE targeted by INVESTIGATE intel is more efficient — you're teaching where the ground is prepared | Reconnaissance before the political offensive |
| INVESTIGATE → ATTACK | Intelligence reveals target vulnerabilities. ATTACKs guided by INVESTIGATE intel are more effective and generate less collateral | The reconnaissance-strike complex |
| INVESTIGATE (counter-intel) → all | Knowing your OPSEC posture protects every other action. If you discover infiltration, you can purge before the state acts on their intelligence | The paranoia that keeps you alive |
| EDUCATE alone (no REPRODUCE) | Consciousness rises but org doesn't grow. You're raising awareness in a community but not converting that awareness into organizational power. Eventually, other orgs (including liberal/fascist ones) recruit from the pool you educated | The professor trap — teaching without organizing |
| REPRODUCE alone (no EDUCATE) | Org grows but members aren't politically developed. Coherence drops. The org is a crowd, not a movement. Vulnerable to co-optation and fragmentation | The influencer trap — numbers without politics |
| INVESTIGATE alone | Information accumulates but nothing is done with it. Analysis paralysis. The state may detect your investigation activity and respond before you act | The intelligence agency trap — knowing without acting |
