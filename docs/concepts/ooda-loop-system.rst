The OODA Loop System
====================

Why Babylon models organizational action as an OODA cycle with
initiative-ordered turn resolution, community-modified costs,
and consequence propagation.

.. contents:: On this page
   :local:
   :depth: 2


Why Boyd's OODA Loop?
---------------------

The OODA loop -- Observe, Orient, Decide, Act -- was developed by
military strategist John Boyd to explain why some organizations
consistently outmaneuver others. Boyd's central insight is that the
organization which can cycle through observation, orientation, decision,
and action *faster* than its adversary gains a compounding advantage:
the slower side is always reacting to a situation that has already
changed.

Babylon adopts this framework because it maps directly onto the dynamics
of class struggle. The state apparatus (FBI, police) has institutional
advantages: federal jurisdiction, surveillance infrastructure, legal
authority. These translate into faster OODA cycles and higher initiative
scores. A revolutionary faction must overcome this structural deficit
through community embeddedness, ideological coherence, and momentum
from successful actions.

The OODA model also captures the tension between speed and legitimacy
in organizational decision-making. An autocratic decision mode (cycle
time base = 1.0 ticks) is fast but brittle -- it depends on one leader.
A consensus decision mode (cycle time base = 5.0 ticks) is slow but
resilient. This maps to the Leninist debate over democratic centralism:
the vanguard party sacrifices democratic process for operational speed,
while mass organizations sacrifice speed for broad participation.


Three-Layer Turn Resolution
----------------------------

Each simulation tick resolves organizational actions in three layers,
not one pass. This separation is deliberate.

**Layer 0: Automatic Metabolism**

Business organizations auto-record EMPLOY actions before any deliberate
organizational action occurs. Capital does not deliberate about whether
to employ labor -- employment is the metabolic function of capital. By
separating this from the initiative-ordered action phase, the simulation
captures the Marxist distinction between capital's automatic reproduction
and the conscious political action of organized forces.

**Action Phase: Initiative-Ordered Actions**

All organizations are scored for initiative and act in descending order.
The state moves first (highest initiative), then organized factions, then
civil society. This models structural power: the FBI does not wait for
a community organization to finish deliberating before acting. Each
organization selects and executes actions constrained by its OODA profile
(action points, coordination range, autonomy).

**Layer 3: Consequence Propagation**

After all actions resolve, consequences propagate to communities. No
organization observes mid-turn feedback. This models the fog of
political action: when the FBI raids a community, it does not see the
consciousness effect until the next tick. The five consequence
sub-processors update community state simultaneously:

1. **Consciousness aggregation** -- CI deltas from all organizations
   sum on each community. No single org dominates discourse.
2. **Heat propagation** -- REPRESS and SURVEIL actions increase
   community heat (state attention intensity).
3. **Edge transitions** -- ORGANIZE actions deepen org-community
   relationships from TRANSACTIONAL to SOLIDARISTIC.
4. **Infrastructure effects** -- BUILD and ATTACK modify community
   material capacity.
5. **Contestation stacking** -- AGITATE actions raise ideological
   contestation, creating conditions for effective EDUCATE.


Initiative and the State Advantage
----------------------------------

At game start, the FBI has an initiative score of approximately 5.5
versus a revolutionary faction's 1.1. This five-to-one advantage comes
from the initiative formula's five components:

1. **Speed** (weight 2.0): inverse cycle time. The FBI's AUTOCRATIC
   mode and low sensor latency produce a short cycle.
2. **Institutional bonus** (weight 1.0): NATIONAL jurisdiction grants
   a bonus of 5.0. Non-state organizations receive 0.0.
3. **Counter-intelligence** (weight 1.5): the FBI's counter-intel
   score of 0.9 contributes 1.35 to initiative.
4. **Community embeddedness** (weight 1.0): membership overlap with
   operating communities. State orgs often have low embeddedness.
5. **Momentum** (weight 0.5): accumulated from successful actions,
   decays by 0.8x per tick.

The institutional bonus is the largest single factor. It models the
structural power that the state possesses before any action is taken.
But embeddedness and momentum are the factors that factions can build
over time. A revolutionary organization with deep community roots and
a streak of successful actions can close the initiative gap.

This dynamic captures a historical pattern: the state always strikes
first (COINTELPRO, Palmer Raids), but sustained community organizing
can erode that advantage (Black Panther survival programs, union
solidarity networks).


Decision Mode and Cycle Time
-----------------------------

The four-phase cycle time formula produces a single number that governs
how quickly an organization can act::

   cycle_time = observe + orient + decide + act

The Decide phase is the most variable component. Decision mode sets a
base time that bureaucratic depth then amplifies:

- **AUTOCRATIC** (base 1.0): One person decides. Fast, but the
  organization is fragile -- remove the leader and it collapses.
- **DELEGATE** (base 2.0): Leader delegates to trusted subordinates.
  A middle ground.
- **DEMOCRATIC** (base 3.0): Majority vote. Slower, but decisions
  have broader buy-in and the organization can survive leadership
  losses.
- **CONSENSUS** (base 5.0): Full agreement required. Very slow, but
  produces the strongest collective commitment.

The Orient phase has its own dynamic: ideological coherence reduces
orient time. An organization with high coherence (0.8) needs less time
to make sense of new information because its members share a common
analytical framework. This models the advantage of ideological unity
in revolutionary organizations -- Leninist parties orient faster because
they have a shared theory of the situation.

The orient time floor (0.1) prevents coherence from reducing Orient to
zero. Even the most ideologically unified organization needs some time
to process new information.


Community-Modified Costs
------------------------

Not all actions cost the same for all organizations. An organization
embedded in a community through shared membership pays less to act
there. An outsider pays more. An organization operating across a
contradiction axis (settler organization acting on a New Afrikan
community) pays the most.

The three cost tiers are:

1. **Embedded** (overlap > 0): discount via
   ``1.0 - overlap * 0.5``, floored at 0.5. The deeper the shared
   membership, the cheaper the action.
2. **Outsider** (no overlap, no contradiction): surcharge of 1.5x.
   No local relationships means higher friction.
3. **Contradiction axis** (structural antagonism): surcharge of 2.5x.
   Operating across lines of national oppression (SETTLER/NEW_AFRIKAN,
   SETTLER/FIRST_NATIONS, SETTLER/CHICANO) or patriarchal oppression
   (PATRIARCHAL/WOMEN, PATRIARCHAL/TRANS) is the most costly.

This models the material basis for the "outside agitator" phenomenon.
An organization without community roots cannot effectively organize
there -- not because of legal barriers, but because of the social
friction of acting without trust. The contradiction surcharge models
the additional cost of operating across structural antagonisms that
the organization's own membership composition cannot bridge.


Consciousness Effects
---------------------

The OODA system extends Feature 031's five-factor consciousness formula
with action-type multipliers. The base formula remains::

   delta = tendency_modifier * cadre_level * cohesion * credibility

The OODA extension adds:

- **Action base multiplier**: each action type has a consciousness
  multiplier. EDUCATE (1.2) has the highest positive effect. AGITATE
  (0.0) has zero CI effect -- it affects contestation instead.
- **Membership overlap credibility**: credibility is scaled by the
  overlap between org members and community members. An org with no
  members in a community has near-zero credibility there.
- **AGITATE-EDUCATE coupling**: AGITATE actions raise community
  contestation. When contestation exceeds 0.3, subsequent EDUCATE
  actions receive a 1.5x bonus. This models how agitation creates
  the conditions for effective political education.
- **Backfire mechanics**: REPRESS and SURVEIL actions produce a
  positive CI delta on the target community (REVOLUTIONARY tendency).
  State violence raises consciousness. REPRESS has a higher backfire
  (action base 0.8) than SURVEIL (0.2).
- **ASSIMILATE**: negative CI delta with LIBERAL tendency pressure.
  Models institutional co-optation that suppresses class consciousness.
- **Per-tick clamping**: maximum absolute CI delta is 0.05 per action.
  Prevents any single action from causing a consciousness revolution
  in one tick.


Lifecycle Capacity
------------------

An organization's action capacity depends on the lifecycle composition
of its membership. This reuses Feature 031's composition calculators:

- **Youth** (D-phase): zero capacity. Children do not contribute to
  organizational action.
- **Adult** (P-phase): full capacity (1.0). The productive phase
  provides the labor power for organizational action.
- **Elder** (D'-phase): reduced capacity (``elder_capacity_factor``,
  default 0.2 from ``OrganizationDefines``). Elders contribute less
  physical labor but more legitimacy.

The elder legitimacy bonus (multiplier 1.3) increases consciousness
deltas when an organization has elder members. This models the
historical observation that elder participation lends moral authority
to organizational action -- the presence of grandmothers at a protest
changes its character.


Edge Transitions
----------------

ORGANIZE actions trigger edge transitions from TRANSACTIONAL to
SOLIDARISTIC. These two edge types represent qualitatively different
org-community relationships:

**TRANSACTIONAL**: the organization provides a service and receives
political support in exchange. The relationship is instrumental --
if the service stops, the support evaporates. Civil society
organizations typically start with transactional relationships.

**SOLIDARISTIC**: mutual commitment based on shared vision and
collective struggle. The relationship persists through hardship
because both org and community are bound by solidarity. Revolutionary
organizations build solidaristic relationships through sustained
organizing work.

The transition from TRANSACTIONAL to SOLIDARISTIC through ORGANIZE
actions models the process of consciousness-raising and relationship
deepening. It is the organizational expression of the broader
transition from transactional politics to solidarity politics.


Coefficient Derivation
----------------------

Every OODA coefficient traces to real-world data through a three-level
derivation chain.

**Level 0: Empirical Irreducibles.** Five empirically-grounded constants
that cannot be derived from the simulation's own logic:

1. **Political half-life** (:math:`\tau_{1/2} = 7` weeks) from FM 3-24
   counterinsurgency doctrine. Produces the decay constant
   :math:`\lambda = \ln 2 / 7 \approx 0.1` that governs consciousness
   decay, agitation decay, heat decay, and routing scale. All four
   represent the same physical process: information entropy without
   active maintenance.

2. **Imperial extraction rate** (:math:`\alpha = 0.8`) from Amin/Emmanuel
   unequal exchange theory. This is the structural capacity, not the
   steady-state rate (which the consciousness ODE moderates). Together
   with :math:`\lambda`, it produces consciousness sensitivity
   :math:`k = \lambda / (1 - \alpha) = 0.5`.

3. **Network percolation threshold** (:math:`p_c \approx 0.3`) from
   percolation theory on random graphs with :math:`\langle k \rangle
   \approx 3\text{--}4`. Below this threshold, solidarity networks
   fragment; above it, system-wide transmission emerges.

4. **Gentrification rent premium** (1.5×) from Census/HUD data.
   Combined with heat decay, produces the high-profile heat gain
   that converges to the eviction threshold in 6--8 ticks,
   matching FM 3-24's "clear" phase timeline.

5. **George Floyd solidarity shift** (:math:`\Delta S = 0.2`) from
   Pew Research 2020 polling data. The 20 percentage point shift in
   white BLM support grounds both the solidarity gain per uprising
   and the OODA momentum success bonus.

**Level 1: Source Primitives.** Thirteen ``GameDefines`` constants
derived from Level 0. These were previously undocumented "magic numbers";
each now carries a Field description citing its empirical source.

**Level 2: OODA Coefficients.** The 67 ``OODADefines`` coefficients.
Of these, 26 (39%) are derived or empirically grounded:

- 4 are **direct substitutions** from source primitives (Category A)
- 12 are **formula derivations** from source primitives (Category B)
- 10 are **empirically grounded** in COIN/census data (Category C)

The remaining 41 are theoretically justified (Category D) or
engineering constants (Category E).

The key insight is that OODA coefficients model the *same physical
processes* as other simulation systems. Repression generates heat
because repression IS the mechanism that makes communities high-profile.
Embeddedness discounts action costs because embeddedness IS solidarity
operating at the organizational level. The derivation chain makes these
identity relationships explicit and testable.

See :doc:`/reference/ooda-coefficients` for the full derivation table and
runtime validation via ``OODADefines.validate_derivations()``.


See Also
--------

- :doc:`/reference/ooda-loop-system` -- Complete API reference
- :doc:`/reference/ooda-coefficients` -- Every tunable coefficient
- :doc:`/concepts/organization-model` -- Organization subtypes and consciousness
- :doc:`/concepts/consciousness-taxonomy` -- Consciousness formation theory
- :doc:`/concepts/community-hypergraph` -- Community layer architecture
