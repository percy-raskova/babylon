"""Unit tests for ingestion preflight checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.data.loader_base import LoaderConfig
from babylon.data.preflight import (
    SCENARIOS,
    PreflightResult,
    ScenarioDataConfig,
    run_preflight,
    run_scenario_preflight,
)


def _find_check(result: PreflightResult, check_id: str):
    return next((check for check in result.checks if check.check_id == check_id), None)


def test_preflight_trade_missing_file_fails(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    result = run_preflight(LoaderConfig(), loaders=["trade"], base_dir=tmp_path)

    check = _find_check(result, "trade:file")
    assert check is not None
    assert check.status == "fail"


def test_preflight_qcew_historical_requires_csvs(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    config = LoaderConfig(qcew_years=[2019])
    result = run_preflight(config, loaders=["qcew"], base_dir=tmp_path)

    check = _find_check(result, "qcew:files")
    assert check is not None
    assert check.status == "fail"


def test_preflight_qcew_historical_accepts_xlsx(tmp_path: Path) -> None:
    data_dir = tmp_path / "data" / "qcew"
    data_dir.mkdir(parents=True)
    (data_dir / "allhlcn19.xlsx").write_text("placeholder", encoding="utf-8")

    config = LoaderConfig(qcew_years=[2019])
    result = run_preflight(config, loaders=["qcew"], base_dir=tmp_path)

    check = _find_check(result, "qcew:files")
    assert check is not None
    assert check.status == "ok"


def test_preflight_qcew_api_years_ok_without_csvs(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    config = LoaderConfig(qcew_years=[2022])
    result = run_preflight(config, loaders=["qcew"], base_dir=tmp_path)

    check = _find_check(result, "qcew:files")
    assert check is not None
    assert check.status == "ok"


def test_preflight_census_cbsa_lfs_pointer_fails(tmp_path: Path) -> None:
    cbsa_dir = tmp_path / "data" / "census"
    cbsa_dir.mkdir(parents=True)
    cbsa_path = cbsa_dir / "cbsa_delineation_2023.xlsx"
    cbsa_path.write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:deadbeef\nsize 1234\n",
        encoding="utf-8",
    )

    result = run_preflight(LoaderConfig(), loaders=["census"], base_dir=tmp_path)
    check = _find_check(result, "census:cbsa_file")
    assert check is not None
    assert check.status == "fail"
    assert check.hint is not None


def test_preflight_fred_api_key_required(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    (tmp_path / "data").mkdir()

    result = run_preflight(LoaderConfig(), loaders=["fred"], base_dir=tmp_path)
    check = _find_check(result, "env:FRED_API_KEY")
    assert check is not None
    assert check.status == "fail"


def test_preflight_materials_accepts_subdir_csv(tmp_path: Path) -> None:
    materials_dir = tmp_path / "data" / "raw_mats" / "commodities"
    materials_dir.mkdir(parents=True)
    (materials_dir / "mcs2025-test_salient.csv").write_text(
        "DataSource,Commodity,Year,USprod_Primary_kt\nMCS2025,Test,2024,1\n",
        encoding="utf-8",
    )

    result = run_preflight(LoaderConfig(), loaders=["materials"], base_dir=tmp_path)
    check = _find_check(result, "materials:files")
    assert check is not None
    assert check.status == "ok"


# =============================================================================
# VerificationProtocol Implementation Tests
# =============================================================================


class TestLodesCrosswalkLoaderVerification:
    """Tests for LodesCrosswalkLoader.check_source_files()."""

    def test_missing_file_reports_failure_with_hint(self, tmp_path: Path) -> None:
        """Story 1, Scenario 1: Missing LODES reports failure with hint."""
        from babylon.data.lodes.loader_3nf import LodesCrosswalkLoader

        (tmp_path / "lodes").mkdir(parents=True)
        loader = LodesCrosswalkLoader()
        checks = loader.check_source_files(tmp_path)

        assert len(checks) == 1
        assert checks[0].status == "fail"
        assert "Missing LODES crosswalk" in checks[0].message
        assert checks[0].hint is not None
        assert "lehd.ces.census.gov" in checks[0].hint

    def test_empty_file_reports_failure(self, tmp_path: Path) -> None:
        """Edge case: Empty file treated as failure."""
        from babylon.data.lodes.loader_3nf import LodesCrosswalkLoader

        lodes_dir = tmp_path / "lodes"
        lodes_dir.mkdir(parents=True)
        (lodes_dir / "us_xwalk.csv").touch()  # Empty file

        loader = LodesCrosswalkLoader()
        checks = loader.check_source_files(tmp_path)

        assert len(checks) == 1
        assert checks[0].status == "fail"
        assert "empty" in checks[0].message.lower()

    def test_valid_file_reports_ok(self, tmp_path: Path) -> None:
        """Valid file passes preflight."""
        from babylon.data.lodes.loader_3nf import LodesCrosswalkLoader

        lodes_dir = tmp_path / "lodes"
        lodes_dir.mkdir(parents=True)
        (lodes_dir / "us_xwalk.csv").write_text("header1,header2\nval1,val2\n")

        loader = LodesCrosswalkLoader()
        checks = loader.check_source_files(tmp_path)

        assert len(checks) == 1
        assert checks[0].status == "ok"


class TestTIGERCountyLoaderVerification:
    """Tests for TIGERCountyLoader.check_source_files()."""

    def test_missing_shapefile_reports_failure_with_hint(self, tmp_path: Path) -> None:
        """Story 1, Scenario 2: Missing TIGER reports failure with hint."""
        from babylon.data.tiger.loader import TIGERCountyLoader

        (tmp_path / "tiger" / "county").mkdir(parents=True)
        loader = TIGERCountyLoader()
        checks = loader.check_source_files(tmp_path)

        assert len(checks) == 1
        assert checks[0].status == "fail"
        assert "Missing TIGER shapefile" in checks[0].message
        assert checks[0].hint is not None
        assert "census.gov" in checks[0].hint

    def test_empty_shapefile_reports_failure(self, tmp_path: Path) -> None:
        """Edge case: Empty shapefile treated as failure."""
        from babylon.data.tiger.loader import TIGERCountyLoader

        shapefile_dir = tmp_path / "tiger" / "county"
        shapefile_dir.mkdir(parents=True)
        (shapefile_dir / "tl_2024_us_county.shp").touch()  # Empty file

        loader = TIGERCountyLoader()
        checks = loader.check_source_files(tmp_path)

        assert len(checks) == 1
        assert checks[0].status == "fail"
        assert "empty" in checks[0].message.lower()

    def test_valid_shapefile_reports_ok(self, tmp_path: Path) -> None:
        """Valid shapefile passes preflight."""
        from babylon.data.tiger.loader import TIGERCountyLoader

        shapefile_dir = tmp_path / "tiger" / "county"
        shapefile_dir.mkdir(parents=True)
        (shapefile_dir / "tl_2024_us_county.shp").write_bytes(b"shapefile content")

        loader = TIGERCountyLoader()
        checks = loader.check_source_files(tmp_path)

        assert len(checks) == 1
        assert checks[0].status == "ok"


class TestCensusLoaderVerification:
    """Tests for CensusLoader.check_source_files()."""

    def test_missing_cbsa_file_reports_failure(self, tmp_path: Path) -> None:
        """Missing CBSA file reports failure."""
        from babylon.data.census.loader_3nf import CensusLoader

        (tmp_path / "census").mkdir(parents=True)
        loader = CensusLoader()
        checks = loader.check_source_files(tmp_path)

        cbsa_check = next((c for c in checks if c.check_id == "census:cbsa_file"), None)
        assert cbsa_check is not None
        assert cbsa_check.status == "fail"
        assert "Missing CBSA" in cbsa_check.message

    def test_lfs_pointer_reports_failure_with_pull_hint(self, tmp_path: Path) -> None:
        """Edge case: Git LFS pointer detected with git lfs pull hint."""
        from babylon.data.census.loader_3nf import CensusLoader

        census_dir = tmp_path / "census"
        census_dir.mkdir(parents=True)
        cbsa_path = census_dir / "cbsa_delineation_2023.xlsx"
        cbsa_path.write_bytes(
            b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123"
        )

        loader = CensusLoader()
        checks = loader.check_source_files(tmp_path)

        cbsa_check = next((c for c in checks if c.check_id == "census:cbsa_file"), None)
        assert cbsa_check is not None
        assert cbsa_check.status == "fail"
        assert "LFS pointer" in cbsa_check.message
        assert cbsa_check.hint is not None
        assert "git lfs pull" in cbsa_check.hint

    def test_missing_api_key_reports_warning(self, tmp_path: Path, monkeypatch) -> None:
        """Story 1, Scenario 5: Missing API key is warning, not failure."""
        from babylon.data.census.loader_3nf import CensusLoader

        monkeypatch.delenv("CENSUS_API_KEY", raising=False)

        census_dir = tmp_path / "census"
        census_dir.mkdir(parents=True)
        cbsa_path = census_dir / "cbsa_delineation_2023.xlsx"
        cbsa_path.write_bytes(b"valid xlsx content that is not an LFS pointer")

        loader = CensusLoader()
        checks = loader.check_source_files(tmp_path)

        api_check = next((c for c in checks if c.check_id == "census:api_key"), None)
        assert api_check is not None
        assert api_check.status == "warn"
        assert "CENSUS_API_KEY" in api_check.message

    def test_valid_cbsa_with_api_key_reports_ok(self, tmp_path: Path, monkeypatch) -> None:
        """Valid CBSA file and API key set passes all checks."""
        from babylon.data.census.loader_3nf import CensusLoader

        monkeypatch.setenv("CENSUS_API_KEY", "test_key")

        census_dir = tmp_path / "census"
        census_dir.mkdir(parents=True)
        cbsa_path = census_dir / "cbsa_delineation_2023.xlsx"
        cbsa_path.write_bytes(b"valid xlsx content that is not an LFS pointer")

        loader = CensusLoader()
        checks = loader.check_source_files(tmp_path)

        cbsa_check = next((c for c in checks if c.check_id == "census:cbsa_file"), None)
        assert cbsa_check is not None
        assert cbsa_check.status == "ok"

        # No API key warning when key is set
        api_check = next((c for c in checks if c.check_id == "census:api_key"), None)
        assert api_check is None


# =============================================================================
# ScenarioDataConfig Tests
# =============================================================================


class TestScenarioDataConfig:
    """Tests for ScenarioDataConfig validation."""

    def test_empty_loaders_raises_value_error(self) -> None:
        """required_loaders cannot be empty."""
        with pytest.raises(ValueError, match="required_loaders cannot be empty"):
            ScenarioDataConfig(
                name="test",
                required_loaders=[],
                county_fips=["26163"],
                year_range=(2010, 2025),
            )

    def test_invalid_year_range_raises_value_error(self) -> None:
        """year_range start must be <= end."""
        with pytest.raises(ValueError, match="year_range start must be <= end"):
            ScenarioDataConfig(
                name="test",
                required_loaders=["census"],
                county_fips=["26163"],
                year_range=(2025, 2010),  # Invalid: start > end
            )

    def test_detroit_config_has_four_sources(self) -> None:
        """Detroit scenario requires all four data sources."""
        detroit = SCENARIOS["detroit"]
        assert len(detroit.required_loaders) == 4
        assert "qcew" in detroit.required_loaders
        assert "lodes" in detroit.required_loaders
        assert "census" in detroit.required_loaders
        assert "tiger" in detroit.required_loaders

    def test_detroit_config_has_three_counties(self) -> None:
        """Detroit scenario covers Wayne, Oakland, Macomb counties."""
        detroit = SCENARIOS["detroit"]
        assert len(detroit.county_fips) == 3
        assert "26163" in detroit.county_fips  # Wayne
        assert "26125" in detroit.county_fips  # Oakland
        assert "26099" in detroit.county_fips  # Macomb


# =============================================================================
# run_scenario_preflight Tests
# =============================================================================


class TestRunScenarioPreflight:
    """Tests for run_scenario_preflight function."""

    def test_unknown_scenario_raises_value_error(self) -> None:
        """Unknown scenario name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown scenario"):
            run_scenario_preflight("nonexistent_scenario")

    def test_detroit_scenario_checks_all_four_sources(self, tmp_path: Path) -> None:
        """SC-002: Detroit preflight checks QCEW, LODES, ACS, TIGER."""
        (tmp_path / "data").mkdir(parents=True)

        result = run_scenario_preflight("detroit", base_dir=tmp_path)

        # Extract unique check prefixes (e.g., "lodes" from "lodes:crosswalk")
        check_prefixes = {c.check_id.split(":")[0] for c in result.checks}

        # Should have checks for all four data sources
        assert "lodes" in check_prefixes
        assert "tiger" in check_prefixes
        assert "census" in check_prefixes
        # QCEW uses existing _check_qcew which produces "qcew:files"
        assert "qcew" in check_prefixes

    def test_partial_data_reports_mixed_results(self, tmp_path: Path) -> None:
        """Story 3, Scenario 3: Partial data shows success + failure."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)

        # Only set up LODES data, missing everything else
        lodes_dir = data_dir / "lodes"
        lodes_dir.mkdir(parents=True)
        (lodes_dir / "us_xwalk.csv").write_text("header\ndata\n")

        result = run_scenario_preflight("detroit", base_dir=tmp_path)

        # Should have at least one success (LODES) and some failures
        assert not result.ok  # Overall fails
        assert len(result.failures) > 0  # Has failures

        # LODES should pass
        lodes_check = next((c for c in result.checks if c.check_id == "lodes:crosswalk"), None)
        assert lodes_check is not None
        assert lodes_check.status == "ok"
