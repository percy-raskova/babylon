"""Tests for metabolic aggregate derivations.

Spec 040 Discipline 2: Verifies the extracted @derived functions
produce the same results as the legacy @computed_field properties.
"""

from __future__ import annotations

from babylon.derivations.metabolic import (
    compute_overshoot_ratio,
    compute_total_biocapacity,
    compute_total_consumption,
    metabolic_registry,
)
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import SectorType, SocialRole
from babylon.models.world_state import WorldState


class TestMetabolicDerivations:
    """Verify metabolic derivations match WorldState computed fields."""

    def test_total_biocapacity_empty(self) -> None:
        """Zero territories -> zero biocapacity."""
        state = WorldState(tick=0)
        assert compute_total_biocapacity(state) == 0.0

    def test_total_biocapacity_sum(self) -> None:
        """Sums biocapacity across territories."""
        t1 = Territory(id="T001", name="A", sector_type=SectorType.INDUSTRIAL, biocapacity=50.0)
        t2 = Territory(id="T002", name="B", sector_type=SectorType.RESIDENTIAL, biocapacity=30.0)
        state = WorldState(tick=0, territories={"T001": t1, "T002": t2})
        assert compute_total_biocapacity(state) == 80.0

    def test_total_consumption_empty(self) -> None:
        """Zero entities -> zero consumption."""
        state = WorldState(tick=0)
        assert compute_total_consumption(state) == 0.0

    def test_total_consumption_sum(self) -> None:
        """Sums consumption_needs across entities."""
        e1 = SocialClass(
            id="C001", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT, s_bio=0.5, s_class=0.3
        )
        e2 = SocialClass(
            id="C002", name="Bosses", role=SocialRole.CORE_BOURGEOISIE, s_bio=0.2, s_class=0.1
        )
        state = WorldState(tick=0, entities={"C001": e1, "C002": e2})
        # s_bio + s_class for each
        expected = (0.5 + 0.3) + (0.2 + 0.1)
        assert abs(compute_total_consumption(state) - expected) < 1e-10

    def test_overshoot_ratio_zero_biocapacity(self) -> None:
        """Zero biocapacity -> 999.0 sentinel."""
        state = WorldState(tick=0)
        assert compute_overshoot_ratio(state) == 999.0

    def test_overshoot_ratio_with_data(self) -> None:
        """Correct ratio with non-zero data."""
        t = Territory(id="T001", name="Land", sector_type=SectorType.INDUSTRIAL, biocapacity=100.0)
        e = SocialClass(
            id="C001", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT, s_bio=0.4, s_class=0.1
        )
        state = WorldState(tick=0, entities={"C001": e}, territories={"T001": t})
        expected = (0.4 + 0.1) / 100.0
        assert abs(compute_overshoot_ratio(state) - expected) < 1e-10

    def test_derivations_match_computed_fields(self) -> None:
        """@derived functions produce same output as WorldState @computed_field."""
        t = Territory(id="T001", name="Zone", sector_type=SectorType.RESIDENTIAL, biocapacity=200.0)
        e = SocialClass(
            id="C001", name="People", role=SocialRole.LABOR_ARISTOCRACY, s_bio=1.0, s_class=2.0
        )
        state = WorldState(tick=5, entities={"C001": e}, territories={"T001": t})

        assert compute_total_biocapacity(state) == state.total_biocapacity
        assert compute_total_consumption(state) == state.total_consumption
        assert abs(compute_overshoot_ratio(state) - state.overshoot_ratio) < 1e-10


class TestMetabolicRegistry:
    """Verify metabolic derivations are registered."""

    def test_registry_has_three_entries(self) -> None:
        """All three metabolic derivations are registered."""
        assert len(metabolic_registry) == 3
        assert "total_biocapacity" in metabolic_registry
        assert "total_consumption" in metabolic_registry
        assert "overshoot_ratio" in metabolic_registry
