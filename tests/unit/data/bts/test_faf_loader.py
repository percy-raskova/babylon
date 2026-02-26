"""Unit tests for BTS FAF5 CSV loader.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (implementation is complete)
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from babylon.data.bts.faf_loader import FAFCSVParser, FAFLoader

# =============================================================================
# Sample FAF5 CSV fixture
# =============================================================================

_SAMPLE_CSV = """\
dms_orig,dms_dest,sctg2,dms_mode,tons_2017,value_2017,tmiles_2017
11,12,1,1,100.0,500.0,1000.0
12,11,1,1,80.0,400.0,800.0
11,11,2,1,50.0,200.0,100.0
119,11,3,2,,150.0,300.0
"""


# =============================================================================
# FAFCSVParser tests
# =============================================================================


class TestFAFCSVParser:
    """Tests for the raw CSV parsing logic (no SQLite)."""

    @pytest.fixture()
    def parser(self) -> FAFCSVParser:
        """Provide a FAFCSVParser instance."""
        return FAFCSVParser()

    @pytest.fixture()
    def sample_rows(self) -> list[dict[str, str]]:
        """Return sample FAF5 CSV rows as dicts."""
        reader = csv.DictReader(StringIO(_SAMPLE_CSV))
        return list(reader)

    @pytest.fixture()
    def headers(self) -> list[str]:
        """Return sample CSV headers."""
        reader = csv.DictReader(StringIO(_SAMPLE_CSV))
        return list(reader.fieldnames or [])

    def test_extract_year_columns_value(self, parser: FAFCSVParser, headers: list[str]) -> None:
        """extract_year_columns finds value_2017 column."""
        cols = parser.extract_year_columns(headers, 2017)
        assert cols.get("value") == "value_2017"

    def test_extract_year_columns_tons(self, parser: FAFCSVParser, headers: list[str]) -> None:
        """extract_year_columns finds tons_2017 column."""
        cols = parser.extract_year_columns(headers, 2017)
        assert cols.get("tons") == "tons_2017"

    def test_extract_year_columns_tmiles(self, parser: FAFCSVParser, headers: list[str]) -> None:
        """extract_year_columns finds tmiles_2017 column."""
        cols = parser.extract_year_columns(headers, 2017)
        assert cols.get("tmiles") == "tmiles_2017"

    def test_extract_year_columns_missing_year(
        self, parser: FAFCSVParser, headers: list[str]
    ) -> None:
        """extract_year_columns returns empty dict for absent year."""
        cols = parser.extract_year_columns(headers, 1990)
        assert not cols

    def test_parse_row_yields_origin(
        self, parser: FAFCSVParser, sample_rows: list[dict[str, str]]
    ) -> None:
        """parse_row extracts origin CFS code."""
        year_cols = {"value": "value_2017", "tons": "tons_2017"}
        result = parser.parse_row(sample_rows[0], year_cols)
        assert result is not None
        assert result[0] == "11"

    def test_parse_row_yields_dest(
        self, parser: FAFCSVParser, sample_rows: list[dict[str, str]]
    ) -> None:
        """parse_row extracts destination CFS code."""
        year_cols = {"value": "value_2017", "tons": "tons_2017"}
        result = parser.parse_row(sample_rows[0], year_cols)
        assert result is not None
        assert result[1] == "12"

    def test_parse_row_yields_sctg(
        self, parser: FAFCSVParser, sample_rows: list[dict[str, str]]
    ) -> None:
        """parse_row extracts SCTG code as integer."""
        year_cols = {"value": "value_2017", "tons": "tons_2017"}
        result = parser.parse_row(sample_rows[0], year_cols)
        assert result is not None
        assert result[2] == 1

    def test_parse_row_yields_value(
        self, parser: FAFCSVParser, sample_rows: list[dict[str, str]]
    ) -> None:
        """parse_row extracts value column (millions USD)."""
        year_cols = {"value": "value_2017", "tons": "tons_2017"}
        result = parser.parse_row(sample_rows[0], year_cols)
        assert result is not None
        assert result[5] == pytest.approx(500.0)

    def test_parse_row_missing_tons_becomes_zero(
        self, parser: FAFCSVParser, sample_rows: list[dict[str, str]]
    ) -> None:
        """Empty tons cell is converted to 0.0."""
        year_cols = {"value": "value_2017", "tons": "tons_2017"}
        # Row at index 3 (119,11,3,2,,150.0,...) has empty tons
        result = parser.parse_row(sample_rows[3], year_cols)
        assert result is not None
        assert result[4] == pytest.approx(0.0)

    def test_parse_row_invalid_sctg_returns_none(self, parser: FAFCSVParser) -> None:
        """Row with non-integer sctg2 returns None."""
        row = {"dms_orig": "11", "dms_dest": "12", "sctg2": "X", "dms_mode": "1"}
        result = parser.parse_row(row, {})
        assert result is None

    def test_parse_row_empty_origin_returns_none(self, parser: FAFCSVParser) -> None:
        """Row with empty origin CFS code returns None."""
        row = {"dms_orig": "", "dms_dest": "12", "sctg2": "1", "dms_mode": "1"}
        result = parser.parse_row(row, {})
        assert result is None

    def test_parse_row_missing_dest_returns_none(self, parser: FAFCSVParser) -> None:
        """Row with missing destination CFS code returns None."""
        row = {"dms_orig": "11", "dms_dest": "", "sctg2": "1", "dms_mode": "1"}
        result = parser.parse_row(row, {})
        assert result is None


# =============================================================================
# FAFLoader initialization tests
# =============================================================================


class TestFAFLoaderInit:
    """Tests for FAFLoader initialization."""

    def test_default_config(self) -> None:
        """Loader creates default config when none provided."""
        loader = FAFLoader()
        assert loader.config is not None

    def test_custom_data_dir(self, tmp_path: Path) -> None:
        """Loader respects custom data dir."""
        loader = FAFLoader(data_dir=tmp_path)
        assert loader.data_dir == tmp_path

    def test_get_dimension_tables(self) -> None:
        """Returns DimCFSArea and DimSCTGCommodity."""
        loader = FAFLoader()
        tables = loader.get_dimension_tables()
        names = [t.__tablename__ for t in tables]
        assert "dim_cfs_area" in names
        assert "dim_sctg_commodity" in names

    def test_get_fact_tables(self) -> None:
        """Returns FactFAFCommodityFlow."""
        loader = FAFLoader()
        tables = loader.get_fact_tables()
        names = [t.__tablename__ for t in tables]
        assert "fact_faf_commodity_flow" in names


# =============================================================================
# FAFLoader missing data tests
# =============================================================================


class TestFAFLoaderMissingData:
    """Tests for graceful handling of missing data directory."""

    def test_missing_csv_returns_zero_stats(self, tmp_path: Path) -> None:
        """Loader returns empty stats when FAF5 CSV not found."""
        loader = FAFLoader(data_dir=tmp_path)
        session = MagicMock()

        stats = loader.load(session, reset=False, verbose=False)
        assert stats.files_processed == 0
        assert stats.has_errors or stats.total_facts == 0

    def test_missing_csv_adds_error_message(self, tmp_path: Path) -> None:
        """Loader records error message when CSV not found."""
        loader = FAFLoader(data_dir=tmp_path)
        session = MagicMock()

        stats = loader.load(session, reset=False, verbose=False)
        assert len(stats.errors) > 0
