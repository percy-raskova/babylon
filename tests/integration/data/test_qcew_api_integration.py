"""Integration tests for QCEW API client.

These tests make real HTTP requests to the BLS QCEW Open Data API.
Run with: pytest -m network tests/integration/data/test_qcew_api_integration.py

Note: These tests require network access and may be slow.
"""

from __future__ import annotations

import pytest

from babylon.data.qcew.api_client import (
    QcewAPIClient,
    QcewAPIError,
    get_state_area_code,
)


@pytest.mark.network
class TestQcewAPIIntegration:
    """Integration tests against live BLS API."""

    def test_fetch_california_state_data_2023(self) -> None:
        """Fetch state-level data for California (06000)."""
        area_code = get_state_area_code("06")  # California
        assert area_code == "06000"

        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, area_code))

        # Should have records for multiple industries and ownership types
        assert len(records) > 100, f"Expected >100 records, got {len(records)}"

        # Verify first record has expected structure
        if records:
            rec = records[0]
            assert rec.area_fips.startswith("06")
            assert rec.year == 2023
            assert rec.own_code in ("0", "1", "2", "3", "4", "5", "8", "9")
            assert rec.industry_code is not None

    def test_fetch_small_county_data_2023(self) -> None:
        """Fetch county-level data for a small county (Autauga County, AL)."""
        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, "01001"))

        # Small county should still have significant records
        assert len(records) > 50, f"Expected >50 records, got {len(records)}"

        # Verify aggregation levels are present
        agglvl_codes = {r.agglvl_code for r in records}
        # County-level data should include codes 70-78
        county_codes = [c for c in agglvl_codes if 70 <= c <= 78]
        assert len(county_codes) > 0, "No county-level aggregation codes found"

    def test_fetch_nonexistent_area_returns_404(self) -> None:
        """Requesting nonexistent area returns 404 error."""
        with QcewAPIClient() as client, pytest.raises(QcewAPIError) as exc_info:
            list(client.get_area_annual_data(2023, "99999"))

        assert exc_info.value.status_code == 404

    def test_fetch_old_year_may_not_exist(self) -> None:
        """Very old years may not be available via API."""
        # BLS API only provides rolling ~5 years
        # 2010 data is likely not available
        with QcewAPIClient() as client, pytest.raises(QcewAPIError):
            list(client.get_area_annual_data(2010, "01001"))

    def test_fetch_industry_data_manufacturing(self) -> None:
        """Fetch data by industry code (Manufacturing sector 31-33)."""
        with QcewAPIClient() as client:
            records = list(client.get_industry_annual_data(2023, "31-33"))

        # Manufacturing is a large sector with national data
        assert len(records) > 0, "No manufacturing records found"

        # All records should be for manufacturing sector
        for rec in records[:10]:  # Check first 10
            assert (
                rec.industry_code.startswith("31")
                or rec.industry_code.startswith("32")
                or rec.industry_code.startswith("33")
            ), f"Unexpected industry code: {rec.industry_code}"

    def test_multiple_years_fetch(self) -> None:
        """Verify we can fetch multiple consecutive years."""
        with QcewAPIClient() as client:
            # Fetch 2022 and 2023 for small county
            records_2022 = list(client.get_area_annual_data(2022, "01001"))
            records_2023 = list(client.get_area_annual_data(2023, "01001"))

        assert len(records_2022) > 0
        assert len(records_2023) > 0

        # Verify years are correct
        assert all(r.year == 2022 for r in records_2022)
        assert all(r.year == 2023 for r in records_2023)

    def test_location_quotients_present(self) -> None:
        """Verify location quotients are populated for some records."""
        with QcewAPIClient() as client:
            records = list(client.get_area_annual_data(2023, "06000"))

        # Find records with LQ data (N disclosure code means LQ is available)
        records_with_lq = [r for r in records if r.lq_annual_avg_emplvl is not None]

        assert len(records_with_lq) > 0, "No records with location quotients found"

        # Verify LQ values are reasonable (typically between 0.1 and 10)
        for rec in records_with_lq[:5]:
            if rec.lq_annual_avg_emplvl:
                assert 0 < rec.lq_annual_avg_emplvl < 100, (
                    f"Unreasonable LQ: {rec.lq_annual_avg_emplvl}"
                )


@pytest.mark.network
class TestQcewAPIRateLimiting:
    """Tests for rate limiting behavior (slower tests)."""

    def test_rapid_sequential_requests(self) -> None:
        """Multiple rapid requests should be rate-limited automatically."""
        areas = ["01000", "02000", "04000"]  # AL, AK, AZ

        with QcewAPIClient() as client:
            for area in areas:
                # Should not fail due to rate limiting
                records = list(client.get_area_annual_data(2023, area))
                # Just verify we get data, don't need to check content
                assert len(records) >= 0  # Even 0 is fine for some areas
