"""Contract tests for BorderCommuteSynthesisLoader (Spec 063 T034 / US3, Option B)."""

from __future__ import annotations

import csv
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from babylon.economics.border_commute_synthesis import (
    BorderCommuteFlow,
    BorderCommuteSynthesisLoader,
    _month_for_iso_week,
    _wednesday_of_iso_week,
)

pytestmark = [pytest.mark.unit]


_TRI_COUNTY_AGGREGATE_HEX = "872ab2c58ffffff"
_DETROIT_PORTS = frozenset(["3801", "3802"])


def _write_minimal_bts_csv(path: Path, *, year: int) -> None:
    """Write a minimal BTS Border Crossing CSV with 12 months × 2 ports."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Port Code", "Measure", "Date", "Value"])
        for month in range(1, 13):
            for port in ("3801", "3802"):
                writer.writerow(
                    [
                        port,
                        "Personal Vehicles",
                        f"{year:04d}-{month:02d}",
                        # 5000 vehicles/port/month × 2 ports × 12 months = 120K/yr per port
                        5000,
                    ]
                )


def test_disabled_loader_is_noop() -> None:
    """When enabled=False, all methods return empty."""
    loader = BorderCommuteSynthesisLoader(
        bts_csv_path=None,
        statcan_csv_path=None,
        border_commute_share=0.50,
        detroit_port_codes=_DETROIT_PORTS,
        tri_county_aggregate_hex=_TRI_COUNTY_AGGREGATE_HEX,
        enabled=False,
    )
    assert not loader.is_enabled()
    assert loader.synthesize_year(2010) == ()


def test_enabled_with_missing_bts_raises_file_not_found(tmp_path: Path) -> None:
    """FR-036: enabled=True with missing BTS file → FileNotFoundError at construction."""
    nonexistent = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError, match="BTS Border Crossing CSV required"):
        BorderCommuteSynthesisLoader(
            bts_csv_path=nonexistent,
            statcan_csv_path=None,
            border_commute_share=0.50,
            detroit_port_codes=_DETROIT_PORTS,
            tri_county_aggregate_hex=_TRI_COUNTY_AGGREGATE_HEX,
            enabled=True,
        )


def test_enabled_with_bts_produces_weekly_rows(tmp_path: Path) -> None:
    """FR-035: enabled loader produces ~52 us_to_canada rows per year when BTS data present."""
    bts_csv = tmp_path / "bts.csv"
    _write_minimal_bts_csv(bts_csv, year=2010)
    loader = BorderCommuteSynthesisLoader(
        bts_csv_path=bts_csv,
        statcan_csv_path=None,  # StatCan absent → us_to_canada only
        border_commute_share=0.50,
        detroit_port_codes=_DETROIT_PORTS,
        tri_county_aggregate_hex=_TRI_COUNTY_AGGREGATE_HEX,
        enabled=True,
    )
    assert loader.is_enabled()

    rows = loader.synthesize_year(2010)
    # 52 weeks × 1 direction (us_to_canada only since StatCan absent)
    assert len(rows) == 52
    assert all(r.direction == "us_to_canada" for r in rows)
    assert all(r.year == 2010 for r in rows)
    assert all(r.aggregate_origin == _TRI_COUNTY_AGGREGATE_HEX for r in rows)
    assert all(r.aggregate_dest == "canada" for r in rows)
    # Magnitude per week: 10000 vehicles/month × 0.5 / (52/12) ≈ 1153.8
    expected_weekly = 10_000.0 * 0.5 / (52 / 12)
    assert rows[0].magnitude_workers == pytest.approx(expected_weekly, rel=1e-9)


def test_constructor_rejects_invalid_border_commute_share() -> None:
    """Constructor MUST reject border_commute_share outside (0, 1]."""
    with pytest.raises(ValueError, match="border_commute_share"):
        BorderCommuteSynthesisLoader(
            bts_csv_path=None,
            statcan_csv_path=None,
            border_commute_share=0.0,  # invalid: must be > 0
            detroit_port_codes=_DETROIT_PORTS,
            tri_county_aggregate_hex=_TRI_COUNTY_AGGREGATE_HEX,
            enabled=False,
        )
    with pytest.raises(ValueError, match="border_commute_share"):
        BorderCommuteSynthesisLoader(
            bts_csv_path=None,
            statcan_csv_path=None,
            border_commute_share=1.5,  # invalid: must be <= 1
            detroit_port_codes=_DETROIT_PORTS,
            tri_county_aggregate_hex=_TRI_COUNTY_AGGREGATE_HEX,
            enabled=False,
        )


def test_iso_8601_week_month_convention_pinned() -> None:
    """FR-035 ISO 8601 convention: month-of-week is month-of-Wednesday-of-week."""
    # 2010 ISO week 1: Mon Jan 4 - Sun Jan 10. Wednesday = Jan 6.
    # Month of Wednesday Jan 6 = January = 1.
    assert _month_for_iso_week(2010, 1) == 1
    assert _wednesday_of_iso_week(2010, 1).day == 6

    # Week 52 of 2010: Mon Dec 27 - Sun Jan 2 2011. Wed = Dec 29 → month 12.
    assert _month_for_iso_week(2010, 52) == 12

    # Mid-year sanity: week 26 of 2010 = late June.
    assert _month_for_iso_week(2010, 26) in (6, 7)  # near month boundary OK


def test_flow_dataclass_is_frozen() -> None:
    """BorderCommuteFlow is a frozen dataclass — accidental mutation rejected."""
    flow = BorderCommuteFlow(
        year=2010,
        week_of_year=1,
        direction="us_to_canada",
        aggregate_origin=_TRI_COUNTY_AGGREGATE_HEX,
        aggregate_dest="canada",
        magnitude_workers=1153.8,
        source_anchor="test",
    )
    with pytest.raises(FrozenInstanceError):
        flow.magnitude_workers = 0  # type: ignore[misc]
