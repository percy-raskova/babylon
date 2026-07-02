"""Spec-086 T011: top-down hierarchical imputation (US1, research D6).

RED phase until T016 implements ``babylon_data.qcew.imputation``.

Rules pinned here:

- disclosed values are NEVER mutated (method ``OBSERVED``);
- exactly one suppressed sibling ⇒ exact recovery ``P − Σdisclosed``;
- several suppressed siblings ⇒ establishments-proportional apportionment,
  integer-exact via largest-remainder;
- no establishment basis ⇒ documented equal split;
- disclosed siblings exceeding the parent ⇒ suppressed siblings get 0 and
  an anomaly is recorded;
- a suppressed intermediate receives at least the sum of its disclosed
  descendants (floor), with any shortfall recorded as an anomaly;
- suppressed ownership totals (71) are apportioned from the county total
  and then constrain their own subtree;
- county total itself suppressed ⇒ fallback chain (Σ disclosed 71 →
  Σ disclosed leaves) and the county is flagged low-confidence;
- employment and wages reconcile independently.
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

pytestmark = [pytest.mark.unit, pytest.mark.math, pytest.mark.red_phase]


def _cell(estabs: int, employment: int | None, wages: int | None, *, disclosed: bool = True):  # type: ignore[no-untyped-def]
    return hierarchy.Cell(estabs=estabs, employment=employment, wages=wages, disclosed=disclosed)


def _county(  # type: ignore[no-untyped-def]
    total,
    own_cells,
    naics_cells=None,
    leaf_cells=None,
):
    return hierarchy.build_county_tree(
        "26163",
        total_cell=total,
        own_cells=own_cells,
        naics_cells=naics_cells or {},
        leaf_cells=leaf_cells or {},
    )


class TestLargestRemainder:
    def test_exact_sum_and_proportions(self) -> None:
        assert imputation.largest_remainder(600, [3, 1]) == [450, 150]

    def test_tie_break_deterministic(self) -> None:
        # 10 over three equal weights: remainders tie; earlier index wins.
        assert imputation.largest_remainder(10, [1, 1, 1]) == [4, 3, 3]

    @pytest.mark.parametrize(
        ("total", "weights"),
        [(0, [1, 2]), (7, [5]), (13, [2, 2, 3]), (1, [0, 0]), (999983, [7, 11, 13, 17])],
    )
    def test_sum_invariant(self, total: int, weights: list[int]) -> None:
        shares = imputation.largest_remainder(total, weights)
        assert sum(shares) == total
        assert all(share >= 0 for share in shares)


class TestLeafLevel:
    def test_single_suppressed_sibling_exact_recovery(self) -> None:
        tree = _county(
            _cell(10, 1000, 50_000_000),
            {"5": _cell(10, 1000, 50_000_000)},
            leaf_cells={
                ("5", "336111"): _cell(6, 600, 30_000_000),
                ("5", "336112"): _cell(4, None, None, disclosed=False),
            },
        )
        result = imputation.impute_county(tree)
        cell = result.leaves[("5", "336112")]
        assert cell.employment == 400
        assert cell.wages == 20_000_000
        assert cell.method == imputation.ImputationMethod.EXACT_RECOVERY
        observed = result.leaves[("5", "336111")]
        assert observed.employment == 600
        assert observed.method == imputation.ImputationMethod.OBSERVED

    def test_multi_sibling_estabs_apportionment(self) -> None:
        tree = _county(
            _cell(10, 1000, 50_000_000),
            {"5": _cell(10, 1000, 50_000_000)},
            leaf_cells={
                ("5", "336111"): _cell(4, 400, 20_000_000),
                ("5", "336112"): _cell(3, None, None, disclosed=False),
                ("5", "336120"): _cell(1, None, None, disclosed=False),
            },
        )
        result = imputation.impute_county(tree)
        b = result.leaves[("5", "336112")]
        c = result.leaves[("5", "336120")]
        assert (b.employment, c.employment) == (450, 150)
        assert (b.wages, c.wages) == (22_500_000, 7_500_000)
        assert b.method == imputation.ImputationMethod.ESTABS_APPORTIONED
        assert c.method == imputation.ImputationMethod.ESTABS_APPORTIONED

    def test_zero_establishment_basis_falls_back_to_equal_split(self) -> None:
        tree = _county(
            _cell(10, 1000, 50_000_000),
            {"5": _cell(10, 1000, 50_000_000)},
            leaf_cells={
                ("5", "336111"): _cell(4, 400, 20_000_000),
                ("5", "336112"): _cell(0, None, None, disclosed=False),
                ("5", "336120"): _cell(0, None, None, disclosed=False),
            },
        )
        result = imputation.impute_county(tree)
        b = result.leaves[("5", "336112")]
        c = result.leaves[("5", "336120")]
        assert (b.employment, c.employment) == (300, 300)
        assert b.method == imputation.ImputationMethod.EQUAL_SPLIT

    def test_negative_remainder_zeroes_and_records_anomaly(self) -> None:
        tree = _county(
            _cell(10, 500, 25_000_000),
            {"5": _cell(10, 500, 25_000_000)},
            leaf_cells={
                ("5", "336111"): _cell(4, 600, 30_000_000),
                ("5", "336112"): _cell(3, None, None, disclosed=False),
            },
        )
        result = imputation.impute_county(tree)
        cell = result.leaves[("5", "336112")]
        assert cell.employment == 0
        assert cell.method == imputation.ImputationMethod.ZERO_NEGATIVE_REMAINDER
        assert result.anomalies, "negative remainder must be recorded"

    def test_sum_reconciles_exactly_when_total_published(self) -> None:
        tree = _county(
            _cell(10, 1003, 50_000_003),
            {"5": _cell(10, 1003, 50_000_003)},
            leaf_cells={
                ("5", "336111"): _cell(4, 400, 20_000_000),
                ("5", "336112"): _cell(3, None, None, disclosed=False),
                ("5", "336120"): _cell(2, None, None, disclosed=False),
                ("5", "541511"): _cell(1, None, None, disclosed=False),
            },
        )
        result = imputation.impute_county(tree)
        emp = sum(cell.employment for cell in result.leaves.values())
        wages = sum(cell.wages for cell in result.leaves.values())
        assert emp == 1003
        assert wages == 50_000_003


class TestIntermediateFloor:
    def test_suppressed_intermediate_constrained_then_recovers_internally(self) -> None:
        # own '5' = 1000: sectors '31-33' (900, disclosed) + '54' (100, disclosed).
        # Inside '31-33': suppressed subsector '336' (holding a disclosed 600
        # leaf + a suppressed leaf) beside disclosed '337' (200).
        tree = _county(
            _cell(12, 1000, 50_000_000),
            {"5": _cell(12, 1000, 50_000_000)},
            naics_cells={
                ("5", "31-33"): _cell(10, 900, 45_000_000),
                ("5", "54"): _cell(2, 100, 5_000_000),
                ("5", "336"): _cell(6, None, None, disclosed=False),
                ("5", "337"): _cell(4, 200, 10_000_000),
            },
            leaf_cells={
                ("5", "336111"): _cell(4, 600, 30_000_000),
                ("5", "336112"): _cell(2, None, None, disclosed=False),
                ("5", "337110"): _cell(4, 200, 10_000_000),
                ("5", "541511"): _cell(2, 100, 5_000_000),
            },
        )
        result = imputation.impute_county(tree)
        # '336' is the single suppressed child of '31-33': 900 − 200 = 700;
        # internally: 700 − 600 disclosed = 100 → the suppressed leaf.
        suppressed_leaf = result.leaves[("5", "336112")]
        assert suppressed_leaf.employment == 100
        assert suppressed_leaf.wages == 5_000_000
        assert sum(cell.employment for cell in result.leaves.values()) == 1000

    def test_floor_shortfall_recorded(self) -> None:
        # '31-33' = 850, but its suppressed child '336' already CONTAINS a
        # disclosed 800 leaf while sibling '337' discloses 250: remainder
        # 850 − 250 = 600 < floor 800. Disclosed data is never contradicted:
        # '336' gets its floor (800) and the inconsistency is an anomaly.
        tree = _county(
            _cell(12, 950, 47_000_000),
            {"5": _cell(12, 950, 47_000_000)},
            naics_cells={
                ("5", "31-33"): _cell(10, 850, 42_000_000),
                ("5", "54"): _cell(2, 100, 5_000_000),
                ("5", "336"): _cell(6, None, None, disclosed=False),
                ("5", "337"): _cell(4, 250, 12_000_000),
            },
            leaf_cells={
                ("5", "336111"): _cell(4, 800, 40_000_000),
                ("5", "336112"): _cell(2, None, None, disclosed=False),
                ("5", "337110"): _cell(4, 250, 12_000_000),
                ("5", "541511"): _cell(2, 100, 5_000_000),
            },
        )
        result = imputation.impute_county(tree)
        assert result.anomalies, "floor shortfall must be recorded"
        # Floor honored: the disclosed 800 leaf survives; its suppressed
        # sibling gets the internal remainder max(800 − 800, 0) = 0.
        assert result.leaves[("5", "336111")].employment == 800
        assert result.leaves[("5", "336112")].employment == 0


class TestOwnershipLevel:
    def test_suppressed_71_apportioned_then_constrains_subtree(self) -> None:
        tree = _county(
            _cell(12, 1000, 50_000_000),
            {
                "5": _cell(9, 800, 40_000_000),
                "3": _cell(3, None, None, disclosed=False),
            },
            leaf_cells={
                ("5", "336111"): _cell(9, 800, 40_000_000),
                ("3", "541511"): _cell(2, None, None, disclosed=False),
                ("3", "541512"): _cell(1, None, None, disclosed=False),
            },
        )
        result = imputation.impute_county(tree)
        own3 = result.ownership_totals["3"]
        assert own3.employment == 200
        assert own3.method == imputation.ImputationMethod.EXACT_RECOVERY
        a = result.leaves[("3", "541511")]
        b = result.leaves[("3", "541512")]
        assert a.employment + b.employment == 200
        assert (a.employment, b.employment) == (133, 67)


class TestCountyTotalFallback:
    def test_suppressed_70_falls_back_to_disclosed_71_sum(self) -> None:
        tree = _county(
            _cell(12, None, None, disclosed=False),
            {
                "5": _cell(9, 800, 40_000_000),
                "3": _cell(3, 150, 7_000_000),
            },
            leaf_cells={
                ("5", "336111"): _cell(9, 800, 40_000_000),
                ("3", "541511"): _cell(3, 150, 7_000_000),
            },
        )
        result = imputation.impute_county(tree)
        assert result.county_total.employment == 950
        assert result.county_total_source == imputation.CountyTotalSource.SUM_DISCLOSED_71
        assert result.low_confidence is True

    def test_all_71_suppressed_falls_back_to_disclosed_leaves(self) -> None:
        tree = _county(
            _cell(12, None, None, disclosed=False),
            {"5": _cell(9, None, None, disclosed=False)},
            leaf_cells={
                ("5", "336111"): _cell(6, 500, 20_000_000),
                ("5", "336112"): _cell(3, None, None, disclosed=False),
            },
        )
        result = imputation.impute_county(tree)
        assert result.county_total.employment == 500
        assert result.county_total_source == imputation.CountyTotalSource.SUM_DISCLOSED_LEAVES
        assert result.low_confidence is True
        # With no published constraint above them, unconstrained suppressed
        # leaves receive 0 and the county-year carries an anomaly.
        assert result.leaves[("5", "336112")].employment == 0
