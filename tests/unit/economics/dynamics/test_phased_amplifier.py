"""Tests for PhasedCrisisAmplifier.

Feature: 018-crisis-devaluation-mechanics
Tasks: T034-T039, T075

Tests phase-dependent amplification of class transition rates:
- US2 acceptance scenarios (early/deep/recovery amplification)
- Confinement to dynamic classes
- Rate clamping to [0, 1]
- Backward compatibility with CrisisAmplifier protocol
"""

from __future__ import annotations

import pytest

from babylon.economics.dynamics.crisis import PhasedCrisisAmplifier
from babylon.economics.dynamics.types import TransitionRates
from babylon.economics.tick.types import CrisisPhase


def _make_rates(
    dispossession: float = 0.02,
    accumulation: float = 0.01,
    precaritization: float = 0.03,
    stabilization: float = 0.05,
) -> TransitionRates:
    """Build test transition rates."""
    return TransitionRates(
        fips="26163",
        year=2015,
        dispossession=dispossession,
        accumulation=accumulation,
        precaritization=precaritization,
        stabilization=stabilization,
    )


# =============================================================================
# T034: US2 AS1 - Early crisis amplification
# =============================================================================


@pytest.mark.unit
class TestEarlyCrisisAmplification:
    """US2 AS1: Onset/Early crisis amplifies rates per FR-006 table."""

    def test_onset_applies_onset_multipliers(self) -> None:
        """ONSET: dispossession 1.2x, precaritization 1.5x, accum 0.8x, stab 0.7x."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        result = amp.amplify_phased(rates, CrisisPhase.ONSET)

        assert result.dispossession == pytest.approx(0.02 * 1.2)
        assert result.precaritization == pytest.approx(0.03 * 1.5)
        assert result.accumulation == pytest.approx(0.01 * 0.8)
        assert result.stabilization == pytest.approx(0.05 * 0.7)

    def test_early_applies_early_multipliers(self) -> None:
        """EARLY: dispossession 1.8x, precaritization 2.5x, accum 0.4x, stab 0.4x."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        result = amp.amplify_phased(rates, CrisisPhase.EARLY)

        assert result.dispossession == pytest.approx(0.02 * 1.8)
        assert result.precaritization == pytest.approx(0.03 * 2.5)
        assert result.accumulation == pytest.approx(0.01 * 0.4)
        assert result.stabilization == pytest.approx(0.05 * 0.4)

    def test_onset_precaritization_greater_than_dispossession(self) -> None:
        """In ONSET, precaritization amplification > dispossession amplification."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates(dispossession=0.01, precaritization=0.01)

        result = amp.amplify_phased(rates, CrisisPhase.ONSET)

        # precaritization 1.5x > dispossession 1.2x (for equal base rates)
        assert result.precaritization > result.dispossession


# =============================================================================
# T035: US2 AS2 - Deep crisis amplification
# =============================================================================


@pytest.mark.unit
class TestDeepCrisisAmplification:
    """US2 AS2: Deep crisis applies maximum amplification per FR-006."""

    def test_deep_applies_deep_multipliers(self) -> None:
        """DEEP: dispossession 3.0x, precaritization 3.5x, accum 0.1x, stab 0.2x."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        result = amp.amplify_phased(rates, CrisisPhase.DEEP)

        assert result.dispossession == pytest.approx(0.02 * 3.0)
        assert result.precaritization == pytest.approx(0.03 * 3.5)
        assert result.accumulation == pytest.approx(0.01 * 0.1)
        assert result.stabilization == pytest.approx(0.05 * 0.2)

    def test_deep_nearly_halts_upward_mobility(self) -> None:
        """DEEP crisis nearly eliminates upward transitions."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates(accumulation=0.05, stabilization=0.05)

        result = amp.amplify_phased(rates, CrisisPhase.DEEP)

        assert result.accumulation < 0.01  # 0.05 * 0.1 = 0.005
        assert result.stabilization < 0.02  # 0.05 * 0.2 = 0.01


# =============================================================================
# T036: US2 AS3 - Recovery with hysteresis
# =============================================================================


@pytest.mark.unit
class TestRecoveryAmplification:
    """US2 AS3: Recovery applies recovery multipliers per FR-006."""

    def test_recovery_applies_recovery_multipliers(self) -> None:
        """RECOVERY: dispossession 1.3x, precaritization 1.2x, accum 0.6x, stab 0.5x."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        result = amp.amplify_phased(rates, CrisisPhase.RECOVERY)

        assert result.dispossession == pytest.approx(0.02 * 1.3)
        assert result.precaritization == pytest.approx(0.03 * 1.2)
        assert result.accumulation == pytest.approx(0.01 * 0.6)
        assert result.stabilization == pytest.approx(0.05 * 0.5)

    def test_recovery_less_severe_than_deep(self) -> None:
        """RECOVERY amplification is less severe than DEEP."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        deep = amp.amplify_phased(rates, CrisisPhase.DEEP)
        recovery = amp.amplify_phased(rates, CrisisPhase.RECOVERY)

        assert recovery.dispossession < deep.dispossession
        assert recovery.precaritization < deep.precaritization
        assert recovery.accumulation > deep.accumulation
        assert recovery.stabilization > deep.stabilization


# =============================================================================
# T037: FR-010 - Confinement to dynamic classes
# =============================================================================


@pytest.mark.unit
class TestConfinementToDynamicClasses:
    """FR-010: Crisis amplification only affects the 3 dynamic classes.

    TransitionRates only contains the 4 pathways between the 3 dynamic
    classes, so confinement is structural. This test verifies that
    the amplifier preserves FIPS/year metadata and operates only on rates.
    """

    def test_preserves_fips_and_year(self) -> None:
        """Amplification preserves FIPS and year metadata."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        result = amp.amplify_phased(rates, CrisisPhase.DEEP)

        assert result.fips == rates.fips
        assert result.year == rates.year


# =============================================================================
# T038: FR-007 - Rate clamping to [0, 1]
# =============================================================================


@pytest.mark.unit
class TestRateClamping:
    """FR-007: Crisis-amplified rates remain clamped to [0, 1]."""

    def test_deep_amplification_clamps_to_one(self) -> None:
        """Large base rates clamped to 1.0 after DEEP amplification."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates(
            dispossession=0.50,  # 0.50 * 3.0 = 1.50, should clamp
            precaritization=0.40,  # 0.40 * 3.5 = 1.40, should clamp
        )

        result = amp.amplify_phased(rates, CrisisPhase.DEEP)

        assert result.dispossession <= 1.0
        assert result.precaritization <= 1.0

    def test_all_rates_non_negative(self) -> None:
        """All amplified rates are >= 0."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        for phase in CrisisPhase:
            result = amp.amplify_phased(rates, phase)
            assert result.dispossession >= 0
            assert result.accumulation >= 0
            assert result.precaritization >= 0
            assert result.stabilization >= 0


# =============================================================================
# T039: Backward compatibility with CrisisAmplifier protocol
# =============================================================================


@pytest.mark.unit
class TestBackwardCompatibility:
    """C-002: PhasedCrisisAmplifier preserves CrisisAmplifier protocol.

    amplify(rates, crisis=True) should map to DEEP phase amplification.
    amplify(rates, crisis=False) should be passthrough (NORMAL).
    """

    def test_amplify_crisis_true_uses_deep(self) -> None:
        """amplify(rates, crisis=True) applies DEEP multipliers."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        result_bool = amp.amplify(rates, crisis=True)
        result_phased = amp.amplify_phased(rates, CrisisPhase.DEEP)

        assert result_bool.dispossession == pytest.approx(result_phased.dispossession)
        assert result_bool.accumulation == pytest.approx(result_phased.accumulation)
        assert result_bool.precaritization == pytest.approx(result_phased.precaritization)
        assert result_bool.stabilization == pytest.approx(result_phased.stabilization)

    def test_amplify_crisis_false_passthrough(self) -> None:
        """amplify(rates, crisis=False) returns rates unchanged."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        result = amp.amplify(rates, crisis=False)

        assert result.dispossession == pytest.approx(rates.dispossession)
        assert result.accumulation == pytest.approx(rates.accumulation)

    def test_satisfies_crisis_amplifier_protocol(self) -> None:
        """PhasedCrisisAmplifier satisfies CrisisAmplifier protocol."""
        from babylon.economics.dynamics.data_sources import CrisisAmplifier

        amp: CrisisAmplifier = PhasedCrisisAmplifier()
        rates = _make_rates()
        result = amp.amplify(rates, crisis=True)
        assert isinstance(result, TransitionRates)

    def test_normal_phase_is_passthrough(self) -> None:
        """NORMAL phase is passthrough (1.0x all multipliers)."""
        amp = PhasedCrisisAmplifier()
        rates = _make_rates()

        result = amp.amplify_phased(rates, CrisisPhase.NORMAL)

        assert result.dispossession == pytest.approx(rates.dispossession)
        assert result.accumulation == pytest.approx(rates.accumulation)
        assert result.precaritization == pytest.approx(rates.precaritization)
        assert result.stabilization == pytest.approx(rates.stabilization)
