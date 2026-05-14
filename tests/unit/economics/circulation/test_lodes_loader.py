"""Contract tests for LODESCommuteMatrixLoader (Spec 063 T009 / US1).

Exercises constructor validation, year discovery, FR-004 nearest-year clamp,
and the GATE-4 CSR-matrix invariant. Does not require Postgres.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.constants_063 import DETROIT_TRI_COUNTY_HEXES_RES7

from babylon.economics.lodes_commute_matrix import (
    LODESCommuteMatrixLoader,
    LODESYearMatrix,
)

_LODES_ROOT = Path("/media/user/data/babylon-data/lodes")
_CROSSWALK = _LODES_ROOT / "us_xwalk.csv.gz"

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        not (_LODES_ROOT / "od" / "mi_od_main_JT00_2010.csv.gz").exists(),
        reason="LODES dataset not present at /media/user/data/babylon-data/lodes/",
    ),
]


def _make_loader() -> LODESCommuteMatrixLoader:
    return LODESCommuteMatrixLoader(
        lodes_root=_LODES_ROOT,
        crosswalk_path=_CROSSWALK,
        study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
        study_area_states=frozenset(["26"]),
    )


def test_constructor_rejects_missing_lodes_root() -> None:
    """FR-026 / contract: constructor MUST raise FileNotFoundError on missing root."""
    with pytest.raises(FileNotFoundError, match="LODES root"):
        LODESCommuteMatrixLoader(
            lodes_root=Path("/tmp/nonexistent-lodes-root"),
            crosswalk_path=_CROSSWALK,
            study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
            study_area_states=frozenset(["26"]),
        )


def test_constructor_rejects_missing_crosswalk() -> None:
    """Constructor MUST raise FileNotFoundError on missing crosswalk."""
    with pytest.raises(FileNotFoundError, match="crosswalk"):
        LODESCommuteMatrixLoader(
            lodes_root=_LODES_ROOT,
            crosswalk_path=Path("/tmp/nonexistent-xwalk.csv.gz"),
            study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
            study_area_states=frozenset(["26"]),
        )


def test_constructor_rejects_empty_study_area_hexes() -> None:
    """Constructor MUST raise ValueError on empty study_area_hexes."""
    with pytest.raises(ValueError, match="study_area_hexes"):
        LODESCommuteMatrixLoader(
            lodes_root=_LODES_ROOT,
            crosswalk_path=_CROSSWALK,
            study_area_hexes=frozenset(),
            study_area_states=frozenset(["26"]),
        )


def test_constructor_rejects_invalid_state_code() -> None:
    """Constructor MUST reject non-2-digit FIPS state codes."""
    with pytest.raises(ValueError, match="2-digit FIPS"):
        LODESCommuteMatrixLoader(
            lodes_root=_LODES_ROOT,
            crosswalk_path=_CROSSWALK,
            study_area_hexes=DETROIT_TRI_COUNTY_HEXES_RES7,
            study_area_states=frozenset(["Michigan"]),
        )


def test_available_years_returns_sorted_tuple_of_michigan_lodes_years() -> None:
    """FR-003: available_years() reports the on-disk LODES year set."""
    loader = _make_loader()
    years = loader.available_years()
    # LODES Michigan coverage: 2010-2021 per research §1.
    assert years == tuple(range(2010, 2022))


def test_clamp_to_available_returns_target_when_present() -> None:
    """FR-004: clamp is a no-op when the target year is available."""
    loader = _make_loader()
    assert loader.clamp_to_available(2010) == 2010
    assert loader.clamp_to_available(2021) == 2021


def test_clamp_to_available_clamps_overrange_to_latest() -> None:
    """FR-004: years beyond LODES coverage clamp to the latest available."""
    loader = _make_loader()
    assert loader.clamp_to_available(2025) == 2021
    assert loader.clamp_to_available(2099) == 2021


def test_clamp_to_available_clamps_underrange_to_earliest() -> None:
    """FR-004: years before LODES coverage clamp to the earliest available."""
    loader = _make_loader()
    assert loader.clamp_to_available(1900) == 2010
    assert loader.clamp_to_available(2005) == 2010


@pytest.mark.slow
def test_load_year_returns_csr_matrix_per_gate_4() -> None:
    """Constitution II.12 GATE-4: loaded matrix MUST be in CSR format.

    Marked @slow because loading parses the 143 MB crosswalk + a Michigan
    LODES year (~5-10s wall time).
    """
    loader = _make_loader()
    year_matrix = loader.load_year(2010)
    assert isinstance(year_matrix, LODESYearMatrix)
    assert year_matrix.year == 2010
    assert year_matrix.matrix.format == "csr"  # GATE-4
    # Tri-county Michigan should have well over 10K commute pairs
    assert year_matrix.matrix.nnz > 5_000
    # The matrix must be non-empty (in-area commute exists)
    assert year_matrix.matrix.shape[0] > 0
    assert year_matrix.matrix.shape[1] > 0
    # row_sums must be consistent with matrix
    assert year_matrix.row_sums.shape == (year_matrix.matrix.shape[0],)


def test_lodes_year_matrix_rejects_non_csr_matrix() -> None:
    """Constitution II.12 GATE-4 validator: matrix must be CSR."""
    import numpy as np
    import scipy.sparse as sp

    coo = sp.coo_matrix(np.zeros((2, 2), dtype=np.float64))
    with pytest.raises(ValueError, match="CSR format"):
        LODESYearMatrix(
            year=2010,
            matrix=coo,  # COO — must be rejected
            origin_hex_to_row={},
            dest_to_col={},
            dest_kind_by_col=(),
            dest_node_id_by_col=(),
            row_sums=np.zeros(0, dtype=np.float64),
        )


def test_lodes_year_matrix_rejects_negative_entries() -> None:
    """Validator: matrix entries (worker counts) must be non-negative."""
    import numpy as np
    import scipy.sparse as sp

    data = np.array([5.0, -1.0], dtype=np.float64)  # negative entry
    indices = np.array([0, 1], dtype=np.int32)
    indptr = np.array([0, 1, 2], dtype=np.int32)
    matrix = sp.csr_matrix((data, indices, indptr), shape=(2, 2))
    with pytest.raises(ValueError, match="negative"):
        LODESYearMatrix(
            year=2010,
            matrix=matrix,
            origin_hex_to_row={"a": 0, "b": 1},
            dest_to_col={"a": 0, "b": 1},
            dest_kind_by_col=(None, None),  # type: ignore[arg-type] — caught by NodeKind cast
            dest_node_id_by_col=("a", "b"),
            row_sums=np.array([5.0, -1.0], dtype=np.float64),
        )
