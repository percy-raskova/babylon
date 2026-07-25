"""Tests for the checked-in Detroit tri-county LODES artifact (Vol II Program, Unit U2).

Verifies the ADR076-style, hash-stamped, hex-resolution LODES OD + crosswalk
artifact under ``src/babylon/data/reference/lodes/`` — CI-no-drive honored,
never touches ``/media/user/data`` — parses through the UNMODIFIED
:class:`LODESCommuteMatrixLoader` (Constitution II.12 sole CSR producer) and
reproduces the exact aggregate matrix a full block-level run against the raw
national LODES data would compute for the tri-county study area (regression
row/nnz counts pinned from ``tools/make_lodes_tri_county_artifact.py``'s
generation run).

See Also:
    ``src/babylon/domain/economics/lodes_study_area.py``.
    ``tools/make_lodes_tri_county_artifact.py``.
    ``data-artifacts.yaml`` (``lodes_od_tri_county_hex_*`` / ``lodes_xwalk_tri_county_hex``).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.lodes_commute_matrix import LODESCommuteMatrixLoader, LODESYearMatrix
from babylon.domain.economics.lodes_study_area import (
    LODES_ARTIFACT_CROSSWALK,
    LODES_ARTIFACT_ROOT,
    LODES_STUDY_AREA_STATES,
    lodes_tri_county_hexes_res7,
)
from babylon.domain.economics.node_kinds import NodeKind
from tests.constants_063 import DETROIT_TRI_COUNTY_HEXES_RES7

pytestmark = pytest.mark.unit

# Pinned from tools/make_lodes_tri_county_artifact.py's generation run
# (regenerate both together if the underlying artifact ever changes).
_EXPECTED_NNZ_BY_YEAR: dict[int, int] = {
    2010: 191332,
    2011: 189957,
    2012: 194577,
    2013: 195680,
    2014: 195892,
    2015: 203144,
    2016: 205839,
    2017: 205778,
    2018: 207309,
    2019: 205325,
    2020: 195984,
    2021: 200596,
}


def _make_loader() -> LODESCommuteMatrixLoader:
    return LODESCommuteMatrixLoader(
        lodes_root=LODES_ARTIFACT_ROOT,
        crosswalk_path=LODES_ARTIFACT_CROSSWALK,
        study_area_hexes=lodes_tri_county_hexes_res7(),
        study_area_states=LODES_STUDY_AREA_STATES,
    )


def test_lodes_tri_county_hexes_matches_test_constants_independently() -> None:
    """Production hex set must equal the test module's — computed independently
    (no import between them), mirroring the
    ``default_tri_county_aggregate_hex`` precedent in
    ``border_commute_synthesis.py``."""
    assert lodes_tri_county_hexes_res7() == DETROIT_TRI_COUNTY_HEXES_RES7


def test_artifact_root_and_crosswalk_exist_in_repo() -> None:
    """The artifact is checked into git — no drive dependency at all."""
    assert LODES_ARTIFACT_ROOT.is_dir()
    assert LODES_ARTIFACT_CROSSWALK.is_file()
    assert (LODES_ARTIFACT_ROOT / "od").is_dir()


def test_available_years_matches_shipped_artifact_years() -> None:
    loader = _make_loader()
    assert loader.available_years() == tuple(sorted(_EXPECTED_NNZ_BY_YEAR))


@pytest.mark.parametrize("year", sorted(_EXPECTED_NNZ_BY_YEAR))
def test_load_year_reproduces_pinned_nnz(year: int) -> None:
    """Constitution II.12 GATE-4 + III.7 determinism: loading the checked-in
    artifact (no drive read) reproduces the exact hex-pair count a full
    block-level run against the raw national LODES data produced at
    generation time."""
    loader = _make_loader()
    matrix = loader.load_year(year)
    assert isinstance(matrix, LODESYearMatrix)
    assert matrix.year == year
    assert matrix.matrix.format == "csr"
    assert matrix.matrix.nnz == _EXPECTED_NNZ_BY_YEAR[year]


def test_load_year_dest_kind_breakdown_includes_external_bucket() -> None:
    """Every year must carry at least one EXTERNAL (rest_of_usa) destination
    column — commuters who leave the tri-county study area for work."""
    loader = _make_loader()
    matrix = loader.load_year(2010)
    breakdown = matrix.dest_kind_breakdown()
    assert breakdown.get(NodeKind.EXTERNAL.value, 0) >= 1
    assert breakdown.get(NodeKind.HEX.value, 0) > 0


def test_load_year_is_deterministic_across_fresh_loaders() -> None:
    """Constitution III.7: same on-disk artifact -> bit-identical CSR matrix
    across independently-constructed loader instances."""
    first = _make_loader().load_year(2010)
    second = _make_loader().load_year(2010)
    assert first.matrix.shape == second.matrix.shape
    assert (first.matrix != second.matrix).nnz == 0
    assert first.origin_hex_to_row == second.origin_hex_to_row
    assert first.dest_to_col == second.dest_to_col
