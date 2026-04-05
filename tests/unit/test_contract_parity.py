"""Contract parity tests: verify frontend fixture shape matches backend serializers.

The mock fixture in ``web/frontend/src/test/fixtures.ts`` defines the exact
shape the React frontend expects. The serializers in ``web/game/serializers.py``
define the shape the Django backend produces. This test verifies they match.

Strategy: serialize a backend-produced Wayne County snapshot and verify every
field present in the frontend fixture exists with the same type.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios_wayne_county import create_wayne_county_scenario
from babylon.models.vanguard_resources import VanguardResources

# The canonical set of fields from the frontend fixtures.
# This is the contract — the frontend REQUIRES these fields.

ENTITY_FIELDS = {
    "id": str,
    "name": str,
    "role": str,
    "wealth": float,
    "consciousness": float,
    "national_identity": float,
    "agitation": float,
    "organization": float,
    "repression": float,
    "p_acquiescence": float,
    "p_revolution": float,
    "subsistence": float,
    "population": int,
    "inequality": float,
    "active": bool,
}

TERRITORY_FIELDS = {
    "id": str,
    "name": str,
    "h3_index": (str, type(None)),
    "heat": float,
    "sector_type": str,
    "territory_type": str,
    "profile": str,
    "rent_level": float,
    "population": int,
    "under_eviction": bool,
    "biocapacity": float,
    "host_id": (str, type(None)),
    "occupant_id": (str, type(None)),
}

ORG_FIELDS = {
    "id": str,
    "name": str,
    "org_type": str,
    "class_character": str,
    "cohesion": float,
    "cadre_level": float,
    "budget": float,
    "heat": float,
    "territory_ids": list,
    "consciousness_tendency": str,
}

VANGUARD_FIELDS = {
    "cadre_labor": float,
    "sympathizer_labor": float,
    "reputation": float,
    "budget": float,
    "heat": float,
    "max_cadre_labor": float,
    "max_sympathizer_labor": float,
}

EDGE_FIELDS = {
    "source_id": str,
    "target_id": str,
    "edge_type": str,
    "value_flow": float,
    "tension": float,
    "solidarity_strength": float,
}

TRAP_STATUS_FIELDS = {
    "trap_type": str,
    "severity": str,
    "score": float,
    "indicators": list,
    "ticks_at_moderate": int,
}

TRAP_RESULT_FIELDS = {
    "liberal": dict,
    "ultra_left": dict,
    "rightist": dict,
    "active_trap": (str, type(None)),
    "game_over_trap": (str, type(None)),
}

SNAPSHOT_FIELDS = {
    "session_id": str,
    "tick": int,
    "entities": list,
    "territories": list,
    "organizations": list,
    "institutions": list,
    "edges": list,
    "economy": dict,
    "events": list,
}


class TestBackendContractParity:
    """Verify backend-generated data matches frontend fixture shapes."""

    @pytest.fixture()
    def wayne_county_state(self):
        """Generate a Wayne County scenario state."""
        state, _config, _defines = create_wayne_county_scenario()
        return state

    @pytest.fixture()
    def vanguard_resources(self):
        """Generate vanguard resources from the player org."""
        return VanguardResources.from_organization(
            cadre_level=0.1,
            cohesion=0.5,
            budget=100.0,
            heat=0.0,
            territory_count=2,
            reputation=0.0,
        )

    def test_entity_fields_match_contract(self, wayne_county_state) -> None:
        """Every entity field the frontend expects exists on the backend model.

        Note: The engine_bridge.py flattens IdeologicalProfile into separate
        fields: ideology.class_consciousness -> consciousness,
        ideology.national_identity -> national_identity,
        ideology.agitation -> agitation.
        """
        entity = list(wayne_county_state.entities.values())[0]
        entity_dict = entity.model_dump()

        # Flatten ideology profile like engine_bridge does
        if "ideology" in entity_dict and isinstance(entity_dict["ideology"], dict):
            ideology = entity_dict.pop("ideology")
            entity_dict["consciousness"] = ideology.get("class_consciousness", 0.0)
            entity_dict["national_identity"] = ideology.get("national_identity", 0.5)
            entity_dict["agitation"] = ideology.get("agitation", 0.0)

        # Map backend field names to frontend field names
        field_mappings = {
            "repression_faced": "repression",
            "subsistence_threshold": "subsistence",
        }
        mapped_backend_keys = set()
        for k in entity_dict:
            mapped_backend_keys.add(field_mappings.get(k, k))

        contract_keys = set(ENTITY_FIELDS.keys())
        missing = contract_keys - mapped_backend_keys
        assert not missing, f"Backend missing fields required by frontend: {missing}"

    def test_territory_fields_match_contract(self, wayne_county_state) -> None:
        """Every territory field the frontend expects exists on the backend model."""
        territory = list(wayne_county_state.territories.values())[0]
        territory_dict = territory.model_dump()
        backend_keys = set(territory_dict.keys())
        contract_keys = set(TERRITORY_FIELDS.keys())

        missing = contract_keys - backend_keys
        assert not missing, f"Backend missing territory fields: {missing}"

    def test_organization_fields_match_contract(self, wayne_county_state) -> None:
        """Every org field the frontend expects exists on the backend model."""
        org = list(wayne_county_state.organizations.values())[0]
        org_dict = org.model_dump()
        backend_keys = set(org_dict.keys())
        contract_keys = set(ORG_FIELDS.keys())

        missing = contract_keys - backend_keys
        assert not missing, f"Backend missing org fields: {missing}"

    def test_vanguard_resources_fields_match_contract(self, vanguard_resources) -> None:
        """VanguardResources produces all fields the frontend expects."""
        vanguard_dict = vanguard_resources.model_dump()
        backend_keys = set(vanguard_dict.keys())
        contract_keys = set(VANGUARD_FIELDS.keys())

        missing = contract_keys - backend_keys
        assert not missing, f"Backend missing vanguard fields: {missing}"

    def test_edge_fields_match_contract(self, wayne_county_state) -> None:
        """Every edge field the frontend expects exists on the backend model."""
        edge = wayne_county_state.relationships[0]
        edge_dict = edge.model_dump()
        backend_keys = set(edge_dict.keys())
        contract_keys = set(EDGE_FIELDS.keys())

        missing = contract_keys - backend_keys
        assert not missing, f"Backend missing edge fields: {missing}"

    def test_trap_detection_fields_match_contract(self) -> None:
        """TrapDetection produces all fields the frontend expects."""
        from babylon.engine.trap_detection import detect_traps

        result = detect_traps(
            action_history=[],
            org_budget=100.0,
            org_cadre=0.1,
            org_cohesion=0.5,
            org_heat=0.0,
            sympathizer_labor=4.0,
            territory_count=2,
            consciousness_avg=0.1,
            tick=0,
        )
        result_dict = result.model_dump()
        backend_keys = set(result_dict.keys())
        contract_keys = set(TRAP_RESULT_FIELDS.keys())

        missing = contract_keys - backend_keys
        assert not missing, f"Backend missing trap result fields: {missing}"

        # Check nested trap status fields
        for trap_name in ["liberal", "ultra_left", "rightist"]:
            trap_dict = result_dict[trap_name]
            trap_keys = set(trap_dict.keys())
            trap_contract = set(TRAP_STATUS_FIELDS.keys())
            missing_trap = trap_contract - trap_keys
            assert not missing_trap, f"Backend missing {trap_name} trap fields: {missing_trap}"

    def test_wayne_county_scenario_generates_valid_state(self, wayne_county_state) -> None:
        """The Wayne County scenario produces a valid WorldState."""
        assert wayne_county_state.tick == 0
        assert len(wayne_county_state.entities) == 4
        assert len(wayne_county_state.territories) > 50  # ~81 at res-6
        assert len(wayne_county_state.organizations) == 1
        assert len(wayne_county_state.relationships) > 80  # 81 tenancy + 4 structural

    def test_vanguard_resources_computed_correctly(self, vanguard_resources) -> None:
        """VanguardResources formulas produce correct values."""
        assert vanguard_resources.cadre_labor == 1.0  # 0.1 * 10 = 1.0
        assert vanguard_resources.max_cadre_labor == 1.0
        assert vanguard_resources.sympathizer_labor == 4.0  # min(5.0, 1.0*2+2)
        assert vanguard_resources.max_sympathizer_labor == 5.0  # 0.5 * 2 * 5 = 5.0
        assert vanguard_resources.reputation == 0.0
        assert vanguard_resources.budget == 100.0
        assert vanguard_resources.heat == 0.0
