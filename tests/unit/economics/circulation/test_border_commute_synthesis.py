"""Contract tests for BorderCommuteSynthesisLoader (Spec 063 T034 / US3, Option B)."""

from __future__ import annotations

import csv
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from babylon.domain.economics.border_commute_synthesis import (
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


# ─────────────────────────────────────────────────────────────────────────────
# T040 completion — merge_into_year_matrix (in-memory half of the T042 merge).
# The Postgres half (merge_into_postgres_lodes) is covered at integration level
# (test_synthesis_enabled_disabled.py); the pure in-memory merge is unit-tested
# here because it needs no Postgres/data and pins the FR-035 mean-of-weeks math.
# ─────────────────────────────────────────────────────────────────────────────


def _enabled_loader(tmp_path: Path) -> BorderCommuteSynthesisLoader:
    bts_csv = tmp_path / "bts.csv"
    _write_minimal_bts_csv(bts_csv, year=2010)
    return BorderCommuteSynthesisLoader(
        bts_csv_path=bts_csv,
        statcan_csv_path=None,
        border_commute_share=0.50,
        detroit_port_codes=_DETROIT_PORTS,
        tri_county_aggregate_hex=_TRI_COUNTY_AGGREGATE_HEX,
        enabled=True,
    )


def test_default_tri_county_aggregate_hex_pins_detroit_centroid_cell() -> None:
    """The production centroid helper resolves the canonical res-7 cell."""
    from babylon.domain.economics.border_commute_synthesis import default_tri_county_aggregate_hex

    assert default_tri_county_aggregate_hex() == _TRI_COUNTY_AGGREGATE_HEX


def test_merge_disabled_returns_input_unchanged() -> None:
    """A disabled loader returns the exact input matrix object (`is` identity)."""
    from babylon.domain.economics.lodes_commute_matrix import build_year_matrix
    from babylon.domain.economics.node_kinds import NodeKind

    loader = BorderCommuteSynthesisLoader(
        bts_csv_path=None,
        statcan_csv_path=None,
        border_commute_share=0.50,
        detroit_port_codes=_DETROIT_PORTS,
        tri_county_aggregate_hex=_TRI_COUNTY_AGGREGATE_HEX,
        enabled=False,
    )
    base = build_year_matrix(
        pair_counts={(_TRI_COUNTY_AGGREGATE_HEX, "872ab2c59ffffff"): 10},
        boundary_dest_kind={"872ab2c59ffffff": NodeKind.HEX},
        year=2010,
    )
    assert loader.merge_into_year_matrix(base, 2010) is base


def test_merge_adds_canada_column_with_mean_weekly_magnitude(tmp_path: Path) -> None:
    """FR-035: canada enters as an EXTERNAL column at the mean weekly count."""
    from babylon.domain.economics.lodes_commute_matrix import build_year_matrix
    from babylon.domain.economics.node_kinds import NodeKind

    loader = _enabled_loader(tmp_path)
    base = build_year_matrix(
        pair_counts={(_TRI_COUNTY_AGGREGATE_HEX, "872ab2c59ffffff"): 10},
        boundary_dest_kind={"872ab2c59ffffff": NodeKind.HEX},
        year=2010,
    )
    merged = loader.merge_into_year_matrix(base, 2010)

    assert "canada" in merged.dest_to_col
    col = merged.dest_to_col["canada"]
    assert merged.dest_kind_by_col[col] is NodeKind.EXTERNAL
    # 12 months × 2 ports × 5000 = 10000 vehicles/month → 10000 × 0.5 / (52/12)
    # ≈ 1153.8 per week; mean of 52 equal weeks rounds to 1154.
    expected = round(10_000 * 0.5 / (52 / 12))
    row = merged.origin_hex_to_row[_TRI_COUNTY_AGGREGATE_HEX]
    assert merged.matrix[row, col] == float(expected)
    # The original frozen matrix is never mutated.
    assert "canada" not in base.dest_to_col


def test_merge_creates_origin_row_when_aggregate_hex_absent(tmp_path: Path) -> None:
    """When the aggregate hex is not already an origin, the merge adds its row."""
    import numpy as np

    from babylon.domain.economics.lodes_commute_matrix import build_year_matrix
    from babylon.domain.economics.node_kinds import NodeKind

    loader = _enabled_loader(tmp_path)
    # Base matrix whose only origin is a DIFFERENT hex — the aggregate hex is absent.
    other_origin = "872ab2c5affffff"
    base = build_year_matrix(
        pair_counts={(other_origin, "872ab2c59ffffff"): 7},
        boundary_dest_kind={"872ab2c59ffffff": NodeKind.HEX},
        year=2010,
    )
    assert _TRI_COUNTY_AGGREGATE_HEX not in base.origin_hex_to_row

    merged = loader.merge_into_year_matrix(base, 2010)
    assert _TRI_COUNTY_AGGREGATE_HEX in merged.origin_hex_to_row
    # row_sums stay consistent with matrix.sum(axis=1) (model_validator would
    # have raised otherwise — assert it directly for a load-bearing pin).
    computed = np.asarray(merged.matrix.sum(axis=1)).ravel()
    assert np.allclose(computed, merged.row_sums)
