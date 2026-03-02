"""Tests for DRF serializers (Phase 4)."""

from __future__ import annotations

import pytest

from game.serializers import (
    CreateGameSerializer,
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
            data={"id": "class_1", "name": "Proletariat", "role": "WORKER", "wealth": 10.0}
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
                "heat": 0.3,
                "sector_type": "INDUSTRIAL",
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
                "economy": {},
                "events": [],
            }
        )
        assert s.is_valid(), s.errors
