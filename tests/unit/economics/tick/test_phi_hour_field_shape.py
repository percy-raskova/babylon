"""T058b — Spec 057 / FR-011 phi_hour field-shape regression.

Asserts that the public field ``CountyEconomicState.phi_hour`` keeps its
``float`` annotation + ``Field(..., ge=0)`` constraint after the Spec 057
Leontief pipeline lands. Per FR-011: "preserve the existing public field
``CountyEconomicState.phi_hour`` and the existing reads of that field in
``accumulation.py``, ``savings_schedule.py``, and the graph bridge in
``simulation.py``."

This is the third defense layer of the three-layer axiom enforcement
(research.md §R5):
  1. Source layer — DefaultPeripheryLaborCoefficientsSource warns
  2. Calculator layer — ProductionChainRentCalculator clamps at line 181
  3. Data-model layer — THIS field constraint
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.dynamics.types import ClassDistribution
from babylon.economics.tick.types import CountyEconomicState


def _county(phi_hour: float) -> CountyEconomicState:
    return CountyEconomicState(
        fips="26163",
        year=2015,
        capital_stock=1e9,
        throughput_position=0.9,
        supply_chain_depth=2.1,
        unemployment_rate=0.05,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.04,
            labor_aristocracy_share=0.10,
            proletariat_share=0.80,
            lumpenproletariat_share=0.05,
        ),
        phi_hour=phi_hour,
    )


@pytest.mark.unit
class TestPhiHourFieldShape:
    """Spec 057 / FR-011 — field-shape preservation regression."""

    def test_phi_hour_annotation_is_float(self) -> None:
        field = CountyEconomicState.model_fields["phi_hour"]
        assert field.annotation is float, (
            f"phi_hour field annotation drifted from float to {field.annotation}. "
            f"Spec 057 / FR-011 requires preserving the field shape."
        )

    def test_phi_hour_has_ge_zero_constraint(self) -> None:
        """The Field(..., ge=0) constraint is the third defense layer of
        the axiom enforcement chain (research.md §R5)."""
        # Construct a county with phi_hour=0 (lower bound) — must succeed
        county_zero = _county(phi_hour=0.0)
        assert county_zero.phi_hour == 0.0
        # Construct a county with phi_hour=-0.001 — must fail
        with pytest.raises(ValidationError):
            _county(phi_hour=-0.001)

    def test_phi_hour_accepts_positive_floats(self) -> None:
        for value in (0.5, 1.0, 100.0, 9999.99):
            county = _county(phi_hour=value)
            assert county.phi_hour == value

    def test_phi_hour_required(self) -> None:
        """phi_hour is a required field (no default), per FR-011."""
        field = CountyEconomicState.model_fields["phi_hour"]
        assert field.is_required(), "phi_hour must remain a required field"
