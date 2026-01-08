"""Unit tests for ingestion preflight checks."""

from __future__ import annotations

from pathlib import Path

from babylon.data.loader_base import LoaderConfig
from babylon.data.preflight import PreflightResult, run_preflight


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
