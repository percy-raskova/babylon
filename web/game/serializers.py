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


class AttackActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/attack/ request body."""

    mode = serializers.ChoiceField(
        choices=["SABOTAGE", "DIRECT", "EXPROPRIATION"],
    )


class MobilizeActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/mobilize/ request body."""

    action_type = serializers.ChoiceField(
        choices=["PROTEST", "STRIKE", "BLOCKADE", "MUTUAL_AID_DRIVE"],
    )


class CampaignActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/campaign/ request body."""

    campaign_type = serializers.ChoiceField(
        choices=["ELECTORAL", "LEGISLATIVE", "PUBLIC_PRESSURE"],
    )


class MoveActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/move/ request body.

    No additional parameters — ``target_id`` IS the destination hex.
    """

    pass


class InvestigateActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/investigate/ request body."""

    depth = serializers.ChoiceField(
        choices=["SURFACE", "TARGETED", "DEEP"],
    )


class ReproduceActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/reproduce/ request body."""

    method = serializers.ChoiceField(
        choices=["CADRE", "MASS"],
    )


class NegotiateActionSerializer(BaseActionSerializer):
    """Validate POST /api/games/{id}/actions/negotiate/ request body."""

    offer_type = serializers.ChoiceField(
        choices=["ALLIANCE", "CEASEFIRE", "RESOURCE_EXCHANGE", "MERGER"],
    )


# ---------------------------------------------------------------------- #
# Response serializers (output formatting)
# ---------------------------------------------------------------------- #


class EntitySerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a social class entity with full visualization fields."""

    id = serializers.CharField()
    name = serializers.CharField()
    role = serializers.CharField()
    wealth = serializers.FloatField()
    consciousness = serializers.FloatField()
    national_identity = serializers.FloatField()
    agitation = serializers.FloatField()
    organization = serializers.FloatField()
    repression = serializers.FloatField()
    p_acquiescence = serializers.FloatField()
    p_revolution = serializers.FloatField()
    subsistence = serializers.FloatField()
    population = serializers.IntegerField()
    inequality = serializers.FloatField()
    active = serializers.BooleanField()


class TerritorySerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a territory with full visualization fields."""

    id = serializers.CharField()
    name = serializers.CharField()
    h3_index = serializers.CharField(allow_null=True)
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
    """Serialize an organization with full visualization fields."""

    id = serializers.CharField()
    name = serializers.CharField()
    org_type = serializers.CharField()
    class_character = serializers.CharField()
    cohesion = serializers.FloatField()
    cadre_level = serializers.FloatField()
    budget = serializers.FloatField()
    heat = serializers.FloatField()
    territory_ids = serializers.ListField(child=serializers.CharField())
    consciousness_tendency = serializers.CharField()
    vanguard = VanguardResourcesSerializer(required=False, allow_null=True)


class InstitutionSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize an institution with full visualization fields."""

    id = serializers.CharField()
    name = serializers.CharField()
    apparatus_type = serializers.CharField()
    social_function = serializers.CharField()
    class_inscription = serializers.CharField()
    legitimacy = serializers.FloatField()
    budget = serializers.FloatField()
    housed_org_ids = serializers.ListField(child=serializers.CharField())
    territory_ids = serializers.ListField(child=serializers.CharField())
    hegemonic_fraction = serializers.CharField()
    liberal_technocratic = serializers.FloatField()
    revanchist_fascist = serializers.FloatField()
    institutionalist_bonapartist = serializers.FloatField()


class EdgeSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a relationship edge."""

    source_id = serializers.CharField()
    target_id = serializers.CharField()
    edge_type = serializers.CharField()
    value_flow = serializers.FloatField()
    tension = serializers.FloatField()
    solidarity_strength = serializers.FloatField()


class EventSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a simulation event."""

    type = serializers.CharField()
    tick = serializers.IntegerField()
    data = serializers.DictField(required=False, default=dict)  # type: ignore[assignment]


class TrapStatusSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a single trap detector status."""

    trap_type = serializers.CharField()
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


class GameSnapshotSerializer(serializers.Serializer[dict[str, Any]]):
    """Serialize a full game state snapshot."""

    session_id = serializers.CharField()
    tick = serializers.IntegerField()
    entities = EntitySerializer(many=True)
    territories = TerritorySerializer(many=True)
    organizations = OrganizationSerializer(many=True)
    institutions = InstitutionSerializer(many=True)
    edges = EdgeSerializer(many=True)
    economy = serializers.DictField()
    events = EventSerializer(many=True)
    traps = TrapDetectionResultSerializer(required=False, allow_null=True)


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
