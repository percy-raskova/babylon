"""ATUS activity code mappings to Babylon reproductive labor categories.

This module defines the mapping from BLS ATUS 6-digit activity codes to
Babylon's reproductive labor categories for Department III calculations.

**ATUS Code Structure:**
- First 2 digits: Major category (02 = Household, 03 = Caring for HH)
- Digits 3-4: Second-tier category
- Digits 5-6: Detailed activity

**Babylon Categories:**
- housework: Cleaning, laundry, maintenance, household management
- cooking: Food and drink preparation
- childcare: Physical care and activities with children
- eldercare: Physical care and activities with adults
- emotional_support: Listening, comforting (reserved for future)

**Data Source:**
ATUS Activity Lexicon: https://www.bls.gov/tus/lexicons.htm

See Also:
    :mod:`babylon.data.atus.loader`: ATUSReferenceLoader uses these mappings.
    :class:`babylon.data.reference.schema.DimATUSActivityCategory`: Database table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ATUSActivityMapping:
    """Mapping from ATUS code prefix to Babylon category.

    Attributes:
        atus_code_prefix: 4-digit ATUS code prefix (e.g., "0201").
        atus_description: Human-readable description from BLS lexicon.
        babylon_category: Target Babylon category.
        major_category: High-level grouping for analysis.
        is_reproductive: Whether this activity counts as reproductive labor.
    """

    atus_code_prefix: str
    atus_description: str
    babylon_category: str
    major_category: str
    is_reproductive: bool = True


# =============================================================================
# ATUS ACTIVITY CODE MAPPINGS
# =============================================================================

# Maps ATUS code prefixes to Babylon reproductive labor categories.
# Code prefixes match activity codes starting with these digits.
# Based on BLS ATUS Activity Lexicon (2023 revision).

ATUS_CODE_MAPPINGS: tuple[ATUSActivityMapping, ...] = (
    # -------------------------------------------------------------------------
    # 02: HOUSEHOLD ACTIVITIES
    # -------------------------------------------------------------------------
    ATUSActivityMapping(
        atus_code_prefix="0201",
        atus_description="Housework (cleaning, laundry)",
        babylon_category="housework",
        major_category="Household Activities",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0202",
        atus_description="Food and drink preparation",
        babylon_category="cooking",
        major_category="Household Activities",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0203",
        atus_description="Interior maintenance, repair, and decoration",
        babylon_category="housework",
        major_category="Household Activities",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0204",
        atus_description="Exterior maintenance, repair, and decoration",
        babylon_category="housework",
        major_category="Household Activities",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0205",
        atus_description="Lawn, garden, and houseplant care",
        babylon_category="housework",
        major_category="Household Activities",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0206",
        atus_description="Animals and pets care",
        babylon_category="housework",
        major_category="Household Activities",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0207",
        atus_description="Vehicles (household)",
        babylon_category="housework",
        major_category="Household Activities",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0208",
        atus_description="Appliances, tools, and toys (household)",
        babylon_category="housework",
        major_category="Household Activities",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0209",
        atus_description="Household management and planning",
        babylon_category="housework",
        major_category="Household Activities",
    ),
    # -------------------------------------------------------------------------
    # 03: CARING FOR HOUSEHOLD MEMBERS
    # -------------------------------------------------------------------------
    ATUSActivityMapping(
        atus_code_prefix="0301",
        atus_description="Caring for and helping household children",
        babylon_category="childcare",
        major_category="Caring for Household Members",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0302",
        atus_description="Activities related to household children's education",
        babylon_category="childcare",
        major_category="Caring for Household Members",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0303",
        atus_description="Activities related to household children's health",
        babylon_category="childcare",
        major_category="Caring for Household Members",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0304",
        atus_description="Caring for and helping household adults",
        babylon_category="eldercare",
        major_category="Caring for Household Members",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0305",
        atus_description="Helping household adults",
        babylon_category="eldercare",
        major_category="Caring for Household Members",
    ),
    # -------------------------------------------------------------------------
    # 04: CARING FOR NON-HOUSEHOLD MEMBERS
    # Note: Included for completeness but weighted differently in calculations
    # -------------------------------------------------------------------------
    ATUSActivityMapping(
        atus_code_prefix="0401",
        atus_description="Caring for and helping non-household children",
        babylon_category="childcare",
        major_category="Caring for Non-Household Members",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0402",
        atus_description="Activities related to non-household children's education",
        babylon_category="childcare",
        major_category="Caring for Non-Household Members",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0403",
        atus_description="Activities related to non-household children's health",
        babylon_category="childcare",
        major_category="Caring for Non-Household Members",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0404",
        atus_description="Caring for and helping non-household adults",
        babylon_category="eldercare",
        major_category="Caring for Non-Household Members",
    ),
    ATUSActivityMapping(
        atus_code_prefix="0405",
        atus_description="Helping non-household adults",
        babylon_category="eldercare",
        major_category="Caring for Non-Household Members",
    ),
)

# Lookup dict for fast access by code prefix
ATUS_CODE_MAPPING: dict[str, ATUSActivityMapping] = {
    mapping.atus_code_prefix: mapping for mapping in ATUS_CODE_MAPPINGS
}

# Categories used in Babylon shadow labor calculations
BABYLON_CATEGORIES: tuple[str, ...] = (
    "housework",
    "cooking",
    "childcare",
    "eldercare",
    "emotional_support",
)

# Major categories for aggregation
MAJOR_CATEGORIES: tuple[str, ...] = (
    "Household Activities",
    "Caring for Household Members",
    "Caring for Non-Household Members",
)


def get_babylon_category(atus_code: str) -> str | None:
    """Get Babylon category for an ATUS activity code.

    Args:
        atus_code: 6-digit ATUS activity code (e.g., "030101").

    Returns:
        Babylon category name, or None if code not mapped.

    Example:
        >>> get_babylon_category("030101")
        'childcare'
        >>> get_babylon_category("020201")
        'cooking'
        >>> get_babylon_category("999999")  # Unknown code
        None
    """
    # Try 4-digit prefix first (most specific)
    prefix_4 = atus_code[:4]
    if prefix_4 in ATUS_CODE_MAPPING:
        return ATUS_CODE_MAPPING[prefix_4].babylon_category

    return None


def get_mapping(atus_code: str) -> ATUSActivityMapping | None:
    """Get full mapping for an ATUS activity code.

    Args:
        atus_code: 6-digit ATUS activity code.

    Returns:
        ATUSActivityMapping or None if not found.
    """
    prefix_4 = atus_code[:4]
    return ATUS_CODE_MAPPING.get(prefix_4)


__all__ = [
    "ATUSActivityMapping",
    "ATUS_CODE_MAPPING",
    "ATUS_CODE_MAPPINGS",
    "BABYLON_CATEGORIES",
    "MAJOR_CATEGORIES",
    "get_babylon_category",
    "get_mapping",
]
