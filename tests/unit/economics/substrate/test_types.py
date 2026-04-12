"""Unit tests for substrate type definitions (T004).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests frozen Pydantic models: HexEconomicState, HexGrid, SubstrateConfig,
BoundaryFlowRegister, TractWeight.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.substrate.types import (
    CONSERVATION_TOLERANCE,
    TRI_COUNTY_FIPS,
    BoundaryFlowRegister,
    HexEconomicState,
    HexGrid,
    HexTenureComposition,
    SubstrateConfig,
    TractWeight,
)

# =============================================================================
# TractWeight
# =============================================================================


@pytest.mark.unit
class TestTractWeight:
    """Tests for TractWeight Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test TractWeight with valid values."""
        tw = TractWeight(
            tract_geoid="26163500100",
            population=4500,
            employed=2100,
            weight=0.015,
        )
        assert tw.tract_geoid == "26163500100"
        assert tw.population == 4500
        assert tw.employed == 2100
        assert tw.weight == 0.015

    def test_frozen_immutability(self) -> None:
        """Test that TractWeight is immutable (frozen=True)."""
        tw = TractWeight(
            tract_geoid="26163500100",
            population=4500,
            employed=2100,
            weight=0.015,
        )
        with pytest.raises(ValidationError):
            tw.weight = 0.5  # type: ignore[misc]

    def test_weight_lower_bound(self) -> None:
        """Test that weight of 0.0 is accepted."""
        tw = TractWeight(
            tract_geoid="26163500100",
            population=0,
            employed=0,
            weight=0.0,
        )
        assert tw.weight == 0.0

    def test_weight_upper_bound(self) -> None:
        """Test that weight of 1.0 is accepted."""
        tw = TractWeight(
            tract_geoid="26163500100",
            population=100,
            employed=50,
            weight=1.0,
        )
        assert tw.weight == 1.0

    def test_weight_above_one_rejected(self) -> None:
        """Test that weight > 1.0 is rejected."""
        with pytest.raises(ValidationError):
            TractWeight(
                tract_geoid="26163500100",
                population=100,
                employed=50,
                weight=1.01,
            )

    def test_weight_negative_rejected(self) -> None:
        """Test that weight < 0.0 is rejected."""
        with pytest.raises(ValidationError):
            TractWeight(
                tract_geoid="26163500100",
                population=100,
                employed=50,
                weight=-0.01,
            )

    def test_tract_geoid_too_short_rejected(self) -> None:
        """Test that tract_geoid shorter than 11 chars is rejected."""
        with pytest.raises(ValidationError):
            TractWeight(
                tract_geoid="2616350010",  # 10 chars
                population=100,
                employed=50,
                weight=0.5,
            )

    def test_tract_geoid_too_long_rejected(self) -> None:
        """Test that tract_geoid longer than 11 chars is rejected."""
        with pytest.raises(ValidationError):
            TractWeight(
                tract_geoid="261635001001",  # 12 chars
                population=100,
                employed=50,
                weight=0.5,
            )

    def test_negative_population_rejected(self) -> None:
        """Test that negative population is rejected."""
        with pytest.raises(ValidationError):
            TractWeight(
                tract_geoid="26163500100",
                population=-1,
                employed=0,
                weight=0.5,
            )

    def test_negative_employed_rejected(self) -> None:
        """Test that negative employed count is rejected."""
        with pytest.raises(ValidationError):
            TractWeight(
                tract_geoid="26163500100",
                population=100,
                employed=-1,
                weight=0.5,
            )


# =============================================================================
# HexTenureComposition
# =============================================================================


@pytest.mark.unit
class TestHexTenureComposition:
    """Tests for HexTenureComposition Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test HexTenureComposition with valid values."""
        h = HexTenureComposition(
            residential_owner_occupied=0.4,
            residential_rental=0.2,
            commercial=0.1,
            industrial=0.1,
            public=0.1,
            trust_land=0.05,
            vacant_abandoned=0.05,
        )
        assert h.residential_owner_occupied == 0.4
        assert h.vacant_abandoned == 0.05

    def test_frozen_immutability(self) -> None:
        """Test that HexTenureComposition is immutable (frozen=True)."""
        h = HexTenureComposition(
            residential_owner_occupied=0.4,
            residential_rental=0.2,
            commercial=0.1,
            industrial=0.1,
            public=0.1,
            trust_land=0.05,
            vacant_abandoned=0.05,
        )
        with pytest.raises(ValidationError):
            h.commercial = 0.5  # type: ignore[misc]

    def test_sum_must_be_one(self) -> None:
        """Test that validation fails if sum is not 1.0."""
        with pytest.raises(ValidationError, match="Tenure shares must sum to 1.0"):
            HexTenureComposition(
                residential_owner_occupied=0.4,
                residential_rental=0.2,
                commercial=0.1,
                industrial=0.1,
                public=0.1,
                trust_land=0.05,
                vacant_abandoned=0.1,  # sum is 1.05
            )

    def test_negative_values_rejected(self) -> None:
        """Test that negative tenure shares are rejected."""
        with pytest.raises(ValidationError):
            HexTenureComposition(
                residential_owner_occupied=-0.1,
                residential_rental=0.5,
                commercial=0.2,
                industrial=0.1,
                public=0.1,
                trust_land=0.1,
                vacant_abandoned=0.1,
            )


# =============================================================================
# HexEconomicState
# =============================================================================


@pytest.mark.unit
class TestHexEconomicState:
    """Tests for HexEconomicState Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test HexEconomicState with valid values."""
        h = HexEconomicState(
            h3_index="872830828ffffff",
            county_fips="26163",
            constant_capital=500.0,
            variable_capital=200.0,
            surplus_value=100.0,
            employment=50.0,
            dept_shares=(0.3, 0.3, 0.2, 0.2),
        )
        assert h.h3_index == "872830828ffffff"
        assert h.county_fips == "26163"
        assert h.constant_capital == 500.0
        assert h.variable_capital == 200.0
        assert h.surplus_value == 100.0
        assert h.employment == 50.0
        assert h.dept_shares == (0.3, 0.3, 0.2, 0.2)
        assert h.profit_rate == 0.0  # default
        assert h.exploitation_rate == 0.0  # default
        assert h.tenure_composition is None  # default

    def test_valid_construction_with_tenure(self) -> None:
        """Test HexEconomicState constructed with HexTenureComposition."""
        tenure = HexTenureComposition(
            residential_owner_occupied=0.5,
            residential_rental=0.2,
            commercial=0.1,
            industrial=0.1,
            public=0.1,
            trust_land=0.0,
            vacant_abandoned=0.0,
        )
        h = HexEconomicState(
            h3_index="872830828ffffff",
            county_fips="26163",
            constant_capital=500.0,
            variable_capital=200.0,
            surplus_value=100.0,
            employment=50.0,
            dept_shares=(0.3, 0.3, 0.2, 0.2),
            tenure_composition=tenure,
        )
        assert h.tenure_composition is not None
        assert h.tenure_composition.residential_owner_occupied == 0.5

    def test_frozen_immutability(self) -> None:
        """Test that HexEconomicState is immutable (frozen=True)."""
        h = HexEconomicState(
            h3_index="872830828ffffff",
            county_fips="26163",
            constant_capital=500.0,
            variable_capital=200.0,
            surplus_value=100.0,
            employment=50.0,
            dept_shares=(0.3, 0.3, 0.2, 0.2),
        )
        with pytest.raises(ValidationError):
            h.constant_capital = 999.0  # type: ignore[misc]

    def test_valid_county_fips_wayne(self) -> None:
        """Test Wayne County FIPS (26163) is accepted."""
        h = HexEconomicState(
            h3_index="872830828ffffff",
            county_fips="26163",
            constant_capital=0.0,
            variable_capital=0.0,
            surplus_value=0.0,
            employment=0.0,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
        )
        assert h.county_fips == "26163"

    def test_valid_county_fips_oakland(self) -> None:
        """Test Oakland County FIPS (26125) is accepted."""
        h = HexEconomicState(
            h3_index="872830880ffffff",
            county_fips="26125",
            constant_capital=0.0,
            variable_capital=0.0,
            surplus_value=0.0,
            employment=0.0,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
        )
        assert h.county_fips == "26125"

    def test_valid_county_fips_macomb(self) -> None:
        """Test Macomb County FIPS (26099) is accepted."""
        h = HexEconomicState(
            h3_index="872830890ffffff",
            county_fips="26099",
            constant_capital=0.0,
            variable_capital=0.0,
            surplus_value=0.0,
            employment=0.0,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
        )
        assert h.county_fips == "26099"

    def test_invalid_county_fips_rejected(self) -> None:
        """Test that non-tri-county FIPS is rejected."""
        with pytest.raises(ValidationError, match="county_fips must be one of"):
            HexEconomicState(
                h3_index="872830828ffffff",
                county_fips="36061",  # Manhattan, not tri-county
                constant_capital=0.0,
                variable_capital=0.0,
                surplus_value=0.0,
                employment=0.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            )

    def test_dept_shares_must_sum_to_one(self) -> None:
        """Test that dept_shares not summing to 1.0 is rejected."""
        with pytest.raises(ValidationError, match="dept_shares must sum to 1.0"):
            HexEconomicState(
                h3_index="872830828ffffff",
                county_fips="26163",
                constant_capital=0.0,
                variable_capital=0.0,
                surplus_value=0.0,
                employment=0.0,
                dept_shares=(0.3, 0.3, 0.3, 0.3),  # sums to 1.2
            )

    def test_dept_shares_negative_rejected(self) -> None:
        """Test that negative dept_shares are rejected."""
        with pytest.raises(ValidationError, match="must be >= 0.0"):
            HexEconomicState(
                h3_index="872830828ffffff",
                county_fips="26163",
                constant_capital=0.0,
                variable_capital=0.0,
                surplus_value=0.0,
                employment=0.0,
                dept_shares=(-0.1, 0.4, 0.4, 0.3),
            )

    def test_dept_shares_valid_sum_within_tolerance(self) -> None:
        """Test that dept_shares summing to 1.0 within tolerance are accepted."""
        # This should be accepted because sum is within CONSERVATION_TOLERANCE of 1.0
        h = HexEconomicState(
            h3_index="872830828ffffff",
            county_fips="26163",
            constant_capital=0.0,
            variable_capital=0.0,
            surplus_value=0.0,
            employment=0.0,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
        )
        assert sum(h.dept_shares) == 1.0

    def test_negative_constant_capital_rejected(self) -> None:
        """Test that negative constant_capital is rejected."""
        with pytest.raises(ValidationError):
            HexEconomicState(
                h3_index="872830828ffffff",
                county_fips="26163",
                constant_capital=-1.0,
                variable_capital=0.0,
                surplus_value=0.0,
                employment=0.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            )

    def test_negative_variable_capital_rejected(self) -> None:
        """Test that negative variable_capital is rejected."""
        with pytest.raises(ValidationError):
            HexEconomicState(
                h3_index="872830828ffffff",
                county_fips="26163",
                constant_capital=0.0,
                variable_capital=-1.0,
                surplus_value=0.0,
                employment=0.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            )

    def test_negative_surplus_value_rejected(self) -> None:
        """Test that negative surplus_value is rejected."""
        with pytest.raises(ValidationError):
            HexEconomicState(
                h3_index="872830828ffffff",
                county_fips="26163",
                constant_capital=0.0,
                variable_capital=0.0,
                surplus_value=-1.0,
                employment=0.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            )

    def test_negative_employment_rejected(self) -> None:
        """Test that negative employment is rejected."""
        with pytest.raises(ValidationError):
            HexEconomicState(
                h3_index="872830828ffffff",
                county_fips="26163",
                constant_capital=0.0,
                variable_capital=0.0,
                surplus_value=0.0,
                employment=-1.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
            )

    def test_zero_capital_accepted(self) -> None:
        """Test that all-zero capital values are accepted."""
        h = HexEconomicState(
            h3_index="872830828ffffff",
            county_fips="26163",
            constant_capital=0.0,
            variable_capital=0.0,
            surplus_value=0.0,
            employment=0.0,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
        )
        assert h.constant_capital == 0.0
        assert h.variable_capital == 0.0
        assert h.surplus_value == 0.0

    def test_custom_profit_rate(self) -> None:
        """Test that custom profit_rate can be set."""
        h = HexEconomicState(
            h3_index="872830828ffffff",
            county_fips="26163",
            constant_capital=100.0,
            variable_capital=50.0,
            surplus_value=25.0,
            employment=10.0,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
            profit_rate=0.167,
        )
        assert h.profit_rate == pytest.approx(0.167)


# =============================================================================
# HexGrid
# =============================================================================


@pytest.mark.unit
class TestHexGrid:
    """Tests for HexGrid Pydantic model."""

    def test_empty_grid_construction(self) -> None:
        """Test empty HexGrid construction."""
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        assert len(grid.hexes) == 0
        assert len(grid.county_hex_ids) == 0

    def test_grid_with_hexes(self, sample_hex_grid: HexGrid) -> None:
        """Test HexGrid constructed from fixture has 9 hexes."""
        assert len(sample_hex_grid.hexes) == 9

    def test_grid_county_assignment(self, sample_hex_grid: HexGrid) -> None:
        """Test that each county has exactly 3 hexes."""
        for fips in TRI_COUNTY_FIPS:
            assert len(sample_hex_grid.county_hex_ids[fips]) == 3

    def test_grid_resolution_hierarchy(self, sample_hex_grid: HexGrid) -> None:
        """Test resolution hierarchy maps are populated."""
        assert len(sample_hex_grid.res6_parents) == 9
        assert len(sample_hex_grid.res5_parents) == 9
        assert len(sample_hex_grid.res6_children) > 0
        assert len(sample_hex_grid.res5_children) > 0

    def test_frozen_immutability(self) -> None:
        """Test that HexGrid is immutable (frozen=True)."""
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        with pytest.raises(ValidationError):
            grid.hexes = {}  # type: ignore[misc]


# =============================================================================
# SubstrateConfig
# =============================================================================


@pytest.mark.unit
class TestSubstrateConfig:
    """Tests for SubstrateConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Test SubstrateConfig default values."""
        config = SubstrateConfig()
        assert config.county_fips_list == ("26163", "26125", "26099")
        assert config.h3_resolution == 7
        assert config.conservation_tolerance == 1e-10
        assert config.equalization_alpha == 0.01
        assert config.tick_count == 260
        assert config.log_conservation_warnings is True

    def test_custom_values(self) -> None:
        """Test SubstrateConfig with custom values."""
        config = SubstrateConfig(
            h3_resolution=6,
            equalization_alpha=0.05,
            tick_count=52,
            log_conservation_warnings=False,
        )
        assert config.h3_resolution == 6
        assert config.equalization_alpha == 0.05
        assert config.tick_count == 52
        assert config.log_conservation_warnings is False

    def test_frozen_immutability(self) -> None:
        """Test that SubstrateConfig is immutable (frozen=True)."""
        config = SubstrateConfig()
        with pytest.raises(ValidationError):
            config.h3_resolution = 8  # type: ignore[misc]

    def test_default_county_count(self) -> None:
        """Test that default config has exactly 3 counties."""
        config = SubstrateConfig()
        assert len(config.county_fips_list) == 3


# =============================================================================
# BoundaryFlowRegister
# =============================================================================


@pytest.mark.unit
class TestBoundaryFlowRegister:
    """Tests for BoundaryFlowRegister Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test BoundaryFlowRegister with valid values."""
        bfr = BoundaryFlowRegister(
            external_outflow_v=150.0,
            external_inflow_v=200.0,
            net_flow=50.0,
        )
        assert bfr.external_outflow_v == 150.0
        assert bfr.external_inflow_v == 200.0
        assert bfr.net_flow == 50.0

    def test_default_values(self) -> None:
        """Test BoundaryFlowRegister defaults to zero."""
        bfr = BoundaryFlowRegister()
        assert bfr.external_outflow_v == 0.0
        assert bfr.external_inflow_v == 0.0
        assert bfr.net_flow == 0.0

    def test_net_flow_validation_correct(self) -> None:
        """Test that net_flow must equal inflow - outflow."""
        bfr = BoundaryFlowRegister(
            external_outflow_v=100.0,
            external_inflow_v=80.0,
            net_flow=-20.0,
        )
        assert bfr.net_flow == -20.0

    def test_net_flow_validation_mismatch_rejected(self) -> None:
        """Test that inconsistent net_flow is rejected."""
        with pytest.raises(ValidationError, match="net_flow must equal"):
            BoundaryFlowRegister(
                external_outflow_v=100.0,
                external_inflow_v=80.0,
                net_flow=999.0,  # should be -20
            )

    def test_frozen_immutability(self) -> None:
        """Test that BoundaryFlowRegister is immutable (frozen=True)."""
        bfr = BoundaryFlowRegister()
        with pytest.raises(ValidationError):
            bfr.net_flow = 100.0  # type: ignore[misc]

    def test_negative_net_flow(self) -> None:
        """Test BoundaryFlowRegister with net outflow."""
        bfr = BoundaryFlowRegister(
            external_outflow_v=5000.0,
            external_inflow_v=4000.0,
            net_flow=-1000.0,
        )
        assert bfr.net_flow == -1000.0
        assert bfr.net_flow == bfr.external_inflow_v - bfr.external_outflow_v


# =============================================================================
# TRI_COUNTY_FIPS Constant
# =============================================================================


@pytest.mark.unit
class TestTriCountyFips:
    """Tests for TRI_COUNTY_FIPS constant."""

    def test_exactly_three_counties(self) -> None:
        """Test that TRI_COUNTY_FIPS has exactly 3 entries."""
        assert len(TRI_COUNTY_FIPS) == 3

    def test_expected_fips_codes(self) -> None:
        """Test that TRI_COUNTY_FIPS contains Wayne, Oakland, Macomb."""
        assert "26163" in TRI_COUNTY_FIPS  # Wayne
        assert "26125" in TRI_COUNTY_FIPS  # Oakland
        assert "26099" in TRI_COUNTY_FIPS  # Macomb

    def test_conservation_tolerance_value(self) -> None:
        """Test CONSERVATION_TOLERANCE is 1e-10."""
        assert CONSERVATION_TOLERANCE == 1e-10
