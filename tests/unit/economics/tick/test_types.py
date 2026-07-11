"""Tests for Simulation Tick Dynamics Pydantic type models.

Feature: 017-simulation-tick-dynamics
Task: T004
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.dynamics.types import ClassDistribution
from babylon.domain.economics.tick.types import (
    BifurcationRiskMetric,
    CountyEconomicState,
    CrisisPhase,
    CrisisState,
    DerivedRates,
    NationalTickParameters,
    PhasedAmplificationProfile,
    SimulationTickState,
    SmoothedCoefficients,
    TickSummary,
)


class TestNationalTickParameters:
    """Tests for NationalTickParameters frozen model."""

    def test_valid_construction(self) -> None:
        """Verify valid construction with all fields."""
        params = NationalTickParameters(
            year=2015,
            tau=62.0,
            gamma_basket=0.68,
            gamma_basket_raw=0.68,
            gamma_III=0.33,
            gamma_III_raw=0.33,
            tau_effective=42.16,
            v_reproduction=12.0,
            estimated=True,
        )
        assert params.year == 2015
        assert params.tau == 62.0
        assert params.gamma_basket == 0.68

    def test_frozen_immutability(self) -> None:
        """Verify frozen model rejects mutation."""
        params = NationalTickParameters(
            year=2015,
            tau=62.0,
            gamma_basket=0.68,
            gamma_basket_raw=0.68,
            gamma_III=0.33,
            gamma_III_raw=0.33,
            tau_effective=42.16,
            v_reproduction=12.0,
        )
        with pytest.raises(ValidationError):
            params.tau = 65.0  # type: ignore[misc]

    def test_year_bounds(self) -> None:
        """Verify year constraint ge=2007, le=2040."""
        with pytest.raises(ValidationError, match="year"):
            NationalTickParameters(
                year=2006,
                tau=62.0,
                gamma_basket=0.68,
                gamma_basket_raw=0.68,
                gamma_III=0.33,
                gamma_III_raw=0.33,
                tau_effective=42.16,
                v_reproduction=12.0,
            )
        with pytest.raises(ValidationError, match="year"):
            NationalTickParameters(
                year=2041,
                tau=62.0,
                gamma_basket=0.68,
                gamma_basket_raw=0.68,
                gamma_III=0.33,
                gamma_III_raw=0.33,
                tau_effective=42.16,
                v_reproduction=12.0,
            )

    def test_tau_must_be_positive(self) -> None:
        """Verify tau gt=0 constraint."""
        with pytest.raises(ValidationError, match="tau"):
            NationalTickParameters(
                year=2015,
                tau=0.0,
                gamma_basket=0.68,
                gamma_basket_raw=0.68,
                gamma_III=0.33,
                gamma_III_raw=0.33,
                tau_effective=42.16,
                v_reproduction=12.0,
            )

    def test_gamma_basket_bounds(self) -> None:
        """Verify gamma_basket gt=0, le=1."""
        with pytest.raises(ValidationError):
            NationalTickParameters(
                year=2015,
                tau=62.0,
                gamma_basket=0.0,
                gamma_basket_raw=0.68,
                gamma_III=0.33,
                gamma_III_raw=0.33,
                tau_effective=42.16,
                v_reproduction=12.0,
            )
        with pytest.raises(ValidationError):
            NationalTickParameters(
                year=2015,
                tau=62.0,
                gamma_basket=1.5,
                gamma_basket_raw=0.68,
                gamma_III=0.33,
                gamma_III_raw=0.33,
                tau_effective=42.16,
                v_reproduction=12.0,
            )


class TestDerivedRates:
    """Tests for DerivedRates frozen model."""

    def test_valid_with_all_rates(self) -> None:
        """Verify construction with all rates present."""
        rates = DerivedRates(
            fips="26163",
            year=2015,
            profit_rate=0.15,
            organic_composition=3.2,
            exploitation_rate=1.5,
            phi_hour=3.50,
        )
        assert rates.profit_rate == 0.15
        assert rates.organic_composition == 3.2

    def test_none_for_division_by_zero(self) -> None:
        """Verify Optional[float] fields accept None for division-by-zero."""
        rates = DerivedRates(
            fips="26163",
            year=2015,
            profit_rate=None,
            organic_composition=None,
            exploitation_rate=None,
            phi_hour=3.50,
        )
        assert rates.profit_rate is None
        assert rates.organic_composition is None
        assert rates.exploitation_rate is None

    def test_fips_length_constraint(self) -> None:
        """Verify FIPS must be exactly 5 characters."""
        with pytest.raises(ValidationError, match="fips"):
            DerivedRates(fips="261", year=2015, phi_hour=3.50)

    def test_phi_hour_non_negative(self) -> None:
        """Verify phi_hour ge=0."""
        with pytest.raises(ValidationError, match="phi_hour"):
            DerivedRates(fips="26163", year=2015, phi_hour=-1.0)


class TestCountyEconomicState:
    """Tests for CountyEconomicState frozen model."""

    def test_valid_construction(self) -> None:
        """Verify valid construction with ClassDistribution."""
        dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        state = CountyEconomicState(
            fips="26163",
            year=2015,
            capital_stock=1e9,
            throughput_position=0.9,
            supply_chain_depth=2.1,
            unemployment_rate=0.053,
            u6_rate=0.10,
            pter_rate=0.04,
            nilf_rate=0.06,
            median_wage=21.0,
            employment=500000.0,
            class_distribution=dist,
            phi_hour=3.50,
        )
        assert state.fips == "26163"
        assert state.capital_stock == 1e9

    def test_supply_chain_depth_bounds(self) -> None:
        """Verify supply_chain_depth ge=0, le=5."""
        dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        with pytest.raises(ValidationError, match="supply_chain_depth"):
            CountyEconomicState(
                fips="26163",
                year=2015,
                capital_stock=1e9,
                throughput_position=0.9,
                supply_chain_depth=5.5,
                unemployment_rate=0.05,
                u6_rate=0.10,
                pter_rate=0.04,
                nilf_rate=0.06,
                median_wage=21.0,
                employment=500000.0,
                class_distribution=dist,
                phi_hour=3.50,
            )


class TestSmoothedCoefficients:
    """Tests for SmoothedCoefficients frozen model."""

    def test_valid_construction(self) -> None:
        """Verify valid construction."""
        coeff = SmoothedCoefficients(
            alpha=0.3,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.35,
            is_initialized=True,
        )
        assert coeff.alpha == 0.3
        assert coeff.is_initialized is True

    def test_alpha_bounds(self) -> None:
        """Verify alpha gt=0, le=1."""
        with pytest.raises(ValidationError, match="alpha"):
            SmoothedCoefficients(
                alpha=0.0,
                gamma_basket=0.68,
                gamma_III=0.33,
                gamma_import=0.35,
            )
        # alpha=1.0 should be valid (no smoothing)
        coeff = SmoothedCoefficients(
            alpha=1.0,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.35,
        )
        assert coeff.alpha == 1.0

    def test_default_not_initialized(self) -> None:
        """Verify is_initialized defaults to False."""
        coeff = SmoothedCoefficients(
            alpha=0.3,
            gamma_basket=0.68,
            gamma_III=0.33,
            gamma_import=0.35,
        )
        assert coeff.is_initialized is False


class TestTickSummary:
    """Tests for TickSummary frozen model."""

    def test_valid_construction(self) -> None:
        """Verify valid construction."""
        summary = TickSummary(
            year=2015,
            counties_processed=3,
            phi_aggregate=1e12,
            national_melt=62.0,
            mean_profit_rate=0.15,
            mean_occ=3.2,
            mean_exploitation_rate=1.5,
            national_class_distribution={
                "bourgeoisie": 0.01,
                "petit_bourgeoisie": 0.09,
                "labor_aristocracy": 0.40,
                "proletariat": 0.35,
                "lumpenproletariat": 0.15,
            },
        )
        assert summary.counties_processed == 3
        assert summary.phi_aggregate == 1e12


class TestSimulationTickState:
    """Tests for SimulationTickState frozen model."""

    def test_valid_construction(
        self,
        sample_national_params: NationalTickParameters,
        sample_county_state: CountyEconomicState,
        sample_coefficients: SmoothedCoefficients,
    ) -> None:
        """Verify valid construction with nested models."""
        state = SimulationTickState(
            year=2015,
            national_params=sample_national_params,
            county_states={"26163": sample_county_state},
            coefficients=sample_coefficients,
        )
        assert state.year == 2015
        assert "26163" in state.county_states
        assert state.tick_summary is None

    def test_fips_key_mismatch_rejected(
        self,
        sample_national_params: NationalTickParameters,
        sample_county_state: CountyEconomicState,
        sample_coefficients: SmoothedCoefficients,
    ) -> None:
        """Verify FIPS key must match county FIPS value."""
        with pytest.raises(ValidationError, match="does not match"):
            SimulationTickState(
                year=2015,
                national_params=sample_national_params,
                county_states={"99999": sample_county_state},
                coefficients=sample_coefficients,
            )

    def test_frozen_immutability(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify frozen model rejects mutation."""
        with pytest.raises(ValidationError):
            sample_tick_state.year = 2016  # type: ignore[misc]


class TestCrisisPhase:
    """Tests for CrisisPhase StrEnum (Feature 018, T014)."""

    def test_all_phases_exist(self) -> None:
        """Verify all 5 lifecycle phases are defined."""
        assert CrisisPhase.NORMAL == "normal"
        assert CrisisPhase.ONSET == "onset"
        assert CrisisPhase.EARLY == "early"
        assert CrisisPhase.DEEP == "deep"
        assert CrisisPhase.RECOVERY == "recovery"

    def test_enum_count(self) -> None:
        """Verify exactly 5 phases."""
        assert len(CrisisPhase) == 5

    def test_definition_order(self) -> None:
        """Verify phases are defined in lifecycle order."""
        phases = list(CrisisPhase)
        assert phases == [
            CrisisPhase.NORMAL,
            CrisisPhase.ONSET,
            CrisisPhase.EARLY,
            CrisisPhase.DEEP,
            CrisisPhase.RECOVERY,
        ]

    def test_is_str_enum(self) -> None:
        """Verify CrisisPhase values are strings for JSON serialization."""
        for phase in CrisisPhase:
            assert isinstance(phase, str)
            assert isinstance(phase.value, str)


class TestCrisisState:
    """Tests for CrisisState frozen model (Feature 018, T015)."""

    def test_normal_factory(self) -> None:
        """Verify .normal() returns NORMAL with all counters zero."""
        state = CrisisState.normal()
        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 0
        assert state.consecutive_recovery == 0
        assert state.crisis_start_period is None
        assert state.crisis_duration == 0
        assert state.peak_severity is None
        assert state.cumulative_wage_compression == 0.0

    def test_default_construction_is_normal(self) -> None:
        """Verify default construction matches .normal()."""
        state = CrisisState()
        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 0

    def test_frozen_immutability(self) -> None:
        """Verify CrisisState is frozen."""
        state = CrisisState.normal()
        with pytest.raises(ValidationError):
            state.phase = CrisisPhase.DEEP  # type: ignore[misc]

    def test_consecutive_below_non_negative(self) -> None:
        """Verify consecutive_below ge=0."""
        with pytest.raises(ValidationError, match="consecutive_below"):
            CrisisState(consecutive_below=-1)

    def test_crisis_duration_non_negative(self) -> None:
        """Verify crisis_duration ge=0."""
        with pytest.raises(ValidationError, match="crisis_duration"):
            CrisisState(crisis_duration=-1)

    def test_cumulative_wage_compression_bounds(self) -> None:
        """Verify cumulative_wage_compression [0, 1]."""
        with pytest.raises(ValidationError, match="cumulative_wage_compression"):
            CrisisState(cumulative_wage_compression=-0.1)
        with pytest.raises(ValidationError, match="cumulative_wage_compression"):
            CrisisState(cumulative_wage_compression=1.1)

    def test_valid_deep_crisis_state(self) -> None:
        """Verify construction of a deep crisis state."""
        state = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=8,
            consecutive_recovery=0,
            crisis_start_period=10,
            crisis_duration=8,
            peak_severity=0.02,
            cumulative_wage_compression=0.06,
        )
        assert state.phase == CrisisPhase.DEEP
        assert state.crisis_duration == 8
        assert state.peak_severity == 0.02

    def test_model_copy_creates_new_state(self) -> None:
        """Verify model_copy works for state transitions."""
        state = CrisisState.normal()
        updated = state.model_copy(update={"phase": CrisisPhase.ONSET, "consecutive_below": 3})
        assert updated.phase == CrisisPhase.ONSET
        assert updated.consecutive_below == 3
        assert state.phase == CrisisPhase.NORMAL  # original unchanged


class TestBifurcationRiskMetric:
    """Tests for BifurcationRiskMetric frozen model (Feature 018, T016)."""

    def test_neutral_factory(self) -> None:
        """Verify .neutral() returns score=0, full legitimation."""
        metric = BifurcationRiskMetric.neutral()
        assert metric.score == 0.0
        assert metric.solidarity_density == 0.0
        assert metric.legitimation == 1.0
        assert metric.class_burden_ratio == 0.0

    def test_score_bounds(self) -> None:
        """Verify score constrained to [-1, +1]."""
        with pytest.raises(ValidationError, match="score"):
            BifurcationRiskMetric(score=-1.1)
        with pytest.raises(ValidationError, match="score"):
            BifurcationRiskMetric(score=1.1)

    def test_score_boundary_values(self) -> None:
        """Verify score accepts exact boundary values."""
        rev = BifurcationRiskMetric(score=-1.0)
        assert rev.score == -1.0
        fas = BifurcationRiskMetric(score=1.0)
        assert fas.score == 1.0

    def test_solidarity_density_bounds(self) -> None:
        """Verify solidarity_density [0, 1]."""
        with pytest.raises(ValidationError, match="solidarity_density"):
            BifurcationRiskMetric(solidarity_density=-0.1)
        with pytest.raises(ValidationError, match="solidarity_density"):
            BifurcationRiskMetric(solidarity_density=1.1)

    def test_legitimation_bounds(self) -> None:
        """Verify legitimation [0, 1]."""
        with pytest.raises(ValidationError, match="legitimation"):
            BifurcationRiskMetric(legitimation=-0.1)
        with pytest.raises(ValidationError, match="legitimation"):
            BifurcationRiskMetric(legitimation=1.1)

    def test_class_burden_ratio_bounds(self) -> None:
        """Verify class_burden_ratio [0, 1]."""
        with pytest.raises(ValidationError, match="class_burden_ratio"):
            BifurcationRiskMetric(class_burden_ratio=-0.1)
        with pytest.raises(ValidationError, match="class_burden_ratio"):
            BifurcationRiskMetric(class_burden_ratio=1.1)

    def test_frozen_immutability(self) -> None:
        """Verify BifurcationRiskMetric is frozen."""
        metric = BifurcationRiskMetric.neutral()
        with pytest.raises(ValidationError):
            metric.score = 0.5  # type: ignore[misc]


class TestPhasedAmplificationProfile:
    """Tests for PhasedAmplificationProfile frozen model (Feature 018, T017)."""

    def test_valid_normal_profile(self) -> None:
        """Verify normal phase profile (all 1.0)."""
        profile = PhasedAmplificationProfile(
            dispossession_multiplier=1.0,
            precaritization_multiplier=1.0,
            accumulation_multiplier=1.0,
            stabilization_multiplier=1.0,
        )
        assert profile.dispossession_multiplier == 1.0

    def test_valid_deep_profile(self) -> None:
        """Verify deep crisis profile matches FR-006 defaults."""
        profile = PhasedAmplificationProfile(
            dispossession_multiplier=3.0,
            precaritization_multiplier=3.5,
            accumulation_multiplier=0.1,
            stabilization_multiplier=0.2,
        )
        assert profile.dispossession_multiplier == 3.0
        assert profile.accumulation_multiplier == 0.1

    def test_dispossession_multiplier_must_be_positive(self) -> None:
        """Verify dispossession_multiplier gt=0."""
        with pytest.raises(ValidationError, match="dispossession_multiplier"):
            PhasedAmplificationProfile(
                dispossession_multiplier=0.0,
                precaritization_multiplier=1.0,
                accumulation_multiplier=1.0,
                stabilization_multiplier=1.0,
            )

    def test_accumulation_multiplier_le_one(self) -> None:
        """Verify accumulation_multiplier le=1 (dampening only)."""
        with pytest.raises(ValidationError, match="accumulation_multiplier"):
            PhasedAmplificationProfile(
                dispossession_multiplier=1.0,
                precaritization_multiplier=1.0,
                accumulation_multiplier=1.1,
                stabilization_multiplier=1.0,
            )

    def test_stabilization_multiplier_le_one(self) -> None:
        """Verify stabilization_multiplier le=1 (dampening only)."""
        with pytest.raises(ValidationError, match="stabilization_multiplier"):
            PhasedAmplificationProfile(
                dispossession_multiplier=1.0,
                precaritization_multiplier=1.0,
                accumulation_multiplier=1.0,
                stabilization_multiplier=1.1,
            )

    def test_frozen_immutability(self) -> None:
        """Verify PhasedAmplificationProfile is frozen."""
        profile = PhasedAmplificationProfile(
            dispossession_multiplier=1.0,
            precaritization_multiplier=1.0,
            accumulation_multiplier=1.0,
            stabilization_multiplier=1.0,
        )
        with pytest.raises(ValidationError):
            profile.dispossession_multiplier = 2.0  # type: ignore[misc]
