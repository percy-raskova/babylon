"""Protocol definition for visibility decomposition computation.

This module defines the contract for computing g₃₃ visibility decomposition.
Implementations must satisfy this protocol for dependency injection.

Note: This is a DESIGN DOCUMENT, not runnable code. It defines the interface
that will be implemented in src/babylon/data/atus/visibility.py.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class VisibilityDecompositionResult(BaseModel):
    """Result of visibility decomposition computation.

    Attributes:
        domestic_unpaid_fraction: Fraction in domestic unpaid category.
        migrant_care_fraction: Fraction in migrant care category.
        peripheral_subsistence_fraction: Fraction in peripheral category.
        state_socialized_fraction: Fraction in state-socialized category.
        total_g33: Weighted visibility coefficient.
    """

    domestic_unpaid_fraction: float
    migrant_care_fraction: float
    peripheral_subsistence_fraction: float
    state_socialized_fraction: float
    total_g33: float


class VisibilityComputerProtocol(Protocol):
    """Protocol for g₃₃ visibility computation services.

    Implementations must provide a method to compute visibility decomposition
    given data source inputs (ATUS, OEWS, QCEW).
    """

    def compute_visibility(
        self,
        year: int,
        class_position: str,
    ) -> VisibilityDecompositionResult:
        """Compute visibility decomposition for a class position.

        Args:
            year: Survey year for data lookup.
            class_position: One of 'proletariat', 'petty_bourgeoisie', 'bourgeoisie'.

        Returns:
            VisibilityDecompositionResult with four fractions and total g₃₃.

        Raises:
            DataSourceUnavailableError: If required data source is unavailable.
            ValueError: If class_position is not recognized.
        """
        ...

    def get_national_g33(self, year: int) -> float:
        """Get national-level g₃₃ (not class-disaggregated).

        Args:
            year: Survey year.

        Returns:
            National average visibility coefficient.
        """
        ...
