"""Unit tests for GeographicHierarchyLoader.

Tests allocation weight calculation, normalization, and hierarchy loading
with mocked database sessions.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from babylon.data.geography.loader import GeographicHierarchyLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.normalize.schema import DimGeographicHierarchy

if TYPE_CHECKING:
    pass


@pytest.mark.unit
class TestGeographicHierarchyLoaderInit:
    """Tests for loader initialization."""

    def test_init_with_default_config(self) -> None:
        """Loader initializes with default LoaderConfig."""
        loader = GeographicHierarchyLoader()
        assert loader.config is not None
        assert loader.config.census_year == 2022

    def test_init_with_custom_config(self) -> None:
        """Loader accepts custom LoaderConfig."""
        config = LoaderConfig(census_year=2021)
        loader = GeographicHierarchyLoader(config)
        assert loader.config.census_year == 2021


@pytest.mark.unit
class TestGeographicHierarchyLoaderTables:
    """Tests for table declarations."""

    def test_get_dimension_tables_returns_hierarchy(self) -> None:
        """get_dimension_tables returns DimGeographicHierarchy."""
        loader = GeographicHierarchyLoader()
        tables = loader.get_dimension_tables()
        assert DimGeographicHierarchy in tables

    def test_get_fact_tables_returns_empty(self) -> None:
        """get_fact_tables returns empty list (no facts)."""
        loader = GeographicHierarchyLoader()
        tables = loader.get_fact_tables()
        assert tables == []


@pytest.mark.unit
class TestWeightNormalization:
    """Tests for weight normalization logic."""

    def test_normalize_weights_sums_to_one(self) -> None:
        """Normalized weights sum to 1.0 for a state."""
        loader = GeographicHierarchyLoader()
        raw_weights = {
            "06001": Decimal("100"),
            "06002": Decimal("200"),
            "06003": Decimal("300"),
        }
        county_fips = ["06001", "06002", "06003"]

        normalized = loader._normalize_weights(raw_weights, county_fips)

        total = sum(normalized.values())
        assert total == pytest.approx(Decimal("1"), abs=Decimal("0.0000001"))

    def test_normalize_weights_preserves_ratios(self) -> None:
        """Normalized weights preserve relative ratios."""
        loader = GeographicHierarchyLoader()
        raw_weights = {
            "06001": Decimal("100"),
            "06002": Decimal("200"),
        }
        county_fips = ["06001", "06002"]

        normalized = loader._normalize_weights(raw_weights, county_fips)

        # 200 is twice 100, so ratio should be 2:1
        ratio = normalized["06002"] / normalized["06001"]
        assert ratio == pytest.approx(Decimal("2"), abs=Decimal("0.0001"))

    def test_normalize_weights_handles_missing_data(self) -> None:
        """Missing county data gets zero weight."""
        loader = GeographicHierarchyLoader()
        raw_weights = {
            "06001": Decimal("100"),
            # 06002 is missing
        }
        county_fips = ["06001", "06002"]

        normalized = loader._normalize_weights(raw_weights, county_fips)

        assert normalized["06001"] == Decimal("1")  # All weight goes to 06001
        assert normalized["06002"] == Decimal("0")

    def test_normalize_weights_equal_distribution_when_no_data(self) -> None:
        """Equal distribution when no raw weight data exists."""
        loader = GeographicHierarchyLoader()
        raw_weights: dict[str, Decimal] = {}  # No data at all
        county_fips = ["06001", "06002", "06003"]

        normalized = loader._normalize_weights(raw_weights, county_fips)

        # Each county should get 1/3
        expected = Decimal("1") / Decimal("3")
        for fips in county_fips:
            assert normalized[fips] == pytest.approx(expected, abs=Decimal("0.0001"))


@pytest.mark.unit
class TestStateMappingExtraction:
    """Tests for state-county mapping extraction."""

    def test_get_state_county_mapping_groups_by_state(self) -> None:
        """State-county mapping groups counties by state_id."""
        loader = GeographicHierarchyLoader()

        # Mock session with sample data
        mock_session = MagicMock()
        mock_rows = [
            MagicMock(state_id=1, county_id=101, fips="01001"),
            MagicMock(state_id=1, county_id=102, fips="01002"),
            MagicMock(state_id=2, county_id=201, fips="02001"),
        ]
        mock_session.execute.return_value = mock_rows

        result = loader._get_state_county_mapping(mock_session)

        assert 1 in result
        assert 2 in result
        assert len(result[1]) == 2  # Two counties in state 1
        assert len(result[2]) == 1  # One county in state 2


@pytest.mark.unit
class TestLoadStatsReporting:
    """Tests for LoadStats reporting."""

    def test_load_stats_reports_source(self) -> None:
        """LoadStats reports 'geography' as source."""
        loader = GeographicHierarchyLoader()

        # Create a mock session that will return empty data
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        mock_session.query.return_value.filter.return_value.delete.return_value = 0

        stats = loader.load(mock_session, verbose=False)

        assert stats.source == "geography"

    def test_load_stats_reports_error_when_no_data(self) -> None:
        """LoadStats reports error when no state-county data found."""
        loader = GeographicHierarchyLoader()

        mock_session = MagicMock()
        mock_session.execute.return_value = []
        mock_session.query.return_value.filter.return_value.delete.return_value = 0

        stats = loader.load(mock_session, verbose=False)

        assert stats.has_errors
        assert "No state-county data found" in stats.errors[0]


@pytest.mark.unit
class TestWeightConstraints:
    """Tests for weight constraint validation."""

    def test_population_weight_in_valid_range(self) -> None:
        """Normalized population weights are between 0 and 1."""
        loader = GeographicHierarchyLoader()
        raw_weights = {
            "06001": Decimal("500000"),
            "06002": Decimal("1500000"),
            "06003": Decimal("3000000"),
        }
        county_fips = ["06001", "06002", "06003"]

        normalized = loader._normalize_weights(raw_weights, county_fips)

        for weight in normalized.values():
            assert Decimal("0") <= weight <= Decimal("1")

    def test_employment_weight_in_valid_range(self) -> None:
        """Normalized employment weights are between 0 and 1."""
        loader = GeographicHierarchyLoader()
        raw_weights = {
            "06001": Decimal("10000"),
            "06002": Decimal("50000"),
        }
        county_fips = ["06001", "06002"]

        normalized = loader._normalize_weights(raw_weights, county_fips)

        for weight in normalized.values():
            assert Decimal("0") <= weight <= Decimal("1")


@pytest.mark.unit
class TestHierarchyRecordCreation:
    """Tests for hierarchy record creation."""

    def test_hierarchy_record_has_required_fields(self) -> None:
        """DimGeographicHierarchy can be instantiated with required fields."""
        hierarchy = DimGeographicHierarchy(
            state_id=1,
            county_id=101,
            population_weight=Decimal("0.25"),
            employment_weight=Decimal("0.30"),
            source_year=2022,
        )

        assert hierarchy.state_id == 1
        assert hierarchy.county_id == 101
        assert hierarchy.population_weight == Decimal("0.25")
        assert hierarchy.employment_weight == Decimal("0.30")
        assert hierarchy.source_year == 2022
        assert hierarchy.gdp_weight is None


@pytest.mark.unit
class TestConfigIntegration:
    """Tests for LoaderConfig integration."""

    def test_uses_census_year_from_config(self) -> None:
        """Loader uses census_year from config for source_year."""
        config = LoaderConfig(census_year=2020)
        loader = GeographicHierarchyLoader(config)

        # Verify config is accessible
        assert loader.config.census_year == 2020
