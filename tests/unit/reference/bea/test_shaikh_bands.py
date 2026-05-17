"""T059-T060: Unit tests for Shaikh bands + validator (spec-068 US4)."""

from __future__ import annotations

import pytest

from babylon.reference.bea.shaikh_bands import (
    SHAIKH_BANDS,
    ShaikhBand,
    ShaikhBandViolation,
    lookup_shaikh_band,
)
from babylon.reference.bea.shaikh_validator import validate_per_industry_c_v


@pytest.mark.unit
class TestShaikhBands:
    """T059: bands table lookup + fallback semantics."""

    def test_manufacturing_band_present(self) -> None:
        band = lookup_shaikh_band("325")  # Chemicals
        assert isinstance(band, ShaikhBand)
        assert band.is_fallback is False
        assert (band.lower, band.upper) == (2.0, 4.0)

    def test_services_band_present(self) -> None:
        band = lookup_shaikh_band("5411")  # Legal services
        assert band.is_fallback is False
        assert (band.lower, band.upper) == (0.3, 0.8)

    def test_unknown_industry_falls_back_to_economy_wide(self) -> None:
        band = lookup_shaikh_band("ZZZ_UNKNOWN")
        assert band.is_fallback is True
        # Economy-wide fallback band
        assert (band.lower, band.upper) == (0.4, 1.2)

    def test_all_bands_have_lower_below_upper(self) -> None:
        for code, (lower, upper) in SHAIKH_BANDS.items():
            assert lower < upper, f"band {code} has lower={lower} >= upper={upper}"
            assert lower >= 0, f"band {code} has negative lower={lower}"


@pytest.mark.unit
class TestShaikhValidator:
    """T060: validator detects in/out-of-band industries with tolerance widening."""

    def test_in_band_no_violation(self) -> None:
        # Manufacturing band [2.0, 4.0], measured 3.0 → in band
        violations = validate_per_industry_c_v(
            {1: 3.0},
            {1: "325"},
            tolerance_fraction=0.0,
        )
        assert violations == []

    def test_out_of_band_yields_violation(self) -> None:
        # Manufacturing band [2.0, 4.0], measured 100.0 → far out-of-band
        violations = validate_per_industry_c_v(
            {1: 100.0},
            {1: "325"},
            tolerance_fraction=0.0,
        )
        assert len(violations) == 1
        v = violations[0]
        assert isinstance(v, ShaikhBandViolation)
        assert v.bea_code == "325"
        assert v.measured_c_v == 100.0

    def test_tolerance_widens_band(self) -> None:
        # Manufacturing band [2.0, 4.0]. measured 5.5 outside but within 50% widening
        # [2.0*0.5, 4.0*1.5] = [1.0, 6.0] → in band
        violations = validate_per_industry_c_v(
            {1: 5.5},
            {1: "325"},
            tolerance_fraction=0.5,
        )
        assert violations == []

    def test_unknown_bea_code_uses_fallback_band(self) -> None:
        # Unknown code → economy-wide fallback [0.4, 1.2]. measured 0.8 in band.
        violations = validate_per_industry_c_v(
            {1: 0.8},
            {1: "ZZZ_UNKNOWN"},
            tolerance_fraction=0.0,
        )
        assert violations == []

    def test_industry_id_without_bea_code_skipped(self) -> None:
        # If we don't know the bea_code for an industry_id, skip silently.
        violations = validate_per_industry_c_v(
            {1: 100.0},
            {},  # empty mapping
            tolerance_fraction=0.0,
        )
        assert violations == []
