"""Tests for CensusHousingLoader (Feature 024, T072).

Verifies CensusHousingLoader returns data for Wayne/Oakland counties,
None for unknown FIPS/years, and satisfies HousingDataSource protocol.
"""

from __future__ import annotations

import pytest

from babylon.data.census.housing_loader import CensusHousingLoader


@pytest.mark.unit
class TestCensusHousingLoaderDefaults:
    """Tests for CensusHousingLoader with default data."""

    def test_init_loads_defaults(self) -> None:
        """Default constructor populates data."""
        loader = CensusHousingLoader()
        assert loader.get_median_home_value("26163", 2015) is not None

    def test_wayne_county_home_value_2015(self) -> None:
        """Returns correct home value for Wayne County 2015."""
        loader = CensusHousingLoader()
        assert loader.get_median_home_value("26163", 2015) == 44_800.0

    def test_wayne_county_home_value_2022(self) -> None:
        """Returns correct home value for Wayne County 2022."""
        loader = CensusHousingLoader()
        assert loader.get_median_home_value("26163", 2022) == 68_000.0

    def test_oakland_county_home_value_2020(self) -> None:
        """Returns correct home value for Oakland County 2020."""
        loader = CensusHousingLoader()
        assert loader.get_median_home_value("26125", 2020) == 235_000.0

    def test_wayne_county_gross_rent_2020(self) -> None:
        """Returns correct gross rent for Wayne County 2020."""
        loader = CensusHousingLoader()
        assert loader.get_median_gross_rent("26163", 2020) == 850.0

    def test_oakland_county_gross_rent_2022(self) -> None:
        """Returns correct gross rent for Oakland County 2022."""
        loader = CensusHousingLoader()
        assert loader.get_median_gross_rent("26125", 2022) == 1250.0

    def test_construction_index_2018(self) -> None:
        """Returns correct construction cost index for 2018."""
        loader = CensusHousingLoader()
        assert loader.get_construction_cost_index(2018) == 100.0

    def test_construction_index_2022(self) -> None:
        """Returns correct construction cost index for 2022."""
        loader = CensusHousingLoader()
        assert loader.get_construction_cost_index(2022) == 118.0


@pytest.mark.unit
class TestCensusHousingLoaderUnknown:
    """Tests for unknown FIPS codes and years."""

    def test_unknown_fips_returns_none(self) -> None:
        """Returns None for unknown FIPS code."""
        loader = CensusHousingLoader()
        assert loader.get_median_home_value("99999", 2020) is None

    def test_unknown_year_returns_none(self) -> None:
        """Returns None for unknown year."""
        loader = CensusHousingLoader()
        assert loader.get_median_home_value("26163", 1990) is None

    def test_unknown_fips_rent_returns_none(self) -> None:
        """Returns None for unknown FIPS gross rent."""
        loader = CensusHousingLoader()
        assert loader.get_median_gross_rent("00000", 2020) is None

    def test_unknown_year_construction_index_returns_none(self) -> None:
        """Returns None for unknown year construction index."""
        loader = CensusHousingLoader()
        assert loader.get_construction_cost_index(1900) is None


@pytest.mark.unit
class TestCensusHousingLoaderCustomData:
    """Tests for CensusHousingLoader with custom injected data."""

    def test_custom_home_values(self) -> None:
        """Custom home values override defaults."""
        custom = {("12345", 2020): 999_999.0}
        loader = CensusHousingLoader(home_values=custom)
        assert loader.get_median_home_value("12345", 2020) == 999_999.0
        assert loader.get_median_home_value("26163", 2015) is None  # Default gone

    def test_custom_gross_rent(self) -> None:
        """Custom gross rent overrides defaults."""
        custom = {("12345", 2020): 2000.0}
        loader = CensusHousingLoader(gross_rent=custom)
        assert loader.get_median_gross_rent("12345", 2020) == 2000.0

    def test_custom_construction_index(self) -> None:
        """Custom construction index overrides defaults."""
        custom = {2025: 130.0}
        loader = CensusHousingLoader(construction_index=custom)
        assert loader.get_construction_cost_index(2025) == 130.0
        assert loader.get_construction_cost_index(2018) is None  # Default gone

    def test_empty_data_returns_none(self) -> None:
        """Empty data dicts return None for all lookups."""
        loader = CensusHousingLoader(home_values={}, gross_rent={}, construction_index={})
        assert loader.get_median_home_value("26163", 2020) is None
        assert loader.get_median_gross_rent("26163", 2020) is None
        assert loader.get_construction_cost_index(2020) is None


@pytest.mark.unit
class TestCensusHousingLoaderProtocolCompliance:
    """Tests that CensusHousingLoader satisfies HousingDataSource protocol."""

    def test_has_get_median_home_value(self) -> None:
        """Loader has get_median_home_value method."""
        loader = CensusHousingLoader()
        assert callable(loader.get_median_home_value)

    def test_has_get_median_gross_rent(self) -> None:
        """Loader has get_median_gross_rent method."""
        loader = CensusHousingLoader()
        assert callable(loader.get_median_gross_rent)

    def test_has_get_construction_cost_index(self) -> None:
        """Loader has get_construction_cost_index method."""
        loader = CensusHousingLoader()
        assert callable(loader.get_construction_cost_index)

    def test_satisfies_protocol_structurally(self) -> None:
        """CensusHousingLoader is structurally compatible with HousingDataSource.

        Uses static type annotation assignment (same pattern as conftest.py)
        to verify structural protocol compliance without runtime_checkable.
        """
        from babylon.economics.rent.data_sources import HousingDataSource

        # Static protocol check via type annotation assignment
        source: HousingDataSource = CensusHousingLoader()
        assert source.get_median_home_value("26163", 2015) is not None


@pytest.mark.unit
class TestCensusHousingLoaderDataConsistency:
    """Tests for data consistency in default values."""

    def test_wayne_home_values_increase_over_time(self) -> None:
        """Wayne County home values increase from 2015 to 2022."""
        loader = CensusHousingLoader()
        val_2015 = loader.get_median_home_value("26163", 2015)
        val_2022 = loader.get_median_home_value("26163", 2022)
        assert val_2015 is not None
        assert val_2022 is not None
        assert val_2022 > val_2015

    def test_oakland_more_expensive_than_wayne(self) -> None:
        """Oakland County has higher home values than Wayne County."""
        loader = CensusHousingLoader()
        wayne = loader.get_median_home_value("26163", 2020)
        oakland = loader.get_median_home_value("26125", 2020)
        assert wayne is not None
        assert oakland is not None
        assert oakland > wayne

    def test_oakland_rent_higher_than_wayne(self) -> None:
        """Oakland County has higher gross rent than Wayne County."""
        loader = CensusHousingLoader()
        wayne = loader.get_median_gross_rent("26163", 2020)
        oakland = loader.get_median_gross_rent("26125", 2020)
        assert wayne is not None
        assert oakland is not None
        assert oakland > wayne
