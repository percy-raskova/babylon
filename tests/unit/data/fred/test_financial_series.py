"""Tests for Volume III financial series in NATIONAL_SERIES (Feature 024, T070).

Verifies that the FRED NATIONAL_SERIES dict contains all series required
for Capital Volume III credit dynamics and fictitious capital modules.
"""

from __future__ import annotations

import pytest

from babylon.data.fred.api_client import NATIONAL_SERIES

# All Volume III series that must be present
VOLUME_III_SERIES: dict[str, str] = {
    "FEDFUNDS": "Federal Funds Effective Rate",
    "DGS10": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity",
    "BAA10Y": "Moody's Seasoned Baa Corporate Bond Yield Relative to Yield on 10-Year Treasury",
    "TCMDO": "All Sectors; Credit Market Instruments; Liability, Level",
    "WILL5000PR": "Wilshire 5000 Total Market Full Cap Index",
    "GFDEBTN": "Federal Debt: Total Public Debt",
    "B230RC0Q173SBEA": "Rental Income of Persons with Capital Consumption Adjustment",
    "A054RC1Q027SBEA": "Taxes on Corporate Income",
}


@pytest.mark.unit
class TestVolumeIIIFinancialSeries:
    """Tests for Volume III financial series in NATIONAL_SERIES."""

    @pytest.mark.parametrize(
        ("series_id", "description"),
        list(VOLUME_III_SERIES.items()),
        ids=list(VOLUME_III_SERIES.keys()),
    )
    def test_series_present_in_national_series(self, series_id: str, description: str) -> None:
        """Each Volume III series is present in NATIONAL_SERIES."""
        assert series_id in NATIONAL_SERIES, (
            f"{series_id} ({description}) missing from NATIONAL_SERIES"
        )

    def test_national_series_values_are_strings(self) -> None:
        """All NATIONAL_SERIES values are description strings."""
        for series_id, desc in NATIONAL_SERIES.items():
            assert isinstance(desc, str), f"{series_id} has non-string value: {desc!r}"
            assert len(desc) > 0, f"{series_id} has empty description"

    def test_fedfunds_description(self) -> None:
        """FEDFUNDS has expected description."""
        assert NATIONAL_SERIES["FEDFUNDS"] == "Federal Funds Effective Rate"

    def test_dgs10_description(self) -> None:
        """DGS10 has expected description."""
        assert "10-Year" in NATIONAL_SERIES["DGS10"]

    def test_baa10y_description(self) -> None:
        """BAA10Y has expected description."""
        assert "Baa" in NATIONAL_SERIES["BAA10Y"]

    def test_tcmdo_description(self) -> None:
        """TCMDO has expected description."""
        assert "Credit Market" in NATIONAL_SERIES["TCMDO"]

    def test_will5000pr_description(self) -> None:
        """WILL5000PR has expected description."""
        assert "Wilshire" in NATIONAL_SERIES["WILL5000PR"]

    def test_gfdebtn_already_existed(self) -> None:
        """GFDEBTN was already in NATIONAL_SERIES (pre-existing)."""
        assert "GFDEBTN" in NATIONAL_SERIES
        assert "Debt" in NATIONAL_SERIES["GFDEBTN"]
