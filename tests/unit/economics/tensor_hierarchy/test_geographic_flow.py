"""Unit tests for GeographicFlowSource, ImperialRentComputer, and GeographicAggregator.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (implementation is complete)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.tensor_hierarchy.geographic_flow import (
    DefaultGeographicAggregator,
    DefaultGeographicFlowSource,
    DefaultImperialRentComputer,
)
from babylon.domain.economics.tensor_hierarchy.types import (
    GeographicFlow,
    ImperialRentField,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_flow(
    year: int = 2017,
    areas: list[str] | None = None,
    matrix: list[list[float]] | None = None,
) -> GeographicFlow:
    """Build a synthetic GeographicFlow for testing.

    Args:
        year: Flow year.
        areas: CFS area codes. Defaults to ["11", "12", "119"].
        matrix: Flow matrix as nested list. Defaults to zeros.

    Returns:
        GeographicFlow with the specified data.
    """
    if areas is None:
        areas = ["11", "12", "119"]
    n = len(areas)
    if matrix is None:
        matrix_arr = np.zeros((n, n), dtype=np.float64)
    else:
        matrix_arr = np.array(matrix, dtype=np.float64)
    return GeographicFlow(year=year, areas=areas, flow_matrix=matrix_arr)


# =============================================================================
# DefaultImperialRentComputer tests
# =============================================================================


class TestDefaultImperialRentComputer:
    """Tests for DefaultImperialRentComputer."""

    @pytest.fixture()
    def computer(self) -> DefaultImperialRentComputer:
        """Provide a DefaultImperialRentComputer instance."""
        return DefaultImperialRentComputer()

    def test_compute_rent_returns_imperial_rent_field(
        self, computer: DefaultImperialRentComputer
    ) -> None:
        """compute_rent returns ImperialRentField for a valid flow."""
        flow = _make_flow()
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)

    def test_phi_shape_matches_areas(self, computer: DefaultImperialRentComputer) -> None:
        """phi vector length equals number of CFS areas."""
        flow = _make_flow(areas=["11", "12", "119"])
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)
        assert result.phi.shape == (3,)

    def test_year_preserved(self, computer: DefaultImperialRentComputer) -> None:
        """ImperialRentField preserves year from source GeographicFlow."""
        flow = _make_flow(year=2022)
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)
        assert result.year == 2022

    def test_areas_preserved(self, computer: DefaultImperialRentComputer) -> None:
        """ImperialRentField preserves area codes from source GeographicFlow."""
        flow = _make_flow(areas=["11", "119"])
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)
        assert result.areas == ["11", "119"]

    @pytest.mark.math
    def test_phi_sums_near_zero(self, computer: DefaultImperialRentComputer) -> None:
        """phi.sum() == 0 (value conservation: all inflows = all outflows)."""
        flow = _make_flow(
            areas=["11", "12"],
            matrix=[[0.0, 200.0], [50.0, 0.0]],
        )
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)
        assert float(result.phi.sum()) == pytest.approx(0.0, abs=1e-9)

    @pytest.mark.math
    def test_positive_phi_for_net_importer(self, computer: DefaultImperialRentComputer) -> None:
        """Area receiving more than it sends has positive phi."""
        # "11" sends 200 to "12"; "12" sends 50 to "11"
        # phi["11"] = inflow(50) - outflow(200) = -150
        # phi["12"] = inflow(200) - outflow(50) = +150
        flow = _make_flow(
            areas=["11", "12"],
            matrix=[[0.0, 200.0], [50.0, 0.0]],
        )
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)
        assert result.phi[1] > 0.0  # area "12" is net importer

    @pytest.mark.math
    def test_negative_phi_for_net_exporter(self, computer: DefaultImperialRentComputer) -> None:
        """Area sending more than it receives has negative phi."""
        flow = _make_flow(
            areas=["11", "12"],
            matrix=[[0.0, 200.0], [50.0, 0.0]],
        )
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)
        assert result.phi[0] < 0.0  # area "11" is net exporter

    @pytest.mark.math
    def test_zero_phi_for_symmetric_flow(self, computer: DefaultImperialRentComputer) -> None:
        """Perfectly symmetric flow (F == F.T) gives all-zero phi."""
        flow = _make_flow(
            areas=["11", "12"],
            matrix=[[100.0, 200.0], [200.0, 100.0]],
        )
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)
        np.testing.assert_allclose(result.phi, 0.0, atol=1e-9)

    @pytest.mark.math
    def test_zero_flow_gives_zero_phi(self, computer: DefaultImperialRentComputer) -> None:
        """All-zero flow matrix gives all-zero phi."""
        flow = _make_flow(areas=["11", "12"], matrix=[[0.0, 0.0], [0.0, 0.0]])
        result = computer.compute_rent(flow)
        assert isinstance(result, ImperialRentField)
        np.testing.assert_allclose(result.phi, 0.0, atol=1e-9)


# =============================================================================
# DefaultGeographicAggregator tests
# =============================================================================


class TestDefaultGeographicAggregator:
    """Tests for DefaultGeographicAggregator."""

    @pytest.fixture()
    def aggregator(self) -> DefaultGeographicAggregator:
        """Provide a DefaultGeographicAggregator instance."""
        return DefaultGeographicAggregator()

    @pytest.fixture()
    def two_area_flow(self) -> GeographicFlow:
        """2-area flow with non-trivial matrix."""
        return _make_flow(
            areas=["11", "12"],
            matrix=[[100.0, 200.0], [50.0, 150.0]],
        )

    def test_aggregate_returns_geographic_flow(
        self, aggregator: DefaultGeographicAggregator, two_area_flow: GeographicFlow
    ) -> None:
        """aggregate returns GeographicFlow."""
        mapping = {"11": "MA", "12": "NY"}
        result = aggregator.aggregate(two_area_flow, mapping)
        assert isinstance(result, GeographicFlow)

    def test_aggregated_areas_are_target_values(
        self, aggregator: DefaultGeographicAggregator, two_area_flow: GeographicFlow
    ) -> None:
        """Aggregated flow areas contain state codes from mapping."""
        mapping = {"11": "MA", "12": "NY"}
        result = aggregator.aggregate(two_area_flow, mapping)
        assert isinstance(result, GeographicFlow)
        assert set(result.areas) == {"MA", "NY"}

    def test_year_preserved(
        self, aggregator: DefaultGeographicAggregator, two_area_flow: GeographicFlow
    ) -> None:
        """Aggregated flow preserves source year."""
        mapping = {"11": "MA", "12": "NY"}
        result = aggregator.aggregate(two_area_flow, mapping)
        assert isinstance(result, GeographicFlow)
        assert result.year == two_area_flow.year

    @pytest.mark.math
    def test_total_flow_preserved_two_to_two(
        self, aggregator: DefaultGeographicAggregator, two_area_flow: GeographicFlow
    ) -> None:
        """Total flow value is preserved when mapping to two different states."""
        mapping = {"11": "MA", "12": "NY"}
        result = aggregator.aggregate(two_area_flow, mapping)
        assert isinstance(result, GeographicFlow)
        original_total = float(two_area_flow.flow_matrix.sum())
        aggregated_total = float(result.flow_matrix.sum())
        assert aggregated_total == pytest.approx(original_total, rel=1e-9)

    @pytest.mark.math
    def test_total_flow_preserved_two_to_one(
        self, aggregator: DefaultGeographicAggregator, two_area_flow: GeographicFlow
    ) -> None:
        """Total flow is preserved when both areas map to same state."""
        mapping = {"11": "MA", "12": "MA"}
        result = aggregator.aggregate(two_area_flow, mapping)
        assert isinstance(result, GeographicFlow)
        original_total = float(two_area_flow.flow_matrix.sum())
        aggregated_total = float(result.flow_matrix.sum())
        assert aggregated_total == pytest.approx(original_total, rel=1e-9)

    def test_unmapped_areas_excluded(self, aggregator: DefaultGeographicAggregator) -> None:
        """Areas without a mapping are dropped from aggregated flow."""
        flow = _make_flow(
            areas=["11", "12", "999"],
            matrix=[
                [100.0, 200.0, 50.0],
                [50.0, 150.0, 30.0],
                [10.0, 20.0, 5.0],
            ],
        )
        mapping = {"11": "MA", "12": "NY"}  # "999" is not mapped
        result = aggregator.aggregate(flow, mapping)
        assert isinstance(result, GeographicFlow)
        assert "999" not in result.areas

    @pytest.mark.math
    def test_aggregated_matrix_shape(
        self, aggregator: DefaultGeographicAggregator, two_area_flow: GeographicFlow
    ) -> None:
        """Aggregated matrix shape equals (n_targets, n_targets)."""
        mapping = {"11": "MA", "12": "NY"}
        result = aggregator.aggregate(two_area_flow, mapping)
        assert isinstance(result, GeographicFlow)
        n = len(result.areas)
        assert result.flow_matrix.shape == (n, n)


# =============================================================================
# DefaultGeographicFlowSource sentinel tests
# =============================================================================


class TestDefaultGeographicFlowSourceSentinel:
    """Tests for DefaultGeographicFlowSource sentinel handling.

    Full DB integration tests belong in tests/integration/.
    These unit tests verify the NoDataSentinel return path.
    """

    @pytest.fixture()
    def mock_source(self) -> DefaultGeographicFlowSource:
        """DefaultGeographicFlowSource backed by a session that returns no data."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        # No flow records for any year
        mock_session.query.return_value.filter.return_value.all.return_value = []
        session_factory = MagicMock(return_value=mock_session)
        return DefaultGeographicFlowSource(session_factory=session_factory)

    def test_get_flow_sentinel_for_empty_year(
        self, mock_source: DefaultGeographicFlowSource
    ) -> None:
        """get_flow returns NoDataSentinel when no flow records exist."""
        result = mock_source.get_flow(1990)
        assert isinstance(result, NoDataSentinel)

    def test_sentinel_year_matches_request(self, mock_source: DefaultGeographicFlowSource) -> None:
        """NoDataSentinel year matches the requested year."""
        result = mock_source.get_flow(1990)
        assert isinstance(result, NoDataSentinel)
        assert result.year == 1990
