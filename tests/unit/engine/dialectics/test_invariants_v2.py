"""TDD RED phase: Tests for the v2 invariant checker.

Validates:
- check_universal_invariants covers weight bounds and type stability
- check_all_invariants aggregates universal + per-type checks
- Violations are reported as descriptive strings
"""

from __future__ import annotations

from babylon.engine.dialectics.invariants_v2 import (
    check_all_invariants,
    check_universal_invariants,
)
from babylon.engine.dialectics.volume_1 import (
    CommodityDialectic,
    ExchangeValue,
    UseValue,
)
from babylon.engine.dialectics.world import World


def _make_commodity(weight: float = 0.5) -> CommodityDialectic:
    return CommodityDialectic(
        pole_a=UseValue(),
        pole_b=ExchangeValue(),
        weight=weight,
        tick_created=0,
        tick_updated=0,
    )


class TestCheckUniversalInvariants:
    """Universal invariants applied to every dialectic."""

    def test_valid_dialectic_no_violations(self) -> None:
        d = _make_commodity(weight=0.5)
        violations = check_universal_invariants(d)
        assert violations == []

    def test_weight_at_boundary_valid(self) -> None:
        d0 = _make_commodity(weight=0.0)
        d1 = _make_commodity(weight=1.0)
        assert check_universal_invariants(d0) == []
        assert check_universal_invariants(d1) == []


class TestCheckAllInvariants:
    """Aggregate invariant check across all dialectics in a World."""

    def test_valid_world_no_violations(self) -> None:
        d = _make_commodity()
        w = World(tick=0, dialectics={d.id: d})
        violations = check_all_invariants(w)
        assert violations == []

    def test_empty_world_no_violations(self) -> None:
        w = World(tick=0)
        violations = check_all_invariants(w)
        assert violations == []
