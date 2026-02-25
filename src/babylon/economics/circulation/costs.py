"""Circulation costs and labor classification per Marx Capital II Ch. 6.

Feature: 023-capital-volume-ii
User Story: US6 - Circulation Costs (FR-018, FR-019, FR-020)

Marx distinguishes between:
    1. **Pure circulation costs** (faux frais): Add no value, merely facilitate
       the change of ownership (sales, accounting, advertising).
    2. **Transportation**: Adds real value by changing spatial location of
       commodities (a genuine use-value transformation).
    3. **Storage of use-values**: Adds value by preserving commodity use-value
       (warehousing perishables, climate-controlled storage).

This module provides labor classification logic to distinguish productive
labor (creates/preserves use-value) from unproductive labor (facilitates
exchange without value creation).

See Also:
    :class:`babylon.economics.circulation.types.PureCirculationCosts`: Cost model
    :class:`babylon.economics.circulation.types.TransportationValue`: Transport model
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LaborClassification(BaseModel):
    """Classification of labor as productive or unproductive of value.

    Per Marx, productive labor transforms material or changes commodity
    location (creating use-value). Unproductive labor merely facilitates
    exchange (sales, accounting, advertising) without creating value.

    Args:
        occupation_code: SOC/OES occupation code.
        description: Human-readable occupation description.
        is_productive: True if labor is productive of value.
        rationale: Explanation of why this classification was made.
    """

    model_config = ConfigDict(frozen=True)

    occupation_code: str
    description: str
    is_productive: bool
    rationale: str


# =============================================================================
# Keyword-based classification rules
# =============================================================================

# Keywords in occupation descriptions that indicate PRODUCTIVE labor.
# These workers transform materials, change commodity location, or
# preserve use-value.
_PRODUCTIVE_KEYWORDS: list[str] = [
    "production",
    "manufacturing",
    "assembl",
    "fabricat",
    "machin",
    "truck driv",
    "transport",
    "warehouse",
    "storage",
    "freight",
    "delivery",
    "packaging",
    "welding",
    "carpenter",
    "construction",
    "electrician",
    "plumber",
    "mechanic",
    "farm",
    "agricultural",
    "mining",
    "logging",
    "fishing",
]

# Keywords indicating UNPRODUCTIVE labor (exchange-facilitating).
_UNPRODUCTIVE_KEYWORDS: list[str] = [
    "cashier",
    "sales",
    "retail",
    "advertising",
    "marketing",
    "account",
    "bookkeep",
    "auditor",
    "security guard",
    "security officer",
    "surveillance",
    "insurance",
    "financial",
    "real estate",
    "broker",
    "teller",
    "clerk",
    "receptionist",
]

# Rationale strings for each classification pathway
_PRODUCTIVE_RATIONALE = "Transforms materials, changes location, or preserves use-value"
_UNPRODUCTIVE_RATIONALE = "Facilitates exchange without creating use-value"
_DEFAULT_RATIONALE = "No matching classification keywords; default to unproductive"

# Maximum number of keywords to check per list (static loop bound)
_MAX_KEYWORDS = 50


def classify_labor(occupation_code: str, description: str) -> LaborClassification:
    """Classify labor as productive or unproductive of value.

    Uses keyword matching on the occupation description to determine
    whether the labor creates use-value (productive) or merely
    facilitates exchange (unproductive).

    Classification rules (from Marx Capital II Ch. 6):
        - Production/manufacturing workers: productive (transforms materials)
        - Truck drivers/transport: productive (changes location = use-value)
        - Warehouse workers: productive (preserves use-value)
        - Cashiers/sales: unproductive (facilitates exchange only)
        - Accountants/bookkeepers: unproductive (facilitates exchange)
        - Advertising/marketing: unproductive (creates no use-value)
        - Security guards: unproductive (protects property relations)

    Args:
        occupation_code: SOC/OES occupation code.
        description: Human-readable occupation description.

    Returns:
        LaborClassification with is_productive flag and rationale.
    """
    desc_lower = description.lower()

    # Check productive keywords first (production takes priority)
    for i, keyword in enumerate(_PRODUCTIVE_KEYWORDS):
        if i >= _MAX_KEYWORDS:
            break
        if keyword in desc_lower:
            return LaborClassification(
                occupation_code=occupation_code,
                description=description,
                is_productive=True,
                rationale=_PRODUCTIVE_RATIONALE,
            )

    # Check unproductive keywords
    for i, keyword in enumerate(_UNPRODUCTIVE_KEYWORDS):
        if i >= _MAX_KEYWORDS:
            break
        if keyword in desc_lower:
            return LaborClassification(
                occupation_code=occupation_code,
                description=description,
                is_productive=False,
                rationale=_UNPRODUCTIVE_RATIONALE,
            )

    # Default: unclassifiable labor defaults to unproductive
    return LaborClassification(
        occupation_code=occupation_code,
        description=description,
        is_productive=False,
        rationale=_DEFAULT_RATIONALE,
    )


__all__ = [
    "LaborClassification",
    "classify_labor",
]
