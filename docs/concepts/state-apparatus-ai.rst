About the State Apparatus AI
============================

Why the state is modeled as a factional coalition, how the escalation
ladder creates legible gameplay, and what design decisions shaped the
implementation. Feature 039 context for developers who want to
understand the reasoning before modifying the system.

.. contents:: On this page
   :local:
   :depth: 2


Why Three Factions, Not a Unitary Actor
----------------------------------------

Most games model the state as a single rational adversary: assess
threat, pick response, escalate linearly. This produces a difficulty
ratchet -- the state gets harder but never *changes character*. The
player learns to manage a single variable (threat level) and gameplay
becomes predictable.

Feature 039 replaces the unitary actor with a three-faction coalition
where each faction has distinct material interests, verb preferences,
and strategic dispositions:

- **Finance-Capital (FC)** prefers CO_OPT and DEVELOP. It tolerates
  organizing unless extraction is threatened. Its material base is
  profit rate and accumulation efficiency.
- **Security-State (SS)** prefers REPRESS and ADMINISTER. It has an
  institutional incentive to *maintain* threat perception (its funding
  depends on threats existing). Its material base is the repressive
  apparatus itself.
- **Settler-Populist (SP)** prefers DEVELOP (displacement) and CO_OPT
  (bribing its base). It provides the mass base for fascism when
  imperial rent contracts. Its material base is the distribution of
  imperial rent to the settler nation.

The key gameplay consequence: player actions don't just provoke state
*responses* -- they shift *which version of the state* the player is
fighting. Disrupting extraction shifts weight toward SS (who wants to
crush the threat) and away from FC (who wanted to co-opt). Building
legitimacy shifts weight toward FC (who prefers cheaper containment).
The state's character is an emergent property of the factional balance,
not a designed escalation script.

This is the MLM-TW analysis: the bourgeois state is not a monolith but
a site of class struggle among ruling-class fractions, and the
strategic orientation of the state depends on which fraction dominates
at any moment.


The Composite Objective Function
---------------------------------

Each faction has its own objective function that scores candidate
actions differently:

- FC scores CO_OPT and DEVELOP verbs highly when heat is low, but
  panics toward REPRESS when extraction is disrupted.
- SS scores REPRESS and ADMINISTER verbs highly regardless of heat --
  its institutional interest is in using the repressive apparatus.
- SP scores DEVELOP (displacement) and CO_OPT (bribe base) verbs.

The state's actual decision is the *weighted sum* of all three
objective functions: ``score(action) = sum(w_i * obj_i(action))``.
This means the same action produces different scores depending on the
current factional balance. A RAID scores 0.3 when FC dominates but 0.8
when SS dominates. The decision function doesn't switch between
strategies -- it continuously blends them.

The alternative considered was a mode-switch architecture (FC-mode,
SS-mode, SP-mode) where the dominant faction simply dictates strategy.
This was rejected because it produces discrete jumps in behavior that
are hard to tune and feel artificial. The weighted blend produces
smooth behavioral transitions that are more legible to the player.


The Escalation Ladder
----------------------

The state has a hard preference for cheap, low-visibility actions. The
escalation ladder encodes this preference as an ordered list:

::

   PROPAGANDIZE -> BRIBE -> INCORPORATE -> SURVEIL -> DIVIDE
       -> INFILTRATE -> INVEST/REZONE -> FUND(security) -> LEGISLATE
           -> RAID -> PROSECUTE -> DISPLACE -> STRATEGIC_WITHDRAWAL
               -> EMERGENCY_POWERS -> MASS_RAID -> LIQUIDATE -> SCORCHED_EARTH

This ordering is not arbitrary. It follows material logic:

1. **Ideological warfare first** (PROPAGANDIZE, BRIBE): cheapest,
   lowest legitimacy cost. The state would rather convince people
   the system works than deploy force.
2. **Surveillance** (SURVEIL, INFILTRATE): information gathering has
   moderate cost but is invisible to the player. The state needs
   intelligence before it can target effectively.
3. **Institutional coercion** (LEGISLATE, FUND, DISPLACE): uses legal
   and economic mechanisms. Higher cost but higher legitimacy.
4. **Direct repression** (RAID, PROSECUTE): expensive, high
   legitimacy cost. The state only reaches here when cheaper options
   have failed.
5. **Elimination** (LIQUIDATE, SCORCHED_EARTH): catastrophically
   expensive in legitimacy. Reserved for fascist convergence or
   EMERGENCY_POWERS conditions.

The ``compute_heat_escalation_score()`` function maps player heat to
escalation rank preference. At low heat, the state strongly prefers
low-rank verbs. As heat rises, higher-rank verbs become competitive.
This creates the legible escalation sequence the player can read and
respond to.


Why Separate StateActionType from ActionType
---------------------------------------------

The existing ``ActionType`` enum models player/org actions (EDUCATE,
RECRUIT, STRIKE, etc.) with CL/SL cost profiles. State verbs have a
structurally different resource profile: budget cost, thread cost, and
legitimacy cost.

These are different *type signatures*, not different values of the same
type. A function accepting ``ActionType`` should never silently accept
LIQUIDATE as a player action. Separate enums enforce the asymmetry
between player and state action spaces at the type level, so static
analysis catches the error before runtime.

The ``VERB_CHILDREN`` mapping (parent verb -> frozenset of sub-verbs)
was chosen over prefix-based naming (``ADMINISTER_FUND``,
``DEVELOP_INVEST``) because:

- No string parsing required for hierarchy validation
- Hierarchy information lives in one canonical location
- Enum values stay clean for serialization and display
- Adding or reorganizing sub-verbs requires changing only the mapping


The Observation Gap
--------------------

The state sees ``G_observed``, never ``G_actual``. This is the
fundamental asymmetry of the intelligence game.

``G_observed`` is constructed as a *separate* NetworkX DiGraph (not a
subgraph view) with distortions applied based on the surveillance
methods used. Each method reveals different aspects:

- **SIGNALS** sees communication edges but conflates edge types
  (SOLIDARISTIC appears as generic COMMUNICATION).
- **FINANCIAL** sees resource flows but has low confidence on
  non-monetary edges.
- **INFORMANT** sees internal state but only within the informant's
  cell, with incentive distortion (informants exaggerate threats to
  maintain relevance).

The observation ceiling per apparatus caps ``intel_completeness`` as a
hard limit (FBI: 0.4, Local PD: 0.2, Fusion Center: 0.5). Cell
topology reduces this further:
``effective_ceiling = base_ceiling * (1 - compartmentalization_factor)``.

This means the state's Sparrow analysis (centrality, equivalence
classes, cutsets) operates on distorted data. The state identifies
"hub nodes" and "vulnerable singletons" in ``G_observed`` that may
not correspond to the actual topology. Player decisions about
organizational structure (cell topology vs. star topology,
compartmentalization, counter-intel) directly affect what the state
can see and therefore what it can target.

The design claim: organizational security is not a defensive chore but
a strategic choice with visible consequences. A flat hierarchy is easy
to coordinate but exposes the whole network when compromised. A cell
structure limits damage but creates coordination costs and makes
Sparrow analysis less effective.


Fascist Convergence
--------------------

Fascist convergence is the system's phase transition -- a qualitative
change in state behavior triggered by quantitative shifts in three
independent variables:

1. Security-State weight > 0.4 (repressive apparatus has internal
   control)
2. Settler collective_identity > 0.6 with ASSIMILATIONIST_FASCIST
   tendency (popular mass base exists)
3. Finance-Capital weight < 0.25 (capital has given up on co-optation)

All three must hold simultaneously. This is deliberate: SS > 0.4
without settler CI > 0.6 is a police state (no mass base), not
fascism. High settler CI without SS dominance is populist backlash,
not fascism. The three conditions together represent the historical
pattern of fascist consolidation.

Entry thresholds are *easier* than exit thresholds. Once the system
enters fascist convergence (requiring a confirmation window of 2
consecutive ticks to filter noise), exiting requires SS < 0.25 AND
settler CI < 0.30 -- a much harder swing. This asymmetry models the
historical observation that fascist regimes are easier to establish
than to dismantle.

In fascist mode, verb selection changes qualitatively:

- CO_OPT budget redirects to REPRESS
- DEVELOP shifts to displacement-oriented sub-verbs (DISPLACE, REZONE)
- WITHDRAW becomes SCORCHED_EARTH in contested territories
- LEGISLATE shifts toward EMERGENCY_POWERS

This is not a difficulty increase but a *character change*. The state
becomes a different kind of adversary with different vulnerabilities.


Budget as Strategic Constraint
-------------------------------

The ``StateBudget`` model constrains action selection by making verbs
compete for finite resources. This creates meaningful tradeoffs:

- The state cannot RAID and INVEST simultaneously at full capacity.
  RAID is expensive; choosing it means disinvesting from
  territory development.
- Budget exhaustion forces the state toward zero-cost or low-cost
  options (NEGLECT over INVEST, PROPAGANDIZE over BRIBE, SURVEIL
  over RAID).
- ADMINISTER.FUND actions grow state capacity but consume current
  budget -- an invest-now-for-later tradeoff the state AI must navigate.

The budget constraint prevents the state from being omnipotent. It
forces *choices*, and those choices reveal strategic priorities that the
player can read and exploit. A state spending heavily on REPRESS has
less capacity for DEVELOP, meaning its territory control weakens in
areas it isn't actively defending.


Territory as Contested Space
-----------------------------

Territory effects model the material ground of class struggle. Each
territory has:

- ``property_value_proxy``: gentrification lever. INVEST raises it,
  triggering displacement pressure.
- ``infrastructure_quality``: disinvestment tool. NEGLECT degrades it,
  hollowing out state capacity but also abandoning control.
- ``heat_level``: state attention. HIGH_PROFILE organizations
  accumulate heat; LOW_PROFILE decays it. Heat >= 0.6 triggers
  escalation.
- ``collective_identity``: cultural resistance. Acts as a resistance
  multiplier against PROPAGANDIZE and a radicalization amplifier for
  RAID (the consciousness dialectic).

PRESENCE edges gate key capabilities: organizations without PRESENCE in
a territory suffer a 90% penalty on recruitment effectiveness. This
forces spatial strategy -- you must establish presence before you can
organize, and presence makes you visible.

The consciousness dialectic in ``compute_raid_consciousness_effect()``
is a key mechanic: raids *suppress* collective identity in
low-consciousness communities (CI < 0.5) but *radicalize*
high-consciousness communities (CI >= 0.5). The state faces a dilemma:
raiding a politicized community risks making it more militant. This
mirrors the historical pattern where repression against organized
communities (Fred Hampton, George Floyd) generates backlash that
strengthens the movement.


Design Constraints
-------------------

The implementation follows several architectural constraints:

**Frozen Pydantic models**: All entity state is immutable. Mutations
return new instances via ``model_copy(update={...})``. This prevents
accidental cross-system contamination and makes the tick boundary
explicit.

**Dict-based effect functions**: Territory effects, CO-OPT effects,
REPRESS effects all accept and return ``dict[str, Any]`` territory or
organization representations rather than typed Pydantic models. This is
a deliberate choice: the effect functions operate on *graph node
attribute dicts* as they flow through the resolution pipeline. Typed
conversion happens at the boundary (input validation in the function,
model reconstruction in the caller).

**Deterministic with seeds**: All stochastic operations (INFILTRATE
detection, RAID capture, PROSECUTE conviction) accept an ``rng_seed``
parameter and use ``random.Random(rng_seed)`` for reproducibility. The
same seed produces the same outcome across runs.

**No persistent_data usage**: Despite the spec's design decision (R2)
to store FactionBalance in ``context.persistent_data``, the
implementation stores it as graph node attributes on the StateApparatus
node. This means FactionBalance does not persist across ``to_graph()``
/ ``from_graph()`` round-trips via the typed model path.

**Protocol-based DI**: ``NPCDecisionStrategy`` is a
``@runtime_checkable`` Protocol, allowing the decision strategy to be
swapped without modifying the dispatch path. This prepares for
per-org-type AI strategies in future features.


Known Limitations
------------------

- **EventType members declared but not emitted**: The six Feature 039
  ``EventType`` values (``STATE_ACTION_EXECUTED``,
  ``FASCIST_CONVERGENCE``, etc.) are defined in the enum but no system
  currently publishes them to the EventBus. The OODA dispatch converts
  ``StateAction`` to legacy ``Action`` objects instead.

- **Protocol signature mismatch**: ``NPCDecisionStrategy.select_action()``
  and ``RuleBasedStateAI.select_action()`` have different parameter
  signatures. The protocol uses generic ``dict[str, Any]`` arguments;
  the implementation uses typed parameters.

- **Deferred requirements**: FR-D10 (per-org-type AI for Business,
  CivilSocietyOrg, PoliticalFaction) and FR-E05 (D-P-D'
  infrastructure: schools, workplaces as entities) are explicitly
  deferred to future features.


See Also
--------

- :doc:`/reference/state-apparatus-ai` -- Complete API reference
- :doc:`/how-to/state-apparatus-ai` -- Goal-oriented guides
- :doc:`/concepts/ooda-loop-system` -- OODA loop system design
- :doc:`/concepts/organization-model` -- Organization base model design
- :doc:`/concepts/ternary-consciousness` -- Ternary consciousness model
