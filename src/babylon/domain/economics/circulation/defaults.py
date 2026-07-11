"""Default turnover profiles by 2-digit NAICS sector.

Feature: 023-capital-volume-ii
Task: T036

Provides DEFAULT_TURNOVER_PROFILES keyed by 2-digit NAICS code and a
FALLBACK_PROFILE for unknown sectors. Values are informed by Census
Annual Survey of Manufactures (ASM), BEA Fixed Asset Tables, and
sector-specific production cycle literature.

See Also:
    :class:`babylon.domain.economics.circulation.types.TurnoverProfile`: Data model.
    :class:`babylon.domain.economics.circulation.turnover.DefaultTurnoverProfileSource`:
        Resolver that uses these defaults.
"""

from __future__ import annotations

from babylon.domain.economics.circulation.types import TurnoverProfile

# =============================================================================
# DEFAULT TURNOVER PROFILES BY 2-DIGIT NAICS
# =============================================================================

DEFAULT_TURNOVER_PROFILES: dict[str, TurnoverProfile] = {
    "11": TurnoverProfile(
        naics_code="11",
        working_period_days=90,
        non_working_production_days=60,
        purchase_time_days=15,
        sale_time_days=30,
        fixed_capital_ratio=0.6,
    ),
    "21": TurnoverProfile(
        naics_code="21",
        working_period_days=60,
        non_working_production_days=30,
        purchase_time_days=20,
        sale_time_days=45,
        fixed_capital_ratio=0.7,
    ),
    "23": TurnoverProfile(
        naics_code="23",
        working_period_days=90,
        non_working_production_days=0,
        purchase_time_days=15,
        sale_time_days=30,
        fixed_capital_ratio=0.5,
    ),
    "31": TurnoverProfile(
        naics_code="31",
        working_period_days=30,
        non_working_production_days=10,
        purchase_time_days=10,
        sale_time_days=20,
        fixed_capital_ratio=0.6,
    ),
    "42": TurnoverProfile(
        naics_code="42",
        working_period_days=5,
        non_working_production_days=0,
        purchase_time_days=10,
        sale_time_days=15,
        fixed_capital_ratio=0.3,
    ),
    "44": TurnoverProfile(
        naics_code="44",
        working_period_days=3,
        non_working_production_days=0,
        purchase_time_days=7,
        sale_time_days=10,
        fixed_capital_ratio=0.4,
    ),
    "48": TurnoverProfile(
        naics_code="48",
        working_period_days=15,
        non_working_production_days=0,
        purchase_time_days=5,
        sale_time_days=10,
        fixed_capital_ratio=0.7,
    ),
    "51": TurnoverProfile(
        naics_code="51",
        working_period_days=30,
        non_working_production_days=0,
        purchase_time_days=10,
        sale_time_days=20,
        fixed_capital_ratio=0.4,
    ),
    "52": TurnoverProfile(
        naics_code="52",
        working_period_days=5,
        non_working_production_days=0,
        purchase_time_days=5,
        sale_time_days=10,
        fixed_capital_ratio=0.3,
    ),
    "54": TurnoverProfile(
        naics_code="54",
        working_period_days=20,
        non_working_production_days=0,
        purchase_time_days=5,
        sale_time_days=15,
        fixed_capital_ratio=0.3,
    ),
    "62": TurnoverProfile(
        naics_code="62",
        working_period_days=1,
        non_working_production_days=0,
        purchase_time_days=3,
        sale_time_days=5,
        fixed_capital_ratio=0.5,
    ),
    "72": TurnoverProfile(
        naics_code="72",
        working_period_days=1,
        non_working_production_days=0,
        purchase_time_days=3,
        sale_time_days=3,
        fixed_capital_ratio=0.5,
    ),
}
"""Default turnover profiles keyed by 2-digit NAICS sector code.

Traceability:
    - Working periods: Census ASM production cycle data
    - Non-working production: Sector-specific (agriculture aging, mining processing)
    - Circulation times: BEA inventory-to-shipments ratios
    - Fixed capital ratios: BEA Fixed Asset Tables capital composition
"""


FALLBACK_PROFILE: TurnoverProfile = TurnoverProfile(
    naics_code="FALLBACK",
    working_period_days=20,
    non_working_production_days=5,
    purchase_time_days=10,
    sale_time_days=15,
    fixed_capital_ratio=0.5,
)
"""Fallback profile for unrecognized NAICS codes.

Moderate values representing a generic mixed-economy sector.
turnover_time = 20 + 5 + 10 + 15 = 50 days.
"""


__all__ = ["DEFAULT_TURNOVER_PROFILES", "FALLBACK_PROFILE"]
