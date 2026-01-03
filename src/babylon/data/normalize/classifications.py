"""Marxian classification logic for dimension tables.

Provides classification functions for:
- World system tier (core/semi-periphery/periphery)
- Class composition (goods_producing/service_producing/circulation/government/extraction)
- Marxian class (proletariat/petty_bourgeois/state_worker/unpaid_labor)
- Labor type (productive/unproductive/reproductive/managerial)
"""

from __future__ import annotations

# =============================================================================
# WORLD SYSTEM TIER CLASSIFICATION
# =============================================================================

# Core countries (imperialist centers receiving value transfers)
# Based on: G7 + major European/Pacific allies + tax havens that facilitate value transfer
CORE_COUNTRIES: frozenset[str] = frozenset(
    {
        # G7
        "United States",
        "Canada",
        "United Kingdom",
        "France",
        "Germany",
        "Italy",
        "Japan",
        # Other major imperialist powers
        "Australia",
        "Austria",
        "Belgium",
        "Denmark",
        "Finland",
        "Ireland",
        "Israel",
        "Luxembourg",
        "Netherlands",
        "New Zealand",
        "Norway",
        "Singapore",
        "South Korea",
        "Spain",
        "Sweden",
        "Switzerland",
        # Tax havens (facilitate imperial rent extraction)
        "Bermuda",
        "Cayman Islands",
        "British Virgin Islands",
        "Liechtenstein",
        "Monaco",
    }
)

# Semi-periphery (industrializing, mixed exploitation patterns)
# BRICS + emerging economies + regional powers
SEMI_PERIPHERY_COUNTRIES: frozenset[str] = frozenset(
    {
        # BRICS
        "Brazil",
        "Russia",
        "India",
        "China",
        "South Africa",
        # Other major emerging economies
        "Mexico",
        "Argentina",
        "Chile",
        "Colombia",
        "Turkey",
        "Indonesia",
        "Malaysia",
        "Thailand",
        "Vietnam",
        "Philippines",
        "Poland",
        "Czech Republic",
        "Hungary",
        "Romania",
        "Greece",
        "Portugal",
        "Saudi Arabia",
        "United Arab Emirates",
        "Qatar",
        "Kuwait",
        "Egypt",
        "Nigeria",
        "Kenya",
        "Morocco",
        "Pakistan",
        "Bangladesh",
        "Ukraine",
        "Kazakhstan",
        # Regional manufacturing hubs
        "Taiwan",
        "Hong Kong",
    }
)


def classify_world_system_tier(country_name: str) -> str | None:
    """Classify a country into world-system tier.

    Args:
        country_name: Country name from trade_countries table

    Returns:
        One of: 'core', 'semi_periphery', 'periphery', or None for regions/aggregates
    """
    if not country_name:
        return None

    # Check for aggregate/region markers (exact match only for geographic terms)
    # These are complete phrases that indicate an aggregate, not a real country
    aggregate_exact = {
        "World",
        "World Total",
        "Africa",
        "Asia",
        "Europe",
        "Pacific Rim",
        "North America",
    }
    if country_name in aggregate_exact:
        return None

    # These markers appear as substrings in aggregate names
    aggregate_substrings = {
        "Total",
        "NAFTA",
        "European Union",
        "CAFTA",
        "OPEC",
        "South and Central America",
        "Advanced Technology",
    }
    for marker in aggregate_substrings:
        if marker in country_name:
            return None  # Not a real country

    if country_name in CORE_COUNTRIES:
        return "core"
    elif country_name in SEMI_PERIPHERY_COUNTRIES:
        return "semi_periphery"
    else:
        return "periphery"


# =============================================================================
# CLASS COMPOSITION CLASSIFICATION (NAICS Industry)
# =============================================================================

# 2-digit NAICS sector codes for classification
# Note: QCEW uses codes like "10", "101", "102" for aggregates

GOODS_PRODUCING_SECTORS: frozenset[str] = frozenset(
    {
        "11",  # Agriculture, forestry, fishing
        "21",  # Mining, quarrying, oil/gas
        "22",  # Utilities
        "23",  # Construction
        "31",  # Manufacturing (food, textiles)
        "32",  # Manufacturing (wood, paper, chemicals)
        "33",  # Manufacturing (metals, machinery)
    }
)

EXTRACTION_SECTORS: frozenset[str] = frozenset(
    {
        "21",  # Mining, quarrying, oil/gas
        "211",  # Oil and gas extraction
        "212",  # Mining (except oil and gas)
        "213",  # Support activities for mining
    }
)

CIRCULATION_SECTORS: frozenset[str] = frozenset(
    {
        "52",  # Finance and insurance
        "53",  # Real estate and rental
        "55",  # Management of companies
    }
)

GOVERNMENT_SECTORS: frozenset[str] = frozenset(
    {
        "92",  # Public administration
    }
)

# BLS aggregation codes
BLS_AGGREGATES: dict[str, str] = {
    "10": "total",  # Total, all industries
    "101": "goods_producing",  # Goods-producing
    "102": "service_producing",  # Service-providing
}


def classify_class_composition(industry_code: str, _industry_title: str = "") -> str | None:
    """Classify an industry by Marxian class composition.

    Args:
        industry_code: NAICS or BLS industry code
        industry_title: Industry title for fallback classification

    Returns:
        One of: 'goods_producing', 'service_producing', 'circulation',
                'government', 'extraction', or None for aggregates
    """
    if not industry_code:
        return None

    # Handle BLS aggregation codes
    if industry_code in BLS_AGGREGATES:
        result = BLS_AGGREGATES[industry_code]
        return result if result != "total" else None

    # Extract 2-digit sector code
    sector = industry_code[:2] if len(industry_code) >= 2 else industry_code

    # Check extraction first (subset of goods-producing)
    if industry_code in EXTRACTION_SECTORS or sector in EXTRACTION_SECTORS:
        return "extraction"

    if sector in GOODS_PRODUCING_SECTORS:
        return "goods_producing"

    if sector in CIRCULATION_SECTORS:
        return "circulation"

    if sector in GOVERNMENT_SECTORS:
        return "government"

    # Everything else is service-producing
    # Includes: 42 (wholesale), 44-45 (retail), 48-49 (transport),
    # 51 (information), 54 (professional), 56 (admin), 61 (education),
    # 62 (healthcare), 71 (arts), 72 (food service), 81 (other services)
    return "service_producing"


def get_sector_code(industry_code: str) -> str | None:
    """Extract 2-digit sector code from NAICS code.

    Args:
        industry_code: Full NAICS or BLS industry code

    Returns:
        2-digit sector code or None
    """
    if not industry_code:
        return None

    # BLS aggregates don't have real sector codes
    if industry_code in {"10", "101", "102"}:
        return None

    # Strip "NAICS " prefix if present (from titles in codes)
    code = industry_code.replace("NAICS ", "").strip()

    # Return first 2 digits
    if len(code) >= 2 and code[:2].isdigit():
        return code[:2]

    return None


# =============================================================================
# MARXIAN CLASS CLASSIFICATION (Census Worker Class)
# =============================================================================

# Census B24080 class of worker codes
PROLETARIAT_CODES: frozenset[str] = frozenset(
    {
        "B24080_003",  # Private for-profit wage and salary workers
        "B24080_004",  # Employee of private company workers
        "B24080_006",  # Private not-for-profit wage and salary workers
        "B24080_013",  # Private for-profit wage and salary workers (Female)
        "B24080_014",  # Employee of private company workers (Female)
        "B24080_016",  # Private not-for-profit wage and salary workers (Female)
    }
)

PETTY_BOURGEOIS_CODES: frozenset[str] = frozenset(
    {
        "B24080_005",  # Self-employed in own incorporated business workers
        "B24080_010",  # Self-employed in own not incorporated business workers
        "B24080_015",  # Self-employed in own incorporated business workers (Female)
        "B24080_020",  # Self-employed in own not incorporated business workers (Female)
    }
)

STATE_WORKER_CODES: frozenset[str] = frozenset(
    {
        "B24080_007",  # Local government workers
        "B24080_008",  # State government workers
        "B24080_009",  # Federal government workers
        "B24080_017",  # Local government workers (Female)
        "B24080_018",  # State government workers (Female)
        "B24080_019",  # Federal government workers (Female)
    }
)

UNPAID_LABOR_CODES: frozenset[str] = frozenset(
    {
        "B24080_011",  # Unpaid family workers
        "B24080_021",  # Unpaid family workers (Female)
    }
)

# Totals/aggregates (not classifiable)
WORKER_CLASS_TOTALS: frozenset[str] = frozenset(
    {
        "B24080_001",  # Total
        "B24080_002",  # Male
        "B24080_012",  # Female
    }
)


def classify_marxian_class(class_code: str, class_label: str = "") -> str | None:
    """Classify a census worker class code into Marxian class.

    Args:
        class_code: Census B24080 column code
        class_label: Class label for fallback

    Returns:
        One of: 'proletariat', 'petty_bourgeois', 'state_worker',
                'unpaid_labor', or None for totals
    """
    if not class_code:
        return None

    if class_code in WORKER_CLASS_TOTALS:
        return None

    if class_code in PROLETARIAT_CODES:
        return "proletariat"

    if class_code in PETTY_BOURGEOIS_CODES:
        return "petty_bourgeois"

    if class_code in STATE_WORKER_CODES:
        return "state_worker"

    if class_code in UNPAID_LABOR_CODES:
        return "unpaid_labor"

    # Fallback to label-based classification
    label_lower = class_label.lower()
    if "private" in label_lower and ("wage" in label_lower or "employee" in label_lower):
        return "proletariat"
    elif "self-employed" in label_lower or "own business" in label_lower:
        return "petty_bourgeois"
    elif "government" in label_lower:
        return "state_worker"
    elif "unpaid" in label_lower:
        return "unpaid_labor"

    return None


# =============================================================================
# LABOR TYPE CLASSIFICATION (Census Occupation)
# =============================================================================

# Occupation category mapping based on Census C24010 categories
LABOR_TYPE_BY_CATEGORY: dict[str, str] = {
    # Productive labor - creates surplus value
    "Natural resources, construction, and maintenance occupations": "productive",
    "Production, transportation, and material moving occupations": "productive",
    # Unproductive labor - circulation, supervision
    "Sales and office occupations": "unproductive",
    # Reproductive labor - care work, social reproduction
    "Service occupations": "reproductive",
    # Managerial - command of labor
    "Management, business, science, and arts occupations": "managerial",
}


def classify_labor_type(occupation_category: str | None) -> str | None:
    """Classify an occupation category into labor type.

    Args:
        occupation_category: Census occupation category string

    Returns:
        One of: 'productive', 'unproductive', 'reproductive',
                'managerial', or None if unknown
    """
    if not occupation_category:
        return None

    return LABOR_TYPE_BY_CATEGORY.get(occupation_category)


# =============================================================================
# OWNERSHIP CLASSIFICATION (QCEW)
# =============================================================================


def classify_ownership(own_code: str) -> tuple[bool, bool]:
    """Classify QCEW ownership code into government/private flags.

    Args:
        own_code: QCEW ownership code (0-5)

    Returns:
        Tuple of (is_government, is_private)
    """
    # QCEW ownership codes:
    # 0 = Total Covered
    # 1 = Federal Government
    # 2 = State Government
    # 3 = Local Government
    # 4 = International Government (rare)
    # 5 = Private

    if own_code in {"1", "2", "3", "4"}:
        return (True, False)  # Government
    elif own_code == "5":
        return (False, True)  # Private
    else:  # "0" or unknown
        return (False, False)  # Total/unknown


# =============================================================================
# RENT BURDEN CLASSIFICATION
# =============================================================================


def classify_rent_burden(burden_bracket: str) -> tuple[bool | None, bool | None]:
    """Classify rent burden bracket.

    Args:
        burden_bracket: Rent burden percentage bracket string

    Returns:
        Tuple of (is_cost_burdened, is_severely_burdened)
    """
    if not burden_bracket:
        return (None, None)

    burden_lower = burden_bracket.lower()

    # Check for "not computed" or "zero" cases
    if "not computed" in burden_lower or "zero or negative" in burden_lower:
        return (None, None)

    # Check percentage thresholds
    # 30%+ is cost-burdened, 50%+ is severely burdened
    if "50" in burden_bracket or any(x in burden_lower for x in ["50.0", "50 percent or more"]):
        return (True, True)  # >= 50% is both burdened and severely burdened
    elif "35" in burden_bracket or "40" in burden_bracket or "45" in burden_bracket:
        return (True, False)  # 35-49% is burdened but not severely
    elif "30" in burden_bracket:
        return (True, False)  # 30-34% is cost-burdened
    elif any(x in burden_bracket for x in ["25", "20", "15", "10", "Less than"]):
        return (False, False)  # < 30% is not burdened

    return (None, None)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # World system
    "CORE_COUNTRIES",
    "SEMI_PERIPHERY_COUNTRIES",
    "classify_world_system_tier",
    # Class composition
    "GOODS_PRODUCING_SECTORS",
    "EXTRACTION_SECTORS",
    "CIRCULATION_SECTORS",
    "GOVERNMENT_SECTORS",
    "classify_class_composition",
    "get_sector_code",
    # Marxian class
    "PROLETARIAT_CODES",
    "PETTY_BOURGEOIS_CODES",
    "STATE_WORKER_CODES",
    "UNPAID_LABOR_CODES",
    "classify_marxian_class",
    # Labor type
    "LABOR_TYPE_BY_CATEGORY",
    "classify_labor_type",
    # Ownership
    "classify_ownership",
    # Rent burden
    "classify_rent_burden",
]
