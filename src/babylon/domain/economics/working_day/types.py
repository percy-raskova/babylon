"""Working Day domain types (Feature 021, FR-007/FR-008).

Frozen Pydantic model for working day characteristics per territory-sector.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkingDayState(BaseModel):
    """Characteristics of the working day for a territory-sector pair.

    Stores the two primitive fields (avg_weekly_hours, labor_intensity_index)
    from which exploitation mode and visibility modifier are derived.

    Args:
        fips_code: 5-digit county FIPS code.
        naics_sector: 2-digit NAICS sector code.
        year: Calendar year.
        avg_weekly_hours: Average actual hours worked per week, in [0, 168].
        labor_intensity_index: Output per hour relative to baseline (1.0 = baseline).
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(min_length=5, max_length=5)
    naics_sector: str = Field(min_length=2, max_length=2)
    year: int = Field(ge=2005, le=2030)
    avg_weekly_hours: float = Field(ge=0.0, le=168.0)
    labor_intensity_index: float = Field(gt=0.0)
