"""ConsistencyReport dataclasses — spec 060 US2 / FR-003.

Carries the diagnostics surfaced by the per-entity MELT consistency
check: which entities were checked, which were skipped (no data /
degenerate), and the worst violation observed.

Per FR-010, the violation record includes both the absolute and
relative error so the failure diagnostic names the magnitude.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntityViolation:
    """One entity that fails the ``money_X ≈ labor_time_X × τ`` check."""

    entity_id: str
    field_name: str  # e.g., "c", "v", "s", "total_value"
    labor_hours: float
    money_currency: float
    expected_money: float  # labor_hours × τ
    relative_error: float
    absolute_error_currency: float


@dataclass(frozen=True)
class ConsistencyReport:
    """Summary of one tick's per-entity MELT consistency audit."""

    n_entities_checked: int
    n_skipped_no_data: int
    n_skipped_degenerate: int
    max_relative_error: float
    worst_entity: EntityViolation | None
    violations: list[EntityViolation] = field(default_factory=list)

    def passed(self, tolerance: float = 1e-9) -> bool:
        return self.max_relative_error <= tolerance

    def diagnostic_message(self, tolerance: float, spec_ref: str = "spec-060 FR-003") -> str:
        if self.worst_entity is None:
            return f"ConsistencyReport: 0 violations (max_relative_error={self.max_relative_error:.2e})"
        w = self.worst_entity
        return (
            f"{spec_ref}: per-entity MELT consistency violated. "
            f"Tolerance {tolerance:.2e}, observed worst {self.max_relative_error:.2e} "
            f"at entity_id={w.entity_id!r} field={w.field_name!r}. "
            f"labor_hours={w.labor_hours:.6g} money={w.money_currency:.6g} "
            f"expected_money={w.expected_money:.6g} delta={w.absolute_error_currency:.6g}. "
            f"{len(self.violations)} entity(ies) exceeded tolerance; "
            f"{self.n_skipped_no_data} skipped (NoDataSentinel), "
            f"{self.n_skipped_degenerate} skipped (degenerate)."
        )


__all__ = ["EntityViolation", "ConsistencyReport"]
