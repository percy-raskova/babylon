"""Unit tests for ATUS activity code mappings.

Tests the mappings module for:
- ATUS code structure compliance
- Babylon category coverage
- Lookup function behavior
"""

from __future__ import annotations

import pytest

from babylon.data.atus.mappings import (
    ATUS_CODE_MAPPING,
    ATUS_CODE_MAPPINGS,
    BABYLON_CATEGORIES,
    MAJOR_CATEGORIES,
    ATUSActivityMapping,
    get_babylon_category,
    get_mapping,
)


class TestATUSActivityMapping:
    """Test ATUSActivityMapping dataclass."""

    def test_mapping_is_frozen(self) -> None:
        """Mapping dataclass should be immutable."""
        mapping = ATUSActivityMapping(
            atus_code_prefix="0201",
            atus_description="Test",
            babylon_category="housework",
            major_category="Household Activities",
        )

        with pytest.raises(AttributeError):
            mapping.atus_code_prefix = "9999"  # type: ignore[misc]

    def test_is_reproductive_defaults_true(self) -> None:
        """is_reproductive should default to True."""
        mapping = ATUSActivityMapping(
            atus_code_prefix="0201",
            atus_description="Test",
            babylon_category="housework",
            major_category="Household Activities",
        )
        assert mapping.is_reproductive is True


class TestATUSCodeMappings:
    """Test ATUS_CODE_MAPPINGS tuple."""

    def test_mappings_not_empty(self) -> None:
        """Should have at least one mapping."""
        assert len(ATUS_CODE_MAPPINGS) > 0

    def test_all_mappings_are_correct_type(self) -> None:
        """All entries should be ATUSActivityMapping."""
        for mapping in ATUS_CODE_MAPPINGS:
            assert isinstance(mapping, ATUSActivityMapping)

    def test_atus_codes_are_4_digits(self) -> None:
        """ATUS code prefixes should be 4 digits."""
        for mapping in ATUS_CODE_MAPPINGS:
            assert len(mapping.atus_code_prefix) == 4
            assert mapping.atus_code_prefix.isdigit()

    def test_all_codes_are_unique(self) -> None:
        """Each ATUS code prefix should appear only once."""
        prefixes = [m.atus_code_prefix for m in ATUS_CODE_MAPPINGS]
        assert len(prefixes) == len(set(prefixes))

    def test_household_activities_mapped(self) -> None:
        """Should have mappings for 02xx codes (Household Activities)."""
        household_codes = [m for m in ATUS_CODE_MAPPINGS if m.atus_code_prefix.startswith("02")]
        assert len(household_codes) > 0

    def test_caring_for_household_members_mapped(self) -> None:
        """Should have mappings for 03xx codes (Caring for HH)."""
        caring_codes = [m for m in ATUS_CODE_MAPPINGS if m.atus_code_prefix.startswith("03")]
        assert len(caring_codes) > 0


class TestBabylonCategories:
    """Test Babylon category coverage."""

    def test_all_categories_defined(self) -> None:
        """BABYLON_CATEGORIES should include all expected categories."""
        expected = {"housework", "cooking", "childcare", "eldercare", "emotional_support"}
        assert set(BABYLON_CATEGORIES) == expected

    def test_mappings_use_valid_categories(self) -> None:
        """All mappings should use categories from BABYLON_CATEGORIES."""
        for mapping in ATUS_CODE_MAPPINGS:
            assert mapping.babylon_category in BABYLON_CATEGORIES

    def test_housework_is_covered(self) -> None:
        """At least one mapping should map to housework."""
        housework_mappings = [m for m in ATUS_CODE_MAPPINGS if m.babylon_category == "housework"]
        assert len(housework_mappings) > 0

    def test_cooking_is_covered(self) -> None:
        """At least one mapping should map to cooking."""
        cooking_mappings = [m for m in ATUS_CODE_MAPPINGS if m.babylon_category == "cooking"]
        assert len(cooking_mappings) > 0

    def test_childcare_is_covered(self) -> None:
        """At least one mapping should map to childcare."""
        childcare_mappings = [m for m in ATUS_CODE_MAPPINGS if m.babylon_category == "childcare"]
        assert len(childcare_mappings) > 0

    def test_eldercare_is_covered(self) -> None:
        """At least one mapping should map to eldercare."""
        eldercare_mappings = [m for m in ATUS_CODE_MAPPINGS if m.babylon_category == "eldercare"]
        assert len(eldercare_mappings) > 0


class TestMajorCategories:
    """Test major category coverage."""

    def test_major_categories_defined(self) -> None:
        """MAJOR_CATEGORIES should include expected values."""
        expected = {
            "Household Activities",
            "Caring for Household Members",
            "Caring for Non-Household Members",
        }
        assert set(MAJOR_CATEGORIES) == expected

    def test_mappings_use_valid_major_categories(self) -> None:
        """All mappings should use categories from MAJOR_CATEGORIES."""
        for mapping in ATUS_CODE_MAPPINGS:
            assert mapping.major_category in MAJOR_CATEGORIES


class TestATUSCodeMappingDict:
    """Test ATUS_CODE_MAPPING lookup dict."""

    def test_dict_matches_tuple(self) -> None:
        """Dict should have same number of entries as tuple."""
        assert len(ATUS_CODE_MAPPING) == len(ATUS_CODE_MAPPINGS)

    def test_keys_are_code_prefixes(self) -> None:
        """Keys should be ATUS code prefixes."""
        for key in ATUS_CODE_MAPPING:
            assert len(key) == 4
            assert key.isdigit()

    def test_values_are_mappings(self) -> None:
        """Values should be ATUSActivityMapping instances."""
        for value in ATUS_CODE_MAPPING.values():
            assert isinstance(value, ATUSActivityMapping)


class TestGetBabylonCategory:
    """Test get_babylon_category function."""

    def test_returns_correct_category_for_housework(self) -> None:
        """Should return housework for 0201xx codes."""
        category = get_babylon_category("020101")
        assert category == "housework"

    def test_returns_correct_category_for_cooking(self) -> None:
        """Should return cooking for 0202xx codes."""
        category = get_babylon_category("020201")
        assert category == "cooking"

    def test_returns_correct_category_for_childcare(self) -> None:
        """Should return childcare for 0301xx codes."""
        category = get_babylon_category("030101")
        assert category == "childcare"

    def test_returns_correct_category_for_eldercare(self) -> None:
        """Should return eldercare for 0304xx codes."""
        category = get_babylon_category("030401")
        assert category == "eldercare"

    def test_returns_none_for_unknown_code(self) -> None:
        """Should return None for unmapped codes."""
        category = get_babylon_category("999999")
        assert category is None

    def test_handles_short_codes(self) -> None:
        """Should handle codes shorter than 6 digits."""
        # 4-digit code still works (uses first 4 chars)
        category = get_babylon_category("0201")
        assert category == "housework"


class TestGetMapping:
    """Test get_mapping function."""

    def test_returns_mapping_for_valid_code(self) -> None:
        """Should return full mapping for valid codes."""
        mapping = get_mapping("020101")

        assert mapping is not None
        assert isinstance(mapping, ATUSActivityMapping)
        assert mapping.babylon_category == "housework"

    def test_returns_none_for_invalid_code(self) -> None:
        """Should return None for unmapped codes."""
        mapping = get_mapping("999999")
        assert mapping is None

    def test_mapping_has_all_fields(self) -> None:
        """Returned mapping should have all required fields."""
        mapping = get_mapping("020101")

        assert mapping is not None
        assert mapping.atus_code_prefix is not None
        assert mapping.atus_description is not None
        assert mapping.babylon_category is not None
        assert mapping.major_category is not None
        assert mapping.is_reproductive is not None


class TestSpecificCodeMappings:
    """Test specific ATUS code mappings from BLS lexicon."""

    def test_0201_is_housework(self) -> None:
        """0201 (Housework) should map to housework."""
        mapping = get_mapping("020199")
        assert mapping is not None
        assert mapping.babylon_category == "housework"
        assert (
            "cleaning" in mapping.atus_description.lower()
            or "housework" in mapping.atus_description.lower()
        )

    def test_0202_is_cooking(self) -> None:
        """0202 (Food prep) should map to cooking."""
        mapping = get_mapping("020299")
        assert mapping is not None
        assert mapping.babylon_category == "cooking"
        assert "food" in mapping.atus_description.lower()

    def test_0301_is_childcare(self) -> None:
        """0301 (Caring for HH children) should map to childcare."""
        mapping = get_mapping("030199")
        assert mapping is not None
        assert mapping.babylon_category == "childcare"
        assert "child" in mapping.atus_description.lower()

    def test_0304_is_eldercare(self) -> None:
        """0304 (Caring for HH adults) should map to eldercare."""
        mapping = get_mapping("030499")
        assert mapping is not None
        assert mapping.babylon_category == "eldercare"
        assert "adult" in mapping.atus_description.lower()
