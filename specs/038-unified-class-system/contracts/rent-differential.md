# Contract: Rent Differential Calculator

**Spec**: FR-007
**Module**: `src/babylon/economics/melt/rent_differential.py`
**Pattern**: Protocol + DefaultRentDifferentialCalculator

---

## Protocol Definition

```python
from __future__ import annotations

from typing import Protocol

from babylon.economics.tensor import NoDataSentinel
from babylon.models.enums import CommunityType


class RentDifferentialCalculator(Protocol):
    """Compute nation-specific imperial rent differentials from ACS earnings data.

    The rent differential measures the gap between settler wages and
    nation-specific wages within the same NAICS code at county level.
    Positive values indicate settler workers earn more (the standard case).
    """

    def compute_differential(
        self,
        fips: str,
        nation: CommunityType,
        naics: str,
        year: int,
    ) -> float | NoDataSentinel:
        """Compute Phi_differential for a specific county x nation x NAICS.

        Formula:
            Phi_differential = median_earnings[SETTLER, fips, naics]
                             - median_earnings[nation, fips, naics]

        Args:
            fips: 5-digit FIPS code.
            nation: Target nation (e.g., NEW_AFRIKAN, CHICANO, FIRST_NATIONS).
            naics: 2-digit NAICS sector code (e.g., "31-33" for Manufacturing).
            year: Calendar year for ACS data.

        Returns:
            Differential in $/year, or NoDataSentinel if either side is suppressed.
        """
        ...

    def compute_county_aggregate(
        self,
        fips: str,
        nation: CommunityType,
        year: int,
    ) -> float | NoDataSentinel:
        """Compute employment-weighted county-level aggregate differential.

        Aggregates per-NAICS differentials weighted by QCEW employment
        composition at county level. NAICS codes returning NoDataSentinel
        are excluded from the weighted average.

        Args:
            fips: 5-digit FIPS code.
            nation: Target nation for differential.
            year: Calendar year.

        Returns:
            Employment-weighted average differential, or NoDataSentinel
            if no NAICS codes have valid data for this county x nation.
        """
        ...
```

---

## Behavioral Contracts

### BC-015: Suppressed Data Propagation
```
GIVEN ACS data suppressed for nation N in NAICS code X at county F
WHEN compute_differential(F, N, X, year) is called
THEN returns NoDataSentinel(fips=F, year=year, reason="ACS suppressed: ...")
```

### BC-016: Positive Differential Convention
```
GIVEN settler earnings > nation earnings for same NAICS at same county
WHEN compute_differential is called
THEN result > 0 (positive = settler advantage)
```

### BC-017: Employment-Weighted Aggregation
```
GIVEN NAICS codes A (1000 employees) and B (100 employees)
WITH differential_A = 5000 and differential_B = 10000
WHEN compute_county_aggregate is called
THEN result ≈ (5000*1000 + 10000*100) / (1000+100) ≈ 5454.55
```

### BC-018: All-Suppressed County
```
GIVEN all NAICS codes return NoDataSentinel for county F, nation N
WHEN compute_county_aggregate(F, N, year) is called
THEN returns NoDataSentinel(fips=F, year=year, reason="No valid NAICS data: ...")
```

### BC-019: SETTLER Nation Self-Differential
```
GIVEN nation = CommunityType.SETTLER
WHEN compute_differential is called
THEN returns 0.0 (settler vs settler = no differential)
```

### BC-020: Wayne > Oakland Differential (Detroit Validation)
```
GIVEN Wayne County (26163) and Oakland County (26125) for NEW_AFRIKAN
WHEN compute_county_aggregate is called for each
THEN Wayne differential >= Oakland differential
(internal colony thesis: gap wider where extractive relationship more direct)
```
