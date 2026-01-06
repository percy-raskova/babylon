"""Unit tests for QCEW API client.

Tests HTTP interaction, rate limiting, error handling, and CSV parsing
using mocked responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from babylon.data.qcew.api_client import (
    QcewAPIClient,
    QcewAPIError,
    _safe_float,
    _safe_int,
    get_state_area_code,
)

# Sample CSV response for testing
SAMPLE_CSV = """area_fips,own_code,industry_code,agglvl_code,size_code,year,qtr,disclosure_code,annual_avg_estabs,annual_avg_emplvl,total_annual_wages,taxable_annual_wages,annual_contributions,annual_avg_wkly_wage,avg_annual_pay,lq_disclosure_code,lq_annual_avg_estabs,lq_annual_avg_emplvl,lq_total_annual_wages,lq_taxable_annual_wages,lq_annual_contributions,lq_annual_avg_wkly_wage,lq_avg_annual_pay,oty_disclosure_code,oty_annual_avg_estabs_chg,oty_annual_avg_estabs_pct_chg,oty_annual_avg_emplvl_chg,oty_annual_avg_emplvl_pct_chg,oty_total_annual_wages_chg,oty_total_annual_wages_pct_chg,oty_taxable_annual_wages_chg,oty_taxable_annual_wages_pct_chg,oty_annual_contributions_chg,oty_annual_contributions_pct_chg,oty_annual_avg_wkly_wage_chg,oty_annual_avg_wkly_wage_pct_chg,oty_avg_annual_pay_chg,oty_avg_annual_pay_pct_chg
01001,5,10,78,0,2023,A,,1234,5678,123456789.00,100000000.00,1234567.00,456,23456,N,1.23,0.89,1.05,1.02,0.95,1.01,1.03,,10,0.8,50,0.9,1234567.00,1.0,1000000.00,1.0,12345.00,1.0,5,1.1,500,2.2
"""


class TestQcewAPIClient:
    """Tests for QcewAPIClient class."""

    def test_context_manager(self) -> None:
        """Client works as context manager."""
        with QcewAPIClient() as client:
            assert client._client is not None
        # Client should be closed after context

    @patch.object(httpx.Client, "get")
    def test_get_area_annual_data_success(self, mock_get: MagicMock) -> None:
        """Successfully fetches and parses area data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_CSV
        mock_get.return_value = mock_response

        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, "01001"))

        assert len(records) == 1
        record = records[0]
        assert record.area_fips == "01001"
        assert record.industry_code == "10"
        assert record.annual_avg_estabs == 1234
        assert record.annual_avg_emplvl == 5678
        assert record.avg_annual_pay == 23456

    @patch.object(httpx.Client, "get")
    def test_get_area_annual_data_404(self, mock_get: MagicMock) -> None:
        """Handles 404 for missing area/year combination."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with QcewAPIClient() as client, pytest.raises(QcewAPIError) as exc_info:
            list(client.get_area_annual_data(2023, "99999"))

        assert exc_info.value.status_code == 404

    @patch.object(httpx.Client, "get")
    def test_retry_on_rate_limit(self, mock_get: MagicMock) -> None:
        """Retries on 429 rate limit response."""
        mock_rate_limited = MagicMock()
        mock_rate_limited.status_code = 429

        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.text = SAMPLE_CSV

        mock_get.side_effect = [mock_rate_limited, mock_success]

        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, "01001"))

        assert len(records) == 1
        assert mock_get.call_count == 2

    @patch.object(httpx.Client, "get")
    def test_server_error_raises(self, mock_get: MagicMock) -> None:
        """Server errors raise QcewAPIError after retries."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with QcewAPIClient() as client, pytest.raises(QcewAPIError) as exc_info:
            list(client.get_area_annual_data(2023, "01001"))

        assert exc_info.value.status_code == 500

    @patch.object(httpx.Client, "get")
    def test_network_error_retries(self, mock_get: MagicMock) -> None:
        """Network errors retry then raise QcewAPIError."""
        mock_get.side_effect = httpx.RequestError("Network unreachable")

        with QcewAPIClient() as client, pytest.raises(QcewAPIError) as exc_info:
            list(client.get_area_annual_data(2023, "01001"))

        assert exc_info.value.status_code == 0
        assert "Max retries exceeded" in exc_info.value.message

    @patch.object(httpx.Client, "get")
    def test_get_industry_annual_data(self, mock_get: MagicMock) -> None:
        """Successfully fetches industry data with NAICS code conversion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_CSV
        mock_get.return_value = mock_response

        with QcewAPIClient() as client:
            records = list(client.get_industry_annual_data(2023, "31-33"))

        assert len(records) == 1
        # Verify URL conversion from hyphens to underscores
        call_args = mock_get.call_args
        assert "31_33" in call_args[0][0]

    @patch.object(httpx.Client, "get")
    def test_parses_all_fields(self, mock_get: MagicMock) -> None:
        """Parses all fields from CSV including LQ and OTY."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_CSV
        mock_get.return_value = mock_response

        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, "01001"))

        record = records[0]

        # Core metrics
        assert record.total_annual_wages == 123456789.00
        assert record.taxable_annual_wages == 100000000.00
        assert record.annual_contributions == 1234567.00
        assert record.annual_avg_wkly_wage == 456

        # Location quotients
        assert record.lq_annual_avg_estabs == 1.23
        assert record.lq_annual_avg_emplvl == 0.89
        assert record.lq_total_annual_wages == 1.05

        # Year-over-year changes
        assert record.oty_annual_avg_estabs_chg == 10
        assert record.oty_annual_avg_estabs_pct_chg == 0.8
        assert record.oty_annual_avg_emplvl_chg == 50
        assert record.oty_annual_avg_wkly_wage_chg == 5

    @patch.object(httpx.Client, "get")
    def test_parses_multiple_rows(self, mock_get: MagicMock) -> None:
        """Parses multiple rows from CSV."""
        multi_row_csv = """area_fips,own_code,industry_code,agglvl_code,size_code,year,qtr,disclosure_code,annual_avg_estabs,annual_avg_emplvl,total_annual_wages,taxable_annual_wages,annual_contributions,annual_avg_wkly_wage,avg_annual_pay,lq_disclosure_code,lq_annual_avg_estabs,lq_annual_avg_emplvl,lq_total_annual_wages,lq_taxable_annual_wages,lq_annual_contributions,lq_annual_avg_wkly_wage,lq_avg_annual_pay,oty_disclosure_code,oty_annual_avg_estabs_chg,oty_annual_avg_estabs_pct_chg,oty_annual_avg_emplvl_chg,oty_annual_avg_emplvl_pct_chg,oty_total_annual_wages_chg,oty_total_annual_wages_pct_chg,oty_taxable_annual_wages_chg,oty_taxable_annual_wages_pct_chg,oty_annual_contributions_chg,oty_annual_contributions_pct_chg,oty_annual_avg_wkly_wage_chg,oty_annual_avg_wkly_wage_pct_chg,oty_avg_annual_pay_chg,oty_avg_annual_pay_pct_chg
01001,5,10,78,0,2023,A,,1000,2000,3000,4000,5000,600,7000,N,1.0,1.0,1.0,1.0,1.0,1.0,1.0,,0,0,0,0,0,0,0,0,0,0,0,0,0,0
01001,5,11,78,0,2023,A,,2000,3000,4000,5000,6000,700,8000,N,1.0,1.0,1.0,1.0,1.0,1.0,1.0,,0,0,0,0,0,0,0,0,0,0,0,0,0,0
01001,5,12,78,0,2023,A,,3000,4000,5000,6000,7000,800,9000,N,1.0,1.0,1.0,1.0,1.0,1.0,1.0,,0,0,0,0,0,0,0,0,0,0,0,0,0,0
"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = multi_row_csv
        mock_get.return_value = mock_response

        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, "01001"))

        assert len(records) == 3
        assert records[0].industry_code == "10"
        assert records[1].industry_code == "11"
        assert records[2].industry_code == "12"


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_safe_int_valid(self) -> None:
        """Converts valid integers."""
        assert _safe_int("123") == 123
        assert _safe_int("0") == 0
        assert _safe_int("-456") == -456

    def test_safe_int_invalid(self) -> None:
        """Returns None for invalid integers."""
        assert _safe_int("") is None
        assert _safe_int("  ") is None
        assert _safe_int("abc") is None
        assert _safe_int("12.34") is None

    def test_safe_float_valid(self) -> None:
        """Converts valid floats."""
        assert _safe_float("123.45") == 123.45
        assert _safe_float("0.0") == 0.0
        assert _safe_float("-456.78") == -456.78

    def test_safe_float_invalid(self) -> None:
        """Returns None for invalid floats."""
        assert _safe_float("") is None
        assert _safe_float("  ") is None
        assert _safe_float("abc") is None

    def test_get_state_area_code(self) -> None:
        """Converts state FIPS to area code."""
        assert get_state_area_code("01") == "01000"
        assert get_state_area_code("06") == "06000"
        assert get_state_area_code("56") == "56000"


class TestQcewAPIErrorDataclass:
    """Tests for QcewAPIError dataclass."""

    def test_error_is_exception(self) -> None:
        """QcewAPIError is an Exception."""
        error = QcewAPIError(status_code=404, message="Not found", url="http://test")
        assert isinstance(error, Exception)

    def test_error_attributes(self) -> None:
        """QcewAPIError stores attributes correctly."""
        error = QcewAPIError(status_code=500, message="Server error", url="http://example.com")
        assert error.status_code == 500
        assert error.message == "Server error"
        assert error.url == "http://example.com"
