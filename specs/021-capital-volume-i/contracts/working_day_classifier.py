"""Contract: WorkingDayClassifier.

Classifies territory-sector pairs by exploitation mode.
Not a System — quasi-static classification stored in persistent_data.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Data source protocol (DI)
# ---------------------------------------------------------------------------
@runtime_checkable
class ProductivityDataSource(Protocol):
    """Provides sector-level hours and productivity data."""

    def get_avg_weekly_hours(
        self, naics_sector: str, year: int
    ) -> float | None:
        """Return average weekly hours for a sector-year."""
        ...

    def get_labor_intensity_index(
        self, naics_sector: str, year: int
    ) -> float | None:
        """Return output-per-hour index (1.0 = baseline) for a sector-year."""
        ...


# ---------------------------------------------------------------------------
# Classifier contract
# ---------------------------------------------------------------------------
@runtime_checkable
class WorkingDayClassifier(Protocol):
    """Classifies sectors by exploitation mode."""

    def classify(
        self,
        avg_weekly_hours: float,
        labor_intensity_index: float,
    ) -> str:
        """Return exploitation mode: ABSOLUTE_DOMINANT, RELATIVE_DOMINANT, or MIXED.

        Classification rules:
        - ABSOLUTE_DOMINANT: hours > 45 and intensity < 1.1
        - RELATIVE_DOMINANT: hours <= 40 and intensity > 1.2
        - MIXED: all other combinations

        Thresholds are configurable via GameDefines.
        """
        ...

    def compute_visibility_modifier(
        self,
        exploitation_mode: str,
    ) -> float:
        """Return consciousness visibility modifier in [0, 1].

        ABSOLUTE_DOMINANT -> 1.0 (fully visible exploitation)
        RELATIVE_DOMINANT -> 0.3 (mostly invisible exploitation)
        MIXED -> interpolated value
        """
        ...
