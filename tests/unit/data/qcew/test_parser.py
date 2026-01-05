"""Unit tests for QCEW CSV parser.

Tests parsing logic for BLS QCEW employment and wage data.
"""

from __future__ import annotations

import pytest

from babylon.data.qcew.parser import (
    QcewRecord,
    determine_area_type,
    determine_naics_level,
    extract_state_fips,
    safe_float,
    safe_int,
)


@pytest.mark.unit
class TestSafeInt:
    """Tests for safe integer conversion."""

    def test_converts_valid_integer(self) -> None:
        """Converts valid integer strings."""
        assert safe_int("12345") == 12345

    def test_returns_none_for_empty(self) -> None:
        """Returns None for empty string."""
        assert safe_int("") is None
        assert safe_int("   ") is None

    def test_returns_none_for_invalid(self) -> None:
        """Returns None for non-numeric strings."""
        assert safe_int("invalid") is None
        assert safe_int("N/A") is None


@pytest.mark.unit
class TestSafeFloat:
    """Tests for safe float conversion."""

    def test_converts_valid_float(self) -> None:
        """Converts valid float strings."""
        assert safe_float("123.45") == 123.45

    def test_converts_integer_string(self) -> None:
        """Converts integer strings to float."""
        result = safe_float("12345")
        assert result == 12345.0
        assert isinstance(result, float)

    def test_returns_none_for_empty(self) -> None:
        """Returns None for empty string."""
        assert safe_float("") is None
        assert safe_float("   ") is None

    def test_returns_none_for_invalid(self) -> None:
        """Returns None for non-numeric strings."""
        assert safe_float("invalid") is None


@pytest.mark.unit
class TestDetermineAreaType:
    """Tests for area type determination from aggregation level code."""

    def test_national_level(self) -> None:
        """agglvl_code 10-18 is national."""
        assert determine_area_type(10, "US000") == "national"
        assert determine_area_type(15, "US000") == "national"
        assert determine_area_type(18, "US000") == "national"

    def test_state_level(self) -> None:
        """State-level FIPS (XX000) with agglvl 20-39."""
        assert determine_area_type(20, "06000") == "state"
        assert determine_area_type(25, "48000") == "state"

    def test_msa_level(self) -> None:
        """MSA-level areas with agglvl 30-69."""
        assert determine_area_type(35, "31080") == "msa"
        assert determine_area_type(50, "31100") == "msa"

    def test_csa_level(self) -> None:
        """CSA areas start with 'CS'."""
        assert determine_area_type(30, "CS488") == "csa"

    def test_county_level(self) -> None:
        """agglvl_code 70+ is county."""
        assert determine_area_type(70, "01001") == "county"
        assert determine_area_type(78, "06037") == "county"


@pytest.mark.unit
class TestDetermineNAICSLevel:
    """Tests for NAICS hierarchy level determination."""

    def test_total_all_industries(self) -> None:
        """Code '10' is total (level 0)."""
        assert determine_naics_level("10") == 0

    def test_domain_codes(self) -> None:
        """Codes 101, 102 are domain level."""
        assert determine_naics_level("101") == 98
        assert determine_naics_level("102") == 98

    def test_supersector_codes(self) -> None:
        """Four-digit codes starting with 10 are supersectors."""
        assert determine_naics_level("1011") == 99
        assert determine_naics_level("1029") == 99

    def test_sector_with_range(self) -> None:
        """Sector codes with ranges like '31-33'."""
        assert determine_naics_level("31-33") == 2
        assert determine_naics_level("44-45") == 2

    def test_standard_naics_levels(self) -> None:
        """Standard NAICS codes by length."""
        assert determine_naics_level("23") == 2  # 2-digit = sector
        assert determine_naics_level("236") == 3  # 3-digit = subsector
        assert determine_naics_level("2361") == 4  # 4-digit = industry group
        assert determine_naics_level("23611") == 5  # 5-digit = industry
        assert determine_naics_level("236115") == 6  # 6-digit = national industry


@pytest.mark.unit
class TestExtractStateFips:
    """Tests for state FIPS extraction."""

    def test_extracts_from_county_fips(self) -> None:
        """Extracts state FIPS from 5-digit county FIPS."""
        assert extract_state_fips("01001") == "01"  # Alabama
        assert extract_state_fips("06037") == "06"  # California
        assert extract_state_fips("48201") == "48"  # Texas

    def test_extracts_from_state_fips(self) -> None:
        """Extracts state FIPS from state-level code."""
        assert extract_state_fips("06000") == "06"

    def test_returns_none_for_csa(self) -> None:
        """Returns None for CSA codes."""
        assert extract_state_fips("CS488") is None

    def test_returns_none_for_national(self) -> None:
        """Returns None for national codes."""
        assert extract_state_fips("US000") is None


@pytest.mark.unit
class TestQcewRecord:
    """Tests for QcewRecord dataclass."""

    def test_record_has_required_fields(self) -> None:
        """QcewRecord has all expected fields."""
        record = QcewRecord(
            area_fips="01001",
            area_title="Autauga County, Alabama",
            agglvl_code=70,
            industry_code="10",
            industry_title="Total, All Industries",
            own_code="0",
            own_title="Total Covered",
            year=2023,
            establishments=1234,
            employment=15678,
            total_wages=650000000.0,
            avg_weekly_wage=800,
            avg_annual_pay=41500,
            lq_employment=0.95,
            lq_avg_annual_pay=0.88,
            oty_employment_chg=100,
            oty_employment_pct=0.6,
            disclosure_code="",
        )

        assert record.area_fips == "01001"
        assert record.year == 2023
        assert record.employment == 15678
        assert record.total_wages == 650000000.0

    def test_record_handles_none_values(self) -> None:
        """QcewRecord accepts None for optional numeric fields."""
        record = QcewRecord(
            area_fips="01001",
            area_title="Test",
            agglvl_code=70,
            industry_code="10",
            industry_title="Test",
            own_code="0",
            own_title="Test",
            year=2023,
            establishments=None,
            employment=None,
            total_wages=None,
            avg_weekly_wage=None,
            avg_annual_pay=None,
            lq_employment=None,
            lq_avg_annual_pay=None,
            oty_employment_chg=None,
            oty_employment_pct=None,
            disclosure_code="N",
        )

        assert record.establishments is None
        assert record.employment is None
        assert record.total_wages is None


@pytest.mark.unit
class TestQcewRecordWithFixture:
    """Tests using shared QCEW fixtures."""

    def test_parse_fixture_row(self, sample_qcew_row: dict[str, str]) -> None:
        """Creates record from fixture data."""
        record = QcewRecord(
            area_fips=sample_qcew_row["area_fips"],
            area_title=sample_qcew_row["area_title"],
            agglvl_code=int(sample_qcew_row["agglvl_code"]),
            industry_code=sample_qcew_row["industry_code"],
            industry_title=sample_qcew_row["industry_title"],
            own_code=sample_qcew_row["own_code"],
            own_title=sample_qcew_row["own_title"],
            year=int(sample_qcew_row["year"]),
            establishments=safe_int(sample_qcew_row["annual_avg_estabs_count"]),
            employment=safe_int(sample_qcew_row["annual_avg_emplvl"]),
            total_wages=safe_float(sample_qcew_row["total_annual_wages"]),
            avg_weekly_wage=safe_int(sample_qcew_row["annual_avg_wkly_wage"]),
            avg_annual_pay=safe_int(sample_qcew_row["avg_annual_pay"]),
            lq_employment=safe_float(sample_qcew_row["lq_annual_avg_emplvl"]),
            lq_avg_annual_pay=safe_float(sample_qcew_row["lq_avg_annual_pay"]),
            oty_employment_chg=safe_int(sample_qcew_row["oty_annual_avg_emplvl_chg"]),
            oty_employment_pct=safe_float(sample_qcew_row["oty_annual_avg_emplvl_pct_chg"]),
            disclosure_code=sample_qcew_row["disclosure_code"],
        )

        assert record.area_fips == "01001"
        assert record.area_title == "Autauga County, Alabama"
        assert record.employment == 15678
