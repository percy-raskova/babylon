"""Frozen Pydantic model for the BEA-to-Department mapping table.

Spec 058 / FR-009 — see ``contracts/bea_mappings.md`` (with the 2026-05-08
commit-7 reformulation note for the actual TOML schema).
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = ["BEAMappings", "VALID_DEPARTMENTS"]


VALID_DEPARTMENTS: frozenset[str] = frozenset({"I", "IIA", "IIB", "III"})
"""Canonical Marxian Department keys per :file:`bea_to_department.toml`.

  - ``I``   — Means of Production (capital goods, producer services, infrastructure)
  - ``IIA`` — Necessary Consumption (wage goods: food, housing, basic services)
  - ``IIB`` — Luxury Consumption (bourgeois consumption, discretionary)
  - ``III`` — Social Reproduction (care, education, health, household services)
"""


class BEAMappings(BaseModel):
    """Frozen, validated container for the BEA-to-Department mapping table.

    Loaded once at import time from ``bea_to_department.toml`` per
    Spec 058 / FR-009 — replaces the per-call TOML reparse pattern in
    :class:`babylon.economics.tensor_hierarchy.inter_industry.DefaultDepartmentAggregator`.

    Schema mirrors the actual TOML on disk: ``{departments: {dept: [bea_codes]}}``
    where each BEA code maps to exactly one department (no fractional weights).

    Validation invariants enforced at construction:
      - All keys in ``departments`` must be in :data:`VALID_DEPARTMENTS`.
      - No BEA code may appear in more than one department (1:1 industry→department).
      - At least one department key must be present.
    """

    model_config = ConfigDict(frozen=True)

    departments: dict[str, list[str]]

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        if not self.departments:
            raise ValueError("BEAMappings.departments must contain at least one department")

        unknown = set(self.departments) - VALID_DEPARTMENTS
        if unknown:
            raise ValueError(
                f"Unknown department keys: {sorted(unknown)}. "
                f"Expected subset of {sorted(VALID_DEPARTMENTS)}."
            )

        seen: dict[str, str] = {}
        for dept, codes in self.departments.items():
            for code in codes:
                if code in seen:
                    raise ValueError(
                        f"BEA code {code!r} appears in both {seen[code]!r} and {dept!r} — "
                        "each industry must map to exactly one department"
                    )
                seen[code] = dept
        return self

    def get_department(self, bea_code: str) -> str:
        """Return the department string (``I``/``IIA``/``IIB``/``III``) for a BEA code.

        Raises:
            KeyError: if ``bea_code`` is not present in any department list.
        """
        for dept, codes in self.departments.items():
            if bea_code in codes:
                return dept
        raise KeyError(f"No department mapping for BEA code {bea_code!r}")

    def as_flat_dict(self) -> dict[str, str]:
        """Return ``{bea_code: department_str}`` flat mapping.

        Matches the legacy
        :meth:`babylon.economics.tensor_hierarchy.inter_industry.DefaultDepartmentAggregator.get_default_mapping`
        output shape, enabling drop-in replacement.
        """
        return {code: dept for dept, codes in self.departments.items() for code in codes}
