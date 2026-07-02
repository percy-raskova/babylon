"""Spec-086 T012: imputation is a pure, order-insensitive function (US1, FR-008).

RED phase until T016 implements ``babylon_data.qcew.imputation``.

Determinism obligations pinned (contracts/determinism_contract.md): input
row/dict ordering must not affect any assigned magnitude; repeated runs
are identical; largest-remainder ties break to the lower industry code.
"""

from __future__ import annotations

import pytest

hierarchy = pytest.importorskip(
    "babylon_data.qcew.hierarchy",
    reason="babylon-data symlink not resolved (CI)",
)
imputation = pytest.importorskip(
    "babylon_data.qcew.imputation",
    reason="babylon-data symlink not resolved (CI)",
)

pytestmark = [pytest.mark.unit, pytest.mark.math]


def _cell(estabs: int, employment: int | None, wages: int | None, *, disclosed: bool = True):  # type: ignore[no-untyped-def]
    return hierarchy.Cell(estabs=estabs, employment=employment, wages=wages, disclosed=disclosed)


def _build(leaf_items):  # type: ignore[no-untyped-def]
    return hierarchy.build_county_tree(
        "26163",
        total_cell=_cell(20, 2000, 100_000_007),
        own_cells={"5": _cell(20, 2000, 100_000_007)},
        naics_cells={},
        leaf_cells=dict(leaf_items),
    )


_LEAVES = [
    (("5", "336111"), _cell(4, 700, 35_000_000)),
    (("5", "336112"), _cell(3, None, None, disclosed=False)),
    (("5", "336120"), _cell(5, None, None, disclosed=False)),
    (("5", "541511"), _cell(2, None, None, disclosed=False)),
    (("5", "541512"), _cell(1, 300, 15_000_000)),
]


def _flat(result):  # type: ignore[no-untyped-def]
    return sorted(
        (key, cell.employment, cell.wages, str(cell.method)) for key, cell in result.leaves.items()
    )


class TestOrderInsensitivity:
    def test_permuted_input_order_identical_output(self) -> None:
        baseline = _flat(imputation.impute_county(_build(_LEAVES)))
        assert _flat(imputation.impute_county(_build(reversed(_LEAVES)))) == baseline
        shuffled = [_LEAVES[2], _LEAVES[0], _LEAVES[4], _LEAVES[1], _LEAVES[3]]
        assert _flat(imputation.impute_county(_build(shuffled))) == baseline

    def test_repeat_runs_identical(self) -> None:
        tree = _build(_LEAVES)
        assert _flat(imputation.impute_county(tree)) == _flat(imputation.impute_county(tree))

    def test_totals_conserved(self) -> None:
        result = imputation.impute_county(_build(_LEAVES))
        assert sum(cell.employment for cell in result.leaves.values()) == 2000
        assert sum(cell.wages for cell in result.leaves.values()) == 100_000_007


class TestTieBreak:
    def test_equal_weights_extra_units_go_to_lower_industry_code(self) -> None:
        # Remainder 1000 over three equal-weight suppressed leaves: 334, 333, 333
        # with the extra unit on the lexicographically lowest industry code.
        tree = hierarchy.build_county_tree(
            "26163",
            total_cell=_cell(3, 1000, 1001),
            own_cells={"5": _cell(3, 1000, 1001)},
            naics_cells={},
            leaf_cells={
                ("5", "336112"): _cell(1, None, None, disclosed=False),
                ("5", "336111"): _cell(1, None, None, disclosed=False),
                ("5", "336120"): _cell(1, None, None, disclosed=False),
            },
        )
        result = imputation.impute_county(tree)
        assert result.leaves[("5", "336111")].employment == 334
        assert result.leaves[("5", "336112")].employment == 333
        assert result.leaves[("5", "336120")].employment == 333
        # 1001 leaves TWO extra units after equal floors of 333 — they land on
        # the two lowest industry codes.
        assert result.leaves[("5", "336111")].wages == 334
        assert result.leaves[("5", "336112")].wages == 334
        assert result.leaves[("5", "336120")].wages == 333
