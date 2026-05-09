"""Tests for Spec 057 LeontiefRentDefines configuration.

Spec 057: tasks T007–T010 (RED → GREEN).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import GameDefines


@pytest.mark.unit
class TestLeontiefRentDefinesDefaults:
    """T007 — defaults match spec 057 Phase 2 entries."""

    def test_qcew_carry_forward_max_years_default(self) -> None:
        defines = GameDefines()
        assert defines.economy.leontief_rent.qcew_carry_forward_max_years == 5

    def test_phi_hour_outlier_threshold_low_default(self) -> None:
        defines = GameDefines()
        assert defines.economy.leontief_rent.phi_hour_outlier_threshold_low == -1000.0

    def test_phi_hour_outlier_threshold_high_default(self) -> None:
        defines = GameDefines()
        assert defines.economy.leontief_rent.phi_hour_outlier_threshold_high == 1000.0


@pytest.mark.unit
class TestLeontiefRentDefinesValidation:
    """T008 — bounds [0, 20] on qcew_carry_forward_max_years."""

    def test_qcew_carry_forward_max_years_negative_rejected(self) -> None:
        from babylon.config.defines.economy_basic import LeontiefRentDefines

        with pytest.raises(ValidationError):
            LeontiefRentDefines(qcew_carry_forward_max_years=-1)

    def test_qcew_carry_forward_max_years_too_large_rejected(self) -> None:
        from babylon.config.defines.economy_basic import LeontiefRentDefines

        with pytest.raises(ValidationError):
            LeontiefRentDefines(qcew_carry_forward_max_years=21)

    def test_qcew_carry_forward_max_years_zero_accepted(self) -> None:
        from babylon.config.defines.economy_basic import LeontiefRentDefines

        d = LeontiefRentDefines(qcew_carry_forward_max_years=0)
        assert d.qcew_carry_forward_max_years == 0

    def test_qcew_carry_forward_max_years_max_accepted(self) -> None:
        from babylon.config.defines.economy_basic import LeontiefRentDefines

        d = LeontiefRentDefines(qcew_carry_forward_max_years=20)
        assert d.qcew_carry_forward_max_years == 20

    def test_frozen_model(self) -> None:
        from babylon.config.defines.economy_basic import LeontiefRentDefines

        d = LeontiefRentDefines()
        with pytest.raises(ValidationError):
            d.qcew_carry_forward_max_years = 10  # type: ignore[misc]
