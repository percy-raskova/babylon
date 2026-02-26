"""Unit tests for BEA I-O XLSX loader.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (loader is implemented)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from babylon.data.bea.io_loader import BEAIOLoader, IOMatrixParser

# =============================================================================
# IOMatrixParser tests (unit, no SQLite)
# =============================================================================


class TestIOMatrixParser:
    """Tests for the raw XLSX parsing logic."""

    def test_parse_yields_industry_codes(self) -> None:
        """Parser extracts industry codes from row 6."""
        parser = IOMatrixParser()
        # Construct a minimal sheet-like dict
        rows = [
            ("Title", None, None, None),  # row 1
            ("(Millions)", None, None, None),  # row 2
            ("BEA", None, None, None),  # row 3
            ("2021", None, None, None),  # row 4
            (None, None, None, None),  # row 5
            (None, "Commodities/Industries", "111CA", "113FF"),  # row 6: codes
            ("IOCode", "Name", "Farms", "Forestry"),  # row 7: names
            ("111CA", "Farms", 1000, "..."),  # row 8: data
            ("113FF", "Forestry", "...", 500),  # row 9: data
        ]
        industries, matrix = parser.parse_rows(rows)
        assert "111CA" in industries
        assert "113FF" in industries

    def test_missing_data_marker_becomes_zero(self) -> None:
        """'...' missing data markers are converted to 0.0."""
        parser = IOMatrixParser()
        rows = [
            ("Title", None, None, None),
            ("(Millions)", None, None, None),
            ("BEA", None, None, None),
            ("2021", None, None, None),
            (None, None, None, None),
            (None, "Commodities/Industries", "111CA", "113FF"),
            ("IOCode", "Name", "Farms", "Forestry"),
            ("111CA", "Farms", 1000, "..."),  # "..." becomes 0.0
            ("113FF", "Forestry", "...", 500),
        ]
        industries, matrix = parser.parse_rows(rows)
        # 111CA to 113FF should be 0.0 (was "...")
        idx_111ca = industries.index("111CA")
        idx_113ff = industries.index("113FF")
        assert matrix[idx_111ca, idx_113ff] == pytest.approx(0.0)

    def test_direct_requirements_normalized_by_output(self) -> None:
        """Use table values are divided by column total to get coefficients."""
        parser = IOMatrixParser()
        # Simple 2x2: output of 111CA=2000, 113FF=1000
        rows = [
            ("Title", None, None, None),
            ("(Millions)", None, None, None),
            ("BEA", None, None, None),
            ("2021", None, None, None),
            (None, None, None, None),
            (None, "Commodities/Industries", "111CA", "113FF"),
            ("IOCode", "Name", "Farms", "Forestry"),
            ("111CA", "Farms", 400, 100),
            ("113FF", "Forestry", 200, 200),
            # Total output row (IOCode="T001" by BEA convention)
            ("T001", "Total Intermediate", 600, 300),
            # Value added
            ("V001", "Value added", 1400, 700),
            # Total gross output
            ("T019", "Total industry output", 2000, 1000),
        ]
        industries, matrix = parser.parse_rows(rows)
        # A[111CA, 111CA] = 400/2000 = 0.2
        idx = industries.index("111CA")
        assert matrix[idx, idx] == pytest.approx(0.2, rel=1e-6)

    def test_output_row_codes_excluded_from_industry_list(self) -> None:
        """Total output / value added rows (T001, V001, T019) are excluded."""
        parser = IOMatrixParser()
        rows = [
            ("Title", None, None, None),
            ("(Millions)", None, None, None),
            ("BEA", None, None, None),
            ("2021", None, None, None),
            (None, None, None, None),
            (None, "Commodities/Industries", "111CA", "113FF"),
            ("IOCode", "Name", "Farms", "Forestry"),
            ("111CA", "Farms", 400, 100),
            ("113FF", "Forestry", 200, 200),
            ("T019", "Total industry output", 2000, 1000),
        ]
        industries, matrix = parser.parse_rows(rows)
        assert "T019" not in industries
        assert "V001" not in industries

    def test_empty_rows_skipped(self) -> None:
        """None/empty rows after data are safely ignored."""
        parser = IOMatrixParser()
        rows = [
            ("Title", None, None, None),
            ("(Millions)", None, None, None),
            ("BEA", None, None, None),
            ("2021", None, None, None),
            (None, None, None, None),
            (None, "Commodities/Industries", "111CA", "113FF"),
            ("IOCode", "Name", "Farms", "Forestry"),
            ("111CA", "Farms", 400, 100),
            (None, None, None, None),  # trailing empty row
        ]
        industries, matrix = parser.parse_rows(rows)
        assert "111CA" in industries


# =============================================================================
# BEAIOLoader tests (unit, SQLite fixtures)
# =============================================================================


class TestBEAIOLoaderInit:
    """Tests for loader initialization."""

    def test_default_config(self) -> None:
        """Loader creates default config when none provided."""
        loader = BEAIOLoader()
        assert loader.config is not None

    def test_custom_data_dir(self, tmp_path: Path) -> None:
        """Loader respects custom data dir."""
        loader = BEAIOLoader(data_dir=tmp_path)
        assert loader.data_dir == tmp_path

    def test_get_dimension_tables(self) -> None:
        """Returns DimBEAIOTableType and DimBEAIndustry."""
        loader = BEAIOLoader()
        tables = loader.get_dimension_tables()
        names = [t.__tablename__ for t in tables]
        assert "dim_bea_io_table_type" in names

    def test_get_fact_tables(self) -> None:
        """Returns FactBEAIOCoefficient."""
        loader = BEAIOLoader()
        tables = loader.get_fact_tables()
        names = [t.__tablename__ for t in tables]
        assert "fact_bea_io_coefficient" in names


class TestBEAIOLoaderMissingDir:
    """Tests for graceful handling of missing data directory."""

    def test_missing_xlsx_returns_zero_stats(self, tmp_path: Path) -> None:
        """Loader returns empty stats when XLSX not found."""
        loader = BEAIOLoader(data_dir=tmp_path)
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None

        stats = loader.load(session, reset=False, verbose=False)
        assert stats.files_processed == 0
        assert stats.has_errors or stats.total_facts == 0


class TestBEAIOLoaderRealFile:
    """Integration-style tests using real BEA XLSX files (if present)."""

    XLSX_PATH = Path("data/input-output/make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx")

    @pytest.mark.skipif(
        not XLSX_PATH.exists(),
        reason="BEA I-O XLSX not available",
    )
    def test_parse_real_summary_xlsx(self) -> None:
        """Can parse real BEA Summary Use table."""
        parser = IOMatrixParser()
        import openpyxl

        wb = openpyxl.load_workbook(self.XLSX_PATH, read_only=True, data_only=True)
        ws = wb["2021"]
        rows = [tuple(cell for cell in row) for row in ws.iter_rows(values_only=True)]
        industries, matrix = parser.parse_rows(rows)
        wb.close()

        assert len(industries) >= 10  # summary level has ~71 industries
        assert matrix.shape[0] == len(industries)
        assert matrix.shape[1] == len(industries)
        # Direct requirements should be nearly non-negative; real BEA data may have
        # tiny negative values in a few cells due to subsidies on products.
        assert float(matrix.min()) >= -0.01
        # Diagonal should be small non-negative fractions (direct self-use)
        assert float(matrix.max()) < 1.0
