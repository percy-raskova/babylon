"""Organizational-capacity contract, ported to the Organization entity (P25 U4, ADR130).

The deprecated ``OrganizationComponent`` shim carried this behavioral contract
(274-line suite) since Feature 007; Feature 031 moved the semantics onto the
``Organization`` entity hierarchy and the shim went lazy-deprecated. U4 retires
the shim and re-pins the contract where the capacity actually lives — including
the graph round-trip (the from_graph gotcha: a dropped field defaults silently).
"""

import pytest
from pydantic import ValidationError

from babylon.models.entities.organization import CivilSocietyOrg
from babylon.models.world_state import _reconstruct_organization


def _org(**overrides) -> CivilSocietyOrg:
    base = {
        "id": "org/test",
        "name": "Test Org",
        "class_character": "proletarian",
        "service_type": "mutual_aid",
    }
    base.update(overrides)
    return CivilSocietyOrg(**base)


class TestCapacityDefaults:
    def test_creation_with_defaults(self) -> None:
        org = _org()
        assert org.cohesion == 0.1  # low cohesion — the shim's contract default
        assert org.cadre_level == 0.0  # no cadre leadership

    def test_creation_with_custom_values(self) -> None:
        org = _org(cohesion=0.75, cadre_level=0.6)
        assert org.cohesion == 0.75
        assert org.cadre_level == 0.6

    def test_boundary_values(self) -> None:
        assert _org(cohesion=0.0, cadre_level=0.0).cohesion == 0.0
        assert _org(cohesion=1.0, cadre_level=1.0).cadre_level == 1.0


class TestCapacityBounds:
    def test_rejects_negative_cohesion(self) -> None:
        with pytest.raises(ValidationError):
            _org(cohesion=-0.1)

    def test_rejects_cohesion_greater_than_one(self) -> None:
        with pytest.raises(ValidationError):
            _org(cohesion=1.1)

    def test_rejects_negative_cadre_level(self) -> None:
        with pytest.raises(ValidationError):
            _org(cadre_level=-0.1)

    def test_rejects_cadre_level_greater_than_one(self) -> None:
        with pytest.raises(ValidationError):
            _org(cadre_level=1.1)


class TestCapacityImmutability:
    def test_cannot_mutate_cohesion(self) -> None:
        org = _org()
        with pytest.raises(ValidationError):
            org.cohesion = 0.9

    def test_cannot_mutate_cadre_level(self) -> None:
        org = _org()
        with pytest.raises(ValidationError):
            org.cadre_level = 0.9


class TestCapacitySerialization:
    def test_json_round_trip_preserves_capacity(self) -> None:
        org = _org(cohesion=0.42, cadre_level=0.33)
        restored = CivilSocietyOrg.model_validate_json(org.model_dump_json())
        assert restored.cohesion == 0.42
        assert restored.cadre_level == 0.33

    def test_graph_round_trip_preserves_capacity(self) -> None:
        # The from_graph gotcha: reconstruction must carry BOTH capacity fields
        # through model_dump() -> node data -> _reconstruct_organization, never
        # silently defaulting them (CLAUDE.md graph-round-trip anti-pattern).
        org = _org(cohesion=0.42, cadre_level=0.33)
        node_data = {"_node_type": "organization", **org.model_dump()}
        restored = _reconstruct_organization(node_data)
        assert restored.cohesion == 0.42
        assert restored.cadre_level == 0.33
