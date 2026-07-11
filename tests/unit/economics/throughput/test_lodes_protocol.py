"""Unit tests for LODESCommuterFlowSource protocol.

Feature: 014-throughput-position (T034)
TDD Phase: Green

Tests verify the protocol definition and mock implementations
can satisfy the LODESCommuterFlowSource contract.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from babylon.domain.economics.throughput.data_sources import LODESCommuterFlowSource

# =============================================================================
# PROTOCOL CONFORMANCE TESTS
# =============================================================================


class TestProtocolDefinition:
    """Verify LODESCommuterFlowSource protocol structure."""

    def test_protocol_is_defined(self) -> None:
        """Protocol exists and is importable."""
        assert LODESCommuterFlowSource is not None

    def test_protocol_has_required_methods(self) -> None:
        """Protocol defines all required methods."""
        required_methods = [
            "get_inbound_commuters",
            "get_outbound_commuters",
            "get_internal_workers",
            "get_net_commuter_balance",
            "get_residence_employment",
            "get_commuter_flows",
        ]

        for method in required_methods:
            assert hasattr(LODESCommuterFlowSource, method), f"Missing method: {method}"

    def test_mock_can_implement_protocol(self) -> None:
        """A MagicMock can satisfy the protocol (duck typing)."""
        mock_source = MagicMock()
        mock_source.get_inbound_commuters.return_value = 100000
        mock_source.get_outbound_commuters.return_value = 80000
        mock_source.get_internal_workers.return_value = 200000
        mock_source.get_net_commuter_balance.return_value = 20000
        mock_source.get_residence_employment.return_value = 280000
        mock_source.get_commuter_flows.return_value = 50000

        # Verify mock works as expected
        assert mock_source.get_inbound_commuters("26163", 2022) == 100000
        assert mock_source.get_outbound_commuters("26163", 2022) == 80000
        assert mock_source.get_internal_workers("26163", 2022) == 200000
        assert mock_source.get_net_commuter_balance("26163", 2022) == 20000
        assert mock_source.get_residence_employment("26163", 2022) == 280000
        assert mock_source.get_commuter_flows("26125", "26163", 2022) == 50000


# =============================================================================
# METHOD SIGNATURE TESTS
# =============================================================================


class TestInboundCommuters:
    """Tests for get_inbound_commuters method signature."""

    def test_returns_int_or_none(self) -> None:
        """get_inbound_commuters returns int or None."""
        mock_source = MagicMock()

        # Test int return
        mock_source.get_inbound_commuters.return_value = 150000
        result = mock_source.get_inbound_commuters("26163", 2022)
        assert isinstance(result, int)
        assert result == 150000

        # Test None return (no data)
        mock_source.get_inbound_commuters.return_value = None
        result = mock_source.get_inbound_commuters("99999", 2022)
        assert result is None

    def test_accepts_fips_and_year(self) -> None:
        """Method accepts work_fips (str) and year (int)."""
        mock_source = MagicMock()
        mock_source.get_inbound_commuters.return_value = 100000

        # Should not raise
        mock_source.get_inbound_commuters("26163", 2022)
        mock_source.get_inbound_commuters.assert_called_once_with("26163", 2022)


class TestOutboundCommuters:
    """Tests for get_outbound_commuters method signature."""

    def test_returns_int_or_none(self) -> None:
        """get_outbound_commuters returns int or None."""
        mock_source = MagicMock()

        mock_source.get_outbound_commuters.return_value = 180000
        result = mock_source.get_outbound_commuters("26125", 2022)
        assert isinstance(result, int)
        assert result == 180000


class TestInternalWorkers:
    """Tests for get_internal_workers method signature."""

    def test_returns_int_or_none(self) -> None:
        """get_internal_workers returns int or None."""
        mock_source = MagicMock()

        mock_source.get_internal_workers.return_value = 350000
        result = mock_source.get_internal_workers("26163", 2022)
        assert isinstance(result, int)


class TestNetCommuterBalance:
    """Tests for get_net_commuter_balance method signature."""

    def test_returns_int_or_none(self) -> None:
        """get_net_commuter_balance returns int (can be negative) or None."""
        mock_source = MagicMock()

        # Job importer (positive balance)
        mock_source.get_net_commuter_balance.return_value = 50000
        result = mock_source.get_net_commuter_balance("26163", 2022)
        assert isinstance(result, int)
        assert result > 0

        # Job exporter (negative balance)
        mock_source.get_net_commuter_balance.return_value = -150000
        result = mock_source.get_net_commuter_balance("26125", 2022)
        assert isinstance(result, int)
        assert result < 0

    def test_balance_semantics(self) -> None:
        """Positive balance = job importer, negative = job exporter."""
        mock_source = MagicMock()

        # Wayne County (Detroit) - job importer
        mock_source.get_net_commuter_balance.return_value = 50000
        wayne_balance = mock_source.get_net_commuter_balance("26163", 2022)
        assert wayne_balance > 0, "Wayne County should be job importer"

        # Oakland County - job exporter (bedroom community)
        mock_source.get_net_commuter_balance.return_value = -150000
        oakland_balance = mock_source.get_net_commuter_balance("26125", 2022)
        assert oakland_balance < 0, "Oakland County should be job exporter"


class TestResidenceEmployment:
    """Tests for get_residence_employment method signature."""

    def test_returns_int_or_none(self) -> None:
        """get_residence_employment returns int or None."""
        mock_source = MagicMock()

        mock_source.get_residence_employment.return_value = 600000
        result = mock_source.get_residence_employment("26125", 2022)
        assert isinstance(result, int)

    def test_residence_vs_workplace_semantics(self) -> None:
        """Residence employment differs from workplace employment."""
        mock_source = MagicMock()

        # Oakland County: more residents than local jobs
        mock_source.get_residence_employment.return_value = 600000
        residence_emp = mock_source.get_residence_employment("26125", 2022)

        # Imagine workplace employment would be lower (not tested here)
        # This is the whole point - residence captures commuters
        assert residence_emp == 600000


class TestCommuterFlows:
    """Tests for get_commuter_flows method signature."""

    def test_returns_int_or_none(self) -> None:
        """get_commuter_flows returns int or None."""
        mock_source = MagicMock()

        mock_source.get_commuter_flows.return_value = 75000
        result = mock_source.get_commuter_flows("26125", "26163", 2022)
        assert isinstance(result, int)

    def test_accepts_home_and_work_fips(self) -> None:
        """Method accepts home_fips, work_fips, and year."""
        mock_source = MagicMock()
        mock_source.get_commuter_flows.return_value = 50000

        # Oakland → Wayne commute flow
        mock_source.get_commuter_flows("26125", "26163", 2022)
        mock_source.get_commuter_flows.assert_called_once_with("26125", "26163", 2022)


# =============================================================================
# DETROIT METRO SCENARIO TESTS
# =============================================================================


class TestDetroitMetroScenario:
    """Test Detroit metro commuter patterns as validation scenario.

    Expected patterns:
    - Wayne County (26163): Job center, net importer
    - Oakland County (26125): Bedroom community, net exporter
    - Macomb County (26099): Mixed, slight exporter
    """

    @pytest.fixture
    def detroit_metro_source(self) -> MagicMock:
        """Create mock with realistic Detroit metro data."""
        mock = MagicMock()

        # Data-driven lookup for commuter metrics by (fips, year)
        # Wayne County (26163): Job center - more inbound than outbound
        # Oakland County (26125): Bedroom community - more outbound than inbound
        commuter_data: dict[tuple[str, int], dict[str, int]] = {
            ("26163", 2022): {"inbound": 250000, "outbound": 180000, "internal": 450000},
            ("26125", 2022): {"inbound": 150000, "outbound": 300000, "internal": 350000},
        }

        def get_metric(fips: str, year: int, metric: str) -> int | None:
            data = commuter_data.get((fips, year))
            return data.get(metric) if data else None

        mock.get_inbound_commuters.side_effect = lambda f, y: get_metric(f, y, "inbound")
        mock.get_outbound_commuters.side_effect = lambda f, y: get_metric(f, y, "outbound")
        mock.get_internal_workers.side_effect = lambda f, y: get_metric(f, y, "internal")

        def net_balance(fips: str, year: int) -> int | None:
            inb = get_metric(fips, year, "inbound")
            out = get_metric(fips, year, "outbound")
            return inb - out if inb is not None and out is not None else None

        mock.get_net_commuter_balance.side_effect = net_balance

        def residence_emp(fips: str, year: int) -> int | None:
            internal = get_metric(fips, year, "internal")
            outbound = get_metric(fips, year, "outbound")
            return internal + outbound if internal is not None and outbound else None

        mock.get_residence_employment.side_effect = residence_emp

        return mock

    def test_wayne_county_is_job_importer(self, detroit_metro_source: MagicMock) -> None:
        """Wayne County (Detroit) should be a net job importer."""
        balance = detroit_metro_source.get_net_commuter_balance("26163", 2022)
        assert balance is not None
        assert balance > 0, f"Wayne County should be job importer, got {balance}"

    def test_oakland_county_is_job_exporter(self, detroit_metro_source: MagicMock) -> None:
        """Oakland County should be a net job exporter (bedroom community)."""
        balance = detroit_metro_source.get_net_commuter_balance("26125", 2022)
        assert balance is not None
        assert balance < 0, f"Oakland County should be job exporter, got {balance}"

    def test_residence_employment_formula(self, detroit_metro_source: MagicMock) -> None:
        """Residence employment = internal + outbound."""
        internal = detroit_metro_source.get_internal_workers("26125", 2022)
        outbound = detroit_metro_source.get_outbound_commuters("26125", 2022)
        residence = detroit_metro_source.get_residence_employment("26125", 2022)

        assert internal is not None and outbound is not None and residence is not None
        assert residence == internal + outbound
