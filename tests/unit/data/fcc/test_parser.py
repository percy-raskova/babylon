"""Unit tests for FCC BDC CSV parser.

Tests parsing logic for FCC Broadband Data Collection summary CSV files.
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from babylon.data.fcc.parser import (
    FCCBroadbandRecord,
    _extract_state_from_desc,
    _parse_fcc_csv_stream,
    count_counties_by_state,
    parse_fcc_summary_csv,
)


@pytest.mark.unit
class TestFCCBroadbandRecord:
    """Tests for FCCBroadbandRecord dataclass."""

    def test_record_has_required_fields(self) -> None:
        """FCCBroadbandRecord has all expected fields."""
        record = FCCBroadbandRecord(
            county_fips="06001",
            county_name="Alameda County",
            state_name="CA",
            total_units=500000,
            pct_25_3=Decimal("0.95"),
            pct_100_20=Decimal("0.85"),
            pct_1000_100=Decimal("0.45"),
        )
        assert record.county_fips == "06001"
        assert record.county_name == "Alameda County"
        assert record.state_name == "CA"
        assert record.total_units == 500000
        assert record.pct_25_3 == Decimal("0.95")
        assert record.pct_100_20 == Decimal("0.85")
        assert record.pct_1000_100 == Decimal("0.45")

    def test_record_is_frozen(self) -> None:
        """FCCBroadbandRecord is immutable."""
        record = FCCBroadbandRecord(
            county_fips="06001",
            county_name="Alameda County",
            state_name="CA",
            total_units=500000,
            pct_25_3=Decimal("0.95"),
            pct_100_20=Decimal("0.85"),
            pct_1000_100=Decimal("0.45"),
        )
        with pytest.raises(AttributeError):
            record.county_fips = "06002"  # type: ignore[misc]


@pytest.mark.unit
class TestExtractStateFromDesc:
    """Tests for state extraction from geography description."""

    def test_extracts_state_from_county_desc(self) -> None:
        """Extracts state from 'County, ST' format."""
        assert _extract_state_from_desc("Alameda County, CA") == "CA"
        assert _extract_state_from_desc("Harris County, TX") == "TX"

    def test_handles_multi_word_county_names(self) -> None:
        """Handles county names with multiple words."""
        assert _extract_state_from_desc("San Francisco County, CA") == "CA"
        assert _extract_state_from_desc("New York County, NY") == "NY"

    def test_returns_empty_for_missing_comma(self) -> None:
        """Returns empty string if no comma-space separator."""
        assert _extract_state_from_desc("Alameda County CA") == ""
        assert _extract_state_from_desc("Unknown") == ""


@pytest.mark.unit
class TestParseFccCsvStream:
    """Tests for FCC CSV stream parsing."""

    def test_parses_valid_csv(self) -> None:
        """Parses valid CSV into records."""
        csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Any Technology,0.95,0.85,0.45
Total,County,06037,Los Angeles County,"Los Angeles County, CA",3500000,R,Any Technology,0.92,0.82,0.40
"""
        stream = StringIO(csv_content)
        records = list(
            _parse_fcc_csv_stream(
                stream,
                area_data_type="Total",
                geography_type="County",
                biz_res="R",
                technology="Any Technology",
            )
        )

        assert len(records) == 2
        assert records[0].county_fips == "06001"
        assert records[0].pct_25_3 == Decimal("0.95")
        assert records[1].county_fips == "06037"

    def test_filters_by_area_data_type(self) -> None:
        """Filters records by area_data_type."""
        csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Any Technology,0.95,0.85,0.45
Urban,County,06001,Alameda County,"Alameda County, CA",400000,R,Any Technology,0.98,0.90,0.55
"""
        stream = StringIO(csv_content)
        records = list(
            _parse_fcc_csv_stream(
                stream,
                area_data_type="Urban",
                geography_type="County",
                biz_res="R",
                technology="Any Technology",
            )
        )

        assert len(records) == 1
        assert records[0].pct_25_3 == Decimal("0.98")

    def test_filters_by_geography_type(self) -> None:
        """Filters records by geography_type."""
        csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Any Technology,0.95,0.85,0.45
Total,State,06,California,California,10000000,R,Any Technology,0.93,0.83,0.43
"""
        stream = StringIO(csv_content)
        records = list(
            _parse_fcc_csv_stream(
                stream,
                area_data_type="Total",
                geography_type="County",
                biz_res="R",
                technology="Any Technology",
            )
        )

        assert len(records) == 1
        assert records[0].county_fips == "06001"

    def test_filters_by_biz_res(self) -> None:
        """Filters records by business/residential flag."""
        csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Any Technology,0.95,0.85,0.45
Total,County,06001,Alameda County,"Alameda County, CA",50000,B,Any Technology,0.99,0.95,0.70
"""
        stream = StringIO(csv_content)
        records = list(
            _parse_fcc_csv_stream(
                stream,
                area_data_type="Total",
                geography_type="County",
                biz_res="B",
                technology="Any Technology",
            )
        )

        assert len(records) == 1
        assert records[0].total_units == 50000

    def test_filters_by_technology(self) -> None:
        """Filters records by technology type."""
        csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Any Technology,0.95,0.85,0.45
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Fiber,0.55,0.55,0.50
"""
        stream = StringIO(csv_content)
        records = list(
            _parse_fcc_csv_stream(
                stream,
                area_data_type="Total",
                geography_type="County",
                biz_res="R",
                technology="Fiber",
            )
        )

        assert len(records) == 1
        assert records[0].pct_25_3 == Decimal("0.55")

    def test_raises_for_missing_columns(self) -> None:
        """Raises KeyError for missing required columns."""
        csv_content = """area_data_type,geography_type,geography_id
Total,County,06001
"""
        stream = StringIO(csv_content)
        with pytest.raises(KeyError, match="Missing required columns"):
            list(
                _parse_fcc_csv_stream(
                    stream,
                    area_data_type="Total",
                    geography_type="County",
                    biz_res="R",
                    technology="Any Technology",
                )
            )

    def test_returns_empty_for_empty_csv(self) -> None:
        """Returns empty iterator for CSV with only headers."""
        csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
"""
        stream = StringIO(csv_content)
        records = list(
            _parse_fcc_csv_stream(
                stream,
                area_data_type="Total",
                geography_type="County",
                biz_res="R",
                technology="Any Technology",
            )
        )
        assert records == []


@pytest.mark.unit
class TestParseFccSummaryCsv:
    """Tests for file-based FCC CSV parsing."""

    def test_parses_file(self) -> None:
        """Parses CSV file from disk."""
        csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Any Technology,0.95,0.85,0.45
"""
        with TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "summary.csv"
            csv_path.write_text(csv_content)

            records = list(parse_fcc_summary_csv(csv_path))

        assert len(records) == 1
        assert records[0].county_fips == "06001"

    def test_raises_for_missing_file(self) -> None:
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            list(parse_fcc_summary_csv(Path("/nonexistent/file.csv")))


@pytest.mark.unit
class TestCountCountiesByState:
    """Tests for state county counting utility."""

    def test_counts_counties_per_state(self) -> None:
        """Counts counties grouped by state."""
        csv_content = """area_data_type,geography_type,geography_id,geography_desc,geography_desc_full,total_units,biz_res,technology,speed_25_3,speed_100_20,speed_1000_100
Total,County,06001,Alameda County,"Alameda County, CA",500000,R,Any Technology,0.95,0.85,0.45
Total,County,06037,Los Angeles County,"Los Angeles County, CA",3500000,R,Any Technology,0.92,0.82,0.40
Total,County,48201,Harris County,"Harris County, TX",1500000,R,Any Technology,0.90,0.80,0.35
"""
        with TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "summary.csv"
            csv_path.write_text(csv_content)

            counts = count_counties_by_state(csv_path)

        assert counts["CA"] == 2
        assert counts["TX"] == 1
