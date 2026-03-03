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
