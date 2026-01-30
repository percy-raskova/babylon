"""Unit tests for the entity_registry module.

Tests verify:
- Entity ID format consistency (^C[0-9]{3}$)
- All IDs are unique
- Bidirectional role<->ID mappings are correct
- All metrics IDs have slot names
- Utility functions work correctly
"""

from __future__ import annotations

import re

import pytest

from babylon.models.entity_registry import (
    ALL_ENTITY_IDS,
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    ENTITY_ID_TO_ROLE,
    ENTITY_SLOT_NAMES,
    LABOR_ARISTOCRACY_ID,
    METRICS_ENTITY_IDS,
    PERIPHERY_WORKER_ID,
    ROLE_TO_ENTITY_ID,
    TERMINAL_CRISIS_ENTITY_IDS,
    entity_id_to_role,
    get_slot_name,
    role_to_entity_id,
)
from babylon.models.enums import SocialRole


class TestEntityIdFormat:
    """Entity IDs must follow consistent format."""

    ENTITY_ID_PATTERN = re.compile(r"^C[0-9]{3}$")

    def test_periphery_worker_id_format(self) -> None:
        """PERIPHERY_WORKER_ID matches C### pattern."""
        assert self.ENTITY_ID_PATTERN.match(PERIPHERY_WORKER_ID)

    def test_comprador_id_format(self) -> None:
        """COMPRADOR_ID matches C### pattern."""
        assert self.ENTITY_ID_PATTERN.match(COMPRADOR_ID)

    def test_core_bourgeoisie_id_format(self) -> None:
        """CORE_BOURGEOISIE_ID matches C### pattern."""
        assert self.ENTITY_ID_PATTERN.match(CORE_BOURGEOISIE_ID)

    def test_labor_aristocracy_id_format(self) -> None:
        """LABOR_ARISTOCRACY_ID matches C### pattern."""
        assert self.ENTITY_ID_PATTERN.match(LABOR_ARISTOCRACY_ID)

    def test_all_entity_ids_match_pattern(self) -> None:
        """All entity IDs in ALL_ENTITY_IDS match C### pattern."""
        for entity_id in ALL_ENTITY_IDS:
            assert self.ENTITY_ID_PATTERN.match(entity_id), f"{entity_id} does not match pattern"


class TestEntityIdUniqueness:
    """All entity IDs must be unique."""

    def test_all_entity_ids_unique(self) -> None:
        """ALL_ENTITY_IDS contains no duplicates."""
        assert len(ALL_ENTITY_IDS) == len(set(ALL_ENTITY_IDS))

    def test_metrics_entity_ids_unique(self) -> None:
        """METRICS_ENTITY_IDS contains no duplicates."""
        assert len(METRICS_ENTITY_IDS) == len(set(METRICS_ENTITY_IDS))

    def test_terminal_crisis_entity_ids_unique(self) -> None:
        """TERMINAL_CRISIS_ENTITY_IDS contains no duplicates."""
        assert len(TERMINAL_CRISIS_ENTITY_IDS) == len(set(TERMINAL_CRISIS_ENTITY_IDS))

    def test_constants_match_expected_values(self) -> None:
        """Entity ID constants match expected hardcoded values."""
        assert PERIPHERY_WORKER_ID == "C001"
        assert COMPRADOR_ID == "C002"
        assert CORE_BOURGEOISIE_ID == "C003"
        assert LABOR_ARISTOCRACY_ID == "C004"


class TestRoleToEntityIdMapping:
    """ROLE_TO_ENTITY_ID bidirectional mappings."""

    def test_periphery_proletariat_maps_to_c001(self) -> None:
        """PERIPHERY_PROLETARIAT maps to C001."""
        assert ROLE_TO_ENTITY_ID[SocialRole.PERIPHERY_PROLETARIAT] == "C001"

    def test_comprador_bourgeoisie_maps_to_c002(self) -> None:
        """COMPRADOR_BOURGEOISIE maps to C002."""
        assert ROLE_TO_ENTITY_ID[SocialRole.COMPRADOR_BOURGEOISIE] == "C002"

    def test_core_bourgeoisie_maps_to_c003(self) -> None:
        """CORE_BOURGEOISIE maps to C003."""
        assert ROLE_TO_ENTITY_ID[SocialRole.CORE_BOURGEOISIE] == "C003"

    def test_labor_aristocracy_maps_to_c004(self) -> None:
        """LABOR_ARISTOCRACY maps to C004."""
        assert ROLE_TO_ENTITY_ID[SocialRole.LABOR_ARISTOCRACY] == "C004"

    def test_carceral_enforcer_maps_to_c005(self) -> None:
        """CARCERAL_ENFORCER maps to C005."""
        assert ROLE_TO_ENTITY_ID[SocialRole.CARCERAL_ENFORCER] == "C005"

    def test_internal_proletariat_maps_to_c006(self) -> None:
        """INTERNAL_PROLETARIAT maps to C006."""
        assert ROLE_TO_ENTITY_ID[SocialRole.INTERNAL_PROLETARIAT] == "C006"

    def test_inverse_mapping_consistent(self) -> None:
        """ENTITY_ID_TO_ROLE is exact inverse of ROLE_TO_ENTITY_ID."""
        for role, entity_id in ROLE_TO_ENTITY_ID.items():
            assert ENTITY_ID_TO_ROLE[entity_id] == role


class TestEntitySlotNames:
    """All metrics entity IDs must have slot names."""

    def test_all_metrics_ids_have_slot_names(self) -> None:
        """Every ID in METRICS_ENTITY_IDS has a corresponding slot name."""
        for entity_id in METRICS_ENTITY_IDS:
            assert entity_id in ENTITY_SLOT_NAMES, f"{entity_id} missing from ENTITY_SLOT_NAMES"

    def test_all_entity_ids_have_slot_names(self) -> None:
        """Every ID in ALL_ENTITY_IDS has a corresponding slot name."""
        for entity_id in ALL_ENTITY_IDS:
            assert entity_id in ENTITY_SLOT_NAMES, f"{entity_id} missing from ENTITY_SLOT_NAMES"

    def test_slot_names_are_valid_identifiers(self) -> None:
        """Slot names are valid Python/CSV identifiers (lowercase, underscores)."""
        for _entity_id, slot_name in ENTITY_SLOT_NAMES.items():
            assert slot_name.islower(), f"{slot_name} is not lowercase"
            assert "_" in slot_name or len(slot_name) <= 3, f"{slot_name} unexpected format"

    def test_expected_slot_name_values(self) -> None:
        """Slot names match expected values."""
        assert ENTITY_SLOT_NAMES["C001"] == "p_w"
        assert ENTITY_SLOT_NAMES["C002"] == "p_c"
        assert ENTITY_SLOT_NAMES["C003"] == "c_b"
        assert ENTITY_SLOT_NAMES["C004"] == "c_w"


class TestEntityGroupings:
    """Entity ID groupings are consistent."""

    def test_metrics_is_subset_of_all(self) -> None:
        """METRICS_ENTITY_IDS is a subset of ALL_ENTITY_IDS."""
        assert set(METRICS_ENTITY_IDS).issubset(set(ALL_ENTITY_IDS))

    def test_terminal_crisis_is_subset_of_all(self) -> None:
        """TERMINAL_CRISIS_ENTITY_IDS is a subset of ALL_ENTITY_IDS."""
        assert set(TERMINAL_CRISIS_ENTITY_IDS).issubset(set(ALL_ENTITY_IDS))

    def test_metrics_and_terminal_are_disjoint(self) -> None:
        """METRICS_ENTITY_IDS and TERMINAL_CRISIS_ENTITY_IDS are disjoint."""
        assert set(METRICS_ENTITY_IDS).isdisjoint(set(TERMINAL_CRISIS_ENTITY_IDS))

    def test_metrics_plus_terminal_equals_all(self) -> None:
        """METRICS + TERMINAL_CRISIS = ALL entity IDs."""
        combined = set(METRICS_ENTITY_IDS) | set(TERMINAL_CRISIS_ENTITY_IDS)
        assert combined == set(ALL_ENTITY_IDS)

    def test_metrics_has_four_entities(self) -> None:
        """METRICS_ENTITY_IDS contains exactly 4 entities (C001-C004)."""
        assert len(METRICS_ENTITY_IDS) == 4

    def test_terminal_crisis_has_two_entities(self) -> None:
        """TERMINAL_CRISIS_ENTITY_IDS contains exactly 2 entities (C005-C006)."""
        assert len(TERMINAL_CRISIS_ENTITY_IDS) == 2


class TestUtilityFunctions:
    """Utility functions work correctly."""

    def test_role_to_entity_id_basic(self) -> None:
        """role_to_entity_id returns correct entity ID."""
        assert role_to_entity_id(SocialRole.PERIPHERY_PROLETARIAT) == "C001"
        assert role_to_entity_id(SocialRole.CORE_BOURGEOISIE) == "C003"

    def test_role_to_entity_id_raises_for_unmapped_role(self) -> None:
        """role_to_entity_id raises KeyError for roles without entity IDs."""
        with pytest.raises(KeyError):
            role_to_entity_id(SocialRole.LUMPENPROLETARIAT)

    def test_entity_id_to_role_basic(self) -> None:
        """entity_id_to_role returns correct SocialRole."""
        assert entity_id_to_role("C001") == SocialRole.PERIPHERY_PROLETARIAT
        assert entity_id_to_role("C003") == SocialRole.CORE_BOURGEOISIE

    def test_entity_id_to_role_raises_for_unknown_id(self) -> None:
        """entity_id_to_role raises KeyError for unknown IDs."""
        with pytest.raises(KeyError):
            entity_id_to_role("C999")

    def test_get_slot_name_basic(self) -> None:
        """get_slot_name returns correct slot name."""
        assert get_slot_name("C001") == "p_w"
        assert get_slot_name("C004") == "c_w"

    def test_get_slot_name_raises_for_unknown_id(self) -> None:
        """get_slot_name raises KeyError for unknown IDs."""
        with pytest.raises(KeyError):
            get_slot_name("C999")

    def test_roundtrip_role_to_id_to_role(self) -> None:
        """role -> entity_id -> role roundtrip is identity."""
        for role in ROLE_TO_ENTITY_ID:
            entity_id = role_to_entity_id(role)
            recovered_role = entity_id_to_role(entity_id)
            assert recovered_role == role

    def test_roundtrip_id_to_role_to_id(self) -> None:
        """entity_id -> role -> entity_id roundtrip is identity."""
        for entity_id in ENTITY_ID_TO_ROLE:
            role = entity_id_to_role(entity_id)
            recovered_id = role_to_entity_id(role)
            assert recovered_id == entity_id
