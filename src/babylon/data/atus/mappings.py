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
- emotional_support: Socializing, religious activities, volunteer counseling

**Occupation Groups (SOC Major Group → Class Proxy):**
- professional_managerial: SOC 11-13 (Management, Business, Financial)
- professional_technical: SOC 15-29 (Computer, Engineering, Science, Legal, Education, Healthcare)
- sales_clerical: SOC 41-43 (Sales, Office/Admin)
- service: SOC 31-39 (Healthcare Support, Protective, Food, Cleaning, Personal Care)
- trades: SOC 45-49 (Farming, Construction, Installation, Maintenance)
- production_transport: SOC 51-53 (Production, Transportation)

**Data Sources:**
- ATUS Activity Lexicon: https://www.bls.gov/tus/lexicons.htm
- SOC Major Groups: https://www.bls.gov/soc/2018/major_groups.htm
- IPUMS ATUS: https://www.atusdata.org

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
    # -------------------------------------------------------------------------
    # 12: SOCIALIZING, RELAXING, AND LEISURE (emotional_support proxy)
    # Note: 1201 = Socializing and Communicating includes emotional labor
    # -------------------------------------------------------------------------
    ATUSActivityMapping(
        atus_code_prefix="1201",
        atus_description="Socializing and communicating (talking, listening)",
        babylon_category="emotional_support",
        major_category="Socializing and Emotional Labor",
    ),
    # -------------------------------------------------------------------------
    # 14: RELIGIOUS AND SPIRITUAL ACTIVITIES (emotional_support proxy)
    # Note: Includes confession, spiritual counseling, support groups
    # -------------------------------------------------------------------------
    ATUSActivityMapping(
        atus_code_prefix="1401",
        atus_description="Religious or spiritual practices",
        babylon_category="emotional_support",
        major_category="Socializing and Emotional Labor",
    ),
    ATUSActivityMapping(
        atus_code_prefix="1402",
        atus_description="Attendance at religious services",
        babylon_category="emotional_support",
        major_category="Socializing and Emotional Labor",
    ),
    ATUSActivityMapping(
        atus_code_prefix="1403",
        atus_description="Participation in religious practices",
        babylon_category="emotional_support",
        major_category="Socializing and Emotional Labor",
    ),
    ATUSActivityMapping(
        atus_code_prefix="1404",
        atus_description="Religious education activities",
        babylon_category="emotional_support",
        major_category="Socializing and Emotional Labor",
    ),
    ATUSActivityMapping(
        atus_code_prefix="1405",
        atus_description="Religious organization activities",
        babylon_category="emotional_support",
        major_category="Socializing and Emotional Labor",
    ),
    # -------------------------------------------------------------------------
    # 15: VOLUNTEER ACTIVITIES (partial emotional_support)
    # Note: 1502 = Social Service and Care includes counseling, mentoring
    # -------------------------------------------------------------------------
    ATUSActivityMapping(
        atus_code_prefix="1502",
        atus_description="Social service and care activities (volunteer)",
        babylon_category="emotional_support",
        major_category="Socializing and Emotional Labor",
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
    "Socializing and Emotional Labor",
)


# =============================================================================
# OCCUPATION GROUP MAPPINGS (SOC → Class Proxy)
# =============================================================================


@dataclass(frozen=True)
class OccupationGroupMapping:
    """Mapping from SOC major group to Babylon occupation group (class proxy).

    Attributes:
        soc_major_range: Tuple of (min, max) SOC major group codes (inclusive).
        soc_description: BLS description of SOC major group.
        babylon_group: Target Babylon occupation group (class proxy).
        class_character: Predominant class character of this occupation group.
    """

    soc_major_range: tuple[int, int]
    soc_description: str
    babylon_group: str
    class_character: str


# Maps SOC major groups to Babylon occupation groups (class proxies).
# Based on BLS 2018 SOC: https://www.bls.gov/soc/2018/major_groups.htm
# Class character based on labor process analysis.
OCCUPATION_GROUP_MAPPINGS: tuple[OccupationGroupMapping, ...] = (
    # Management, Business, Financial Operations
    OccupationGroupMapping(
        soc_major_range=(11, 13),
        soc_description="Management, Business, and Financial Operations",
        babylon_group="professional_managerial",
        class_character="bourgeois/petit_bourgeois",
    ),
    # Computer, Engineering, Science, Legal, Education, Arts, Healthcare Practitioners
    OccupationGroupMapping(
        soc_major_range=(15, 29),
        soc_description="Professional and Technical Occupations",
        babylon_group="professional_technical",
        class_character="labor_aristocracy",
    ),
    # Healthcare Support, Protective, Food Prep, Cleaning, Personal Care
    OccupationGroupMapping(
        soc_major_range=(31, 39),
        soc_description="Service Occupations",
        babylon_group="service",
        class_character="proletariat",
    ),
    # Sales, Office and Administrative Support
    OccupationGroupMapping(
        soc_major_range=(41, 43),
        soc_description="Sales and Office Occupations",
        babylon_group="sales_clerical",
        class_character="proletariat/petit_bourgeois",
    ),
    # Farming, Construction, Installation, Maintenance
    OccupationGroupMapping(
        soc_major_range=(45, 49),
        soc_description="Natural Resources, Construction, and Maintenance",
        babylon_group="trades",
        class_character="proletariat",
    ),
    # Production, Transportation, Material Moving
    OccupationGroupMapping(
        soc_major_range=(51, 53),
        soc_description="Production, Transportation, and Material Moving",
        babylon_group="production_transport",
        class_character="proletariat",
    ),
)

# Babylon occupation groups for disaggregation
BABYLON_OCCUPATION_GROUPS: tuple[str, ...] = (
    "professional_managerial",
    "professional_technical",
    "sales_clerical",
    "service",
    "trades",
    "production_transport",
)

# Lookup dict for SOC → occupation group
SOC_TO_OCCUPATION_GROUP: dict[int, str] = {}
for mapping in OCCUPATION_GROUP_MAPPINGS:
    for soc in range(mapping.soc_major_range[0], mapping.soc_major_range[1] + 1):
        SOC_TO_OCCUPATION_GROUP[soc] = mapping.babylon_group


def get_occupation_group(soc_major: int) -> str | None:
    """Get Babylon occupation group for a SOC major group code.

    Args:
        soc_major: 2-digit SOC major group code (11-53).

    Returns:
        Babylon occupation group name, or None if not mapped.

    Example:
        >>> get_occupation_group(11)
        'professional_managerial'
        >>> get_occupation_group(31)
        'service'
        >>> get_occupation_group(99)  # Unknown
        None
    """
    return SOC_TO_OCCUPATION_GROUP.get(soc_major)


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
    # Activity mappings
    "ATUSActivityMapping",
    "ATUS_CODE_MAPPING",
    "ATUS_CODE_MAPPINGS",
    "BABYLON_CATEGORIES",
    "MAJOR_CATEGORIES",
    "get_babylon_category",
    "get_mapping",
    # Occupation group mappings
    "OccupationGroupMapping",
    "OCCUPATION_GROUP_MAPPINGS",
    "BABYLON_OCCUPATION_GROUPS",
    "SOC_TO_OCCUPATION_GROUP",
    "get_occupation_group",
]
