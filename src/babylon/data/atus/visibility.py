"""Visibility decomposition computation service (Feature 005).

This module provides the VisibilityComputer service that computes the
visibility coefficient g₃₃ from ATUS seed data weights.

**g₃₃ Computation:**

The visibility coefficient determines what fraction of Department III
(reproductive) labor is visible to the price system. It is computed as
a weighted average of four category coefficients:

    g₃₃ = Σ(w_i × g_i)

Where:
    - w_i = fraction of reproductive labor in category i
    - g_i = visibility coefficient for category i

**Categories:**

1. domestic_unpaid (g=0.0): Invisible household labor
2. migrant_care (g=0.3): Partially visible cash economy
3. peripheral_subsistence (g=0.0): Externalized to periphery
4. state_socialized (g=1.0): Fully visible public spending

See Also:
    :mod:`babylon.data.atus.models`: VisibilityDecomposition model.
    :mod:`babylon.economics.shadow_labor`: Shadow labor calculations.
    specs/005-atus-department-iii/research.md: Weight derivation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from babylon.data.atus.models import VisibilityDecomposition

logger = logging.getLogger(__name__)


class DataSourceUnavailableError(Exception):
    """Raised when required data source is unavailable.

    Per FR-006: System must fail fast with clear error if data sources unavailable.
    """

    pass


class VisibilityComputer:
    """Service for computing g₃₃ visibility decomposition from seed data.

    This service loads visibility weights from the ATUS seed data YAML file
    and computes the national-level g₃₃ coefficient.

    **Usage:**

        >>> computer = VisibilityComputer()
        >>> g33 = computer.get_national_g33()
        >>> print(f"National g₃₃ = {g33:.3f}")
        National g₃₃ = 0.180

        >>> decomp = computer.compute_visibility()
        >>> print(f"Domestic unpaid: {decomp.domestic_unpaid:.1%}")
        Domestic unpaid: 70.0%

    Args:
        seed_data_path: Path to ATUS seed data YAML file. If None, uses default.

    Raises:
        DataSourceUnavailableError: If seed data file is unavailable.
    """

    # Default path relative to this module
    _DEFAULT_SEED_DATA = Path(__file__).parent / "seed_data.yaml"

    def __init__(self, seed_data_path: str | Path | None = None) -> None:
        """Initialize the visibility computer.

        Args:
            seed_data_path: Optional path to seed data YAML. Uses default if None.

        Raises:
            DataSourceUnavailableError: If seed data cannot be loaded.
        """
        path = Path(seed_data_path) if seed_data_path else self._DEFAULT_SEED_DATA

        if not path.exists():
            msg = f"Visibility seed data not found: {path}"
            raise DataSourceUnavailableError(msg)

        try:
            with open(path, encoding="utf-8") as f:
                self._data: dict[str, Any] = yaml.safe_load(f)
        except (OSError, yaml.YAMLError) as e:
            msg = f"Failed to load visibility seed data from {path}: {e}"
            raise DataSourceUnavailableError(msg) from e

        # Validate required section exists
        if "visibility_weights" not in self._data:
            msg = f"Seed data missing 'visibility_weights' section: {path}"
            raise DataSourceUnavailableError(msg)

        self._weights = self._data["visibility_weights"]
        self._fractions = self._weights["fractions"]
        self._coefficients = self._weights["coefficients"]

        logger.debug("VisibilityComputer initialized with fractions: %s", self._fractions)

    def compute_visibility(self) -> VisibilityDecomposition:
        """Compute visibility decomposition from seed data weights.

        Returns:
            VisibilityDecomposition with four category fractions and total_g33.

        Example:
            >>> computer = VisibilityComputer()
            >>> decomp = computer.compute_visibility()
            >>> decomp.total_g33
            0.18
        """
        return VisibilityDecomposition(
            domestic_unpaid=self._fractions["domestic_unpaid"],
            migrant_care=self._fractions["migrant_care"],
            peripheral_subsistence=self._fractions["peripheral_subsistence"],
            state_socialized=self._fractions["state_socialized"],
        )

    def get_national_g33(self) -> float:
        """Get national-level g₃₃ visibility coefficient.

        This is a convenience method that computes the decomposition and
        returns just the total_g33 value.

        Returns:
            National average visibility coefficient (typically 0.1-0.3).

        Example:
            >>> computer = VisibilityComputer()
            >>> computer.get_national_g33()
            0.18
        """
        return self.compute_visibility().total_g33


__all__ = [
    "DataSourceUnavailableError",
    "VisibilityComputer",
]
