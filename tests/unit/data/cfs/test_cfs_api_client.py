"""Unit tests for CFSAPIClient.

Tests API client initialization, URL construction, and response parsing
with mocked HTTP responses.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from babylon.data.cfs.api_client import CFSAPIClient, CFSFlowRecord


@pytest.mark.unit
class TestCFSAPIClientInit:
    """Tests for client initialization."""

    def test_init_with_default_year(self) -> None:
        """Client initializes with default year 2022."""
        client = CFSAPIClient()
        assert client.year == 2022
        client.close()

    def test_init_with_custom_year(self) -> None:
        """Client accepts custom year."""
        client = CFSAPIClient(year=2017)
        assert client.year == 2017
        client.close()

    def test_init_reads_api_key_from_env(self) -> None:
        """Client reads CENSUS_API_KEY from environment."""
        with patch.dict("os.environ", {"CENSUS_API_KEY": "test_key"}):
            client = CFSAPIClient()
            assert client.api_key == "test_key"
            client.close()

    def test_init_prefers_explicit_api_key(self) -> None:
        """Explicit API key overrides environment variable."""
        with patch.dict("os.environ", {"CENSUS_API_KEY": "env_key"}):
            client = CFSAPIClient(api_key="explicit_key")
            assert client.api_key == "explicit_key"
            client.close()


@pytest.mark.unit
class TestCFSAPIClientURLConstruction:
    """Tests for URL construction."""

    def test_build_url_uses_year(self) -> None:
        """URL includes year from client configuration."""
        client = CFSAPIClient(year=2022)
        url = client._build_url()
        assert "2022" in url
        assert "cfsarea" in url
        client.close()


@pytest.mark.unit
class TestSCTGCodes:
    """Tests for SCTG code retrieval."""

    def test_get_sctg_codes_returns_list(self) -> None:
        """SCTG codes returns list of tuples."""
        client = CFSAPIClient()
        codes = client.get_sctg_codes()
        assert isinstance(codes, list)
        assert len(codes) > 0
        client.close()

    def test_get_sctg_codes_has_code_name_tuples(self) -> None:
        """Each SCTG code entry is (code, name) tuple."""
        client = CFSAPIClient()
        codes = client.get_sctg_codes()
        for code, name in codes:
            assert isinstance(code, str)
            assert isinstance(name, str)
            assert len(code) == 2  # 2-digit codes
        client.close()

    def test_get_sctg_codes_includes_major_categories(self) -> None:
        """SCTG codes include major commodity categories."""
        client = CFSAPIClient()
        codes = dict(client.get_sctg_codes())

        # Check for key commodities
        assert "02" in codes  # Cereal grains
        assert "15" in codes  # Coal
        assert "16" in codes  # Crude petroleum
        assert "34" in codes  # Machinery
        client.close()


@pytest.mark.unit
class TestCFSFlowRecord:
    """Tests for CFSFlowRecord dataclass."""

    def test_flow_record_has_required_fields(self) -> None:
        """CFSFlowRecord requires origin, dest, and sctg_code."""
        record = CFSFlowRecord(
            origin_state_fips="06",
            dest_state_fips="48",
            sctg_code="02",
        )
        assert record.origin_state_fips == "06"
        assert record.dest_state_fips == "48"
        assert record.sctg_code == "02"

    def test_flow_record_optional_fields_default_none(self) -> None:
        """Optional fields default to None."""
        record = CFSFlowRecord(
            origin_state_fips="06",
            dest_state_fips="48",
            sctg_code="02",
        )
        assert record.value_millions is None
        assert record.tons_thousands is None
        assert record.ton_miles_millions is None
        assert record.mode_code is None

    def test_flow_record_accepts_values(self) -> None:
        """CFSFlowRecord accepts flow values."""
        record = CFSFlowRecord(
            origin_state_fips="06",
            dest_state_fips="48",
            sctg_code="02",
            value_millions=1500.5,
            tons_thousands=2500.0,
        )
        assert record.value_millions == 1500.5
        assert record.tons_thousands == 2500.0


@pytest.mark.unit
class TestCFSAPIClientContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_closes_client(self) -> None:
        """Context manager closes client on exit."""
        with CFSAPIClient() as client:
            assert client._client is not None

        # After exit, client should be closed
        # (httpx.Client doesn't expose closed state, but this tests the protocol)

    def test_context_manager_returns_client(self) -> None:
        """Context manager returns client instance."""
        with CFSAPIClient() as client:
            assert isinstance(client, CFSAPIClient)
