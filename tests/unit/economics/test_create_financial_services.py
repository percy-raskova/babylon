"""Unit tests for create_financial_services (honesty sweep, U2).

Feature: 024-capital-volume-iii
"""

from __future__ import annotations

from babylon.config.defines import CapitalVolumeIIIDefines, GameDefines
from babylon.domain.economics.factory import create_financial_services


class TestCreateFinancialServicesHousingRate:
    def test_default_housing_capitalization_rate_is_capital_vol3_default(self) -> None:
        overrides = create_financial_services()
        housing_calc = overrides["housing_calculator"]
        assert (
            housing_calc._interest_rate
            == GameDefines().capital_vol3.housing_capitalization_rate_default
        )

    def test_custom_defines_changes_housing_capitalization_rate(self) -> None:
        defines = GameDefines(
            capital_vol3=CapitalVolumeIIIDefines(housing_capitalization_rate_default=0.12)
        )
        overrides = create_financial_services(defines=defines)
        housing_calc = overrides["housing_calculator"]
        assert housing_calc._interest_rate == 0.12
