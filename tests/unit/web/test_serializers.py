"""Tests for DRF serializers (Phase 4)."""

from __future__ import annotations

import pytest

from game.serializers import (
    CreateGameSerializer,
    EdgeSerializer,
    EntitySerializer,
    GameSnapshotSerializer,
    SubmitActionSerializer,
    TerritorySerializer,
)


@pytest.mark.unit
class TestCreateGameSerializer:
    """Validate CreateGameSerializer input validation."""

    def test_valid_minimal(self) -> None:
        s = CreateGameSerializer(data={"scenario": "detroit_1967"})
        assert s.is_valid(), s.errors

    def test_valid_full(self) -> None:
        s = CreateGameSerializer(
            data={
                "scenario": "test",
                "config": {"extraction_efficiency": 0.5},
                "defines": {},
                "rng_seed": 42,
            }
        )
        assert s.is_valid(), s.errors

    def test_missing_scenario(self) -> None:
        s = CreateGameSerializer(data={})
        assert not s.is_valid()
        assert "scenario" in s.errors

    def test_scenario_max_length(self) -> None:
        s = CreateGameSerializer(data={"scenario": "x" * 65})
        assert not s.is_valid()


@pytest.mark.unit
class TestSubmitActionSerializer:
    """Validate SubmitActionSerializer input validation."""

    def test_valid_minimal(self) -> None:
        s = SubmitActionSerializer(data={"org_id": "org_workers", "verb": "RECRUIT"})
        assert s.is_valid(), s.errors

    def test_valid_full(self) -> None:
        s = SubmitActionSerializer(
            data={
                "org_id": "org_workers",
                "verb": "RECRUIT",
                "action_type": "RECRUIT",
                "target_id": "territory_detroit",
                "target_community": "community_1",
                "params_json": {"intensity": 0.5},
            }
        )
        assert s.is_valid(), s.errors

    def test_missing_org_id(self) -> None:
        s = SubmitActionSerializer(data={"verb": "RECRUIT"})
        assert not s.is_valid()
        assert "org_id" in s.errors

    def test_missing_verb(self) -> None:
        s = SubmitActionSerializer(data={"org_id": "org_workers"})
        assert not s.is_valid()
        assert "verb" in s.errors


@pytest.mark.unit
class TestEntitySerializer:
    """Validate EntitySerializer output format."""

    def test_serializes_entity(self) -> None:
        s = EntitySerializer(
            data={
                "id": "class_1",
                "name": "Proletariat",
                "role": "WORKER",
                "wealth": 10.0,
                "consciousness": 0.5,
                "national_identity": 0.3,
                "agitation": 0.0,
                "organization": 0.1,
                "repression": 0.5,
                "p_acquiescence": 0.7,
                "p_revolution": 0.2,
                "subsistence": 5.0,
                "population": 1000,
                "inequality": 0.4,
                "active": True,
            }
        )
        assert s.is_valid(), s.errors


@pytest.mark.unit
class TestTerritorySerializer:
    """Validate TerritorySerializer output format."""

    def test_serializes_territory(self) -> None:
        s = TerritorySerializer(
            data={
                "id": "t_detroit",
                "name": "Detroit",
                "h3_index": None,
                "heat": 0.3,
                "sector_type": "INDUSTRIAL",
                "territory_type": "CORE",
                "profile": "LOW_PROFILE",
                "rent_level": 1.0,
                "population": 500,
                "under_eviction": False,
                "biocapacity": 100.0,
                "host_id": None,
                "occupant_id": None,
            }
        )
        assert s.is_valid(), s.errors


@pytest.mark.unit
class TestEdgeSerializer:
    """Validate EdgeSerializer output format."""

    def test_serializes_edge(self) -> None:
        s = EdgeSerializer(
            data={
                "source_id": "C001",
                "target_id": "C002",
                "edge_type": "EXPLOITATION",
                "value_flow": 5.0,
                "tension": 0.3,
                "solidarity_strength": 0.0,
            }
        )
        assert s.is_valid(), s.errors


@pytest.mark.unit
class TestGameSnapshotSerializer:
    """Validate GameSnapshotSerializer output format."""

    def test_serializes_snapshot(self) -> None:
        s = GameSnapshotSerializer(
            data={
                "session_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "tick": 0,
                "entities": [],
                "territories": [],
                "organizations": [],
                "institutions": [],
                "edges": [],
                "economy": {},
                "events": [],
            }
        )
        assert s.is_valid(), s.errors
