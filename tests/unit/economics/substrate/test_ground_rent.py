"""Unit tests for ground rent extraction in Volume III equalization (FR-010).

Feature: 026-tri-county-economic-substrate (amended by 043-land-ownership-substrate)
Date: 2026-04-09

Tests:
  - Absolute rent extraction from surplus value.
  - Differential rent based on local profit rate advantage.
  - Integration with equalization pipeline.
  - Conservation: total value (c+v+s) must be conserved.
  - No-op when tenure_composition is absent.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import RentCircuitDefines
from babylon.economics.substrate.ground_rent import (
    GroundRentResult,
    compute_ground_rent,
)
from babylon.economics.substrate.types import (
    HexEconomicState,
    HexTenureComposition,
)

from .conftest import WAYNE_HEX_IDS


def _make_tenure(
    owner: float = 0.4,
    rental: float = 0.2,
    commercial: float = 0.1,
    industrial: float = 0.1,
    public: float = 0.1,
    trust: float = 0.0,
    vacant: float = 0.1,
) -> HexTenureComposition:
    """Create a HexTenureComposition with defaults summing to 1.0."""
    return HexTenureComposition(
        residential_owner_occupied=owner,
        residential_rental=rental,
        commercial=commercial,
        industrial=industrial,
        public=public,
        trust_land=trust,
        vacant_abandoned=vacant,
    )


def _make_hex(
    h3_id: str,
    fips: str,
    c: float,
    v: float,
    s: float,
    tenure: HexTenureComposition | None = None,
) -> HexEconomicState:
    """Create a HexEconomicState with computed profit rate."""
    cv = c + v
    pr = s / cv if cv > 0 else 0.0
    er = s / v if v > 0 else 0.0
    return HexEconomicState(
        h3_index=h3_id,
        county_fips=fips,
        constant_capital=c,
        variable_capital=v,
        surplus_value=s,
        employment=100.0,
        dept_shares=(0.25, 0.25, 0.25, 0.25),
        profit_rate=pr,
        exploitation_rate=er,
        tenure_composition=tenure,
    )


@pytest.mark.unit
class TestGroundRentResult:
    """Tests for the GroundRentResult data model."""

    def test_frozen_immutability(self) -> None:
        """Ground rent results are immutable."""
        result = GroundRentResult(
            absolute_rent=10.0,
            differential_rent=5.0,
            total_rent=15.0,
            rent_from_v=6.0,
            rent_from_s=9.0,
        )
        with pytest.raises(Exception):  # noqa: B017
            result.absolute_rent = 99.0  # type: ignore[misc]

    def test_total_equals_sum(self) -> None:
        """Total rent must equal absolute + differential."""
        result = GroundRentResult(
            absolute_rent=10.0,
            differential_rent=5.0,
            total_rent=15.0,
            rent_from_v=6.0,
            rent_from_s=9.0,
        )
        assert abs(result.total_rent - (result.absolute_rent + result.differential_rent)) < 1e-10

    def test_rent_from_v_and_s_sum_to_total(self) -> None:
        """Rent decomposition into v-sourced and s-sourced must sum to total."""
        result = GroundRentResult(
            absolute_rent=10.0,
            differential_rent=5.0,
            total_rent=15.0,
            rent_from_v=6.0,
            rent_from_s=9.0,
        )
        assert abs(result.rent_from_v + result.rent_from_s - result.total_rent) < 1e-10


@pytest.mark.unit
class TestComputeGroundRent:
    """Tests for compute_ground_rent function."""

    def test_no_tenure_returns_zero_rent(self) -> None:
        """Hex without tenure_composition produces zero rent."""
        state = _make_hex(WAYNE_HEX_IDS[0], "26163", c=100, v=50, s=30)
        defines = RentCircuitDefines()
        result = compute_ground_rent(state, r_avg=0.2, defines=defines)
        assert result.total_rent == 0.0
        assert result.absolute_rent == 0.0
        assert result.differential_rent == 0.0

    def test_absolute_rent_extracted_from_surplus(self) -> None:
        """Absolute rent is a fraction of surplus based on private land share.

        Formula: R_abs = s * absolute_rent_fraction * (1 - public - trust_land)
        The private land share excludes public and trust land.
        """
        tenure = _make_tenure(
            owner=0.3,
            rental=0.3,
            commercial=0.1,
            industrial=0.1,
            public=0.1,
            trust=0.0,
            vacant=0.1,
        )
        state = _make_hex(WAYNE_HEX_IDS[0], "26163", c=100, v=50, s=100, tenure=tenure)
        defines = RentCircuitDefines(absolute_rent_fraction=0.10)
        result = compute_ground_rent(state, r_avg=0.2, defines=defines)

        # Private land share = 1.0 - 0.1 (public) - 0.0 (trust) = 0.9
        # Absolute rent = 100 * 0.10 * 0.9 = 9.0
        assert result.absolute_rent == pytest.approx(9.0, abs=1e-9)

    def test_differential_rent_above_average(self) -> None:
        """Hex with above-average profit rate yields positive differential rent.

        Differential rent (type I) = elasticity * (r_local - r_avg) * s * land_intensity
        where land_intensity = commercial + industrial + residential_rental.
        """
        tenure = _make_tenure(
            owner=0.3,
            rental=0.2,
            commercial=0.2,
            industrial=0.1,
            public=0.1,
            trust=0.0,
            vacant=0.1,
        )
        # r_local = 50 / (100 + 50) = 0.333
        state = _make_hex(WAYNE_HEX_IDS[0], "26163", c=100, v=50, s=50, tenure=tenure)
        defines = RentCircuitDefines(differential_rent_elasticity=1.0)
        r_avg = 0.2
        result = compute_ground_rent(state, r_avg=r_avg, defines=defines)

        # Above average -> positive differential rent
        assert result.differential_rent > 0.0

    def test_differential_rent_below_average(self) -> None:
        """Hex with below-average profit rate yields zero differential rent.

        Per Marxian theory, differential rent cannot be negative; a hex
        earning below-average profit has no locational surplus to extract.
        """
        tenure = _make_tenure()
        # r_local = 10 / (100 + 50) = 0.0667
        state = _make_hex(WAYNE_HEX_IDS[0], "26163", c=100, v=50, s=10, tenure=tenure)
        defines = RentCircuitDefines(differential_rent_elasticity=1.2)
        r_avg = 0.2
        result = compute_ground_rent(state, r_avg=r_avg, defines=defines)

        # Below average -> zero differential rent (floor)
        assert result.differential_rent == 0.0

    def test_rent_split_between_v_and_s(self) -> None:
        """Ground rent is split: residential from v, commercial/industrial from s.

        Residential rent is intercepted from the worker's reproduction fund (v).
        Commercial/industrial rent divides surplus value (s).
        """
        tenure = _make_tenure(
            owner=0.3,
            rental=0.3,
            commercial=0.2,
            industrial=0.1,
            public=0.0,
            trust=0.0,
            vacant=0.1,
        )
        state = _make_hex(WAYNE_HEX_IDS[0], "26163", c=100, v=100, s=100, tenure=tenure)
        defines = RentCircuitDefines(absolute_rent_fraction=0.10)
        r_avg = state.profit_rate  # Equal to average -> no differential rent
        result = compute_ground_rent(state, r_avg=r_avg, defines=defines)

        # Total rent = absolute only (no differential when r == r_avg)
        # rent_from_v comes from residential share of absolute rent
        # rent_from_s comes from commercial+industrial share
        assert result.rent_from_v >= 0.0
        assert result.rent_from_s >= 0.0
        assert result.rent_from_v + result.rent_from_s == pytest.approx(result.total_rent)

    def test_trust_land_excluded_from_rent(self) -> None:
        """Trust land does not participate in private rent extraction.

        Per spec 038 INDIGENOUS filtration: trust land operates under a
        qualitatively different property regime without appreciation/extraction.
        """
        # Heavy trust land presence
        tenure = _make_tenure(
            owner=0.1,
            rental=0.1,
            commercial=0.05,
            industrial=0.05,
            public=0.1,
            trust=0.5,
            vacant=0.1,
        )
        state = _make_hex(WAYNE_HEX_IDS[0], "26163", c=100, v=50, s=50, tenure=tenure)
        defines = RentCircuitDefines(absolute_rent_fraction=0.10)
        r_avg = 0.1
        result = compute_ground_rent(state, r_avg=r_avg, defines=defines)

        # Private land = 1.0 - 0.1 (public) - 0.5 (trust) = 0.4
        # Absolute rent = 50 * 0.10 * 0.4 = 2.0
        assert result.absolute_rent == pytest.approx(2.0, abs=1e-9)

    def test_vacant_land_contributes_no_differential_rent(self) -> None:
        """Hex that is entirely vacant produces no differential rent.

        No productive activity on vacant land -> no locational surplus.
        """
        tenure = _make_tenure(
            owner=0.0,
            rental=0.0,
            commercial=0.0,
            industrial=0.0,
            public=0.0,
            trust=0.0,
            vacant=1.0,
        )
        state = _make_hex(WAYNE_HEX_IDS[0], "26163", c=100, v=50, s=50, tenure=tenure)
        defines = RentCircuitDefines(differential_rent_elasticity=1.2)
        result = compute_ground_rent(state, r_avg=0.1, defines=defines)

        # land_intensity = 0 -> differential rent = 0
        assert result.differential_rent == 0.0
