# EDUCATE Verb: API Endpoint Specification

**Parent Spec**: `043-consciousness-value-integration`, `037-player-verb-resolution`, `038-django-web-application-v3`
**Scope**: Two endpoints — the GET that populates the EDUCATE page, and the POST that submits the action
**Date**: 2026-04-10

---

## Why This Document Exists

The contract-first approach means we define the JSON shape before writing Django views or React components. This document IS the contract. A `curl` and `jq` can validate every claim. The React page consumes this JSON. The Django view produces it. The engine resolves it. Each layer can be built and tested independently.

EDUCATE is the first verb endpoint because consciousness is the backbone mechanic (spec 043). If this endpoint works, the pattern repeats for the other eight with verb-specific variations.

---

## Endpoint 1: GET Available EDUCATE Targets

### Route

```
GET /api/games/{game_id}/verbs/educate/?org_id={org_id}
```

### Purpose

Populate the EDUCATE page. Returns everything the player needs to choose a target and understand the projected effects before submitting. The frontend renders this as a form — dropdown of communities, consciousness state of each, credibility scores, cost preview, feedforward projections.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `org_id` | string (UUID) | Yes | The acting organization. Passed from the Organizations page when the player clicks "Educate" on an org card |

### Authorization

Session cookie required. The `org_id` must belong to a player-controlled organization in this game session. Returns 403 if the org exists but isn't the player's. Returns 404 if the org doesn't exist.

### Response: 200 OK

```json
{
  "status": "ok",
  "tick": 14,
  "verb": "educate",
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
    },
    "cadre_level": 0.65,
    "cohesion": 0.78
  },
  "cost": {
    "action_points": 1,
    "cadre_labor": 3.0,
    "sympathizer_labor": 0.0,
    "material": 0.0,
    "can_afford": true,
    "over_budget": false,
    "over_budget_penalty": null
  },
  "targets": [
    {
      "community_id": "community-new-afrikan-wayne",
      "community_type": "NEW_AFRIKAN",
      "category": "contradiction_pair",
      "territory_name": "Wayne County",
      "territory_id": "territory-26163",
      "credibility": 0.72,
      "credibility_explanation": "72% membership overlap — 34 of 47 cadre are members of this community",
      "consciousness": {
        "r": 0.25,
        "l": 0.55,
        "f": 0.20,
        "dominant_tendency": "liberal",
        "collective_identity": 0.25,
        "ideological_contestation": 0.82
      },
      "material_readiness": {
        "avg_agitation": 0.45,
        "readiness_score": 1.0,
        "readiness_explanation": "Agitation above education threshold (0.30) — material conditions have prepared the ground. Education will land."
      },
      "education_pressure": {
        "current": 0.12,
        "projected_delta": 0.036,
        "projected_new": 0.156,
        "decay_per_tick": 0.012
      },
      "feedforward": {
        "projected_routing_shift": {
          "r_gain_per_tick": 0.008,
          "f_reduction_per_tick": 0.005,
          "l_reduction_per_tick": 0.003,
          "explanation": "With current agitation (0.45) and solidarity infrastructure (3 solidaristic edges), increased education pressure will shift ~0.8% of consciousness toward revolutionary tendency per tick"
        },
        "state_ai_visibility": "medium",
        "state_ai_likely_response": "RESEARCH — state will attempt to map your ideological network",
        "turns_to_dominant_tendency_shift": 18,
        "turns_explanation": "At current education rate with sustained agitation, revolutionary tendency could become dominant in ~18 ticks. This assumes no state CO-OPT or REPRESS intervention."
      }
    },
    {
      "community_id": "community-women-wayne",
      "community_type": "WOMEN",
      "category": "contradiction_pair",
      "territory_name": "Wayne County",
      "territory_id": "territory-26163",
      "credibility": 0.41,
      "credibility_explanation": "41% membership overlap — 19 of 47 cadre are members of this community",
      "consciousness": {
        "r": 0.15,
        "l": 0.70,
        "f": 0.15,
        "dominant_tendency": "liberal",
        "collective_identity": 0.15,
        "ideological_contestation": 0.58
      },
      "material_readiness": {
        "avg_agitation": 0.22,
        "readiness_score": 0.73,
        "readiness_explanation": "Agitation below education threshold (0.30) — material conditions have not fully prepared the ground. Education will have reduced effect (73% effectiveness)."
      },
      "education_pressure": {
        "current": 0.03,
        "projected_delta": 0.015,
        "projected_new": 0.045,
        "decay_per_tick": 0.003
      },
      "feedforward": {
        "projected_routing_shift": {
          "r_gain_per_tick": 0.002,
          "f_reduction_per_tick": 0.001,
          "l_reduction_per_tick": 0.001,
          "explanation": "Low agitation (0.22) limits routing effect. Education pressure will accumulate but won't produce significant consciousness shift until material conditions deteriorate further."
        },
        "state_ai_visibility": "low",
        "state_ai_likely_response": "None — below surveillance threshold",
        "turns_to_dominant_tendency_shift": null,
        "turns_explanation": "Cannot estimate — material conditions insufficient for sustained shift"
      }
    }
  ],
  "unavailable_communities": [
    {
      "community_id": "community-settler-oakland",
      "community_type": "SETTLER",
      "territory_name": "Oakland County",
      "reason": "No membership overlap — your organization has zero members in this community. Credibility ≈ 0."
    }
  ]
}
```

### Response Field Semantics

**`acting_org`**: Frozen snapshot of the org at the moment the page loads. `cadre_level` and `cohesion` are the multipliers that affect EDUCATE effectiveness (spec 043: `education_delta = base_effect × credibility × material_readiness × cadre_level × cohesion`). Showing these lets the player understand why their education effort is strong or weak.

**`cost`**: EDUCATE costs 1 AP and Cadre Labor (CL). CL cost is a GameDefines constant (`EDUCATE_CL_COST`). `can_afford` = true if org has enough AP and CL. `over_budget` = true if AP exceeded but action still resolves with degraded effectiveness (Constitution I.11: never refuse a verb). `over_budget_penalty` describes the degradation if applicable.

**`targets`**: Array of valid communities. A community is a valid target if: (a) it exists in a territory where the org has presence, AND (b) the org has nonzero membership overlap (credibility > 0). Sorted by credibility descending — highest-impact targets first. Each target includes:

- **`credibility`**: Float [0, 1]. Org's membership overlap with the community. The Gramscian organic intellectual requirement — you can't educate a community from outside it. Computed from XGI hyperedge intersection.

- **`consciousness`**: The community's current TernaryConsciousness (r/l/f simplex). This is what the player is trying to shift. `ideological_contestation` (Shannon entropy of r/l/f) indicates how contested the community's direction is — high contestation means the community is in active ideological struggle, which means EDUCATE can have more impact.

- **`material_readiness`**: From spec 043. `avg_agitation` is the mean agitation across population nodes that are members of this community in this territory. `readiness_score` = min(1.0, avg_agitation / AGITATION_EDUCATION_THRESHOLD). When < 1.0, EDUCATE effectiveness is proportionally reduced — you're teaching theory that doesn't match lived experience.

- **`education_pressure`**: Current accumulated education effects on this community, the projected increase from this action, and the per-tick decay rate. Lets the player see whether they're building on past EDUCATE actions or starting from scratch.

- **`feedforward`**: The projected effects of choosing this target. NOT a promise — a projection based on current conditions. Includes: routing shift estimates (how much r/l/f will change per tick if agitation holds), state AI visibility and likely response, and a rough estimate of how many ticks until the dominant tendency could shift. The `turns_to_dominant_tendency_shift` can be null if conditions are insufficient.

**`unavailable_communities`**: Communities in the game world that this org CANNOT target, with reasons. Transparency: the player sees what's blocked and why. Important for strategic planning — you might need to REPRODUCE (recruit members from this community) before you can EDUCATE within it.

### Response: 400 Bad Request

```json
{
  "status": "error",
  "error": "org_id is required",
  "code": "MISSING_PARAMETER"
}
```

### Response: 403 Forbidden

```json
{
  "status": "error",
  "error": "Organization 'org-fbi-detroit' is not player-controlled",
  "code": "NOT_PLAYER_ORG"
}
```

---

## Endpoint 2: POST Submit EDUCATE Action

### Route

```
POST /api/games/{game_id}/verbs/educate/
```

### Purpose

Queue an EDUCATE action for tick resolution. Does NOT resolve the action immediately — it queues it. Resolution happens when the player hits "End Turn" (POST to `/api/games/{game_id}/resolve/`). This allows the player to queue one action per org, review all queued actions, and then resolve the full tick.

### Request Body

```json
{
  "org_id": "org-detroit-freedom-school",
  "target_community_id": "community-new-afrikan-wayne",
  "params": {}
}
```

**`org_id`**: The acting organization. Must be player-controlled, must have AP remaining.

**`target_community_id`**: The target community hyperedge. Must be a valid target (nonzero credibility, in a territory where org has presence).

**`params`**: Reserved for future sub-verb selection (study_circle vs mass_rally vs media_campaign). Empty object for MVP. The endpoint accepts and stores it but ignores contents during resolution.

### Validation (Django Serializer)

The serializer validates:

1. `org_id` exists and belongs to `request.user` in this game session
2. `target_community_id` exists in the game's hypergraph
3. The org has presence in a territory where this community exists
4. The org has nonzero membership overlap with this community (credibility > 0)
5. The org has not already queued an action for this tick (uniqueness: game + tick + org_id)
6. The org has sufficient AP (or if over-budget, flag for degraded resolution)

Validation does NOT check CL budget. Constitution I.11: never refuse a verb. If CL is insufficient, the action resolves with degraded effectiveness, and the `ActionResult` records why.

### Response: 201 Created

```json
{
  "status": "ok",
  "action": {
    "id": "action-uuid-here",
    "tick": 14,
    "org_id": "org-detroit-freedom-school",
    "verb": "educate",
    "target_id": "community-new-afrikan-wayne",
    "params": {},
    "queued_at": "2026-04-10T15:30:00Z",
    "cost_estimate": {
      "action_points": 1,
      "cadre_labor": 3.0,
      "over_budget": false
    }
  },
  "org_status": {
    "action_points_remaining": 1,
    "has_pending_action": true,
    "can_queue_more": false
  },
  "message": "EDUCATE action queued. Detroit Freedom School will conduct political education within the New Afrikan community in Wayne County when the tick resolves."
}
```

**`action`**: The queued action record. Mirrors the `PlayerAction` Django model. The `cost_estimate` is computed at queue time but costs are actually deducted during resolution (conditions may change if multiple orgs act in the same tick).

**`org_status`**: Updated org state after queuing. `has_pending_action` = true means this org has a queued action. `can_queue_more` reflects whether the org has more AP for additional actions (post-MVP: multi-action orgs).

**`message`**: Human-readable confirmation. The frontend displays this. Written in the game's voice — not "Action submitted successfully" but a description of what the org is doing.

### Response: 409 Conflict

```json
{
  "status": "error",
  "error": "Organization 'Detroit Freedom School' already has a pending action for tick 14",
  "code": "ACTION_ALREADY_QUEUED",
  "existing_action": {
    "id": "action-existing-uuid",
    "verb": "educate",
    "target_id": "community-new-afrikan-wayne"
  }
}
```

The player must DELETE the existing action before queuing a new one. Endpoint for that:

```
DELETE /api/games/{game_id}/actions/{action_id}/
```

### Response: 422 Unprocessable Entity

```json
{
  "status": "error",
  "error": "Organization has zero membership overlap with target community 'SETTLER' in Oakland County. Credibility ≈ 0 — you cannot educate a community you are not embedded in.",
  "code": "ZERO_CREDIBILITY"
}
```

---

## Endpoint 3: Resolution (Part of Tick Resolution Pipeline)

The EDUCATE action is not resolved by its own endpoint. It resolves when the player POSTs to:

```
POST /api/games/{game_id}/resolve/
```

This triggers the full tick resolution pipeline. EDUCATE resolution happens in the Action Phase, after Layer 0 economic metabolism.

### EDUCATE Resolution Logic

```python
def resolve_educate(
    action: PlayerAction,
    graph: GraphProtocol,
    hypergraph: xgi.Hypergraph,
    defines: ConsciousnessDefines,
) -> VerbResult:
    """Resolve a queued EDUCATE action.

    Graph operation: Increase education_pressure on target community.
    Does NOT directly modify consciousness (r/l/f). Education pressure
    modifies the ROUTING of agitation to consciousness in Layer 3.

    Per spec 043: EDUCATE builds interpretive capacity that determines
    how accumulated material experience (agitation) routes through the
    r/l/f simplex. Education without agitation is weak. Agitation
    without education routes to fascism.
    """
    org = graph.get_node(action.org_id)
    community = hypergraph.get_hyperedge(action.target_id)

    # 1. Compute credibility (Gramsci's organic intellectual gate)
    credibility = compute_community_overlap(org, community, hypergraph)
    # credibility was validated > 0 at queue time, but recheck

    # 2. Compute material readiness (Mao's practice-first epistemology)
    pop_nodes = get_population_nodes_in_community(
        community, org.territory_id, graph
    )
    avg_agitation = mean(n.material_conditions.agitation for n in pop_nodes)
    material_readiness = min(
        1.0,
        avg_agitation / defines.agitation_education_threshold
    )

    # 3. Compute resource cost and deduct
    cl_cost = defines.educate_cl_cost
    ap_cost = 1

    over_budget_factor = 1.0
    if org.resources.cadre_labor < cl_cost:
        # Over budget: resolve with degraded effectiveness
        over_budget_factor = org.resources.cadre_labor / cl_cost
        cl_spent = org.resources.cadre_labor  # Spend everything
    else:
        cl_spent = cl_cost

    deduct_resources(org, cadre_labor=cl_spent, action_points=ap_cost)

    # 4. Compute education delta
    education_delta = (
        defines.educate_base_effect
        * credibility
        * material_readiness
        * org.cadre_level
        * org.cohesion
        * over_budget_factor
    )

    # 5. Apply to community education_pressure
    # This is the ONE atomic graph mutation for this verb
    old_pressure = community.education_pressure
    community.education_pressure += education_delta

    # 6. Compute consciousness side-effect direction
    # (Does NOT modify r/l/f directly — that happens in Layer 3 routing)
    tendency = org.consciousness_strategy  # REVOLUTIONARY, LIBERAL, FASCIST

    # 7. Generate state AI signal
    visibility = compute_educate_visibility(
        org, community, education_delta, defines
    )

    # 8. Build result
    return VerbResult(
        mutations=[
            GraphMutation(
                target_type="community_hyperedge",
                target_id=community.id,
                field="education_pressure",
                old_value=old_pressure,
                new_value=community.education_pressure,
            )
        ],
        events=[
            SimulationEvent(
                type=EventType.CONSCIOUSNESS_TRANSMISSION,
                payload={
                    "org_id": org.id,
                    "community_id": community.id,
                    "education_delta": education_delta,
                    "tendency": tendency.value,
                    "credibility": credibility,
                    "material_readiness": material_readiness,
                },
            )
        ],
        ap_spent=ap_cost,
        resources_spent={"cadre_labor": cl_spent},
        feedback=VerbFeedback(
            success=True,
            summary=f"Political education conducted within {community.display_name}",
            details={
                "education_pressure_added": education_delta,
                "credibility": credibility,
                "material_readiness": material_readiness,
                "over_budget": over_budget_factor < 1.0,
                "state_visibility": visibility,
            },
        ),
    )
```

### What Happens in Layer 3

After all Action Phase verbs resolve, Layer 3 propagates consequences. For EDUCATE, the relevant Layer 3 effect is:

1. `education_pressure` on the target community has been increased (verb effect)
2. The agitation routing formula (spec 043) uses `education_pressure` to shift how agitation flows through the r/l/f simplex
3. Higher `education_pressure` → more agitation routes to r, less to f
4. But if `avg_agitation ≈ 0`, there's nothing to route — education pressure accumulates waiting for material crisis
5. `education_pressure` decays by `education_pressure_decay` per tick — sustained organizing required

The consciousness change is NOT attributed to the EDUCATE action in the `ActionResult`. It shows up in the tick results as a consequence of the full agitation routing computation, which integrates ALL inputs (material conditions, solidarity edges, education pressure, state co-optation). EDUCATE is one input among several. The player sees "consciousness shifted" in the results, with attribution to contributing factors.

---

## Tick Results: EDUCATE Feedback

After tick resolution, the EDUCATE action's outcome appears in:

```
GET /api/games/{game_id}/results/{tick}/
```

Within the `action_outcomes` array:

```json
{
  "action_id": "action-uuid-here",
  "verb": "educate",
  "org_name": "Detroit Freedom School",
  "target_name": "New Afrikan community, Wayne County",
  "success": true,
  "costs_paid": {
    "action_points": 1,
    "cadre_labor": 3.0
  },
  "effects": {
    "education_pressure_added": 0.036,
    "education_pressure_total": 0.156,
    "credibility_used": 0.72,
    "material_readiness": 1.0,
    "consciousness_attribution": {
      "this_action_contributed": true,
      "community_consciousness_before": {"r": 0.25, "l": 0.55, "f": 0.20},
      "community_consciousness_after": {"r": 0.258, "l": 0.547, "f": 0.195},
      "other_contributing_factors": [
        "Agitation from s/v increase (Δ = +0.03)",
        "3 solidaristic edges provided routing infrastructure",
        "State RESEARCH action increased surveillance of this community"
      ]
    }
  },
  "state_response": {
    "triggered": true,
    "response_verb": "RESEARCH",
    "response_description": "FBI Detroit field office opened an ideological assessment file on political education activities within the New Afrikan community.",
    "new_threat_level": "surveilled"
  },
  "narrative": "The Freedom School's weekly study circle drew 23 attendees this week — up from 14 last month. The discussion centered on wage theft in the auto parts supply chain. Three attendees asked for copies of the reading list. Meanwhile, a new face in the back row took careful notes but asked no questions."
}
```

### Narrative Generation

The `narrative` field is generated by the AI narrative layer (if enabled) or is null/empty if disabled. The narrative is generated FROM the mechanical results, never determines them (Constitution II.7: AI Observes, Never Controls). The narrative layer receives the `VerbResult` and `ActionResult` and produces flavor text. For EDUCATE, the narrative should evoke study circles, freedom schools, consciousness-raising groups — the historical grounding cited in the spec-kit prompt.

---

## Mock Fixture

For contract-first development, the React page is built against this mock fixture before the Django endpoint exists.

```json
// File: frontend/src/mocks/educate.json
{
  "status": "ok",
  "tick": 14,
  "verb": "educate",
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
    },
    "cadre_level": 0.65,
    "cohesion": 0.78
  },
  "cost": {
    "action_points": 1,
    "cadre_labor": 3.0,
    "sympathizer_labor": 0.0,
    "material": 0.0,
    "can_afford": true,
    "over_budget": false,
    "over_budget_penalty": null
  },
  "targets": [
    {
      "community_id": "community-new-afrikan-wayne",
      "community_type": "NEW_AFRIKAN",
      "category": "contradiction_pair",
      "territory_name": "Wayne County",
      "territory_id": "territory-26163",
      "credibility": 0.72,
      "credibility_explanation": "72% membership overlap",
      "consciousness": {
        "r": 0.25, "l": 0.55, "f": 0.20,
        "dominant_tendency": "liberal",
        "collective_identity": 0.25,
        "ideological_contestation": 0.82
      },
      "material_readiness": {
        "avg_agitation": 0.45,
        "readiness_score": 1.0,
        "readiness_explanation": "Material conditions have prepared the ground."
      },
      "education_pressure": {
        "current": 0.12,
        "projected_delta": 0.036,
        "projected_new": 0.156,
        "decay_per_tick": 0.012
      },
      "feedforward": {
        "projected_routing_shift": {
          "r_gain_per_tick": 0.008,
          "f_reduction_per_tick": 0.005,
          "l_reduction_per_tick": 0.003,
          "explanation": "Education will shift ~0.8% toward revolutionary tendency per tick"
        },
        "state_ai_visibility": "medium",
        "state_ai_likely_response": "RESEARCH",
        "turns_to_dominant_tendency_shift": 18,
        "turns_explanation": "~18 ticks assuming sustained effort"
      }
    },
    {
      "community_id": "community-women-wayne",
      "community_type": "WOMEN",
      "category": "contradiction_pair",
      "territory_name": "Wayne County",
      "territory_id": "territory-26163",
      "credibility": 0.41,
      "credibility_explanation": "41% membership overlap",
      "consciousness": {
        "r": 0.15, "l": 0.70, "f": 0.15,
        "dominant_tendency": "liberal",
        "collective_identity": 0.15,
        "ideological_contestation": 0.58
      },
      "material_readiness": {
        "avg_agitation": 0.22,
        "readiness_score": 0.73,
        "readiness_explanation": "Material conditions have not fully prepared the ground."
      },
      "education_pressure": {
        "current": 0.03,
        "projected_delta": 0.015,
        "projected_new": 0.045,
        "decay_per_tick": 0.003
      },
      "feedforward": {
        "projected_routing_shift": {
          "r_gain_per_tick": 0.002,
          "f_reduction_per_tick": 0.001,
          "l_reduction_per_tick": 0.001,
          "explanation": "Low agitation limits effect"
        },
        "state_ai_visibility": "low",
        "state_ai_likely_response": "None",
        "turns_to_dominant_tendency_shift": null,
        "turns_explanation": "Material conditions insufficient"
      }
    }
  ],
  "unavailable_communities": [
    {
      "community_id": "community-settler-oakland",
      "community_type": "SETTLER",
      "territory_name": "Oakland County",
      "reason": "No membership overlap — credibility ≈ 0"
    }
  ]
}
```

### Contract Parity Test

When the Django endpoint is built, validate with:

```bash
# 1. Fetch from mock
MOCK=$(cat frontend/src/mocks/educate.json)

# 2. Fetch from Django
LIVE=$(curl -s -b session.cookie \
  "http://localhost:8000/api/games/${GAME_ID}/verbs/educate/?org_id=${ORG_ID}")

# 3. Compare structure (ignore values, check keys and types)
diff <(echo "$MOCK" | jq 'keys_unsorted') \
     <(echo "$LIVE" | jq 'keys_unsorted')

# 4. Deep structural comparison
diff <(echo "$MOCK" | jq '[paths | join(".")]' | sort) \
     <(echo "$LIVE" | jq '[paths | join(".")]' | sort)
```

If these diffs are empty, the contract holds. React doesn't care whether data comes from mock or Django — it renders the same JSON shape either way.

---

## Django Implementation Sketch

### Serializer

```python
class EducateTargetSerializer(serializers.Serializer):
    community_id = serializers.CharField()
    community_type = serializers.CharField()
    category = serializers.CharField()
    territory_name = serializers.CharField()
    territory_id = serializers.CharField()
    credibility = serializers.FloatField()
    credibility_explanation = serializers.CharField()
    consciousness = TernaryConsciousnessSerializer()
    material_readiness = MaterialReadinessSerializer()
    education_pressure = EducationPressureSerializer()
    feedforward = FeedforwardSerializer()


class EducateAvailableSerializer(serializers.Serializer):
    status = serializers.CharField()
    tick = serializers.IntegerField()
    verb = serializers.CharField()
    acting_org = OrgSummarySerializer()
    cost = VerbCostSerializer()
    targets = EducateTargetSerializer(many=True)
    unavailable_communities = UnavailableCommunitySerializer(many=True)


class EducateSubmitSerializer(serializers.Serializer):
    org_id = serializers.CharField()
    target_community_id = serializers.CharField()
    params = serializers.DictField(required=False, default=dict)

    def validate_org_id(self, value):
        game = self.context["game"]
        user = self.context["request"].user
        # Check org exists, is player-controlled, has AP
        ...

    def validate_target_community_id(self, value):
        # Check community exists, org has credibility > 0
        ...

    def validate(self, data):
        # Check no existing action for this org this tick
        ...
```

### View

```python
class EducateVerbView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id):
        """Return available EDUCATE targets for an org."""
        game = get_object_or_404(GameSession, id=game_id, created_by=request.user)
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response(
                {"status": "error", "error": "org_id required", "code": "MISSING_PARAMETER"},
                status=400,
            )

        bridge = EngineBridge(game)
        data = bridge.get_educate_targets(org_id)
        serializer = EducateAvailableSerializer(data)
        return Response(serializer.data)

    def post(self, request, game_id):
        """Queue an EDUCATE action."""
        game = get_object_or_404(GameSession, id=game_id, created_by=request.user)
        serializer = EducateSubmitSerializer(
            data=request.data,
            context={"game": game, "request": request},
        )
        serializer.is_valid(raise_exception=True)

        action = PlayerAction.objects.create(
            game=game,
            tick=game.current_tick,
            organization_id=serializer.validated_data["org_id"],
            verb="educate",
            target_id=serializer.validated_data["target_community_id"],
            parameters=serializer.validated_data.get("params", {}),
        )

        return Response(
            {
                "status": "ok",
                "action": PlayerActionSerializer(action).data,
                "org_status": bridge.get_org_status(action.organization_id),
                "message": build_educate_message(action),
            },
            status=201,
        )
```

### URL Pattern

```python
# web/game/urls.py
urlpatterns = [
    ...
    path(
        "api/games/<uuid:game_id>/verbs/educate/",
        EducateVerbView.as_view(),
        name="verb-educate",
    ),
]
```

---

## Pattern for Other Verbs

This endpoint pattern repeats for all nine verbs. What changes per verb:

| Verb | Target Type | Target Selection UI | Verb-Specific Fields |
|------|------------|--------------------|--------------------|
| Educate | Community hyperedge | Dropdown | consciousness, material_readiness, education_pressure, feedforward |
| Reproduce | Self (org) + territory | Territory dropdown + mode toggle (cadre/mass) | recruitment_pool, quality_vs_quantity, coherence_impact |
| Investigate | Org / territory / institution | Dropdown or map click | known_vs_hidden, investigation_depth, detection_risk |
| Attack | Org / institution | Dropdown | combat_ratio, heat_projection, opsec_risk |
| Mobilize | Territory | Map click | sympathizer_base, projected_turnout, solidarity_multiplier, backfire_probability |
| Campaign | Institution | Dropdown | factional_balance, projected_shift, legitimacy_cost |
| Aid | Territory / org | Map click or dropdown | material_transfer, edge_mode_projection |
| Move | Territory | Map click | origin, destination, what_moves |
| Negotiate | Org / institution | Dropdown | current_edge_mode, possible_transitions, bilateral_interests |

Each verb gets its own `GET /api/games/{id}/verbs/{verb}/` and `POST /api/games/{id}/verbs/{verb}/` with the same structural pattern (acting_org, cost, targets, feedforward) but verb-specific target serialization and feedforward computation.

---

## What Claude Code Needs to Know

1. **The mock fixture is the contract.** Build the React page against it first. Build the Django endpoint second. Validate contract parity with `jq` diff.

2. **EDUCATE does not modify consciousness directly.** It modifies `education_pressure` on a community hyperedge. Consciousness changes happen in Layer 3 via the agitation routing formula (spec 043). This is a critical architectural distinction — the endpoint resolves one graph mutation, and the consequences propagate separately.

3. **The feedforward is a projection, not a promise.** It's computed from current conditions and will change if conditions change. The frontend should present it as "at current rates" language, not guarantees.

4. **Validation rejects only structural impossibilities.** Zero credibility = reject (422). Insufficient CL = accept with degradation. Constitution I.11: never refuse a verb for resource reasons.

5. **The narrative field in tick results comes from the AI layer and is optional.** Engine resolution is complete without it. AI failure is non-fatal (Constitution II.7).
