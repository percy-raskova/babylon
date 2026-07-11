"""NAICS to Marxian Department mapping.

Maps NAICS codes to Marxian reproduction schema departments based on
end-use destination, not production process.

Departments:
    I   = Means of Production (consumed productively by capital)
    IIa = Necessary Consumption (wage goods for proletariat reproduction)
    IIb = Luxury Consumption (surplus value sink, bourgeois consumption)
    III = Social Reproduction (produces labor power itself)

Example:
    >>> from babylon.domain.economics.department_mapper import DepartmentMapper, Department
    >>> mapper = DepartmentMapper.from_yaml("naics_to_dept.yaml")
    >>> allocation = mapper.get_allocation("336111")  # Automobile Mfg
    >>> allocation.allocate(1_000_000)  # $1M in wages
    {Department.I: 0.0, Department.IIa: 650000.0, Department.IIb: 350000.0, Department.III: 0.0}

See Also:
    :mod:`babylon.domain.economics.tensor`: ValueTensor4x3 output format.
    :mod:`babylon.domain.economics.hydrator`: Uses mapper for transformation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping


class Department(Enum):
    """Marxian reproduction schema departments.

    The four departments represent the destination of economic output:

    - I: Means of Production (capital goods consumed by other industries)
    - IIa: Necessary Consumption (wage goods for working class reproduction)
    - IIb: Luxury Consumption (surplus value sink, bourgeois consumption)
    - III: Social Reproduction (produces labor power: care, education, health)
    """

    I = "dept_I"  # noqa: E741 - Roman numeral naming is intentional for Marxian theory
    IIa = "dept_IIa"  # Necessary Consumption
    IIb = "dept_IIb"  # Luxury Consumption
    III = "dept_III"  # Social Reproduction

    def __str__(self) -> str:
        """Return department name without 'dept_' prefix."""
        return self.name


@dataclass(frozen=True)
class DepartmentAllocation:
    """Allocation of a value across departments.

    Weights sum to 1.0 (within tolerance of 0.001).

    Args:
        dept_I: Weight for Means of Production.
        dept_IIa: Weight for Necessary Consumption.
        dept_IIb: Weight for Luxury Consumption.
        dept_III: Weight for Social Reproduction.

    Example:
        >>> alloc = DepartmentAllocation(dept_I=0.3, dept_IIa=0.4, dept_IIb=0.2, dept_III=0.1)
        >>> alloc.allocate(1_000_000)
        {Department.I: 300000.0, Department.IIa: 400000.0, ...}
    """

    dept_I: float = 0.0
    dept_IIa: float = 0.0
    dept_IIb: float = 0.0
    dept_III: float = 0.0

    def __post_init__(self) -> None:
        """Validate weights sum to 1.0."""
        total = self.dept_I + self.dept_IIa + self.dept_IIb + self.dept_III
        if abs(total - 1.0) > 0.001:
            msg = (
                f"Department weights must sum to 1.0, got {total}: "
                f"I={self.dept_I}, IIa={self.dept_IIa}, "
                f"IIb={self.dept_IIb}, III={self.dept_III}"
            )
            raise ValueError(msg)

    def allocate(self, value: float) -> dict[Department, float]:
        """Distribute a value across departments according to weights.

        Args:
            value: The value to distribute (e.g., total wages, employment).

        Returns:
            Dictionary mapping Department to allocated value.
        """
        return {
            Department.I: value * self.dept_I,
            Department.IIa: value * self.dept_IIa,
            Department.IIb: value * self.dept_IIb,
            Department.III: value * self.dept_III,
        }

    def to_dict(self) -> dict[str, float]:
        """Return weights as a dictionary."""
        return {
            "dept_I": self.dept_I,
            "dept_IIa": self.dept_IIa,
            "dept_IIb": self.dept_IIb,
            "dept_III": self.dept_III,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, float]) -> DepartmentAllocation:
        """Create from a dictionary of weights.

        Missing departments default to 0.0.

        Args:
            d: Dictionary with dept_* keys and float weights.

        Returns:
            DepartmentAllocation with specified weights.
        """
        return cls(
            dept_I=d.get("dept_I", 0.0),
            dept_IIa=d.get("dept_IIa", 0.0),
            dept_IIb=d.get("dept_IIb", 0.0),
            dept_III=d.get("dept_III", 0.0),
        )


@dataclass(frozen=True)
class DefaultRatios:
    """Default c/v and s/v ratios for a department.

    Used when BEA industry-specific data is unavailable.

    Args:
        cv_ratio: Organic composition of capital (c/v).
        sv_ratio: Rate of surplus value (s/v).
    """

    cv_ratio: float
    sv_ratio: float


class DepartmentMapper:
    """Maps NAICS codes to Marxian Departments with split coefficients.

    Lookup proceeds from most specific (6-digit) to least specific (2-digit).
    Dual-use sectors are allocated across departments using split coefficients.

    Args:
        defaults: 2-digit sector code -> allocation mapping.
        overrides: 3-6 digit NAICS code -> allocation mapping.
        excluded: Set of excluded NAICS codes (outside M-C-M' circuit).
        default_ratios: Per-department default c/v and s/v ratios.
        sector_ratios: 2-digit sector code -> DefaultRatios mapping.

    Example:
        >>> mapper = DepartmentMapper.from_yaml("naics_to_dept.yaml")
        >>> allocation = mapper.get_allocation("336111")  # Automobile Mfg
        >>> allocation.allocate(1_000_000)  # $1M in wages
        {Department.I: 0.0, Department.IIa: 900000.0, ...}
    """

    def __init__(
        self,
        defaults: dict[str, DepartmentAllocation],
        overrides: dict[str, DepartmentAllocation],
        excluded: set[str],
        default_ratios: dict[Department, DefaultRatios] | None = None,
        sector_ratios: dict[str, DefaultRatios] | None = None,
    ) -> None:
        """Initialize the mapper.

        Args:
            defaults: 2-digit sector code -> allocation mapping.
            overrides: 3-6 digit NAICS code -> allocation mapping.
            excluded: Set of excluded NAICS codes (outside M-C-M' circuit).
            default_ratios: Per-department default c/v and s/v ratios.
            sector_ratios: 2-digit sector code -> c/v and s/v ratios.
        """
        self._defaults = defaults
        self._overrides = overrides
        self._excluded = excluded
        self._default_ratios = default_ratios or {}
        self._sector_ratios = sector_ratios or {}

    @classmethod
    def from_yaml(cls, path: str | Path) -> DepartmentMapper:  # pragma: no mutate — file I/O
        """Load mapping configuration from YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Configured DepartmentMapper instance.
        """
        path = Path(path)  # pragma: no mutate
        with path.open() as f:  # pragma: no mutate
            config = yaml.safe_load(f)  # pragma: no mutate

        defaults: dict[str, DepartmentAllocation] = {}  # pragma: no mutate
        for code, weights in config.get("defaults", {}).items():  # pragma: no mutate
            defaults[str(code)] = DepartmentAllocation.from_dict(weights)  # pragma: no mutate

        overrides: dict[str, DepartmentAllocation] = {}  # pragma: no mutate
        for code, weights in config.get("overrides", {}).items():  # pragma: no mutate
            overrides[str(code)] = DepartmentAllocation.from_dict(weights)  # pragma: no mutate

        excluded: set[str] = set()  # pragma: no mutate
        for code in config.get("excluded", []):  # pragma: no mutate
            excluded.add(str(code))  # pragma: no mutate

        # Parse default_ratios
        default_ratios: dict[Department, DefaultRatios] = {}  # pragma: no mutate
        ratios_config = config.get("default_ratios", {})  # pragma: no mutate
        dept_map = {  # pragma: no mutate
            "dept_I": Department.I,  # pragma: no mutate
            "dept_IIa": Department.IIa,  # pragma: no mutate
            "dept_IIb": Department.IIb,  # pragma: no mutate
            "dept_III": Department.III,  # pragma: no mutate
        }  # pragma: no mutate
        for dept_key, ratios in ratios_config.items():  # pragma: no mutate
            dept = dept_map.get(dept_key)  # pragma: no mutate
            if dept is not None:  # pragma: no mutate
                default_ratios[dept] = DefaultRatios(  # pragma: no mutate
                    cv_ratio=ratios.get("cv_ratio", 1.0),  # pragma: no mutate
                    sv_ratio=ratios.get("sv_ratio", 1.0),  # pragma: no mutate
                )  # pragma: no mutate

        # Parse sector_ratios (BEA-derived sector-level ratios)
        sector_ratios: dict[str, DefaultRatios] = {}  # pragma: no mutate
        sector_config = config.get("sector_ratios", {})  # pragma: no mutate
        for sector_code, ratios in sector_config.items():  # pragma: no mutate
            sector_ratios[str(sector_code)] = DefaultRatios(  # pragma: no mutate
                cv_ratio=ratios.get("cv_ratio", 1.0),  # pragma: no mutate
                sv_ratio=ratios.get("sv_ratio", 1.0),  # pragma: no mutate
            )  # pragma: no mutate

        return cls(  # pragma: no mutate
            defaults=defaults,  # pragma: no mutate
            overrides=overrides,  # pragma: no mutate
            excluded=excluded,  # pragma: no mutate
            default_ratios=default_ratios,  # pragma: no mutate
            sector_ratios=sector_ratios,  # pragma: no mutate
        )  # pragma: no mutate

    def is_excluded(self, naics_code: str) -> bool:
        """Check if a NAICS code is excluded from mapping.

        Args:
            naics_code: NAICS code to check.

        Returns:
            True if excluded (e.g., government sector).
        """
        code = str(naics_code).strip()
        # Check exact match and 2-digit prefix
        return code in self._excluded or code[:2] in self._excluded

    def get_allocation(self, naics_code: str) -> DepartmentAllocation | None:
        """Get department allocation for a NAICS code.

        Lookup proceeds from most specific to least specific:
        6-digit -> 5-digit -> 4-digit -> 3-digit -> 2-digit

        Args:
            naics_code: NAICS code (2-6 digits).

        Returns:
            DepartmentAllocation or None if excluded/unknown.
        """
        code = str(naics_code).strip()

        if self.is_excluded(code):
            return None

        # Try most specific to least specific
        for length in (6, 5, 4, 3, 2):
            prefix = code[:length] if len(code) >= length else code
            if prefix in self._overrides:
                return self._overrides[prefix]

        # Fall back to 2-digit default
        sector = code[:2] if len(code) >= 2 else code
        return self._defaults.get(sector)

    def get_default_cv_ratio(self, dept: Department) -> float:
        """Get default c/v ratio for a department.

        Args:
            dept: Department enum value.

        Returns:
            Organic composition of capital (c/v) ratio.
        """
        ratios = self._default_ratios.get(dept)
        if ratios is None:
            return 1.0  # Default to 1.0 if not configured
        return ratios.cv_ratio

    def get_default_sv_ratio(self, dept: Department) -> float:
        """Get default s/v ratio for a department.

        Args:
            dept: Department enum value.

        Returns:
            Rate of surplus value (s/v) ratio.
        """
        ratios = self._default_ratios.get(dept)
        if ratios is None:
            return 1.0  # Default to 1.0 if not configured
        return ratios.sv_ratio

    def get_sector_sv_ratio(self, sector_code: str) -> float | None:
        """Get s/v ratio for a NAICS sector from sector_ratios config.

        Args:
            sector_code: 2-digit NAICS sector code.

        Returns:
            Rate of surplus value (s/v) ratio, or None if not configured.
        """
        ratios = self._sector_ratios.get(str(sector_code)[:2])
        if ratios is None:
            return None
        return ratios.sv_ratio

    def get_sector_cv_ratio(self, sector_code: str) -> float | None:
        """Get c/v ratio for a NAICS sector from sector_ratios config.

        Args:
            sector_code: 2-digit NAICS sector code.

        Returns:
            Organic composition of capital (c/v) ratio, or None if not configured.
        """
        ratios = self._sector_ratios.get(str(sector_code)[:2])
        if ratios is None:
            return None
        return ratios.cv_ratio

    def allocate_value(
        self,
        naics_code: str,
        value: float,
    ) -> dict[Department, float] | None:
        """Distribute a value across departments for a NAICS code.

        Convenience method combining get_allocation and allocate.

        Args:
            naics_code: NAICS code.
            value: Value to distribute (e.g., wages, employment).

        Returns:
            Dictionary mapping Department to allocated value, or None if excluded.
        """
        allocation = self.get_allocation(naics_code)
        if allocation is None:
            return None
        return allocation.allocate(value)

    def allocate_batch(
        self,
        records: list[tuple[str, float]],
    ) -> dict[Department, float]:
        """Allocate values for multiple NAICS codes, summing results.

        Args:
            records: List of (naics_code, value) tuples.

        Returns:
            Dictionary mapping Department to total allocated value.
        """
        totals: dict[Department, float] = dict.fromkeys(Department, 0.0)

        for naics_code, value in records:
            allocated = self.allocate_value(naics_code, value)
            if allocated is not None:
                for dept, amt in allocated.items():
                    totals[dept] += amt

        return totals


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_mapper: DepartmentMapper | None = None


def get_default_mapper(
    config_path: str | Path | None = None,
) -> DepartmentMapper:  # pragma: no mutate — singleton I/O
    """Get or create the default DepartmentMapper.

    Args:
        config_path: Optional path to YAML config. If not provided,
                     looks for naics_to_dept.yaml in standard locations.

    Returns:
        Singleton DepartmentMapper instance.
    """
    global _default_mapper  # pragma: no mutate

    if _default_mapper is None:  # pragma: no mutate
        if config_path is None:  # pragma: no mutate
            # Look in standard locations
            candidates = [  # pragma: no mutate
                Path("naics_to_dept.yaml"),  # pragma: no mutate
                Path("data/mappings/naics_to_dept.yaml"),  # pragma: no mutate
                Path(__file__).parent / "data" / "naics_to_dept.yaml",  # pragma: no mutate
                # one extra .parent: economics moved under domain/ (P14 3d)
                Path(__file__).parent.parent.parent
                / "data"
                / "mappings"
                / "naics_to_dept.yaml",  # pragma: no mutate
            ]  # pragma: no mutate
            for candidate in candidates:  # pragma: no mutate
                if candidate.exists():  # pragma: no mutate
                    config_path = candidate  # pragma: no mutate
                    break  # pragma: no mutate
            else:  # pragma: no mutate
                msg = f"Could not find naics_to_dept.yaml in: {candidates}"  # pragma: no mutate
                raise FileNotFoundError(msg)  # pragma: no mutate

        _default_mapper = DepartmentMapper.from_yaml(config_path)  # pragma: no mutate

    return _default_mapper  # pragma: no mutate


def map_sector_value(  # pragma: no mutate — convenience wrapper with I/O
    naics_code: str,
    value: float,
    config_path: str | Path | None = None,  # pragma: no mutate
) -> dict[Department, float] | None:
    """Map a single sector's value to departments.

    Convenience wrapper around DepartmentMapper.allocate_value.

    Args:
        naics_code: NAICS code.
        value: Value to distribute.
        config_path: Optional path to config file.

    Returns:
        Department allocations or None if excluded.
    """
    mapper = get_default_mapper(config_path)  # pragma: no mutate
    return mapper.allocate_value(naics_code, value)  # pragma: no mutate


__all__ = [
    "DefaultRatios",
    "Department",
    "DepartmentAllocation",
    "DepartmentMapper",
    "get_default_mapper",
    "map_sector_value",
]
