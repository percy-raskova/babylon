"""Hypothesis strategy for generating valid HexGrid instances.

Spec 053 T011: Generates ``HexGrid`` instances with consistent res-6 and res-5
parent maps (computed via real ``h3.cell_to_parent``) for property-based tests
of conservation invariants (INV-001, INV-002, INV-003).

Seed pool
---------
The seed pool ``MICHIGAN_RES7_SEED_CELLS`` is constructed once at module
import time by expanding the existing tri-county anchor cells (defined in
``tests/unit/economics/substrate/conftest.py``) via ``h3.grid_disk``. The
``HexEconomicState.county_fips`` field requires a tri-county FIPS code
(Wayne 26163, Oakland 26125, Macomb 26099), so each expanded cell inherits
its anchor cell's county. Expansion radius defaults to ``k=15`` which
produces ~700 cells per anchor and ~6 300 cells total for the tri-county
seed pool — enough to comfortably exercise the scaled-tolerance bound in
INV-001 / INV-003 while remaining within the validator constraints.

For ambitions beyond the tri-county scope, increase ``EXPAND_RADIUS`` or
override ``seed_cells=`` when calling ``hex_grid_strategy``.
"""

from __future__ import annotations

from typing import Final

import h3
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from babylon.domain.economics.substrate.types import HexEconomicState, HexGrid

# Anchor cells from the existing tri-county fixtures. Each anchor's county
# applies to every cell in its grid_disk.
_WAYNE_ANCHORS: Final[tuple[str, ...]] = (
    "872830828ffffff",
    "872830829ffffff",
    "87283082affffff",
)
_OAKLAND_ANCHORS: Final[tuple[str, ...]] = (
    "872830880ffffff",
    "872830881ffffff",
    "872830882ffffff",
)
_MACOMB_ANCHORS: Final[tuple[str, ...]] = (
    "872830890ffffff",
    "872830891ffffff",
    "872830892ffffff",
)

EXPAND_RADIUS: Final[int] = 15
"""Grid-disk expansion radius (k). k=15 yields ~700 cells per anchor."""


def _build_seed_pool() -> tuple[list[str], dict[str, str]]:
    """Expand each anchor cell via h3.grid_disk and tag with county FIPS.

    Returns:
        A pair ``(cells, fips_map)`` where ``cells`` is the deduplicated
        list of res-7 cell IDs and ``fips_map[cell] = county_fips``. If a
        cell is reachable from anchors in multiple counties, the first
        anchor wins (deterministic by anchor list ordering).
    """
    fips_map: dict[str, str] = {}
    cells: list[str] = []
    for fips, anchors in (
        ("26163", _WAYNE_ANCHORS),
        ("26125", _OAKLAND_ANCHORS),
        ("26099", _MACOMB_ANCHORS),
    ):
        for anchor in anchors:
            for cell in h3.grid_disk(anchor, EXPAND_RADIUS):
                if cell not in fips_map:
                    fips_map[cell] = fips
                    cells.append(cell)
    return cells, fips_map


MICHIGAN_RES7_SEED_CELLS, _CELL_TO_FIPS = _build_seed_pool()
"""Module-level cached seed pool. ~6 300 cells (k=15 across 9 anchors)."""


def _build_grid_from_cells(
    cells: list[str],
    cvs_values: list[tuple[float, float, float]],
) -> HexGrid:
    """Construct a HexGrid from drawn cell IDs and per-hex c/v/s values."""
    hexes: dict[str, HexEconomicState] = {}
    county_hex_ids: dict[str, set[str]] = {"26163": set(), "26125": set(), "26099": set()}
    res6_parents: dict[str, str] = {}
    res5_parents: dict[str, str] = {}
    res6_children: dict[str, set[str]] = {}
    res5_children: dict[str, set[str]] = {}

    for cell, (c, v, s) in zip(cells, cvs_values, strict=True):
        fips = _CELL_TO_FIPS[cell]
        # Compute derived rates so the grid represents a valid post-Production
        # state. Equalization (and other downstream computers) read the stored
        # ``profit_rate`` field; leaving it at default 0.0 breaks the
        # capital-weighted-mean conservation proof in equalize_capital.
        cv = c + v
        profit_rate = s / cv if cv > 0 else 0.0
        exploitation_rate = s / v if v > 0 else 0.0
        hexes[cell] = HexEconomicState(
            h3_index=cell,
            county_fips=fips,
            constant_capital=c,
            variable_capital=v,
            surplus_value=s,
            employment=0.0,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
            profit_rate=profit_rate,
            exploitation_rate=exploitation_rate,
        )
        county_hex_ids[fips].add(cell)
        r6 = h3.cell_to_parent(cell, 6)
        r5 = h3.cell_to_parent(cell, 5)
        res6_parents[cell] = r6
        res5_parents[cell] = r5
        res6_children.setdefault(r6, set()).add(cell)
        res5_children.setdefault(r5, set()).add(cell)

    return HexGrid(
        hexes=hexes,
        county_hex_ids={k: frozenset(v) for k, v in county_hex_ids.items() if v},
        res6_parents=res6_parents,
        res5_parents=res5_parents,
        res6_children={k: frozenset(v) for k, v in res6_children.items()},
        res5_children={k: frozenset(v) for k, v in res5_children.items()},
    )


@st.composite
def _hex_grid_strategy_impl(
    draw: st.DrawFn,
    min_hexes: int,
    max_hexes: int,
    seed_cells: list[str],
) -> HexGrid:
    upper = min(max_hexes, len(seed_cells))
    if upper < min_hexes:
        upper = min_hexes  # fall through; will be clamped by available cells
    n = draw(st.integers(min_value=min_hexes, max_value=max(min_hexes, upper)))
    n = min(n, len(seed_cells))
    sampled_indices = draw(
        st.lists(
            st.integers(min_value=0, max_value=len(seed_cells) - 1),
            min_size=n,
            max_size=n,
            unique=True,
        )
    )
    cells = [seed_cells[i] for i in sampled_indices]
    cvs_values = draw(
        st.lists(
            st.tuples(
                st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
                st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
                st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
            ),
            min_size=n,
            max_size=n,
        )
    )
    return _build_grid_from_cells(cells, cvs_values)


def hex_grid_strategy(
    min_hexes: int = 1,
    max_hexes: int = 25_000,
    seed_cells: list[str] | None = None,
) -> SearchStrategy[HexGrid]:
    """Generate valid HexGrid instances drawn from the Michigan tri-county pool.

    Args:
        min_hexes: Minimum hex count per generated grid (default 1).
        max_hexes: Maximum hex count per generated grid. Hypothesis size-biased
            shrinking favors small grids; the upper bound is clamped to the
            seed-pool size (~6 300 with default expansion).
        seed_cells: Optional override for the seed pool. If provided, every
            cell MUST appear in ``MICHIGAN_RES7_SEED_CELLS`` so its county
            FIPS is known.

    Returns:
        A Hypothesis ``SearchStrategy[HexGrid]``.
    """
    pool = seed_cells if seed_cells is not None else MICHIGAN_RES7_SEED_CELLS
    return _hex_grid_strategy_impl(min_hexes, max_hexes, pool)
