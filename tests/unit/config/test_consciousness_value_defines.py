"""Tests for ConsciousnessDefines expansion (Spec 043, Phase 1).

TDD Red Phase: These tests verify the new consciousness value integration
defines fields exist on ConsciousnessDefines with correct defaults,
bounds, and provenance documentation.

Key fields:
    exploitation_sensitivity: Δ(s/v) → agitation conversion
    rent_decline_sensitivity: Δ(Φ) decline → agitation conversion
    reproduction_visibility_coefficient: Δ(g₃₃) → agitation
    repression_backfire: Agitation from state REPRESS events
    rent_opacity_factor: How much Φ dampens exploitation visibility
    agitation_consumption_rate: Fraction consumed per tick by routing
    liberal_drift_rate: Per-tick drift toward `l` under stability
    educate_base_effect: Base education_pressure per EDUCATE
    agitation_education_threshold: Agitation for full EDUCATE effectiveness
    education_pressure_decay: Per-tick decay of education_pressure
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import ConsciousnessDefines, GameDefines


@pytest.mark.unit
class TestConsciousnessValueDefinesFields:
    """Verify new fields exist with correct defaults."""

    def test_exploitation_sensitivity_default(self) -> None:
        """Exploitation sensitivity converts Δ(s/v) to agitation."""
        defines = ConsciousnessDefines()
        assert defines.exploitation_sensitivity == pytest.approx(0.15)

    def test_rent_decline_sensitivity_default(self) -> None:
        """Rent decline sensitivity converts Δ(Φ) to agitation."""
        defines = ConsciousnessDefines()
        assert defines.rent_decline_sensitivity == pytest.approx(0.2)

    def test_reproduction_visibility_coefficient_default(self) -> None:
        """Reproduction visibility converts Δ(g₃₃) to agitation."""
        defines = ConsciousnessDefines()
        assert defines.reproduction_visibility_coefficient == pytest.approx(0.1)

    def test_repression_backfire_default(self) -> None:
        """Repression backfire generates agitation from state violence."""
        defines = ConsciousnessDefines()
        assert defines.repression_backfire == pytest.approx(0.3)

    def test_rent_opacity_factor_default(self) -> None:
        """Rent opacity dampens exploitation visibility via imperial rent."""
        defines = ConsciousnessDefines()
        assert defines.rent_opacity_factor == pytest.approx(1.0)

    def test_agitation_consumption_rate_default(self) -> None:
        """Agitation consumption rate — fraction consumed by routing."""
        defines = ConsciousnessDefines()
        assert defines.agitation_consumption_rate == pytest.approx(0.6)

    def test_liberal_drift_rate_default(self) -> None:
        """Liberal drift rate — per-tick drift toward hegemony."""
        defines = ConsciousnessDefines()
        assert defines.liberal_drift_rate == pytest.approx(0.02)

    def test_educate_base_effect_default(self) -> None:
        """EDUCATE base effect — education pressure per verb."""
        defines = ConsciousnessDefines()
        assert defines.educate_base_effect == pytest.approx(0.05)

    def test_agitation_education_threshold_default(self) -> None:
        """Agitation level for EDUCATE to reach full effectiveness."""
        defines = ConsciousnessDefines()
        assert defines.agitation_education_threshold == pytest.approx(0.3)

    def test_education_pressure_decay_default(self) -> None:
        """Education pressure decays per tick."""
        defines = ConsciousnessDefines()
        assert defines.education_pressure_decay == pytest.approx(0.1)


@pytest.mark.unit
class TestConsciousnessValueDefinesBounds:
    """Verify field validation constraints."""

    def test_exploitation_sensitivity_must_be_nonnegative(self) -> None:
        """exploitation_sensitivity >= 0.0."""
        with pytest.raises(ValidationError):
            ConsciousnessDefines(exploitation_sensitivity=-0.1)

    def test_rent_decline_sensitivity_must_be_nonnegative(self) -> None:
        """rent_decline_sensitivity >= 0.0."""
        with pytest.raises(ValidationError):
            ConsciousnessDefines(rent_decline_sensitivity=-0.1)

    def test_rent_opacity_factor_must_be_nonnegative(self) -> None:
        """rent_opacity_factor >= 0.0."""
        with pytest.raises(ValidationError):
            ConsciousnessDefines(rent_opacity_factor=-0.5)

    def test_agitation_consumption_rate_bounded(self) -> None:
        """agitation_consumption_rate in [0, 1]."""
        with pytest.raises(ValidationError):
            ConsciousnessDefines(agitation_consumption_rate=1.5)
        with pytest.raises(ValidationError):
            ConsciousnessDefines(agitation_consumption_rate=-0.1)

    def test_liberal_drift_rate_bounded(self) -> None:
        """liberal_drift_rate in [0, 1]."""
        with pytest.raises(ValidationError):
            ConsciousnessDefines(liberal_drift_rate=-0.01)

    def test_education_pressure_decay_bounded(self) -> None:
        """education_pressure_decay in [0, 1]."""
        with pytest.raises(ValidationError):
            ConsciousnessDefines(education_pressure_decay=2.0)


@pytest.mark.unit
class TestConsciousnessValueDefinesIntegration:
    """Verify new fields integrate with GameDefines."""

    def test_new_fields_accessible_from_gamedefines(self) -> None:
        """GameDefines.consciousness exposes all new fields."""
        defines = GameDefines()
        c = defines.consciousness
        # All new fields should be accessible
        assert hasattr(c, "exploitation_sensitivity")
        assert hasattr(c, "rent_decline_sensitivity")
        assert hasattr(c, "reproduction_visibility_coefficient")
        assert hasattr(c, "repression_backfire")
        assert hasattr(c, "rent_opacity_factor")
        assert hasattr(c, "agitation_consumption_rate")
        assert hasattr(c, "liberal_drift_rate")
        assert hasattr(c, "educate_base_effect")
        assert hasattr(c, "agitation_education_threshold")
        assert hasattr(c, "education_pressure_decay")

    def test_existing_fields_preserved(self) -> None:
        """Existing ConsciousnessDefines fields unchanged."""
        defines = ConsciousnessDefines()
        assert defines.sensitivity == pytest.approx(0.5)
        assert defines.decay_lambda == pytest.approx(0.1)
        assert defines.routing_scale == pytest.approx(0.1)
        assert defines.agitation_decay_rate == pytest.approx(0.1)
