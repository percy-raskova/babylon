# Article V: Action Vocabulary

> Annex to [Babylon Constitution](../constitution.md). This file contains the full verb definitions, groupings, and implementation requirements for both the player and the state AI.

## Player Verbs

The player interacts with the simulation through nine verbs. These verbs are exhaustive—every player action maps to exactly one verb. Every verb maps to a specific graph operation.

### The Nine Verbs

| Verb | Domain | Description |
| --------------- | -------------------- | --------------------------------------------------------------------------- |
| **Educate** | Political education | Consciousness-raising, propaganda, agitation, ideological development |
| **Aid** | Mutual support | Mutual aid, material support, reproduction cost reduction for base |
| **Attack** | Armed action | Ambushes, guerrilla operations, retributive strikes |
| **Mobilize** | Mass action | Rallies, strikes, demonstrations, protests, boycotts |
| **Campaign** | Electoral action | Reformist political engagement, legislative pressure |
| **Move** | Logistics | Relocate cadre, allocate resources, supply lines, infrastructure, fundraising, expropriation |
| **Investigate** | Intelligence | Reconnaissance, counter-surveillance, assessing conditions |
| **Reproduce** | Recruitment | Training, cadre development, converting sympathizers → members → cadre |
| **Negotiate** | Diplomacy | United fronts, coalitions, alliances, ceasefires, inter-organizational agreements |

### Strategic Function Grouping (Player-Facing)

The player's mental model organizes verbs by strategic purpose:

| Function | Verbs | Purpose |
| ----------------------------------------- | -------------------------------- | -------------------------------------------- |
| **Build your organization** | Educate, Reproduce, Investigate | Internal capacity development |
| **Project power** | Attack, Mobilize, Campaign | External action against targets |
| **Manage relationships and resources** | Aid, Move, Negotiate | Logistics, alliances, material support |

This is the grouping the UI presents. Three groups of three.

### Target Type Grouping (Engine-Facing)

The engine processes verbs by what part of the graph they modify:

| Target | Verbs | Graph Operation |
| ----------------------- | -------------------------------- | ------------------------------------------------------------------- |
| **Your organization** | Reproduce, Move, Investigate | Modify agent's internal state (node attributes) |
| **Populations** | Educate, Aid, Mobilize | Modify edges between organization and social class nodes |
| **Other actors** | Attack, Campaign, Negotiate | Modify edges between organizations or between organization and state |

This grouping determines implementation. Each target type maps to a distinct graph operation:

- **Organization verbs** mutate the player's agent node (cadre count, resource allocation, intelligence level)
- **Population verbs** create, strengthen, or transform edges between the organization and class nodes (consciousness transmission, solidarity building, mass mobilization)
- **Other-actor verbs** create, modify, or destroy edges between organizational nodes (alliances, hostilities, negotiations with state or rival organizations)

### Player Verb Implementation Requirements

1. **Both groupings are true simultaneously.** The strategic grouping (build/project/manage) is what the player sees in the UI. The target grouping (org/population/actor) is how the engine processes them.

1. **Every verb MUST map to a graph operation.** No verb produces effects outside the graph. This maintains the architecture principle that the graph is the discretized manifold (II.3).

1. **Verbs are atomic actions.** A single verb execution produces a single graph mutation per tick. Complex strategies emerge from verb sequencing, not from compound verbs.

1. **All nine verbs MUST be available.** The game does not prevent any action (I.11, Emergent Pedagogy). Consequences are modeled; choices are not restricted.

1. **Verb effects are deterministic given state.** The outcome of a verb depends on current graph state (material conditions, organization level, enemy disposition). The engine computes results; the AI narrates them (II.5).

**Rationale**: Nine verbs is the complete action vocabulary for revolutionary organization. Fewer verbs force unrealistic abstraction (combining armed action with mass mobilization). More verbs fragment decisions without adding strategic depth. The dual grouping ensures the player thinks strategically while the engine operates mechanically.

## State AI Verbs

The state AI interacts with the simulation through six verbs. These mirror the player's vocabulary in structure but reflect the asymmetric power of the state — broader kinds of power, even if the player can sometimes outmaneuver within any one category.

### The Six Verbs

| Verb | Domain | Sub-verbs | Description |
| --------------- | ---------------------- | -------------------------------------------------- | ------------------------------------------------------------------ |
| **Administer** | Internal management | Fund, Staff, Audit, Legislate | Reproduce the state apparatus each tick |
| **Develop** | Material base | Rezone, Invest, Eminent Domain, Tax Incentive Zone | Reshape the territory layer — the substrate all organizations stand on |
| **Research** | Technology | *(per technologies.json)* | Advance state capabilities; products potentially seizable by player |
| **Co-opt** | Ideological absorption | Bribe, Propagandize, Incorporate, Divide | Convert opposition into system-compatible forms or destroy relationships |
| **Repress** | Direct violence | Surveil, Infiltrate, Raid, Prosecute, Liquidate | Escalation ladder — each step costs more legitimacy, delivers more immediate effect |
| **Withdraw** | Disengagement | Strategic, Tactical, Scorched Earth | Concede, reposition, or deny territory |

### State AI Verb Mechanics

**Administer** — The state's BUILD equivalent. Internal capacity management: funding agencies, staffing positions, auditing loyalty, legislating authority. No controversy — it's how the state reproduces itself each tick.

**Develop** — The asymmetric verb the player does not have. Rezoning, infrastructure investment, eminent domain, tax incentive zones. DEVELOP changes the *territory layer*, which changes the substrate all organizations operate on. When the state DEVELOPs a territory, it's not attacking the player directly — it's changing the ground under them.

- Displaces population nodes
- Raises cost-of-living (changes reproduction requirements)
- Attracts different class composition
- Gentrification as a verb

The player responds to DEVELOP not with counter-force but with counter-organization — mutual aid networks, tenant unions, land trusts — or loses the territory through demographic replacement.

**Research** — Advance technology. Whatever the state develops becomes *potentially* available to the player if they can seize or replicate it (the tech tree in technologies.json supports this — Predictive Repression Systems, Autonomous Disinformation Networks, etc.). Strategic tension for the state AI: research selfishly (repression tech) or broadly (infrastructure that benefits population but increases legitimacy)?

**Co-opt** — Ideological and material absorption. Four sub-verbs:

- **Bribe**: Direct material concession to specific actors
- **Propagandize**: Ideological capture via narrative control
- **Incorporate**: Absorb opposition structures into state-compatible forms
- **Divide**: Topology surgery — targets *edges* rather than nodes. Destroys relationships between actors without trying to win either over. COINTELPRO's directive to "prevent coalition" was Divide, not co-optation.

Note: Negotiate is not a separate state verb. Negotiation emerges as a mode of Withdraw (negotiate terms of concession) or Co-opt (negotiate terms of absorption).

**Repress** — Direct violence. The escalation ladder, from cheapest/most deniable to most costly/most visible:

1. **Surveil**: Cheapest, most deniable. Intelligence gathering.
1. **Infiltrate**: Low visibility, slow burn. Degrades organizational Coherence from inside. Potentially more destructive than any raid.
1. **Raid**: Visible, costly, immediate disruption. Destroys material resources and arrests cadre.
1. **Prosecute**: Legalized violence. Neutralizes individuals through the judicial system. Medium legitimacy cost.
1. **Liquidate**: Extrajudicial elimination. Maximum immediate effect, maximum legitimacy cost.

Every step up the ladder costs more legitimacy but delivers more immediate effect. The state AI SHOULD have a strong bias toward the bottom of the ladder, escalating only when lower-intensity options fail or when attention thread pressure forces a response.

**Withdraw** — Three distinct modes the player must learn to read:

- **Strategic withdrawal**: The state concedes a territory because holding it costs more than it's worth. White flight, capital flight, base closures. The state hollows out first — defunds services, lets infrastructure decay, pulls investment. The player "wins" the territory but inherits a husk. Historically: what happens to Black neighborhoods after civil rights victories. Formal control without material base.

- **Tactical retreat**: Temporary pullback to consolidate attention threads elsewhere. Not a concession — a repositioning. The territory isn't abandoned; the state just stops actively contesting it for a while. Dangerous because it looks like victory but the state is reloading.

- **Scorched earth**: The state can't hold the territory and doesn't want the player to benefit. Active destruction of productive capacity, infrastructure, records. Massive legitimacy cost, but denies the player any material base. Historically: what colonial powers do on their way out.

The distinction matters because the player must read *which kind of withdrawal is happening* to respond correctly. Celebrating strategic withdrawal as liberation when inheriting a hollowed shell is a trap. Treating tactical retreat as permanent is a different trap.

### State AI Target Type Grouping (Engine-Facing)

| Target | Verbs | Graph Operation |
| ----------------------- | ------------------------------------ | ------------------------------------------------------------------- |
| **State apparatus** | Administer, Research | Modify state agent node attributes (budget, tech level, staffing) |
| **Territory layer** | Develop, Withdraw | Modify territory node attributes (infrastructure, cost-of-living, class composition) |
| **Opposition actors** | Co-opt, Repress | Modify edges between state and player/population nodes; degrade opposition node attributes |

### State AI Verb Implementation Requirements

1. **Six verbs are exhaustive for state action.** Every state action maps to exactly one verb. No state action produces effects outside the graph.

1. **Asymmetry is structural.** The player has nine verbs; the state has six. But the state's verbs (especially Develop) operate on the territory layer the player cannot directly modify. This asymmetry is correct — the state has more *kinds* of power.

1. **Escalation has cost.** Every Repress sub-verb above Surveil costs legitimacy. The state AI MUST track cumulative legitimacy cost and prefer lower-intensity options when they suffice.

1. **Withdraw modes are distinguishable.** The engine MUST tag withdrawals with their mode (strategic, tactical, scorched earth). The player's ability to read the mode depends on their Investigate intelligence level.

1. **Develop changes substrate, not actors.** DEVELOP modifies territory nodes. Effects on population are *indirect* — mediated through changed reproduction requirements, class composition shifts, and cost-of-living increases. The state is not attacking the player; it is rearranging the ground.

1. **Co-opt:Divide targets edges.** Unlike other Co-opt sub-verbs (which target nodes), Divide targets edges between actors. It destroys or degrades relationships without trying to absorb either party.

1. **Research products are seizable.** Technology developed by the state MUST be flagged as potentially available to the player via Attack (raid a facility) or Investigate (steal research). The tech tree governs availability.

**Rationale**: Six state verbs against nine player verbs reflects the real asymmetry of power. The state doesn't need Educate or Reproduce — it has Propagandize and Staff. It doesn't need Negotiate as a top-level verb — negotiation is a mode of Co-opt or Withdraw. What the state uniquely has is Develop: the power to reshape the material base itself. This is the verb that makes gentrification, redlining, and urban renewal legible as *state actions* rather than market forces.
