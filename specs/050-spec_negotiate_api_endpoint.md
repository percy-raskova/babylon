# NEGOTIATE Verb: API Endpoint Specification

**Parent Spec**: `043-consciousness-value-integration`, `037-player-verb-resolution`
**Date**: 2026-04-10

---

## Theoretical Grounding: NEGOTIATE and the Edge Mode State Machine

NEGOTIATE is the only player verb with bilateral resolution — the counterparty must agree. Every other verb is unilateral. This makes NEGOTIATE fundamentally different: its success depends not on the player's capacity alone but on the alignment (or coercion) of interests between two actors.

### NEGOTIATE's Domain: Edge Modes

NEGOTIATE directly manipulates the edge mode state machine:

```
No relationship → TRANSACTIONAL:           NEGOTIATE creates initial contact
EXTRACTIVE → TRANSACTIONAL:                NEGOTIATE converts exploitation into exchange
ANTAGONISTIC → TRANSACTIONAL:              NEGOTIATE de-escalates conflict (bilateral pressure required)
TRANSACTIONAL + sustained AID + EDUCATE → SOLIDARISTIC: NOT via NEGOTIATE alone
```

NEGOTIATE creates TRANSACTIONAL edges and de-escalates ANTAGONISTIC edges. It CANNOT create SOLIDARISTIC edges directly — those require material solidarity (AID) and shared consciousness (EDUCATE). Solidarity cannot be declared into existence; it must be built through practice. NEGOTIATE formalizes what AID + EDUCATE have already built materially.

### The United Front (Mao)

Three types of alliance, each with different durability:

**Strategic** (revolutionary + revolutionary): Edge can progress to SOLIDARISTIC through sustained AID + EDUCATE. Most durable. The state fears this most.

**Tactical** (revolutionary + liberal): Edge stays TRANSACTIONAL. Useful for coordination but the liberal ally is vulnerable to state CO-OPT. If the state bribes them, the edge may degrade to CO-OPTIVE.

**Temporary** (revolutionary + hostile org, under shared extreme threat): Edge de-escalated from ANTAGONISTIC to TRANSACTIONAL. Lasts only while the shared threat persists. When the threat passes, edge drifts back toward ANTAGONISTIC.

### Bilateral Resolution: Interest + Leverage

Success probability = f(interest_alignment, leverage).

**Interest alignment**: Computed from shared enemies, shared communities, compatible consciousness strategies, and compatible material interests. A revolutionary org and a liberal org have moderate interest alignment (shared enemies, divergent goals). A revolutionary org and a fascist org have near-zero alignment.

**Leverage**: Computed from demonstrated capacity — MOBILIZE history (mass base), ATTACK history (willingness to use force), solidarity edge count (network strength), and reputation. An org with zero demonstrated capacity cannot negotiate because it has nothing to offer or threaten. This creates the natural sequence: build power → THEN negotiate from strength.

For institutional targets, leverage is weighted much more heavily than interest (institutions respond to power, not shared values).

### The State Fears Coordination

Alliance formation triggers CO-OPT responses. The state fears coordinated networks more than individual orgs because networks can saturate attention threads (DDoS). When NEGOTIATE creates an org-org edge, the state's threat model updates. Revolutionary + revolutionary alliance → `organization_threat` spikes. Revolutionary + liberal alliance → state may try CO-OPT:DIVIDE to break the alliance by peeling off the weaker ally.

### NEGOTIATE Can Fail

Failure costs only the AP spent. But failure reveals your interest in the relationship, which the state may observe ("they're trying to build alliances — increase surveillance"). And repeated failed negotiations damage reputation with the target ("they keep asking, we keep saying no").

---

## GET Endpoint

```
GET /api/games/{game_id}/verbs/negotiate/?org_id={org_id}
```

Returns: org leverage assessment, available targets (orgs and institutions) with interest alignment scores, existing edge states, negotiation proposals per target with success probabilities, alliance type predictions, betrayal risk assessments, state response projections, and de-escalation opportunities for ANTAGONISTIC edges.

Key fields per target:

- **interest_alignment.score**: Float [0,1]. How much interests overlap. Broken down into shared_interests and divergent_interests with natural-language explanations.
- **interest_alignment.alliance_type**: "strategic", "tactical", "temporary", or "impossible_under_current_conditions". Determines the durability of any resulting edge.
- **negotiation_options[]**: Array of specific proposals, each with success probability, edge effect, state response prediction, and betrayal risk.
- **betrayal_risk**: How likely the alliance degrades. Factors: target's vulnerability to state CO-OPT, material dependency on institutional funding, consciousness strategy divergence.
- **de_escalation_targets**: Orgs with ANTAGONISTIC edges that could be de-escalated. Shows what caused the antagonism and what reconciliation would require.

## POST Endpoint

```
POST /api/games/{game_id}/verbs/negotiate/
```

```json
{
  "org_id": "org-detroit-freedom-school",
  "target_id": "org-wayne-mutual-aid-network",
  "params": { "proposal": "coordination_pact" }
}
```

**params.proposal**: Which proposal from the GET response to present. Each proposal has different mechanics: `coordination_pact` (enables DDoS mobilization), `resource_sharing` (bidirectional resource flow), `ceasefire` (de-escalate ANTAGONISTIC), `demand_policy_change` (institutional target), `reconciliation` (repair damaged relationship).

**Costs**: 1 AP. No CL, SL, or material cost. Diplomacy is free in material terms.

**Validation**: Org and target exist, proposal is valid for this target pair, no existing action this tick. For institutions, leverage check warns but doesn't refuse (Constitution I.11).

## Resolution Logic

1. Compute interest alignment between org and target
2. Compute org's leverage (from MOBILIZE history, ATTACK history, solidarity edges, reputation)
3. Success probability = weighted combination of interest and leverage
4. Resolution roll: random() < success_probability
5. If success and no existing edge → create TRANSACTIONAL edge with alliance metadata
6. If success and ANTAGONISTIC edge → de-escalate to TRANSACTIONAL (discrete event per Constitution I.7)
7. If success and existing TRANSACTIONAL edge → strengthen (increment solidarity_accumulation, apply proposal effects)
8. If coordination_pact → register both orgs as coordination partners (enables future simultaneous MOBILIZE)
9. If failure → no edge change. State may detect the negotiation attempt.
10. Emit ALLIANCE_FORMED or NEGOTIATION_FAILED event for state AI processing

**The bilateral constraint**: NPC orgs evaluate proposals against their own interest function. A liberal NPC org accepts alliances against state repression but rejects revolutionary framing. A fascist NPC org rejects almost everything. An NPC org currently being CO-OPTed by the state rejects alliance with revolutionary orgs (the state's bribe is more attractive). The player cannot force alliances — only create conditions where alliance is rational for the counterparty.

**Edge mode transition**: NEGOTIATE respects Anti-Pattern VIII.1 (no skipping). ANTAGONISTIC → TRANSACTIONAL is the maximum single-action de-escalation. TRANSACTIONAL → SOLIDARISTIC requires sustained AID + EDUCATE, not additional NEGOTIATE.

## GameDefines

```python
class NegotiateDefines(BaseModel):
    interest_weight: float = Field(default=0.6)
    leverage_weight: float = Field(default=0.4)
    institutional_leverage_weight: float = Field(default=0.8)
    negotiate_solidarity_increment: float = Field(default=0.05)
    betrayal_base_rate: float = Field(default=0.05)
    leverage_threshold_for_institutions: float = Field(default=0.50)
```

---

## Relationship to Other Verbs

| Pairing | Effect |
|---------|--------|
| AID → NEGOTIATE | Material support creates basis for alliance. Orgs you've AIDed are more likely to accept proposals |
| NEGOTIATE → MOBILIZE | Coordination pact enables DDoS. The strategic payoff of alliance building |
| NEGOTIATE → AID (to allied org) | Alliance enables resource sharing. Your CL can teach in their programs; their SL augments your mobilizations |
| MOBILIZE → NEGOTIATE (with institution) | Demonstrated mass base creates leverage for institutional demands. Project power first, then negotiate from strength |
| INVESTIGATE → NEGOTIATE | Intelligence reveals target's true interests, vulnerability to CO-OPT, and betrayal risk. Negotiate with information |
| CAMPAIGN → NEGOTIATE (with institution) | CAMPAIGN builds institutional legitimacy. NEGOTIATE from institutional position. But this is the liberal trap sequence — you're playing the institution's game |
| EDUCATE in shared community → NEGOTIATE | Education builds the ideological basis for strategic (not just tactical) alliance. Orgs whose communities share high r can negotiate toward SOLIDARISTIC partnership |
| State CO-OPT:DIVIDE → NEGOTIATE (repair) | When the state breaks your alliance, NEGOTIATE can attempt repair. But the trust deficit makes success probability lower. Sustained AID rebuilds the material basis for renewed alliance |
