OODA Coefficients Reference
===========================

Complete catalog of every tunable coefficient in the OODA Loop System
(Feature 032). All coefficients live in the ``OODADefines`` class within
``src/babylon/config/defines.py`` unless otherwise noted.

**Access pattern:**

.. code-block:: python

   from babylon.config.defines import GameDefines

   defines = GameDefines()
   ooda = defines.ooda  # OODADefines instance

   # Example: get base observe time
   ooda.base_observe_time  # 1.0

.. contents:: On this page
   :local:
   :depth: 2


Cycle Time Weights
------------------

Used in :func:`babylon.ooda.cycle_time.compute_cycle_time` to compute the
four-phase additive OODA cycle time.

**Formula:**

.. math::

   T_{cycle} = T_{observe} + T_{orient} + T_{decide} + T_{act}

Where:

.. math::

   T_{observe} &= \texttt{base\_observe\_time} + \texttt{sensor\_latency} \times \texttt{latency\_weight} \\
   T_{orient} &= \max\bigl(\texttt{base\_orient\_time} \times (1 - \texttt{coherence} \times \texttt{coherence\_weight}),\ \texttt{orient\_time\_floor}\bigr) \\
   T_{decide} &= \texttt{decision\_base} \times (1 + \texttt{bureaucratic\_depth} \times \texttt{depth\_weight}) \\
   T_{act} &= \texttt{base\_act\_time}

.. list-table::
   :header-rows: 1
   :widths: 30 10 15 45

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``base_observe_time``
     - 1.0
     - ``gt=0``
     - Base Observe phase duration (ticks).
   * - ``latency_weight``
     - 0.5
     - ``ge=0``
     - Weight of ``sensor_latency`` on Observe phase.
   * - ``base_orient_time``
     - 2.0
     - ``gt=0``
     - Base Orient phase duration.
   * - ``coherence_weight``
     - 0.6
     - ``ge=0, le=1.0``
     - Weight of ``ideological_coherence`` on Orient phase.
   * - ``base_act_time``
     - 1.0
     - ``gt=0``
     - Base Act phase duration (fixed, not modified by profile).
   * - ``coord_weight``
     - 0.3
     - ``ge=0``
     - Weight of coordination on Act phase (reserved for future use).
   * - ``depth_weight``
     - 0.4
     - ``ge=0``
     - Weight of ``bureaucratic_depth`` on Decide phase.
   * - ``orient_time_floor``
     - 0.1
     - ``ge=0.0``
     - Minimum Orient phase duration. Prevents coherence from zeroing out Orient.

**Code location:** ``src/babylon/config/defines.py:2141-2177``, used in
``src/babylon/ooda/cycle_time.py:17-39``.


Decision Mode Base Times
------------------------

The ``decision_base`` term in the Decide phase formula. Looked up by
``DecisionMode`` enum value in :func:`babylon.ooda.cycle_time.compute_cycle_time`.

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``decision_mode_base_autocratic``
     - 1.0
     - ``gt=0``
     - AUTOCRATIC: single decision-maker, fastest.
   * - ``decision_mode_base_delegate``
     - 2.0
     - ``gt=0``
     - DELEGATE: leader delegates to trusted subordinates.
   * - ``decision_mode_base_democratic``
     - 3.0
     - ``gt=0``
     - DEMOCRATIC: majority vote among members.
   * - ``decision_mode_base_consensus``
     - 5.0
     - ``gt=0``
     - CONSENSUS: full agreement required, slowest.

**Ordering invariant:** AUTOCRATIC (1.0) < DELEGATE (2.0) < DEMOCRATIC (3.0) < CONSENSUS (5.0).

**Code location:** ``src/babylon/config/defines.py:2179-2199``, used in
``src/babylon/ooda/cycle_time.py:42-58``.


Initiative Scoring Weights
--------------------------

Five-component weighted sum in :func:`babylon.ooda.initiative.compute_initiative_score`.

**Formula:**

.. math::

   I = w_{speed} \times \frac{1}{T_{cycle}} + w_{inst} \times B_{inst} + w_{ci} \times C + w_{embed} \times E + w_{mom} \times M

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``initiative_weight_speed``
     - 2.0
     - ``ge=0``
     - Weight for speed component (inverse cycle time).
   * - ``initiative_weight_institutional``
     - 1.0
     - ``ge=0``
     - Weight for institutional bonus (state advantage).
   * - ``initiative_weight_counterintel``
     - 1.5
     - ``ge=0``
     - Weight for counter-intelligence capability.
   * - ``initiative_weight_embeddedness``
     - 1.0
     - ``ge=0``
     - Weight for community embeddedness.
   * - ``initiative_weight_momentum``
     - 0.5
     - ``ge=0``
     - Weight for recent success momentum.

**Code location:** ``src/babylon/config/defines.py:2201-2226``, used in
``src/babylon/ooda/initiative.py:22-67``.


Institutional Bonus by Jurisdiction
-----------------------------------

The :math:`B_{inst}` term in the initiative formula. Looked up by
``JurisdictionLevel`` enum value.

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``institutional_bonus_federal``
     - 5.0
     - ``ge=0``
     - NATIONAL (federal) jurisdiction. FBI, DEA, ATF.
   * - ``institutional_bonus_state``
     - 3.0
     - ``ge=0``
     - STATE jurisdiction. State police, National Guard.
   * - ``institutional_bonus_local``
     - 1.5
     - ``ge=0``
     - COUNTY or MUNICIPAL jurisdiction. Local PD, sheriff.
   * - ``institutional_bonus_nonstate``
     - 0.0
     - ``ge=0``
     - Non-state organizations (factions, civil society, business).

**Code location:** ``src/babylon/config/defines.py:2228-2248``, used in
``src/babylon/ooda/initiative.py:148-167``.


Momentum
--------

Momentum rewards consecutive successful actions and decays exponentially
per tick.

**Formula:**

.. math::

   M_{t+1} = M_t \times \texttt{momentum\_decay} + \begin{cases} \texttt{momentum\_success\_bonus} & \text{if action succeeded} \\ 0 & \text{otherwise} \end{cases}

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``momentum_decay``
     - 0.8
     - ``ge=0, lt=1.0``
     - Exponential decay factor per tick. Higher = slower decay.
   * - ``momentum_success_bonus``
     - 0.2
     - ``ge=0``
     - Bonus added per successful action.

**Code location:** ``src/babylon/config/defines.py:2250-2261``, used in
``src/babylon/ooda/initiative.py:127-145``.


Action Cost Modifiers
---------------------

Community-modified action costs in :func:`babylon.ooda.action_costs.compute_action_cost`.

**Formula:**

.. math::

   \texttt{modifier} = \begin{cases}
   \max\bigl(\texttt{min\_cost\_modifier},\ 1.0 - \texttt{overlap} \times \texttt{embeddedness\_discount}\bigr) & \text{if embedded (overlap > 0)} \\
   \texttt{contradiction\_cost\_multiplier} & \text{if across contradiction axis} \\
   \texttt{outsider\_cost\_multiplier} & \text{otherwise (outsider)}
   \end{cases}

.. math::

   \texttt{effective\_cost} = \max\bigl(1,\ \lceil \texttt{base\_cost} \times \texttt{modifier} \rceil\bigr)

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``embeddedness_discount``
     - 0.5
     - ``ge=0, le=1.0``
     - Cost discount factor for embedded orgs. Higher = steeper discount.
   * - ``contradiction_cost_multiplier``
     - 2.5
     - ``gt=1.0``
     - Cost multiplier when org and target are on opposite sides of a contradiction axis.
   * - ``outsider_cost_multiplier``
     - 1.5
     - ``gt=1.0``
     - Cost multiplier for orgs with no membership in the target community.
   * - ``min_cost_modifier``
     - 0.5
     - ``gt=0, le=1.0``
     - Floor cost modifier. Even fully embedded orgs pay at least 50% of base cost.

**Code location:** ``src/babylon/config/defines.py:2263-2285``, used in
``src/babylon/ooda/action_costs.py:34-82``.


Consciousness Effect Limits
----------------------------

Per-tick clamping in :func:`babylon.ooda.action_effects.compute_consciousness_delta`.

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``max_ci_delta_per_tick``
     - 0.05
     - ``gt=0, le=1.0``
     - Maximum absolute CI delta per action per tick. Prevents runaway consciousness shifts.

**Code location:** ``src/babylon/config/defines.py:2287-2293``, used in
``src/babylon/ooda/action_effects.py:85-88``.


Action Base Consciousness Multipliers
--------------------------------------

The ``action_base`` term in the consciousness delta formula. Zero means the
action has no consciousness effect (e.g., AGITATE affects contestation instead).

**Formula:**

.. math::

   \Delta_{CI} = \text{clamp}\bigl(\texttt{tendency\_modifier} \times \texttt{cadre} \times \texttt{cohesion} \times \texttt{credibility} \times \texttt{action\_base},\ \pm\texttt{max\_ci\_delta}\bigr)

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``action_base_educate``
     - 1.2
     - ``ge=0``
     - EDUCATE: direct political education. Highest CI multiplier.
   * - ``action_base_agitate``
     - 0.0
     - ``ge=0``
     - AGITATE: increases contestation, not CI directly. Zero base.
   * - ``action_base_provide_service``
     - 0.6
     - ``ge=0``
     - PROVIDE_SERVICE: serve-the-people programs. Moderate CI effect.
   * - ``action_base_recruit``
     - 0.3
     - ``ge=0``
     - RECRUIT: bringing in new members. Low CI effect.
   * - ``action_base_organize``
     - 0.5
     - ``ge=0``
     - ORGANIZE: building community structures. Moderate CI effect.
   * - ``action_base_propagandize``
     - 0.8
     - ``ge=0``
     - PROPAGANDIZE: media and messaging. High CI effect.
   * - ``action_base_repress``
     - 0.8
     - ``ge=0``
     - REPRESS: state violence. Backfire CI effect (always +CI on target, REVOLUTIONARY tendency).
   * - ``action_base_surveil``
     - 0.2
     - ``ge=0``
     - SURVEIL: state surveillance. Smaller backfire CI effect than REPRESS.
   * - ``action_base_assimilate``
     - 1.0
     - ``ge=0``
     - ASSIMILATE: institutional co-optation. Negative CI effect (pushes LIBERAL tendency).

**Special case -- PROVIDE_SERVICE tendency split** (hardcoded in ``_get_effective_action_base``):

- REVOLUTIONARY org: uses ``action_base_provide_service`` (0.6)
- LIBERAL org: uses ``action_base_provide_service * 0.3`` (0.18)
- Other tendency: zero effect

**Code location:** ``src/babylon/config/defines.py:2295-2340``, used in
``src/babylon/ooda/action_effects.py:231-246``.


Autonomy Tradeoff
-----------------

The autonomy-breadth tradeoff in :func:`babylon.ooda.constraints.apply_autonomy_modifier`.

**Formula:**

.. math::

   \texttt{effectiveness} = \begin{cases}
   1.0 & \text{if } n_{targets} \leq 1 \\
   \max\bigl(0.1,\ 1.0 - \texttt{autonomy} \times \texttt{scale} \times \frac{n_{targets} - 1}{n_{targets}}\bigr) & \text{otherwise}
   \end{cases}

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``autonomy_effectiveness_scale``
     - 0.5
     - ``ge=0, le=1.0``
     - Scale factor for the autonomy-effectiveness tradeoff. Higher = steeper penalty for spreading actions.

**Code location:** ``src/babylon/config/defines.py:2342-2348``, used in
``src/babylon/ooda/constraints.py:92-116``.


Agitation-Contestation Coupling
-------------------------------

AGITATE actions increase ``ideological_contestation`` on the target community.
When contestation exceeds a threshold, EDUCATE actions receive a bonus multiplier.

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``agitation_contestation_delta``
     - 0.1
     - ``ge=0, le=1.0``
     - Contestation increase per AGITATE action.
   * - ``agitation_educate_bonus``
     - 1.5
     - ``ge=1.0``
     - EDUCATE CI delta multiplier when community contestation exceeds threshold.
   * - ``contestation_threshold``
     - 0.3
     - ``ge=0, le=1.0``
     - Contestation level at which EDUCATE bonus activates.

**Mechanic:** AGITATE first to raise contestation above 0.3, then EDUCATE
with 1.5x multiplier. This models how agitation creates the conditions for
effective political education.

**Code location:** ``src/babylon/config/defines.py:2350-2367``, used in
``src/babylon/ooda/action_effects.py:78-82`` (EDUCATE bonus) and
``src/babylon/ooda/action_effects.py:150-163`` (AGITATE resolver).


Lifecycle Modifiers
-------------------

Elder legitimacy in :func:`babylon.ooda.lifecycle_capacity.elder_legitimacy_bonus`.

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``elder_legitimacy_multiplier``
     - 1.3
     - ``ge=1.0``
     - CI delta multiplier when organization has elder (D'-phase) members. Elders lend legitimacy.

**Code location:** ``src/babylon/config/defines.py:2369-2374``, used in
``src/babylon/ooda/lifecycle_capacity.py:44-70``.


Counter-Intelligence
--------------------

Counter-intelligence score progression.

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``counter_intel_increment``
     - 0.1
     - ``ge=0, le=1.0``
     - Counter-intel score increment per successful COUNTER_INTEL action.

**Code location:** ``src/babylon/config/defines.py:2376-2382``.


Base Action Point Costs
-----------------------

Default AP cost for each of the 21 action types. All are integers with
``ge=1``. Modified at runtime by :func:`babylon.ooda.action_costs.compute_action_cost`.

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Parameter
     - Default
     - Description
   * - ``base_cost_educate``
     - 1
     - Political education. Cheap, high CI impact.
   * - ``base_cost_agitate``
     - 1
     - Raise contestation. Cheap, no direct CI effect.
   * - ``base_cost_fundraise``
     - 1
     - Generate resources.
   * - ``base_cost_employ``
     - 1
     - Business auto-metabolism.
   * - ``base_cost_surveil``
     - 1
     - State surveillance. Cheap, low backfire.
   * - ``base_cost_map_network``
     - 1
     - Intelligence mapping.
   * - ``base_cost_propose_alliance``
     - 1
     - Diplomatic overture.
   * - ``base_cost_denounce``
     - 1
     - Public condemnation.
   * - ``base_cost_recruit``
     - 2
     - Grow membership.
   * - ``base_cost_organize``
     - 2
     - Build community structures.
   * - ``base_cost_propagandize``
     - 2
     - Media and messaging.
   * - ``base_cost_provide_service``
     - 2
     - Serve-the-people programs.
   * - ``base_cost_repress``
     - 2
     - State violence. Moderate cost, high backfire.
   * - ``base_cost_protest``
     - 2
     - Public demonstration.
   * - ``base_cost_counter_intel``
     - 2
     - Counter-intelligence operations.
   * - ``base_cost_attack_infrastructure``
     - 2
     - Sabotage community infrastructure.
   * - ``base_cost_assimilate``
     - 2
     - Institutional co-optation.
   * - ``base_cost_strike``
     - 3
     - Labor withdrawal. Expensive, powerful.
   * - ``base_cost_expropriate``
     - 3
     - Seize property/resources. Expensive.
   * - ``base_cost_infiltrate``
     - 3
     - Intelligence infiltration. Expensive.
   * - ``base_cost_build_infrastructure``
     - 3
     - Build community infrastructure. Expensive, lasting effect.

**Code location:** ``src/babylon/config/defines.py:2384-2411``.


Layer 3 Propagation Coefficients
--------------------------------

Used by :func:`babylon.ooda.layer3.process_layer3` to propagate action
consequences to community state.

.. list-table::
   :header-rows: 1
   :widths: 35 10 15 40

   * - Parameter
     - Default
     - Constraints
     - Description
   * - ``repress_heat_delta``
     - 0.15
     - ``ge=0.0, le=1.0``
     - Heat increase per REPRESS action. Heavy state attention.
   * - ``surveil_heat_delta``
     - 0.05
     - ``ge=0.0, le=1.0``
     - Heat increase per SURVEIL action. Light state attention.
   * - ``build_infrastructure_delta``
     - 0.1
     - ``ge=0.0, le=1.0``
     - Infrastructure increase per BUILD_INFRASTRUCTURE action.
   * - ``attack_infrastructure_delta``
     - 0.1
     - ``ge=0.0, le=1.0``
     - Infrastructure decrease per ATTACK_INFRASTRUCTURE action.

**Code location:** ``src/babylon/config/defines.py:2413-2428``, used in
``src/babylon/ooda/layer3.py:97-222``.


Module-Level Constants
----------------------

Constants defined outside ``OODADefines``, typically structural data or
loop safety limits.

Structural Constants
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Constant
     - Location
     - Description
   * - ``_CONTRADICTION_PAIRS``
     - ``action_costs.py:25-31``
     - 5 tuples of ``(CommunityType, CommunityType)`` defining contradiction axes:
       SETTLER/NEW_AFRIKAN, SETTLER/FIRST_NATIONS, SETTLER/CHICANO,
       PATRIARCHAL/WOMEN, PATRIARCHAL/TRANS.
   * - ``_UNIVERSAL_ACTIONS``
     - ``action_eligibility.py``
     - ``frozenset`` of 12 ActionTypes available to all org types: RECRUIT, ORGANIZE,
       EDUCATE, AGITATE, PROPAGANDIZE, FUNDRAISE, PROTEST, COUNTER_INTEL, MAP_NETWORK,
       PROPOSE_ALLIANCE, DENOUNCE, BUILD_INFRASTRUCTURE.
   * - ``_NPC_PRIORITIES``
     - ``npc_stub.py:20-47``
     - Priority queues by org type. STATE_APPARATUS: SURVEIL first.
       POLITICAL_FACTION: EDUCATE first. CIVIL_SOCIETY: PROVIDE_SERVICE first.
       BUSINESS: EMPLOY first.

Loop Safety Limits
~~~~~~~~~~~~~~~~~~

All OODA modules enforce static upper bounds on iterations per the project's
loop safety rule. These are not tunable game parameters.

.. list-table::
   :header-rows: 1
   :widths: 25 10 25 40

   * - Constant
     - Value
     - Location
     - Scope
   * - ``_MAX_ACTIONS_PER_ORG``
     - 20
     - ``constraints.py:15``
     - Maximum actions processed per organization per tick.
   * - ``max_orgs``
     - 1000
     - ``layer0.py:39``
     - Maximum Business orgs processed in Layer 0.
   * - ``max_results``
     - 1000
     - ``layer3.py`` (5 functions)
     - Maximum action results iterated per sub-processor.
   * - ``max_edges``
     - 1000
     - ``action_costs.py:102,141``
     - Maximum edges iterated for membership overlap.
   * - ``max_nodes``
     - 1000
     - ``action_effects.py:281``
     - Maximum nodes iterated for community membership.
   * - ``max_actions``
     - 20
     - ``npc_stub.py:78``
     - Maximum NPC actions selected per org.

Hardcoded Multipliers
~~~~~~~~~~~~~~~~~~~~~

Two values are hardcoded in function bodies rather than in ``OODADefines``:

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - Value
     - Location
     - Purpose
   * - 0.3
     - ``action_effects.py:243``
     - LIBERAL tendency multiplier for PROVIDE_SERVICE (``action_base * 0.3``).
   * - 0.1
     - ``constraints.py:116``
     - Autonomy effectiveness floor. Prevents complete ineffectiveness.
   * - 0.01
     - ``action_effects.py:68``
     - Minimum overlap for credibility (``max(overlap, 0.01)``).


See Also
--------

- :doc:`/concepts/ooda-loop-system` -- Why these coefficients have these values
- :doc:`/reference/ooda-loop-system` -- Complete API reference
- :doc:`/reference/organizations` -- Organization model and consciousness formula
- :doc:`/reference/configuration` -- GameDefines configuration system
