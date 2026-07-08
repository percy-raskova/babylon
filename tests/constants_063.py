"""Test constants and fixtures for Spec 063 (Vol II Circulation + LODES).

Provides:

- ``DETROIT_TRI_COUNTY_HEXES_RES7`` — frozenset of H3 res-7 cell IDs covering
  the Wayne / Oakland / Macomb tri-county area (used by tests as the
  in-study-area hex set for the ``LODESCommuteMatrixLoader`` and
  ``CrossBorderCommuteClassifier`` constructors). Computed lazily on first
  access from the canonical tri-county polygon.
- ``DETROIT_PORT_CODES`` — BTS port codes for Ambassador Bridge (3801) and
  Detroit-Windsor Tunnel (3802). Used by ``BorderCommuteSynthesisLoader``.
- ``DETROIT_TRI_COUNTY_AGGREGATE_HEX`` — single representative H3 res-7
  cell at the tri-county centroid; used as the synthetic origin/destination
  for Option B border-commute synthesis aggregate flows.
- ``US_DOMESTIC_FIPS_STATES`` — frozenset of all US 2-digit FIPS state codes
  (50 states + DC + 5 territories). Default ``domestic_states`` value for
  ``CrossBorderCommuteClassifier`` per data-model.md §1.4.

See also:
    ``tests/conftest.py``: re-exports these as pytest fixtures.
    ``specs/063-vol-ii-circulation/data-model.md`` §1.1, §1.4, §1.5b.
"""

from __future__ import annotations

from functools import lru_cache

import h3

from babylon.economics.border_commute_synthesis import DETROIT_PORT_CODES

# Canonical Detroit tri-county FIPS codes (Wayne, Oakland, Macomb).
DETROIT_TRI_COUNTY_FIPS: frozenset[str] = frozenset({"26163", "26125", "26099"})

# Approximate bounding polygon for the Wayne+Oakland+Macomb tri-county region.
# Coordinates: (lat, lon) pairs traversed clockwise. Loose envelope — h3.polygon_to_cells
# at res-7 produces ~1700 cells inside this envelope, matching the plan.md scale estimate.
_TRI_COUNTY_BOUNDS_LATLNG: tuple[tuple[float, float], ...] = (
    (42.045, -83.290),  # SW corner (Wayne County southwest)
    (42.045, -82.870),  # SE corner (Wayne County southeast — at Detroit River)
    (42.890, -82.795),  # NE corner (Macomb County northeast)
    (42.890, -83.690),  # NW corner (Oakland County northwest)
    (42.045, -83.290),  # close
)

# Detroit metro centroid (~Wayne County center) for the aggregate synthesis hex.
_DETROIT_CENTROID_LATLNG: tuple[float, float] = (42.331, -83.046)


@lru_cache(maxsize=1)
def _compute_tri_county_hexes_res7() -> frozenset[str]:
    """Compute the res-7 hex set for the Detroit tri-county polygon.

    Lazy + cached to avoid paying the polygon_to_cells cost during pytest
    collection. Returns ~1500-1900 cells depending on h3-py version.
    """
    polygon = h3.LatLngPoly(_TRI_COUNTY_BOUNDS_LATLNG)
    return frozenset(h3.polygon_to_cells(polygon, 7))


def _compute_aggregate_hex() -> str:
    """Single H3 res-7 cell at the Detroit metro centroid (synthesis aggregate)."""
    return h3.latlng_to_cell(*_DETROIT_CENTROID_LATLNG, 7)


# Module-level lazy proxies — avoid top-level h3 calls so import is free of side effects.
class _LazyHexSet:
    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(_compute_tri_county_hexes_res7(), name)

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(_compute_tri_county_hexes_res7())

    def __contains__(self, item) -> bool:  # type: ignore[no-untyped-def]
        return item in _compute_tri_county_hexes_res7()

    def __len__(self) -> int:
        return len(_compute_tri_county_hexes_res7())


DETROIT_TRI_COUNTY_HEXES_RES7: frozenset[str] = _compute_tri_county_hexes_res7()
"""Eagerly computed at import — needed because most callsites pass it directly to
constructors that expect a real frozenset (not a proxy)."""

DETROIT_TRI_COUNTY_AGGREGATE_HEX: str = _compute_aggregate_hex()


# All US FIPS state codes (50 states + DC + 5 territories: 60 American Samoa,
# 66 Guam, 69 Northern Mariana Islands, 72 Puerto Rico, 78 US Virgin Islands).
# Per data-model.md §1.4: this is the canonical default `domestic_states` value
# for CrossBorderCommuteClassifier; any 15-digit Census block whose 2-digit
# state-prefix is in this set routes to rest_of_usa, otherwise to canada.
US_DOMESTIC_FIPS_STATES: frozenset[str] = frozenset(
    [f"{n:02d}" for n in range(1, 57) if n not in (3, 7, 14, 43, 52)]
    + ["60", "66", "69", "72", "78"]
)
"""50 states + DC (11) + 5 territories. Excluded numerics (3,7,14,43,52) are
unassigned in the FIPS-55 codeset; including them would falsely route legitimate
Canadian destinations to rest_of_usa."""


__all__ = [
    "DETROIT_TRI_COUNTY_FIPS",
    "DETROIT_TRI_COUNTY_HEXES_RES7",
    "DETROIT_TRI_COUNTY_AGGREGATE_HEX",
    "DETROIT_PORT_CODES",
    "US_DOMESTIC_FIPS_STATES",
]
