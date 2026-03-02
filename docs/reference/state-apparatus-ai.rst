State Apparatus AI (Feature 039)
=================================

Technical reference for the state apparatus AI subsystem: entity models,
enums, decision functions, effect resolution, attention/intelligence
modules, formulas, and configuration parameters.

.. contents:: On this page
   :local:
   :depth: 2

Module Layout
-------------

::

   src/babylon/
   +-- config/defines.py                  StateApparatusAIDefines
   +-- models/
   |   +-- enums.py                       StateFaction, StateActionType, ThreadPhase, SurveillanceMethod
   |   +-- entities/
   |       +-- state_apparatus_ai.py      FactionBalance, StateBudget, StateAction, LegalFramework
   |       +-- attention_thread.py        AttentionThread, SparrowAnalysis
   +-- formulas/state_ai.py              Faction shift, fascist convergence formulas
   +-- ooda/
       +-- state_ai/                      Decision engine + effect resolution (11 modules)
       |   +-- protocols.py               NPCDecisionStrategy protocol
       |   +-- decision.py                RuleBasedStateAI class
       |   +-- escalation.py              Escalation ladder ranking
       |   +-- faction_dynamics.py        Faction weight shifts
       |   +-- territory_effects.py       DEVELOP/WITHDRAW effects
       |   +-- co_opt_effects.py          CO-OPT effects
       |   +-- repress_effects.py         REPRESS pipeline
       |   +-- administer_effects.py      ADMINISTER capacity
       |   +-- legislate_effects.py       LEGISLATE consumption
       |   +-- observability.py           Player-visible events + god mode
       +-- attention/                     Intelligence gathering (4 modules)
           +-- observation.py             G_observed construction
           +-- sparrow.py                 Network vulnerability analysis
           +-- thread_manager.py          Thread lifecycle management


Enums
-----

All state AI enums are ``StrEnum`` subclasses in
:mod:`babylon.models.enums`.

StateFaction
^^^^^^^^^^^^

Ruling-class factions within the state coalition.

.. list-table::
   :header-rows: 1
   :widths: 30 30

   * - Member
     - Value
   * - ``FINANCE_CAPITAL``
     - ``"finance_capital"``
   * - ``SECURITY_STATE``
     - ``"security_state"``
   * - ``SETTLER_POPULIST``
     - ``"settler_populist"``


StateActionType
^^^^^^^^^^^^^^^

State verb taxonomy. Six top-level verbs and their sub-verbs.

**Top-level verbs:**

.. list-table::
   :header-rows: 1
   :widths: 30 30

   * - Member
     - Value
   * - ``ADMINISTER``
     - ``"administer"``
   * - ``DEVELOP``
     - ``"develop"``
   * - ``RESEARCH``
     - ``"research"``
   * - ``CO_OPT``
     - ``"co_opt"``
   * - ``REPRESS``
     - ``"repress"``
   * - ``WITHDRAW``
     - ``"withdraw"``

**Sub-verbs by parent:**

.. list-table::
   :header-rows: 1
   :widths: 20 30 30

   * - Parent
     - Sub-verb
     - Value
   * - ADMINISTER
     - ``FUND``
     - ``"fund"``
   * -
     - ``STAFF``
     - ``"staff"``
   * -
     - ``LEGISLATE``
     - ``"legislate"``
   * -
     - ``AUDIT``
     - ``"audit"``
   * -
     - ``REVOKE``
     - ``"revoke"``
   * - DEVELOP
     - ``INVEST``
     - ``"invest"``
   * -
     - ``REZONE``
     - ``"rezone"``
   * -
     - ``DISPLACE``
     - ``"displace"``
   * -
     - ``NEGLECT``
     - ``"neglect"``
   * - RESEARCH
     - ``PURSUE_TECH``
     - ``"pursue_tech"``
   * -
     - ``DEPLOY_TECH``
     - ``"deploy_tech"``
   * - CO_OPT
     - ``BRIBE``
     - ``"bribe"``
   * -
     - ``PROPAGANDIZE``
     - ``"propagandize"``
   * -
     - ``INCORPORATE``
     - ``"incorporate"``
   * -
     - ``DIVIDE``
     - ``"divide"``
   * - REPRESS
     - ``SURVEIL``
     - ``"surveil_state"``
   * -
     - ``INFILTRATE``
     - ``"infiltrate_state"``
   * -
     - ``RAID``
     - ``"raid"``
   * -
     - ``PROSECUTE``
     - ``"prosecute"``
   * -
     - ``LIQUIDATE``
     - ``"liquidate"``
   * - WITHDRAW
     - ``STRATEGIC_WITHDRAWAL``
     - ``"strategic_withdrawal"``
   * -
     - ``TACTICAL_RETREAT``
     - ``"tactical_retreat"``
   * -
     - ``SCORCHED_EARTH``
     - ``"scorched_earth"``


ThreadPhase
^^^^^^^^^^^

Attention thread intelligence phase progression.

.. list-table::
   :header-rows: 1
   :widths: 30 30 30

   * - Member
     - Value
     - Intel threshold
   * - ``DORMANT``
     - ``"dormant"``
     - < 0.1
   * - ``MONITORING``
     - ``"monitoring"``
     - >= 0.1
   * - ``ACTIVE_INVESTIGATION``
     - ``"active_investigation"``
     - >= 0.4
   * - ``DISRUPTION``
     - ``"disruption"``
     - >= 0.7


SurveillanceMethod
^^^^^^^^^^^^^^^^^^

Intelligence collection methods. Each reveals different network aspects.

.. list-table::
   :header-rows: 1
   :widths: 20 20

   * - Member
     - Value
   * - ``SIGNALS``
     - ``"signals"``
   * - ``FINANCIAL``
     - ``"financial"``
   * - ``SOCIAL_MEDIA``
     - ``"social_media"``
   * - ``INFORMANT``
     - ``"informant"``
   * - ``PHYSICAL``
     - ``"physical"``


Entity Models
-------------

All entity models use ``ConfigDict(frozen=True)``. Mutation via
``model_copy(update={...})`` only.

FactionBalance
^^^^^^^^^^^^^^

:mod:`babylon.models.entities.state_apparatus_ai`

Three-faction weight vector. Weights must sum to 1.0 (within 0.01
tolerance, enforced by model validator).

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 20

   * - Field
     - Type
     - Constraints
     - Default
   * - ``finance_capital``
     - ``float``
     - ``ge=0.0, le=1.0``
     - required
   * - ``security_state``
     - ``float``
     - ``ge=0.0, le=1.0``
     - required
   * - ``settler_populist``
     - ``float``
     - ``ge=0.0, le=1.0``
     - required
   * - ``stability``
     - ``Probability``
     - ``[0.0, 1.0]``
     - required
   * - ``legitimacy``
     - ``Probability``
     - ``[0.0, 1.0]``
     - required

**Computed property:**

- ``dominant_faction`` -> ``StateFaction``: faction with the highest weight.


StateBudget
^^^^^^^^^^^

:mod:`babylon.models.entities.state_apparatus_ai`

.. list-table::
   :header-rows: 1
   :widths: 25 25 30

   * - Field
     - Type
     - Constraints
   * - ``revenue``
     - ``float``
     - ``ge=0.0``
   * - ``available``
     - ``float``
     - ``ge=0.0``; cannot exceed ``revenue + 0.01``
   * - ``allocated``
     - ``dict[StateActionType, float]``
     - keys must be top-level verbs; values ``>= 0.0``; sum <= ``revenue + 0.01``
   * - ``imperial_rent_pool``
     - ``float``
     - ``ge=0.0``


StateAction
^^^^^^^^^^^

:mod:`babylon.models.entities.state_apparatus_ai`

Model validator enforces ``sub_verb`` is a valid child of ``verb`` via
``VERB_CHILDREN``.

.. list-table::
   :header-rows: 1
   :widths: 22 22 20 15

   * - Field
     - Type
     - Constraints
     - Default
   * - ``verb``
     - ``StateActionType``
     - must be in ``TOP_LEVEL_VERBS``
     - required
   * - ``sub_verb``
     - ``StateActionType``
     - must be in ``VERB_CHILDREN[verb]``
     - required
   * - ``target_id``
     - ``str | None``
     -
     - ``None``
   * - ``budget_cost``
     - ``float``
     - ``ge=0.0``
     - required
   * - ``thread_cost``
     - ``int``
     - ``ge=0``
     - required
   * - ``legitimacy_cost``
     - ``float``
     -
     - required
   * - ``faction_alignment``
     - ``StateFaction``
     -
     - required
   * - ``parameters``
     - ``dict[str, Any]``
     -
     - ``{}``


LegalFramework
^^^^^^^^^^^^^^

:mod:`babylon.models.entities.state_apparatus_ai`

Model validator enforces ``law_type`` is in ``VALID_LAW_TYPES``.

.. list-table::
   :header-rows: 1
   :widths: 25 20 35

   * - Field
     - Type
     - Constraints
   * - ``framework_id``
     - ``str``
     - ``min_length=1``
   * - ``law_type``
     - ``str``
     - one of: ``SURVEILLANCE_EXPANSION``, ``CRIMINALIZATION``, ``EMERGENCY_POWERS``, ``ZONING_CHANGE``, ``TAX_INCENTIVE``, ``LABOR_RESTRICTION``
   * - ``scope``
     - ``str``
     - JurisdictionLevel value
   * - ``severity``
     - ``Probability``
     - ``[0.0, 1.0]``
   * - ``effects``
     - ``dict[str, float]``
     -
   * - ``created_tick``
     - ``int``
     - ``ge=0``
   * - ``creating_apparatus_id``
     - ``str``
     - ``min_length=1``


AttentionThread
^^^^^^^^^^^^^^^

:mod:`babylon.models.entities.attention_thread`

Model validator enforces ``target_type`` is in ``VALID_TARGET_TYPES``
(``"organization"``, ``"territory"``, ``"community"``).

.. list-table::
   :header-rows: 1
   :widths: 22 22 20 15

   * - Field
     - Type
     - Constraints
     - Default
   * - ``thread_id``
     - ``str``
     - ``min_length=1``
     - required
   * - ``target_type``
     - ``str``
     - in ``VALID_TARGET_TYPES``
     - required
   * - ``target_id``
     - ``str``
     - ``min_length=1``
     - required
   * - ``phase``
     - ``ThreadPhase``
     -
     - required
   * - ``intensity``
     - ``Probability``
     - ``[0.0, 1.0]``
     - required
   * - ``intel_completeness``
     - ``Probability``
     - ``[0.0, 1.0]``
     - required
   * - ``surveillance_methods``
     - ``list[SurveillanceMethod]``
     -
     - ``[]``
   * - ``observed_node_ids``
     - ``frozenset[str]``
     -
     - ``frozenset()``
   * - ``observed_edge_ids``
     - ``frozenset[tuple[str, str]]``
     -
     - ``frozenset()``
   * - ``stickiness``
     - ``Probability``
     - ``[0.0, 1.0]``
     - required
   * - ``ticks_active``
     - ``int``
     - ``ge=0``
     - required
   * - ``owning_apparatus_id``
     - ``str``
     - ``min_length=1``
     - required


SparrowAnalysis
^^^^^^^^^^^^^^^

:mod:`babylon.models.entities.attention_thread`

.. list-table::
   :header-rows: 1
   :widths: 25 35

   * - Field
     - Type
   * - ``thread_id``
     - ``str`` (``min_length=1``)
   * - ``tick``
     - ``int`` (``ge=0``)
   * - ``centrality_rankings``
     - ``dict[str, dict[str, float]]`` (node_id -> {metric: score})
   * - ``equivalence_classes``
     - ``list[frozenset[str]]``
   * - ``identified_singletons``
     - ``frozenset[str]``
   * - ``known_cutsets``
     - ``list[frozenset[str]]``
   * - ``confidence``
     - ``Probability``


Constants and Mappings
^^^^^^^^^^^^^^^^^^^^^^

:mod:`babylon.models.entities.state_apparatus_ai`

- ``VERB_CHILDREN: dict[StateActionType, frozenset[StateActionType]]``
  -- Authoritative parent-child verb hierarchy. Keys are the six
  top-level verbs; values are frozensets of valid sub-verbs.
- ``TOP_LEVEL_VERBS: frozenset[StateActionType]`` -- The six keys of
  ``VERB_CHILDREN``.
- ``ALL_SUB_VERBS: frozenset[StateActionType]`` -- Union of all values
  in ``VERB_CHILDREN``.
- ``VALID_LAW_TYPES: frozenset[str]`` -- The six permitted law type
  strings.
- ``get_parent_verb(sub_verb: StateActionType) -> StateActionType | None``
  -- Returns the parent verb of a sub-verb, or ``None`` if the input is
  itself top-level.


Event Types
-----------

Six ``EventType`` members added in :mod:`babylon.models.enums`:

.. list-table::
   :header-rows: 1
   :widths: 35 40

   * - EventType
     - Value
   * - ``STATE_ACTION_EXECUTED``
     - ``"state_action_executed"``
   * - ``FASCIST_CONVERGENCE``
     - ``"fascist_convergence"``
   * - ``FACTION_SHIFT``
     - ``"faction_shift"``
   * - ``THREAD_ESCALATION``
     - ``"thread_escalation"``
   * - ``LEGAL_FRAMEWORK_ENACTED``
     - ``"legal_framework_enacted"``
   * - ``LEGAL_FRAMEWORK_REVOKED``
     - ``"legal_framework_revoked"``

Three ``EdgeType`` members for graph relationships:

- ``TARGETS`` -- AttentionThread -> target entity
- ``OWNED_BY`` -- AttentionThread -> StateApparatus
- ``JURISDICTION`` -- LegalFramework -> Territory

.. note::

   These EventType members are declared in the enum but not yet emitted
   by any system. They define the integration surface for downstream
   consumers. The OODA dispatch path converts ``StateAction`` results
   into legacy ``Action`` objects for the existing resolution pipeline.


Decision Engine
---------------

NPCDecisionStrategy Protocol
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.protocols`

``@runtime_checkable`` protocol for state AI decision strategies.

.. code-block:: python

   def select_action(
       self,
       org_id: str,
       org_attrs: dict[str, Any],
       graph: Any,
       context: dict[str, Any],
       defines: StateApparatusAIDefines,
   ) -> list[StateAction]: ...


RuleBasedStateAI
^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.decision`

Implements the faction-weighted OODA decision loop. The actual
``select_action`` method signature differs from the protocol, using
fully-typed parameters:

.. code-block:: python

   def select_action(
       self,
       org_id: str,
       faction_balance: FactionBalance,
       budget: StateBudget,
       heat: float,
       defines: StateApparatusAIDefines,
       rng_seed: int | None = None,
   ) -> list[StateAction]: ...

**OODA cycle:**

1. **OBSERVE+ORIENT**: ``_generate_candidates()`` enumerates all
   sub-verbs whose ``budget_cost <= budget.available``.
2. **DECIDE**: Each candidate scored via ``score_action()`` (weighted
   dot product of faction objectives) plus
   ``compute_heat_escalation_score()`` plus a small random tiebreaker.
3. **ACT**: Top ``defines.actions_per_tick`` candidates selected within
   remaining budget.

.. code-block:: python

   def get_debug_state(
       self,
       defines: StateApparatusAIDefines,
       faction_balance: FactionBalance | None = None,
       budget: StateBudget | None = None,
       last_actions: list[StateAction] | None = None,
   ) -> dict[str, Any] | None: ...

Returns ``None`` when ``defines.god_mode_enabled`` is ``False``.

**Scoring functions** (module-level):

.. code-block:: python

   def finance_capital_objective(action: StateAction, heat: float) -> float: ...
   def security_state_objective(action: StateAction, heat: float) -> float: ...
   def settler_populist_objective(action: StateAction, heat: float) -> float: ...
   def score_action(action: StateAction, balance: FactionBalance, heat: float) -> float: ...


Escalation
^^^^^^^^^^

:mod:`babylon.ooda.state_ai.escalation`

.. code-block:: python

   def get_escalation_rank(
       sub_verb: StateActionType,
       defines: StateApparatusAIDefines,
   ) -> int: ...

Returns 0-based index in ``defines.escalation_ladder``, or ``-1`` if not
present.

.. code-block:: python

   def compute_heat_escalation_score(
       heat: float,
       escalation_rank: int,
       max_rank: int,
   ) -> float: ...

Returns score in ``[0.0, 2.0]``. Formula:
``max(0, 1 - |heat - rank/max_rank|) * 2.0``.


Faction Dynamics
^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.faction_dynamics`

.. code-block:: python

   def apply_player_action_shift(
       action_type: str,
       outcome: str,
       current_balance: FactionBalance,
       defines: StateApparatusAIDefines,
   ) -> FactionBalance: ...

Valid ``action_type`` keys: ``"heat_generation"``,
``"surviving_repression"``, ``"extraction_disruption"``,
``"narrative_victory"``, ``"legitimacy_building"``. Outcome ``"success"``
applies full magnitude; otherwise ``0.5x``.

.. code-block:: python

   def apply_repression_failure_shift(
       current_balance: FactionBalance,
       membership_retained_ratio: float,
       defines: StateApparatusAIDefines,
   ) -> FactionBalance: ...

No-op if ``membership_retained_ratio <= 0.5``. Otherwise shifts
Security-State weight down proportionally to ``(retained - 0.5) * 2.0``.

.. code-block:: python

   def apply_material_condition_shift(
       condition_type: str,
       magnitude: float,
       current_balance: FactionBalance,
       defines: StateApparatusAIDefines,
   ) -> FactionBalance: ...

Valid ``condition_type`` keys: ``"profit_rate_decline"``,
``"legitimacy_crisis"``, ``"imperial_rent_contraction"``,
``"successful_co_opt"``.

.. code-block:: python

   def renormalize_faction_balance(
       balance: FactionBalance,
       max_shift: float,
       previous_balance: FactionBalance,
   ) -> FactionBalance: ...

Iterative clamp-normalize (up to 5 iterations). No per-faction delta
exceeds ``max_shift``.

.. code-block:: python

   def compute_stability(
       shift_history: list[FactionBalance],
       window: int,
   ) -> float: ...

Returns ``[0.0, 1.0]``. Formula:
``max(0, 1 - total_variance / 0.10)``.

.. code-block:: python

   def apply_fascist_overrides(
       actions: list[StateAction],
       balance: FactionBalance,
       defines: StateApparatusAIDefines,
   ) -> list[StateAction]: ...

Active when ``is_fascist_convergence()`` conditions hold. Redirections:
``CO_OPT -> REPRESS.RAID``, ``DEVELOP -> DEVELOP.DISPLACE``,
``WITHDRAW -> WITHDRAW.SCORCHED_EARTH``.


Effect Resolution
-----------------

Territory Effects
^^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.territory_effects`

All functions accept ``dict[str, Any]`` territory representations and
return new dicts (no in-place mutation).

.. code-block:: python

   def resolve_invest(territory: dict[str, Any], defines: StateApparatusAIDefines) -> dict[str, Any]: ...
   def resolve_neglect(territory: dict[str, Any], defines: StateApparatusAIDefines) -> dict[str, Any]: ...

.. code-block:: python

   def resolve_displace(
       territory: dict[str, Any],
       defines: StateApparatusAIDefines,
   ) -> tuple[dict[str, Any], int]: ...

Returns ``(updated_territory, displaced_count)``.

.. code-block:: python

   def resolve_strategic_withdrawal(
       territory: dict[str, Any],
       defines: StateApparatusAIDefines,
       asset_extraction: bool = False,
   ) -> tuple[dict[str, Any], float]: ...

Returns ``(updated_territory, budget_recovered)``.

.. code-block:: python

   def resolve_scorched_earth(
       territory: dict[str, Any],
       defines: StateApparatusAIDefines,
   ) -> tuple[dict[str, Any], float]: ...

Returns ``(updated_territory, legitimacy_cost)``.

.. code-block:: python

   def compute_heat_accumulation(current_heat: float, high_profile_count: int, low_profile_count: int, defines: StateApparatusAIDefines) -> float: ...
   def compute_heat_decay(current_heat: float, has_presence: bool, defines: StateApparatusAIDefines) -> float: ...
   def compute_propagandize_effect(collective_identity: float, base_delta: float, defines: StateApparatusAIDefines) -> float: ...
   def compute_scorched_earth_legitimacy(territory_type: str, defines: StateApparatusAIDefines) -> float: ...
   def check_recruit_effectiveness(has_presence: bool, base_effectiveness: float, defines: StateApparatusAIDefines) -> float: ...
   def assess_territory_threat(territory_ci: float, territory_heat: float, defines: StateApparatusAIDefines) -> float: ...

.. code-block:: python

   def resolve_eviction_cascade(
       source_territory: dict[str, Any],
       neighbor_territories: list[dict[str, Any]],
       displaced_count: int,
       defines: StateApparatusAIDefines,
   ) -> tuple[dict[str, Any], list[dict[str, Any]]]: ...


CO-OPT Effects
^^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.co_opt_effects`

.. code-block:: python

   def resolve_propagandize(
       territory: dict[str, Any],
       narrative: str,
       intensity: float,
       defines: StateApparatusAIDefines,
   ) -> dict[str, Any]: ...

Valid narratives: ``"we_are_all_americans"`` (1.0x), ``"reform_is_working"``
(0.7x), ``"threat_narrative"`` (0.5x), ``"delegitimize_opposition"`` (0.3x).
``"threat_narrative"`` increases settler CI instead of reducing target CI.

.. code-block:: python

   def compute_incorporate_probability(
       coherence: float,
       collective_identity: float,
       offer_attractiveness: float,
       defines: StateApparatusAIDefines,
   ) -> float: ...

Formula: ``(1 - coherence) * (1 - CI) * max(offer, base_attractiveness)``.

.. code-block:: python

   def resolve_divide(
       current_edge_type: str,
       has_prior_surveil: bool,
       defines: StateApparatusAIDefines,
   ) -> str: ...

Degrades edges: ``solidaristic -> transactional -> antagonistic``.
No-op when ``divide_requires_prior_surveil=True`` and no prior surveil.

.. code-block:: python

   def resolve_bribe(
       target: dict[str, Any],
       bribe_amount: float,
       defines: StateApparatusAIDefines,
   ) -> dict[str, Any]: ...

Increases ``wealth``, decreases ``r_tendency``, increases ``l_tendency``.


REPRESS Effects
^^^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.repress_effects`

.. code-block:: python

   def resolve_infiltrate(
       target_org: dict[str, Any],
       thread: dict[str, Any],
       agent_type: str,
       defines: StateApparatusAIDefines,
       rng_seed: int,
       current_tick: int = 0,
   ) -> tuple[dict[str, Any], dict[str, Any], bool]: ...

Returns ``(updated_thread, infiltration_record, detected)``. Valid
``agent_type``: ``"INFORMANT"``, ``"PROVOCATEUR"``, ``"MOLE"``.
PROVOCATEUR has 1.5x detection chance. Raises ``ValueError`` for
invalid agent type.

.. code-block:: python

   def compute_raid_consciousness_effect(
       ci: float,
       defines: StateApparatusAIDefines,
   ) -> float: ...

Returns ``+raid_ci_radicalization_boost`` if
``ci >= raid_ci_radicalization_threshold``, else
``-raid_ci_suppression_rate``. This is the consciousness dialectic:
raids crush low-CI communities but radicalize high-CI ones.

.. code-block:: python

   def resolve_raid(
       target_org: dict[str, Any],
       territory: dict[str, Any],
       scale: str,
       force_level: str,
       thread_intel: float,
       key_figure_ids: list[str],
       defines: StateApparatusAIDefines,
       rng_seed: int,
   ) -> tuple[dict[str, Any], dict[str, Any], list[str], float]: ...

Returns ``(updated_org, updated_territory, captured_figure_ids,
legitimacy_cost)``. Valid scales: ``"TARGETED"``, ``"SWEEP"``,
``"MASS"``. Valid force levels: ``"POLICE"``, ``"SWAT"``,
``"MILITARY"``. MASS scale damages ``community_infrastructure_quality``.

.. code-block:: python

   def resolve_prosecute(
       target_org: dict[str, Any],
       target_key_figure_id: str | None,
       charge: str,
       defines: StateApparatusAIDefines,
       rng_seed: int,
       current_tick: int = 0,
   ) -> tuple[dict[str, Any], dict[str, Any], float]: ...

Returns ``(updated_org, prosecution_record, legitimacy_delta)``. Valid
charges: ``"CONSPIRACY"``, ``"RACKETEERING"``, ``"TAX"``,
``"CIVIL_RIGHTS_VIOLATION"``, ``"TERRORISM"``. Legitimacy delta is
positive on conviction, negative on acquittal.

.. code-block:: python

   def resolve_liquidate(
       target_org: dict[str, Any],
       target_key_figure_id: str,
       method: str,
       deniability: float,
       territory_type: str,
       liquidate_available_in_core: bool,
       is_singleton: bool,
       defines: StateApparatusAIDefines,
   ) -> tuple[dict[str, Any], float, bool]: ...

Returns ``(updated_org, legitimacy_cost, org_collapsed)``. Valid
methods: ``"ASSASSINATION"``, ``"DISAPPEARANCE"``, ``"RENDITION"``,
``"PRISON_KILLING"``. Raises ``ValueError`` for CORE territory without
``liquidate_available_in_core=True`` (requires EMERGENCY_POWERS).


ADMINISTER Effects
^^^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.administer_effects`

.. code-block:: python

   def resolve_fund(
       apparatus: dict[str, Any],
       capacity_type: str,
       defines: StateApparatusAIDefines,
   ) -> dict[str, Any]: ...

Valid ``capacity_type``: ``"violence"``, ``"surveillance"``,
``"service"``. Increments the corresponding capacity field by
``fund_capacity_increment``, capped at ``1.0``.

.. code-block:: python

   def resolve_staff(
       apparatus: dict[str, Any],
       current_pool_size: int,
       count: int,
       defines: StateApparatusAIDefines,
   ) -> tuple[dict[str, Any], int]: ...

Returns ``(updated_apparatus, new_pool_size)``. Capped by
``staff_max_per_tick`` and ``thread_pool_max``. No-op if
``surveillance_capacity <= 0.0``.

.. code-block:: python

   def resolve_audit(
       apparatus: dict[str, Any],
       active_infiltrations: list[dict[str, Any]],
       depth: str,
       defines: StateApparatusAIDefines,
       rng_seed: int,
   ) -> tuple[dict[str, Any], list[dict[str, Any]]]: ...

Returns ``(updated_apparatus, detected_infiltrations)``. Valid depths:
``"ROUTINE"`` (0.2 chance), ``"THOROUGH"`` (0.5 chance), ``"DEEP"``
(0.8 chance).


LEGISLATE Effects
^^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.legislate_effects`

.. code-block:: python

   def consume_legal_framework_effects(
       active_frameworks: list[dict[str, Any]],
       baseline: dict[str, Any],
       defines: StateApparatusAIDefines,
   ) -> dict[str, Any]: ...

Idempotent: each ``law_type`` applied at most once regardless of
framework count. Effects by law type:

- ``EMERGENCY_POWERS``: multiplies ``thread_pool_max`` by
  ``emergency_powers_thread_multiplier``, sets
  ``liquidate_in_core=True``.
- ``SURVEILLANCE_EXPANSION``: adds ``surveillance_expansion_intel_bonus``
  to ``intel_bonus``.


Observability
^^^^^^^^^^^^^

:mod:`babylon.ooda.state_ai.observability`

.. code-block:: python

   def create_observable_action(
       action: StateAction,
       territory_heat: float,
   ) -> dict[str, Any]: ...

Returns ``{verb, sub_verb, target_id, visible_intensity,
territory_heat}``. Visible intensity formula:
``min(1, budget_cost/20) * 0.7 + heat * 0.3``.

.. code-block:: python

   def create_territory_observables(
       territory: dict[str, Any],
   ) -> dict[str, Any]: ...

Returns ``{property_value_proxy, infrastructure_quality, heat,
population, collective_identity}``.

.. code-block:: python

   def resolve_counter_intel(
       intel_success: float,
       faction_balance: FactionBalance,
       last_actions: list[StateAction],
       defines: StateApparatusAIDefines,
   ) -> dict[str, Any]: ...

Tiered disclosure by ``intel_success``:

- ``>= 0.0``: ``intel_level``, ``visible_actions`` (verb + target only)
- ``>= 0.3``: adds ``faction_balance`` (rounded to 2 decimals)
- ``>= 0.6``: adds ``action_details`` (verb, sub_verb, target,
  budget_cost, faction_alignment)
- ``>= 0.8``: adds ``full_state`` (dominant_faction, stability,
  legitimacy)


Attention / Intelligence
------------------------

G_observed Construction
^^^^^^^^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.attention.observation`

.. code-block:: python

   def build_g_observed(
       thread: AttentionThread,
       full_graph: nx.DiGraph[str],
   ) -> nx.DiGraph[str]: ...

Builds subgraph from ``thread.observed_node_ids`` and
``thread.observed_edge_ids`` with method-specific distortions. Node cap:
1000. Edge cap: 5000.

Distortion rules:

- ``SIGNALS`` only: sets ``edge_type = "observed_connection"``
- ``FINANCIAL`` only: non-monetary edges get ``distorted=True,
  confidence=0.3``

.. code-block:: python

   def compute_observation_ceiling(
       base_ceiling: float,
       compartmentalization_factor: float,
   ) -> float: ...

Formula: ``base_ceiling * (1 - compartmentalization_factor)``, clamped
to ``[0.0, 1.0]``.


Sparrow Analysis
^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.attention.sparrow`

.. code-block:: python

   def analyze_network(
       thread_id: str,
       tick: int,
       g_observed: nx.DiGraph[str],
       confidence: float = 0.8,
   ) -> SparrowAnalysis: ...

Computes degree, betweenness, and closeness centrality. Equivalence
classes by degree signature. Singletons: nodes with betweenness > 2x
mean. Cutsets: NetworkX articulation points (on undirected view).
Returns empty ``SparrowAnalysis`` for empty graphs.


Thread Lifecycle
^^^^^^^^^^^^^^^^

:mod:`babylon.ooda.attention.thread_manager`

.. code-block:: python

   def allocate_threads(
       existing_threads: list[AttentionThread],
       target_scores: dict[str, float],
       pool_size: int,
       defines: StateApparatusAIDefines,
   ) -> list[AttentionThread]: ...

Greedy allocation. Stickiness bonus =
``minimum_effect_floor * 5.0 * ticks_active``, capped at 1.0.

.. code-block:: python

   def advance_thread_phase(
       thread: AttentionThread,
       defines: StateApparatusAIDefines,
   ) -> AttentionThread: ...

One-directional phase advancement (no regression). Thresholds from
``defines.thread_escalation_thresholds``.

Phase-to-methods mapping:

- ``DORMANT`` -> ``[]``
- ``MONITORING`` -> ``[SIGNALS]``
- ``ACTIVE_INVESTIGATION`` -> ``[SIGNALS, FINANCIAL]``
- ``DISRUPTION`` -> ``[SIGNALS, FINANCIAL, INFORMANT]``

.. code-block:: python

   def update_thread_tick(
       thread: AttentionThread,
       intel_gain: float,
       observation_ceiling: float,
   ) -> AttentionThread: ...

Increments ``ticks_active`` by 1. Increments ``intel_completeness`` by
``intel_gain``, capped at ``observation_ceiling`` and ``1.0``.


Formulas
--------

:mod:`babylon.formulas.state_ai`

.. code-block:: python

   def calculate_faction_shift(
       heat: float,
       current_balance: FactionBalance,
       defines: StateApparatusAIDefines,
   ) -> FactionBalance: ...

Heat-driven Security-State weight adjustment:

- ``heat > 0.5``: SS gains up to ``(heat - 0.5) * 0.2``, clamped to
  ``max_shift``. FC/SP absorb loss proportionally.
- ``heat < 0.3``: SS loses ``(0.3 - heat) * 0.1 * 0.5``. FC recovers
  60%, SP 40%.
- ``0.3 <= heat <= 0.5``: no change.

.. code-block:: python

   def is_fascist_convergence(
       balance: FactionBalance,
       settler_ci: float,
       consecutive_ticks: int,
       defines: StateApparatusAIDefines,
   ) -> bool: ...

Three-pillar check (all strict inequalities):

1. ``SS > fascist_security_threshold`` (default 0.4)
2. ``settler_ci > fascist_settler_ci_threshold`` (default 0.6)
3. ``FC < fascist_finance_ceiling`` (default 0.25)
4. ``consecutive_ticks >= convergence_confirmation_ticks`` (default 2)

.. code-block:: python

   def check_fascist_reversion(
       balance: FactionBalance,
       settler_ci: float,
       defines: StateApparatusAIDefines,
   ) -> bool: ...

Exit thresholds (asymmetrically harder than entry):

1. ``SS < reversion_ss_threshold`` (default 0.25)
2. ``settler_ci < reversion_ci_threshold`` (default 0.30)


Configuration
-------------

:class:`StateApparatusAIDefines` in :mod:`babylon.config.defines`.
Frozen ``BaseModel``. All fields tagged ``[S] SYNTHETIC``.

Faction Dynamics
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``max_faction_shift_per_tick``
     - float
     - 0.05
     - [0.0, 0.2]
   * - ``minimum_effect_floor``
     - float
     - 0.02
     - [0.0, 0.1]
   * - ``heat_to_ss_coefficient``
     - float
     - 0.1
     - [0.0, 1.0]

Fascist Convergence
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``fascist_security_threshold``
     - float
     - 0.4
     - [0.0, 1.0]
   * - ``fascist_settler_ci_threshold``
     - float
     - 0.6
     - [0.0, 1.0]
   * - ``fascist_finance_ceiling``
     - float
     - 0.25
     - [0.0, 1.0]
   * - ``convergence_confirmation_ticks``
     - int
     - 2
     - [1, 10]
   * - ``reversion_ss_threshold``
     - float
     - 0.25
     - [0.0, 1.0]
   * - ``reversion_ci_threshold``
     - float
     - 0.30
     - [0.0, 1.0]

Attention Threads
^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``thread_pool_base``
     - int
     - 5
     - [1, 50]
   * - ``thread_pool_max``
     - int
     - 8
     - [1, 100]
   * - ``thread_escalation_thresholds``
     - dict
     - ``{dormant_to_monitoring: 0.1, monitoring_to_active: 0.4, active_to_disruption: 0.7}``
     -

Budget
^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``detroit_2010_annual_budget``
     - float
     - 100.0
     - ge=0.0
   * - ``actions_per_tick``
     - int
     - 1
     - [1, 10]

Territory Effects
^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``develop_infrastructure_boost``
     - float
     - 0.1
     - [0.0, 1.0]
   * - ``neglect_infrastructure_decay``
     - float
     - 0.05
     - [0.0, 1.0]
   * - ``displace_population_fraction``
     - float
     - 0.1
     - [0.0, 1.0]
   * - ``neglect_quality_floor``
     - float
     - 0.1
     - [0.0, 1.0]
   * - ``consciousness_resistance_factor``
     - float
     - 0.5
     - [0.0, 1.0]
   * - ``high_profile_heat_rate``
     - float
     - 0.1
     - [0.0, 1.0]
   * - ``low_profile_heat_rate``
     - float
     - 0.02
     - [0.0, 1.0]
   * - ``heat_escalation_threshold``
     - float
     - 0.6
     - [0.0, 1.0]
   * - ``scorched_earth_legitimacy_core``
     - float
     - 0.15
     - [0.0, 1.0]
   * - ``scorched_earth_legitimacy_periphery``
     - float
     - 0.03
     - [0.0, 1.0]
   * - ``strategic_withdrawal_decay_multiplier``
     - float
     - 2.0
     - [1.0, 10.0]
   * - ``strategic_withdrawal_asset_recovery``
     - float
     - 0.5
     - [0.0, 1.0]
   * - ``displace_ci_reduction``
     - float
     - 0.2
     - [0.0, 1.0]
   * - ``displace_community_infra_reduction``
     - float
     - 0.3
     - [0.0, 1.0]

Spatial Dynamics
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``heat_decay_rate``
     - float
     - 0.05
     - [0.0, 1.0]
   * - ``recruit_no_presence_penalty``
     - float
     - 0.9
     - [0.0, 1.0]
   * - ``eviction_scatter_ci_loss``
     - float
     - 0.15
     - [0.0, 1.0]

CO-OPT Effects
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``propagandize_base_delta``
     - float
     - 0.05
     - [0.0, 0.5]
   * - ``incorporate_base_attractiveness``
     - float
     - 0.3
     - [0.0, 1.0]
   * - ``bribe_consciousness_shift``
     - float
     - 0.05
     - [0.0, 0.5]
   * - ``bribe_liberal_increase``
     - float
     - 0.03
     - [0.0, 0.5]
   * - ``divide_requires_prior_surveil``
     - bool
     - True
     -
   * - ``incorporate_requires_prior_surveil``
     - bool
     - True
     -

ADMINISTER Effects
^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``fund_capacity_increment``
     - float
     - 0.05
     - [0.0, 0.5]
   * - ``staff_thread_cost``
     - float
     - 3.0
     - [0.0, 50.0]
   * - ``staff_max_per_tick``
     - int
     - 2
     - [1, 10]
   * - ``audit_routine_detection_chance``
     - float
     - 0.2
     - [0.0, 1.0]
   * - ``audit_thorough_detection_chance``
     - float
     - 0.5
     - [0.0, 1.0]
   * - ``audit_deep_detection_chance``
     - float
     - 0.8
     - [0.0, 1.0]

REPRESS Effects
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``infiltrate_informant_intel_rate``
     - float
     - 0.05
     - [0.0, 0.5]
   * - ``infiltrate_provocateur_intel_rate``
     - float
     - 0.03
     - [0.0, 0.5]
   * - ``infiltrate_mole_intel_rate``
     - float
     - 0.08
     - [0.0, 0.5]
   * - ``infiltrate_detection_base_chance``
     - float
     - 0.1
     - [0.0, 1.0]
   * - ``raid_ci_radicalization_threshold``
     - float
     - 0.5
     - [0.0, 1.0]
   * - ``raid_ci_radicalization_boost``
     - float
     - 0.1
     - [0.0, 0.5]
   * - ``raid_ci_suppression_rate``
     - float
     - 0.15
     - [0.0, 0.5]
   * - ``raid_org_coherence_damage``
     - float
     - 0.2
     - [0.0, 1.0]
   * - ``raid_key_figure_capture_base``
     - float
     - 0.3
     - [0.0, 1.0]
   * - ``raid_force_multiplier_swat``
     - float
     - 1.5
     - [1.0, 5.0]
   * - ``raid_force_multiplier_military``
     - float
     - 2.5
     - [1.0, 10.0]
   * - ``prosecute_org_morale_damage``
     - float
     - 0.1
     - [0.0, 0.5]
   * - ``prosecute_key_figure_removal_chance``
     - float
     - 0.6
     - [0.0, 1.0]
   * - ``prosecute_terrorism_charge_multiplier``
     - float
     - 1.5
     - [1.0, 5.0]
   * - ``prosecute_legitimacy_boost_success``
     - float
     - 0.02
     - [0.0, 0.1]
   * - ``liquidate_singleton_collapse_chance``
     - float
     - 0.7
     - [0.0, 1.0]
   * - ``liquidate_core_legitimacy_cost``
     - float
     - 0.15
     - [0.0, 0.5]
   * - ``liquidate_periphery_legitimacy_cost``
     - float
     - 0.03
     - [0.0, 0.5]
   * - ``liquidate_deniability_threshold``
     - float
     - 0.5
     - [0.0, 1.0]
   * - ``liquidate_coherence_damage``
     - float
     - 0.3
     - [0.0, 1.0]

LEGISLATE Consumption
^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``emergency_powers_thread_multiplier``
     - float
     - 2.0
     - [1.0, 5.0]
   * - ``emergency_powers_liquidate_in_core``
     - bool
     - True
     -
   * - ``surveillance_expansion_intel_bonus``
     - float
     - 0.1
     - [0.0, 0.5]

Debug
^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 20

   * - Field
     - Type
     - Default
     - Range
   * - ``god_mode_enabled``
     - bool
     - False
     -


OODA Dispatch Integration
-------------------------

The OODA system dispatches state apparatus decisions through the
following path:

1. ``OODASystem.step()`` (``engine/systems/ooda.py``) iterates
   organizations by initiative.
2. For ``OrgType.STATE_APPARATUS``, calls ``select_npc_actions()``
   (``ooda/npc_stub.py``).
3. ``_try_state_ai_dispatch()`` checks for ``faction_balance`` on the
   graph node. If present, instantiates ``RuleBasedStateAI`` and calls
   ``select_action()``.
4. Returned ``list[StateAction]`` is converted to legacy ``list[Action]``
   for the existing resolution pipeline.
5. If ``faction_balance`` is absent, falls through to the legacy
   priority-queue stub (``SURVEIL -> REPRESS -> INFILTRATE ->
   MAP_NETWORK -> COUNTER_INTEL``).

``FactionBalance`` and ``StateBudget`` are stored as graph node
attributes on the ``StateApparatus`` node, not as Pydantic model fields.
They do not survive ``WorldState.to_graph()`` / ``from_graph()``
round-trips via the typed model path.


See Also
--------

- :doc:`organizations` -- Organization base model (Feature 031)
- :doc:`ooda-loop-system` -- OODA loop system (Feature 032)
- :doc:`/concepts/state-apparatus-ai` -- Design rationale and architecture
- :doc:`/how-to/state-apparatus-ai` -- Goal-oriented guides for working
  with the state AI
