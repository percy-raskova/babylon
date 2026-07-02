"""Spec-086 T010: per-county constraint-tree assembly (US1).

RED phase until T015 implements ``babylon_data.qcew.hierarchy``.

The tree is built ONLY from rows the year's singlefile publishes
(research D6): county total (70) → per-ownership totals (71) → NAICS
prefix chain from the 74–77 subtotal rows → 6-digit leaves (78).
Suppressed rows are structurally present but ``disclosed=False``.
"""

from __future__ import annotations

import pytest

hierarchy = pytest.importorskip(
    "babylon_data.qcew.hierarchy",
    reason="babylon-data symlink not resolved (CI)",
)

pytestmark = [pytest.mark.unit, pytest.mark.ledger]


def _cell(estabs: int, employment: int | None, wages: int | None, *, disclosed: bool = True):  # type: ignore[no-untyped-def]
    return hierarchy.Cell(estabs=estabs, employment=employment, wages=wages, disclosed=disclosed)


class TestSectorMapping:
    def test_range_sectors(self) -> None:
        assert hierarchy.sector_for("33") == "31-33"
        assert hierarchy.sector_for("31") == "31-33"
        assert hierarchy.sector_for("44") == "44-45"
        assert hierarchy.sector_for("49") == "48-49"

    def test_plain_sector(self) -> None:
        assert hierarchy.sector_for("54") == "54"


class TestOwnershipTree:
    def test_full_chain_parenting(self) -> None:
        tree = hierarchy.build_ownership_tree(
            "5",
            total_cell=_cell(9, 900, 45_000_000),
            naics_cells={
                "31-33": _cell(9, 900, 45_000_000),
                "336": _cell(9, 900, 45_000_000),
                "3361": _cell(9, 900, 45_000_000),
                "33611": _cell(9, 900, 45_000_000),
            },
            leaf_cells={
                "336111": _cell(5, 600, 30_000_000),
                "336112": _cell(4, None, None, disclosed=False),
            },
        )
        root = tree.root
        assert root.disclosed is True and root.employment == 900
        (sector,) = root.children
        assert sector.naics == "31-33"
        path = []
        node = sector
        while node.children:
            assert len(node.children) == 1 or node.naics == "33611"
            node = node.children[0] if len(node.children) == 1 else node
            path.append(node.naics)
            if node.naics == "33611":
                break
        leaf_parent = node
        leaf_codes = sorted(child.naics for child in leaf_parent.children)
        assert leaf_codes == ["336111", "336112"]
        suppressed = next(c for c in leaf_parent.children if c.naics == "336112")
        assert suppressed.disclosed is False
        assert suppressed.estabs == 4

    def test_missing_intermediates_attach_to_nearest_present_prefix(self) -> None:
        tree = hierarchy.build_ownership_tree(
            "5",
            total_cell=_cell(9, 900, 45_000_000),
            naics_cells={"31-33": _cell(9, 900, 45_000_000)},
            leaf_cells={"336111": _cell(5, 600, 30_000_000)},
        )
        (sector,) = tree.root.children
        (leaf,) = sector.children
        assert leaf.naics == "336111"

    def test_no_rows_but_leaves_attach_to_root(self) -> None:
        tree = hierarchy.build_ownership_tree(
            "5",
            total_cell=None,
            naics_cells={},
            leaf_cells={"541511": _cell(2, 40, 2_000_000)},
        )
        assert tree.root.synthetic is True
        assert tree.root.disclosed is False
        (leaf,) = tree.root.children
        assert leaf.naics == "541511"

    def test_suppressed_intermediate_present_and_undisclosed(self) -> None:
        tree = hierarchy.build_ownership_tree(
            "5",
            total_cell=_cell(9, 900, 45_000_000),
            naics_cells={
                "31-33": _cell(9, 900, 45_000_000),
                "336": _cell(6, None, None, disclosed=False),
            },
            leaf_cells={"336111": _cell(5, 600, 30_000_000)},
        )
        (sector,) = tree.root.children
        (intermediate,) = sector.children
        assert intermediate.naics == "336"
        assert intermediate.disclosed is False
        (leaf,) = intermediate.children
        assert leaf.naics == "336111"


class TestCountyTree:
    def test_county_assembly(self) -> None:
        county = hierarchy.build_county_tree(
            "26163",
            total_cell=_cell(10, 1000, 50_000_000),
            own_cells={"5": _cell(9, 900, 45_000_000), "3": _cell(1, None, None, disclosed=False)},
            naics_cells={("5", "31-33"): _cell(9, 900, 45_000_000)},
            leaf_cells={
                ("5", "336111"): _cell(5, 600, 30_000_000),
                ("3", "541511"): _cell(1, None, None, disclosed=False),
            },
        )
        assert county.fips == "26163"
        assert county.total_cell is not None and county.total_cell.employment == 1000
        assert set(county.ownerships) == {"5", "3"}
        assert county.ownerships["3"].root.disclosed is False
