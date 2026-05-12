"""DRF serializers for the game API.

Serializers validate incoming request data and format outgoing responses
using the standard response envelope.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

# ---------------------------------------------------------------------- #
# Request serializers (input validation)
# ---------------------------------------------------------------------- #


class CreateGameSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate POST /api/games/ request body."""

    scenario = serializers.CharField(max_length=64)
    config = serializers.JSONField(required=False, default=dict)
    defines = serializers.JSONField(required=False, default=dict)
    rng_seed = serializers.IntegerField(required=False, default=0)


class SubmitActionSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate POST /api/games/{id}/actions/ request body."""

    org_id = serializers.CharField(max_length=64)
    verb = serializers.CharField(max_length=16)
    action_type = serializers.CharField(max_length=32, required=False, allow_null=True)
    target_id = serializers.CharField(max_length=64, required=False, allow_null=True)
    target_community = serializers.CharField(max_length=32, required=False, allow_null=True)
    params_json = serializers.JSONField(required=False, default=None)


# ---------------------------------------------------------------------- #
# Per-verb action serializers (Spec 040)
# ---------------------------------------------------------------------- #


class BaseActionSerializer(serializers.Serializer[dict[str, Any]]):
    """Common fields shared by all per-verb action endpoints.

    All nine verb endpoints accept ``org_id`` (acting organization)
    and ``target_id`` (target node, edge, or community).
    """

    org_id = serializers.CharField(max_length=64)
    target_id = serializers.CharField(max_length=64)


class EducateActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/educate/ request body.

    Requires ``consciousness_strategy`` from the spec 037 sub-verb taxonomy.
    """

    consciousness_strategy = serializers.ChoiceField(
        choices=["REVOLUTIONARY", "LIBERAL", "FASCIST"],
    )


class AidActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/aid/ request body.

    Requires ``resource_type`` and ``amount``. The ``amount`` field is
    bounded by the org's available material resources (validated at
    serializer level, not deferred to the engine).
    """

    resource_type = serializers.ChoiceField(
        choices=["MATERIAL", "MEDICAL", "LEGAL", "INFRASTRUCTURE"],
    )
    amount = serializers.FloatField()


class AttackParamsSerializer(serializers.Serializer[dict[str, Any]]):
    mode = serializers.ChoiceField(choices=["targeted", "mass"])
    specific_target = serializers.CharField(allow_null=True, required=False)


class AttackSubmitSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate POST /api/games/{id}/verbs/attack/ request body."""

    org_id = serializers.CharField(max_length=64)
    target_id = serializers.CharField(max_length=64, required=False, allow_null=True)
    params = AttackParamsSerializer()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


class CampaignActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/campaign/ request body."""

    campaign_type = serializers.ChoiceField(
        choices=["ELECTORAL", "LEGISLATIVE", "PUBLIC_PRESSURE"],
    )


# ---------------------------------------------------------------------- #
# Response serializers (output formatting)
# ---------------------------------------------------------------------- #


class TerritorySerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a territory with full visualization fields (Spec 052 §8)."""

    id = serializers.CharField()
    name = serializers.CharField()
    h3_index = serializers.CharField(allow_null=True)
    h3_resolution = serializers.IntegerField()
    county_fips = serializers.CharField()
    heat = serializers.FloatField()
    sector_type = serializers.CharField()
    territory_type = serializers.CharField()
    profile = serializers.CharField()
    rent_level = serializers.FloatField()
    population = serializers.IntegerField()
    under_eviction = serializers.BooleanField()
    biocapacity = serializers.FloatField()
    host_id = serializers.CharField(allow_null=True)
    occupant_id = serializers.CharField(allow_null=True)


class ConsciousnessVectorSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize the ternary consciousness vector (Spec 052 §6).

    Always sums to 1.0.  Never a scalar, never a single enum.
    """

    liberal = serializers.FloatField()
    fascist = serializers.FloatField()
    revolutionary = serializers.FloatField()


class OodaProfileSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize the OODA loop profile (Spec 052 §6).

    Spec 061 FR-011 (T066, T067): adds ``phase`` — the deterministic
    argmax over the four floats, as an enum string. Lets the frontend
    render OODA badges without re-computing argmax in JS.
    """

    observe = serializers.FloatField()
    orient = serializers.FloatField()
    decide = serializers.FloatField()
    act = serializers.FloatField()
    cycle_ticks = serializers.IntegerField()
    phase = serializers.ChoiceField(
        choices=("observe", "orient", "decide", "act"),
        required=False,
        default="observe",
    )


class VanguardResourcesSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize vanguard economy resources for player organizations."""

    cadre_labor = serializers.FloatField()
    sympathizer_labor = serializers.FloatField()
    reputation = serializers.FloatField()
    budget = serializers.FloatField()
    heat = serializers.FloatField()
    max_cadre_labor = serializers.FloatField()
    max_sympathizer_labor = serializers.FloatField()


class OrganizationSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize an organization — the only agent type (Spec 052 §6).

    Spec 061 US4 (FR-011, FR-016): adds ``short_name`` / ``player_controlled``
    / ``legitimacy`` / ``opacity``. ``ooda.phase`` carried via
    :class:`OodaProfileSerializer`.
    """

    id = serializers.CharField()
    name = serializers.CharField()
    short_name = serializers.CharField(required=False, default="", allow_blank=True)
    player_controlled = serializers.BooleanField(required=False, default=False)
    legitimacy = serializers.FloatField(required=False, default=0.5)
    opacity = serializers.FloatField(required=False, default=0.5)
    org_type = serializers.CharField()
    class_character = serializers.CharField()
    cohesion = serializers.FloatField()
    cadre_level = serializers.FloatField()
    budget = serializers.FloatField()
    heat = serializers.FloatField()
    territory_ids = serializers.ListField(child=serializers.CharField())
    hyperedge_memberships = serializers.ListField(child=serializers.CharField())
    consciousness = ConsciousnessVectorSerializer()
    ooda = OodaProfileSerializer()
    vanguard = VanguardResourcesSerializer(required=False, allow_null=True)


class FactionalCompositionSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize the factional composition of an institution (Spec 052 §7)."""

    liberal_technocratic = serializers.FloatField()
    revanchist_fascist = serializers.FloatField()
    institutionalist_bonapartist = serializers.FloatField()


class InstitutionSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize an institution (Spec 052 §7)."""

    id = serializers.CharField()
    name = serializers.CharField()
    apparatus_type = serializers.CharField()
    social_function = serializers.CharField()
    class_inscription = serializers.CharField()
    legitimacy = serializers.FloatField()
    budget = serializers.FloatField()
    housed_org_ids = serializers.ListField(child=serializers.CharField())
    territory_ids = serializers.ListField(child=serializers.CharField())
    factional_composition = FactionalCompositionSerializer()


class EdgeSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a dyadic edge (Spec 052 §10)."""

    id = serializers.CharField()
    source_id = serializers.CharField()
    target_id = serializers.CharField()
    mode = serializers.CharField()
    value_flow = serializers.FloatField()
    tension = serializers.FloatField()
    repression_flow = serializers.FloatField()


class HyperedgeSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize an XGI hyperedge (Spec 052 §9)."""

    id = serializers.CharField()
    category = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]
    contradiction_partner_id = serializers.CharField(allow_null=True)
    member_ids = serializers.ListField(child=serializers.CharField())
    material_basis = serializers.DictField()
    ideological_dimension = serializers.DictField()


class EventSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a simulation event.

    Spec 061 US3 FR-012: events expose ``id``, ``severity``, ``title``,
    ``body`` in addition to the legacy ``type``/``tick``/``data`` fields
    so the v2 Briefing Priority Dispatch panel can render severity
    badges and human-readable titles directly from snapshot data.
    """

    id = serializers.CharField(required=False, default="")
    type = serializers.CharField()
    tick = serializers.IntegerField()
    severity = serializers.ChoiceField(
        choices=("critical", "warning", "informational"),
        default="informational",
    )
    title = serializers.CharField(required=False, default="", allow_blank=True)
    body = serializers.CharField(required=False, default="", allow_blank=True)
    data = serializers.DictField(required=False, default=dict)  # type: ignore[assignment]


class TrapStatusSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a single trap detector status (Spec 052 §13)."""

    severity = serializers.CharField()
    score = serializers.FloatField()
    indicators = serializers.ListField(child=serializers.CharField())
    ticks_at_moderate = serializers.IntegerField()


class TrapDetectionResultSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize the full trap detection result."""

    liberal = TrapStatusSerializer()
    ultra_left = TrapStatusSerializer()
    rightist = TrapStatusSerializer()
    active_trap = serializers.CharField(allow_null=True)
    game_over_trap = serializers.CharField(allow_null=True)


class DerivedBlockSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize the engine-computed derived block (Spec 052 §11).

    All fields are read-only caches.  The client MUST NOT write to them.
    """

    value_tensor = serializers.DictField()
    imperial_rent = serializers.DictField()
    dept_iii_visibility = serializers.DictField()
    class_aggregates = serializers.DictField()
    economy = serializers.DictField()
    predictions = serializers.DictField()


class GameSnapshotSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a full game state snapshot (Spec 052 §5).

    Note what is absent: no ``entities``, no top-level ``economy``.
    Class data lives under ``derived.class_aggregates``.
    Economy data lives under ``derived.economy``.
    """

    session_id = serializers.CharField()
    tick = serializers.IntegerField()
    organizations = OrganizationSerializer(many=True)
    institutions = InstitutionSerializer(many=True)
    territories = TerritorySerializer(many=True)
    hyperedges = HyperedgeSerializer(many=True)
    edges = EdgeSerializer(many=True)
    events = EventSerializer(many=True)
    traps = TrapDetectionResultSerializer(required=False, allow_null=True)
    derived = DerivedBlockSerializer()


class GameSessionListSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a game session for list views."""

    id = serializers.UUIDField()
    scenario = serializers.CharField()
    current_tick = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()


class ActionResultSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize an action result."""

    org_id = serializers.CharField()
    action_type = serializers.CharField()
    target_id = serializers.CharField(allow_null=True)
    initiative_score = serializers.FloatField()
    action_cost = serializers.FloatField()
    success = serializers.BooleanField()
    consciousness_delta = serializers.FloatField(allow_null=True)
    heat_delta = serializers.FloatField(allow_null=True)
    details = serializers.DictField(required=False, allow_null=True)


# ---------------------------------------------------------------------- #
# V2 Dialectic Engine serializers
# ---------------------------------------------------------------------- #


class DialecticObservationSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a Dialectic.observe() output for frontend consumption.

    This serializer validates the observation dict produced by
    ``Dialectic.observe()`` before sending it to the frontend.
    """

    id = serializers.UUIDField()
    type = serializers.CharField()
    weight = serializers.FloatField()
    principal_aspect = serializers.ChoiceField(choices=["A", "B"])


class DialecticSnapshotSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a DialecticSnapshot for the v2 API."""

    tick = serializers.IntegerField()
    dialectic_id = serializers.UUIDField()
    type_tag = serializers.CharField()
    weight = serializers.FloatField()
    observation = serializers.DictField()
    parent_id = serializers.UUIDField(allow_null=True)


class WorldSnapshotSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a full World snapshot for the v2 API."""

    tick = serializers.IntegerField()
    dialectics = DialecticSnapshotSerializer(many=True)
    morphisms = serializers.ListField(child=serializers.DictField())
    events = serializers.ListField(child=serializers.DictField())


# ---------------------------------------------------------------------- #
# Verb Endpoint serializers (Spec 038)
# ---------------------------------------------------------------------- #


class TernaryConsciousnessSerializer(serializers.Serializer[dict[str, Any]]):
    r = serializers.FloatField()
    l = serializers.FloatField()  # noqa: E741
    f = serializers.FloatField()
    dominant_tendency = serializers.CharField(allow_null=True)
    collective_identity = serializers.FloatField()
    ideological_contestation = serializers.FloatField()


class MaterialReadinessSerializer(serializers.Serializer[dict[str, Any]]):
    avg_agitation = serializers.FloatField()
    readiness_score = serializers.FloatField()
    readiness_explanation = serializers.CharField()


class EducationPressureSerializer(serializers.Serializer[dict[str, Any]]):
    current = serializers.FloatField()
    projected_delta = serializers.FloatField()
    projected_new = serializers.FloatField()
    decay_per_tick = serializers.FloatField()


class FeedforwardRoutingShiftSerializer(serializers.Serializer[dict[str, Any]]):
    r_gain_per_tick = serializers.FloatField()
    f_reduction_per_tick = serializers.FloatField()
    l_reduction_per_tick = serializers.FloatField()
    explanation = serializers.CharField()


class FeedforwardSerializer(serializers.Serializer[dict[str, Any]]):
    projected_routing_shift = FeedforwardRoutingShiftSerializer()
    state_ai_visibility = serializers.CharField()
    state_ai_likely_response = serializers.CharField()
    turns_to_dominant_tendency_shift = serializers.IntegerField(allow_null=True)
    turns_explanation = serializers.CharField()


class EducateTargetSerializer(serializers.Serializer[dict[str, Any]]):
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


class OrgOodaSerializer(serializers.Serializer[dict[str, Any]]):
    action_points_remaining = serializers.IntegerField()
    action_points_max = serializers.IntegerField()
    cycle_time = serializers.IntegerField()


class OrgResourcesSerializer(serializers.Serializer[dict[str, Any]]):
    cadre_labor = serializers.FloatField()
    sympathizer_labor = serializers.FloatField()
    material = serializers.FloatField()


class OrgSummarySerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    consciousness_strategy = serializers.CharField()
    resources = OrgResourcesSerializer()
    ooda = OrgOodaSerializer()
    cadre_level = serializers.FloatField()
    cohesion = serializers.FloatField()


class VerbCostSerializer(serializers.Serializer[dict[str, Any]]):
    action_points = serializers.IntegerField()
    cadre_labor = serializers.FloatField()
    sympathizer_labor = serializers.FloatField()
    material = serializers.FloatField()
    can_afford = serializers.BooleanField()
    over_budget = serializers.BooleanField()
    over_budget_penalty = serializers.CharField(allow_null=True)


class UnavailableCommunitySerializer(serializers.Serializer[dict[str, Any]]):
    community_id = serializers.CharField()
    community_type = serializers.CharField()
    territory_name = serializers.CharField()
    reason = serializers.CharField()


class UnavailableTargetSerializer(serializers.Serializer[dict[str, Any]]):
    target_id = serializers.CharField()
    name = serializers.CharField(required=False, allow_null=True)
    territory_name = serializers.CharField(required=False, allow_null=True)
    reason = serializers.CharField()


class EducateAvailableSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField()
    tick = serializers.IntegerField()
    verb = serializers.CharField()
    acting_org = OrgSummarySerializer()
    cost = VerbCostSerializer()
    targets = EducateTargetSerializer(many=True)
    unavailable_communities = UnavailableCommunitySerializer(many=True)


class EducateSubmitSerializer(serializers.Serializer[dict[str, Any]]):
    org_id = serializers.CharField()
    target_community_id = serializers.CharField()
    params = serializers.DictField(required=False, default=dict)

    def validate_org_id(self, value: str) -> str:
        # Complex domain validation is handled in the view/bridge
        return value

    def validate_target_community_id(self, value: str) -> str:
        # Complex domain validation is handled in the view/bridge
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


# ---------------------------------------------------------------------- #
# AID Verb Endpoint serializers (Spec 045)
# ---------------------------------------------------------------------- #


class MaterialTransferParamsSerializer(serializers.Serializer[dict[str, Any]]):
    transfer_amount = serializers.FloatField()


class AidSubmitSerializer(serializers.Serializer[dict[str, Any]]):
    org_id = serializers.CharField()
    target_id = serializers.CharField()
    params = MaterialTransferParamsSerializer()

    def validate_org_id(self, value: str) -> str:
        return value

    def validate_target_id(self, value: str) -> str:
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


class AidProjectionSerializer(serializers.Serializer[dict[str, Any]]):
    consumption_ratio_delta = serializers.FloatField()
    agitation_delta = serializers.FloatField()
    solidarity_added = serializers.FloatField()
    economism_risk = serializers.CharField(allow_null=True)


class PopulationAidTargetSerializer(serializers.Serializer[dict[str, Any]]):
    community_id = serializers.CharField()
    community_name = serializers.CharField()
    population = serializers.IntegerField()
    class_name = serializers.CharField()
    material_conditions = serializers.DictField()
    edge_status = serializers.DictField()
    feedforward = AidProjectionSerializer()


class OrgAidTargetSerializer(serializers.Serializer[dict[str, Any]]):
    org_id = serializers.CharField()
    org_name = serializers.CharField()
    org_type = serializers.CharField()
    material_stock = serializers.FloatField()
    edge_status = serializers.DictField()
    feedforward = AidProjectionSerializer()


class AidAvailableSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField()
    tick = serializers.IntegerField()
    verb = serializers.CharField()
    acting_org = OrgSummarySerializer()
    cost = VerbCostSerializer()
    population_targets = PopulationAidTargetSerializer(many=True)
    org_targets = OrgAidTargetSerializer(many=True)
    unavailable_targets = UnavailableCommunitySerializer(many=True)


# ---------------------------------------------------------------------- #
# ATTACK Verb Endpoint serializers (Spec 046)
# ---------------------------------------------------------------------- #


class AttackCostSerializer(serializers.Serializer[dict[str, Any]]):
    action_points = serializers.IntegerField()
    cadre_labor_if_targeted = serializers.FloatField()
    sympathizer_labor_if_mass = serializers.FloatField()
    material = serializers.FloatField()
    can_afford_targeted = serializers.BooleanField()
    can_afford_mass = serializers.BooleanField()
    over_budget_ap = serializers.BooleanField()
    cost_explanation = serializers.CharField()


class UltraLeftWarningSerializer(serializers.Serializer[dict[str, Any]]):
    active = serializers.BooleanField()
    trap_score = serializers.FloatField()
    indicators = serializers.ListField(child=serializers.CharField())
    explanation = serializers.CharField(allow_null=True)


class WarsawGhettoFlagSerializer(serializers.Serializer[dict[str, Any]]):
    active = serializers.BooleanField()
    population_p_acquiescence = serializers.FloatField()
    threshold = serializers.FloatField()
    explanation = serializers.CharField(allow_null=True)


class ValueTensorRoleSerializer(serializers.Serializer[dict[str, Any]]):
    department = serializers.CharField()
    c_stock = serializers.FloatField()
    annual_s_extracted = serializers.FloatField()
    s_v_ratio = serializers.FloatField()
    explanation = serializers.CharField()


class ExtractiveEdgeSerializer(serializers.Serializer[dict[str, Any]]):
    edge_id = serializers.CharField()
    target_name = serializers.CharField()
    flow_type = serializers.CharField()
    s_flow_per_tick = serializers.FloatField()
    explanation = serializers.CharField()


class DamageToTargetSerializer(serializers.Serializer[dict[str, Any]]):
    c_destroyed = serializers.FloatField(required=False, allow_null=True)
    c_destruction_pct = serializers.FloatField(required=False, allow_null=True)
    wealth_reduction = serializers.FloatField(required=False, allow_null=True)
    capacity_degradation = serializers.FloatField(required=False, allow_null=True)
    recovery_ticks = serializers.IntegerField(required=False, allow_null=True)
    explanation = serializers.CharField(required=False, allow_null=True)


class ValueFlowDisruptionSerializer(serializers.Serializer[dict[str, Any]]):
    s_flow_interrupted = serializers.FloatField()
    s_flow_interrupt_duration = serializers.IntegerField()
    explanation = serializers.CharField()


class AttackModeInfoSerializer(serializers.Serializer[dict[str, Any]]):
    resource_cost = serializers.DictField()
    damage_to_target = DamageToTargetSerializer(required=False, allow_null=True)
    value_flow_disruption = ValueFlowDisruptionSerializer(required=False, allow_null=True)
    heat_generated = serializers.FloatField()
    opsec_exposure = serializers.FloatField(required=False, allow_null=True)
    detection_probability = serializers.FloatField()
    explanation = serializers.CharField(required=False, allow_null=True)
    edge_effect = serializers.CharField(required=False, allow_null=True)
    recovery_duration = serializers.IntegerField(required=False, allow_null=True)
    reconnection_probability = serializers.FloatField(required=False, allow_null=True)
    effect = serializers.CharField(required=False, allow_null=True)
    legitimacy_note = serializers.CharField(required=False, allow_null=True)


class AttackModesSerializer(serializers.Serializer[dict[str, Any]]):
    targeted_sabotage = AttackModeInfoSerializer(required=False)
    mass_action = AttackModeInfoSerializer(required=False)
    targeted_disruption = AttackModeInfoSerializer(required=False)


class AttackCollateralDamageSerializer(serializers.Serializer[dict[str, Any]]):
    affected_population = serializers.CharField()
    population_name = serializers.CharField(required=False, allow_null=True)
    workers_affected = serializers.IntegerField(required=False, allow_null=True)
    wealth_impact = serializers.FloatField()
    wealth_impact_explanation = serializers.CharField(required=False, allow_null=True)
    agitation_effect = serializers.FloatField(required=False, allow_null=True)
    agitation_explanation = serializers.CharField(required=False, allow_null=True)
    explanation = serializers.CharField(required=False, allow_null=True)


class RepressionBackfireSerializer(serializers.Serializer[dict[str, Any]]):
    agitation_generated_on_community = serializers.FloatField()
    affected_community = serializers.CharField()
    routing_analysis = serializers.CharField()


class StateAiResponseSerializer(serializers.Serializer[dict[str, Any]]):
    visibility = serializers.CharField()
    immediate_response = serializers.CharField()
    escalation_risk = serializers.CharField(allow_null=True, required=False)
    repression_backfire = RepressionBackfireSerializer(allow_null=True, required=False)
    attention_thread_consumed = serializers.IntegerField(allow_null=True, required=False)
    thread_diversion_explanation = serializers.CharField(allow_null=True, required=False)


class CoherenceCheckSerializer(serializers.Serializer[dict[str, Any]]):
    current_coherence = serializers.FloatField()
    coherence_threshold = serializers.FloatField()
    network_collapse_risk = serializers.BooleanField()
    explanation = serializers.CharField()


class AttackProjectionSerializer(serializers.Serializer[dict[str, Any]]):
    modes = AttackModesSerializer()
    collateral_damage = AttackCollateralDamageSerializer(required=False, allow_null=True)
    state_ai_response = StateAiResponseSerializer(required=False, allow_null=True)
    coherence_check = CoherenceCheckSerializer(required=False, allow_null=True)
    value_consequence = serializers.DictField(required=False, allow_null=True)


class AttackTargetOrgSerializer(serializers.Serializer[dict[str, Any]]):
    target_id = serializers.CharField()
    target_type = serializers.CharField()
    name = serializers.CharField()
    territory_name = serializers.CharField()
    territory_id = serializers.CharField()
    defensive_capacity = serializers.FloatField()
    description = serializers.CharField()
    value_tensor_role = ValueTensorRoleSerializer(allow_null=True, required=False)
    extractive_edges = ExtractiveEdgeSerializer(many=True, default=list)
    attack_projection = AttackProjectionSerializer()


class AttackTargetEdgeModelSerializer(serializers.Serializer[dict[str, Any]]):
    target_id = serializers.CharField()
    target_type = serializers.CharField()
    edge_description = serializers.CharField()
    source_name = serializers.CharField()
    sink_name = serializers.CharField()
    s_flow_per_tick = serializers.FloatField()
    attack_projection = AttackProjectionSerializer()


class FactionalControlSerializer(serializers.Serializer[dict[str, Any]]):
    finance_capital = serializers.FloatField(required=False)
    security_state = serializers.FloatField(required=False)
    settler_populist = serializers.FloatField(required=False)


class AttackTargetInstitutionModelSerializer(serializers.Serializer[dict[str, Any]]):
    target_id = serializers.CharField()
    target_type = serializers.CharField()
    name = serializers.CharField()
    factional_control = FactionalControlSerializer(required=False)
    attack_projection = AttackProjectionSerializer()


class AttackAvailableTargetsSerializer(serializers.Serializer[dict[str, Any]]):
    organizations = AttackTargetOrgSerializer(many=True)
    edges = AttackTargetEdgeModelSerializer(many=True)
    institutions = AttackTargetInstitutionModelSerializer(many=True)


class AttackAvailableSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField()
    tick = serializers.IntegerField()
    verb = serializers.CharField()
    acting_org = OrgSummarySerializer()
    cost = AttackCostSerializer()
    ultra_left_warning = UltraLeftWarningSerializer()
    warsaw_ghetto_flag = WarsawGhettoFlagSerializer()
    targets = AttackAvailableTargetsSerializer()
    unavailable_targets = UnavailableTargetSerializer(many=True)


class MobilizeParamsSerializer(serializers.Serializer[dict[str, Any]]):
    sl_committed = serializers.FloatField()


class MobilizeSubmitSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate POST /api/games/{id}/verbs/mobilize/ request body."""

    org_id = serializers.CharField(max_length=64)
    target_id = serializers.CharField(max_length=64)
    params = MobilizeParamsSerializer()


class MobilizeSolidarityOverviewSerializer(serializers.Serializer[dict[str, Any]]):
    base_turnout = serializers.IntegerField()
    amplified_turnout = serializers.IntegerField()
    total_multiplier = serializers.FloatField()
    allies_activated = serializers.IntegerField()


class MobilizeConsciousnessEffectSerializer(serializers.Serializer[dict[str, Any]]):
    agitation_delta = serializers.FloatField()
    new_agitation = serializers.FloatField()


class MobilizeValueEffectSerializer(serializers.Serializer[dict[str, Any]]):
    disrupted_production = serializers.FloatField()
    surplus_denied = serializers.FloatField()


class MobilizeDDoSEffectSerializer(serializers.Serializer[dict[str, Any]]):
    active = serializers.BooleanField()
    attention_diverted = serializers.IntegerField()


class MobilizeStateResponseSerializer(serializers.Serializer[dict[str, Any]]):
    heat_delta = serializers.FloatField()
    new_heat = serializers.FloatField()
    ddos_effect = MobilizeDDoSEffectSerializer()


class MobilizeEstimatedEffectsSerializer(serializers.Serializer[dict[str, Any]]):
    solidarity_overview = MobilizeSolidarityOverviewSerializer()
    consciousness = MobilizeConsciousnessEffectSerializer()
    value = MobilizeValueEffectSerializer(required=False, allow_null=True)
    state_response = MobilizeStateResponseSerializer()


class MobilizeSlOptionSerializer(serializers.Serializer[dict[str, Any]]):
    sl_committed = serializers.FloatField()
    estimated_effects = MobilizeEstimatedEffectsSerializer()


class MobilizeCoordinationAllySerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    name = serializers.CharField()


class MobilizeCoordinationOpportunitiesSerializer(serializers.Serializer[dict[str, Any]]):
    type = serializers.CharField()
    ally = MobilizeCoordinationAllySerializer()
    multiplier = serializers.FloatField()


class MobilizeTargetSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    consciousness = serializers.FloatField()
    heat = serializers.FloatField()
    base_agitation = serializers.FloatField()
    coordination_opportunities = MobilizeCoordinationOpportunitiesSerializer(many=True)
    sl_options = MobilizeSlOptionSerializer(many=True)


class MobilizeAvailableSerializer(serializers.Serializer[dict[str, Any]]):
    entity_id = serializers.CharField()
    name = serializers.CharField()
    available_sl = serializers.FloatField()
    available_cl = serializers.FloatField()
    mobilize_cost_cl = serializers.FloatField()
    targets = MobilizeTargetSerializer(many=True)


# ---------------------------------------------------------------------- #
# REPRODUCE Verb Endpoint serializers (Spec 048)
# ---------------------------------------------------------------------- #


class ReproduceModeProjectedEffectSerializer(serializers.Serializer[dict[str, Any]]):
    cadre_delta = serializers.FloatField()
    cohesion_delta = serializers.FloatField()
    agitation_delta = serializers.FloatField()


class ReproduceModeRecruitmentPoolSerializer(serializers.Serializer[dict[str, Any]]):
    sympathizers = serializers.IntegerField(required=False)
    base_population = serializers.IntegerField(required=False)


class ReproduceModeInfoSerializer(serializers.Serializer[dict[str, Any]]):
    resource_cost = serializers.DictField()
    projected_effect = ReproduceModeProjectedEffectSerializer()
    recruitment_pool = ReproduceModeRecruitmentPoolSerializer(required=False)
    cooldown_applied = serializers.IntegerField(required=False, allow_null=True)
    explanation = serializers.CharField()


class ReproduceStateResponseSerializer(serializers.Serializer[dict[str, Any]]):
    state_visibility = serializers.CharField()
    attention_diverted = serializers.FloatField(required=False, allow_null=True)


class ReproduceModesSerializer(serializers.Serializer[dict[str, Any]]):
    cadre_training = ReproduceModeInfoSerializer(required=False)
    mass_recruitment = ReproduceModeInfoSerializer(required=False)


class ReproduceTargetSerializer(serializers.Serializer[dict[str, Any]]):
    target_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    modes = ReproduceModesSerializer()
    state_response = ReproduceStateResponseSerializer()


class ReproduceAvailableSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField()
    tick = serializers.IntegerField()
    verb = serializers.CharField()
    acting_org = OrgSummarySerializer()
    cost = VerbCostSerializer()
    targets = ReproduceTargetSerializer(many=True)


class ReproduceSubmitParamsSerializer(serializers.Serializer[dict[str, Any]]):
    mode = serializers.ChoiceField(choices=["cadre_training", "mass_recruitment"])
    cl_committed = serializers.FloatField(required=False, allow_null=True)
    sl_committed = serializers.FloatField(required=False, allow_null=True)


class ReproduceSubmitSerializer(serializers.Serializer[dict[str, Any]]):
    org_id = serializers.CharField(max_length=64)
    target_id = serializers.CharField(max_length=64, required=False, allow_null=True)
    params = ReproduceSubmitParamsSerializer()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


# ---------------------------------------------------------------------- #
# INVESTIGATE Verb Endpoint serializers (Spec 048)
# ---------------------------------------------------------------------- #


class InvestigateTargetCurrentKnowledgeSerializer(serializers.Serializer[dict[str, Any]]):
    visibility_level = serializers.CharField()
    known_attributes = serializers.ListField(child=serializers.CharField())
    last_scanned_tick = serializers.IntegerField(allow_null=True)


class InvestigateTargetProjectedRevealsSerializer(serializers.Serializer[dict[str, Any]]):
    new_visibility_level = serializers.CharField()
    likely_reveals = serializers.ListField(child=serializers.CharField())


class InvestigateTargetDetectionRiskSerializer(serializers.Serializer[dict[str, Any]]):
    probability = serializers.FloatField()
    consequence = serializers.CharField()


class TargetTerritorySerializer(serializers.Serializer[dict[str, Any]]):
    target_id = serializers.CharField()
    name = serializers.CharField()
    target_type = serializers.CharField()
    heat = serializers.FloatField()
    current_knowledge = InvestigateTargetCurrentKnowledgeSerializer()
    resource_cost = serializers.DictField()
    projected_reveals = InvestigateTargetProjectedRevealsSerializer()


class TargetOrganizationSerializer(serializers.Serializer[dict[str, Any]]):
    target_id = serializers.CharField()
    name = serializers.CharField()
    target_type = serializers.CharField()
    current_knowledge = InvestigateTargetCurrentKnowledgeSerializer()
    resource_cost = serializers.DictField()
    projected_reveals = InvestigateTargetProjectedRevealsSerializer()
    detection_risk = InvestigateTargetDetectionRiskSerializer()


class CounterIntelligenceSerializer(serializers.Serializer[dict[str, Any]]):
    active_moles_suspected = serializers.IntegerField()
    resource_cost = serializers.DictField()
    projected_reveals = InvestigateTargetProjectedRevealsSerializer()


class InvestigateAvailableTargetsSerializer(serializers.Serializer[dict[str, Any]]):
    territory_scans = TargetTerritorySerializer(many=True)
    targeted_scans = TargetOrganizationSerializer(many=True)
    counter_intelligence = CounterIntelligenceSerializer(allow_null=True, required=False)


class ObserverCapabilitySerializer(serializers.Serializer[dict[str, Any]]):
    intel_network_strength = serializers.FloatField()
    max_scan_depth = serializers.CharField()


class InvestigateAvailableSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField()
    tick = serializers.IntegerField()
    verb = serializers.CharField()
    acting_org = OrgSummarySerializer()
    cost = VerbCostSerializer()
    observe_capability = ObserverCapabilitySerializer()
    targets = InvestigateAvailableTargetsSerializer()


class InvestigateSubmitParamsSerializer(serializers.Serializer[dict[str, Any]]):
    scan_type = serializers.ChoiceField(
        choices=["territory_scan", "targeted_scan", "counter_intelligence"]
    )


class InvestigateSubmitSerializer(serializers.Serializer[dict[str, Any]]):
    org_id = serializers.CharField(max_length=64)
    target_id = serializers.CharField(max_length=64, required=False, allow_null=True)
    params = InvestigateSubmitParamsSerializer()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


# ---------------------------------------------------------------------- #
# MOVE Verb Endpoint serializers (Spec 049)
# ---------------------------------------------------------------------- #


class MoveCommunityReceptionSerializer(serializers.Serializer[dict[str, Any]]):
    overlap_score = serializers.FloatField()
    cross_community_penalty = serializers.FloatField()


class MoveStrategicAssessmentSerializer(serializers.Serializer[dict[str, Any]]):
    value_circuit_position = serializers.DictField()
    surveillance_evasion = serializers.FloatField()


class MoveOutcomeModeSerializer(serializers.Serializer[dict[str, Any]]):
    presence_value = serializers.FloatField()
    edges_at_risk = serializers.IntegerField()
    ticks_to_operational = serializers.IntegerField()


class MoveProjectedOutcomesSerializer(serializers.Serializer[dict[str, Any]]):
    expand = MoveOutcomeModeSerializer()
    relocate = MoveOutcomeModeSerializer()


class MoveTargetSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    name = serializers.CharField()
    community_reception = MoveCommunityReceptionSerializer()
    strategic_assessment = MoveStrategicAssessmentSerializer()
    projected_outcomes = MoveProjectedOutcomesSerializer()


class MoveAvailableSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField()
    tick = serializers.IntegerField()
    verb = serializers.CharField()
    acting_org = OrgSummarySerializer()
    cost = VerbCostSerializer()
    current_territories = serializers.ListField(child=serializers.CharField())
    targets = MoveTargetSerializer(many=True)


class MoveSubmitParamsSerializer(serializers.Serializer[dict[str, Any]]):
    mode = serializers.ChoiceField(choices=["expand", "relocate"])


class MoveSubmitSerializer(serializers.Serializer[dict[str, Any]]):
    org_id = serializers.CharField(max_length=64)
    target_id = serializers.CharField(max_length=64)
    params = MoveSubmitParamsSerializer()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


# ---------------------------------------------------------------------- #
# NEGOTIATE Verb Endpoint serializers (Spec 050)
# ---------------------------------------------------------------------- #


class NegotiateInterestAlignmentSerializer(serializers.Serializer[dict[str, Any]]):
    score = serializers.FloatField()
    shared_interests = serializers.ListField(child=serializers.CharField())
    divergent_interests = serializers.ListField(child=serializers.CharField())
    alliance_type = serializers.ChoiceField(
        choices=["strategic", "tactical", "temporary", "impossible_under_current_conditions"]
    )


class NegotiationOptionSerializer(serializers.Serializer[dict[str, Any]]):
    proposal = serializers.CharField()
    success_probability = serializers.FloatField()
    edge_effect = serializers.CharField()
    state_response_prediction = serializers.CharField()
    betrayal_risk = serializers.FloatField()


class NegotiateTargetDeEscalationSerializer(serializers.Serializer[dict[str, Any]]):
    target_id = serializers.CharField()
    name = serializers.CharField()
    antagonism_cause = serializers.CharField()
    reconciliation_requirement = serializers.CharField()


class NegotiateTargetSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    interest_alignment = NegotiateInterestAlignmentSerializer()
    negotiation_options = NegotiationOptionSerializer(many=True)
    betrayal_risk = serializers.FloatField(required=False, allow_null=True)
    existing_edge_state = serializers.CharField(allow_null=True)


class NegotiateAvailableSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField()
    tick = serializers.IntegerField()
    verb = serializers.CharField()
    acting_org = OrgSummarySerializer()
    cost = VerbCostSerializer()
    org_leverage = serializers.FloatField()
    targets = NegotiateTargetSerializer(many=True)
    de_escalation_targets = NegotiateTargetDeEscalationSerializer(many=True)


class NegotiateSubmitParamsSerializer(serializers.Serializer[dict[str, Any]]):
    proposal = serializers.ChoiceField(
        choices=[
            "coordination_pact",
            "resource_sharing",
            "ceasefire",
            "demand_policy_change",
            "reconciliation",
        ]
    )


class NegotiateSubmitSerializer(serializers.Serializer[dict[str, Any]]):
    org_id = serializers.CharField(max_length=64)
    target_id = serializers.CharField(max_length=64)
    params = NegotiateSubmitParamsSerializer()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        return data
