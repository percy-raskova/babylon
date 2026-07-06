"""Proxy-data INFLUENCES seed computation pipeline (T112).

Computes ``seed_influences.json`` for the Detroit tri-county area
(Wayne + Oakland + Macomb counties) per FR-039 + data-model.md §8.

This module ships a **fixture-grade** computation that approximates the
real QCEW/LODES/AIANNH/election pipeline with a geographic demographic
model. The approximation is grounded in publicly known tri-county
demographics:

- **Detroit core**: high union density (UAW legacy), heavily Democratic
  presidential vote, minimal AIANNH intersection (per research.md R-001:
  "Wayne / Oakland / Macomb counties intersect with no major AIANNH
  areas").
- **Inner suburbs** (Dearborn, Hamtramck, Highland Park ring): moderate
  union, mixed voting.
- **Outer suburbs** (Livonia, Warren, Southfield): lower union density,
  more Republican.
- **Exurban** (northern Oakland/Macomb): lowest union, most Republican.

The fixture uses ``CENSUS_BUREAU_FIXTURE`` provenance per the schema's
``election_source`` enum. When real QCEW/LODES/AIANNH/election data
becomes available, the ``_workers_congress_influence``,
``_decolonial_influence``, and ``_restorationist_influence`` functions
can be replaced with data-driven loaders without changing the module
interface.

Determinism (FR-044 + SC-011): given the same bounding box + resolution +
cap + provenance constants, the output is byte-identical on every run.
The ``computed_at_iso`` timestamp is fixed (not ``datetime.now()``).
Cadre/sympathizer counts use a SHA-256-based deterministic RNG seeded
from ``hex_id + faction_id``.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import h3

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tri-county bounding box: covers Wayne (26163) + Oakland (26125) +
# Macomb (26099) with a small margin to catch edge hexes.
TRI_COUNTY_BOUNDS: dict[str, float] = {
    "lat_min": 42.05,
    "lat_max": 43.10,
    "lon_min": -83.70,
    "lon_max": -82.80,
}

H3_RESOLUTION: int = 7

# Downtown Detroit core (the reference point for zone classification)
DETROIT_CORE: tuple[float, float] = (42.3314, -83.0458)

# Zone distance thresholds (km from Detroit core)
_CORE_RADIUS_KM: float = 10.0
_INNER_SUBURB_RADIUS_KM: float = 25.0
_OUTER_SUBURB_RADIUS_KM: float = 45.0

DEFAULT_LIBERAL_IMPERIAL_CAP: float = 0.4

# Fixture provenance (per schema seed_influences.schema.json)
FIXTURE_QCEW_VINTAGE: str = "2024"
FIXTURE_NATURAL_EARTH_VERSION: str = "5.1.2"
FIXTURE_ELECTION_SOURCE: str = "CENSUS_BUREAU_FIXTURE"
FIXTURE_ELECTION_YEAR: int = 2020

# Fixed timestamp for byte-identical determinism (SC-011)
FIXTURE_COMPUTED_AT: str = "2026-01-01T00:00:00Z"
FIXTURE_VERSION: str = "1.0.0"

# Faction IDs (must match seed_factions.json)
_FAC_WORKERS_CONGRESS: str = "FAC_WORKERS_CONGRESS"
_FAC_DECOLONIAL: str = "FAC_DECOLONIAL"
_FAC_RESTORATIONIST: str = "FAC_RESTORATIONIST"
_FAC_LIBERAL_IMPERIAL: str = "FAC_LIBERAL_IMPERIAL"

# Support type mapping (per schema description + data-model.md §8)
_SUPPORT_TYPE_LABOR: str = "labor"
_SUPPORT_TYPE_IDEOLOGICAL: str = "ideological"
_SUPPORT_TYPE_ELECTORAL: str = "electoral"

# Zone classification labels
_ZONE_CORE: str = "detroit_core"
_ZONE_INNER: str = "inner_suburb"
_ZONE_OUTER: str = "outer_suburb"
_ZONE_EXURBAN: str = "exurban"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km (Haversine formula)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _classify_zone(distance_km: float) -> str:
    """Classify a hex by distance from Detroit core into a demographic zone."""
    if distance_km < _CORE_RADIUS_KM:
        return _ZONE_CORE
    if distance_km < _INNER_SUBURB_RADIUS_KM:
        return _ZONE_INNER
    if distance_km < _OUTER_SUBURB_RADIUS_KM:
        return _ZONE_OUTER
    return _ZONE_EXURBAN


def _generate_tri_county_hexes(
    bounds: dict[str, float],
    resolution: int,
) -> list[str]:
    """Generate sorted H3 cell IDs within the tri-county bounding box.

    The bounding box is a rough rectangle; a real pipeline would filter to
    the three county FIPS polygons. For the fixture, the bounding box is
    sufficient and deterministic.
    """
    polygon = h3.LatLngPoly(
        [
            (bounds["lat_min"], bounds["lon_min"]),
            (bounds["lat_max"], bounds["lon_min"]),
            (bounds["lat_max"], bounds["lon_max"]),
            (bounds["lat_min"], bounds["lon_max"]),
        ]
    )
    cells = h3.polygon_to_cells(polygon, resolution)
    return sorted(cells)


# ---------------------------------------------------------------------------
# Deterministic RNG (FR-044 + SC-011)
# ---------------------------------------------------------------------------


def _hex_seed(hex_id: str) -> int:
    """Deterministic 32-bit integer seed from hex ID."""
    return int(hashlib.sha256(hex_id.encode("utf-8")).hexdigest()[:8], 16)


def _deterministic_float(seed: int, salt: str) -> float:
    """Deterministic float in [-0.5, 0.5) from seed + salt."""
    h = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()
    return (int(h[:8], 16) / 0xFFFFFFFF) - 0.5


def _deterministic_int(seed: int, salt: str, lo: int, hi: int) -> int:
    """Deterministic integer in [lo, hi] (inclusive) from seed + salt."""
    if hi < lo:
        return lo
    h = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()
    span = hi - lo + 1
    return lo + (int(h[:8], 16) % span)


# ---------------------------------------------------------------------------
# Influence level computation (fixture-grade)
# ---------------------------------------------------------------------------

# Base influence levels by zone. These approximate publicly known
# demographics of the Detroit tri-county area:
# - Detroit core: UAW legacy → high Workers' Congress; heavily
#   Democratic → low Restorationist; minimal AIANNH → low Decolonial.
# - Exurban ring: lower union density; more Republican.
_BASE_WORKERS: dict[str, float] = {
    _ZONE_CORE: 0.62,
    _ZONE_INNER: 0.42,
    _ZONE_OUTER: 0.28,
    _ZONE_EXURBAN: 0.20,
}
_BASE_DECOLONIAL: dict[str, float] = {
    _ZONE_CORE: 0.08,
    _ZONE_INNER: 0.05,
    _ZONE_OUTER: 0.03,
    _ZONE_EXURBAN: 0.02,
}
_BASE_RESTORATIONIST: dict[str, float] = {
    _ZONE_CORE: 0.10,
    _ZONE_INNER: 0.32,
    _ZONE_OUTER: 0.48,
    _ZONE_EXURBAN: 0.58,
}

# Jitter amplitude (±) per faction — keeps totals bounded.
_JITTER_WORKERS: float = 0.04
_JITTER_DECOLONIAL: float = 0.02
_JITTER_RESTORATIONIST: float = 0.05


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _workers_congress_influence(zone: str, seed: int) -> float:
    """Union-employment-share prorated by LODES residential density."""
    base = _BASE_WORKERS[zone]
    jitter = _deterministic_float(seed, "wc") * _JITTER_WORKERS
    return round(_clamp(base + jitter, 0.0, 1.0), 4)


def _decolonial_influence(zone: str, seed: int) -> float:
    """AIANNH intersection area (minimal in tri-county per R-001)."""
    base = _BASE_DECOLONIAL[zone]
    jitter = _deterministic_float(seed, "dec") * _JITTER_DECOLONIAL
    return round(_clamp(base + jitter, 0.0, 1.0), 4)


def _restorationist_influence(zone: str, seed: int) -> float:
    """Republican presidential vote share prorated by LODES."""
    base = _BASE_RESTORATIONIST[zone]
    jitter = _deterministic_float(seed, "res") * _JITTER_RESTORATIONIST
    return round(_clamp(base + jitter, 0.0, 1.0), 4)


def _liberal_imperial_influence(
    workers: float,
    decolonial: float,
    restorationist: float,
    cap: float,
) -> float:
    """Complement clamped to ``liberal_imperial_influence_cap``."""
    complement = 1.0 - (workers + decolonial + restorationist)
    return round(_clamp(complement, 0.0, cap), 4)


# ---------------------------------------------------------------------------
# Cadre / sympathizer counts
# ---------------------------------------------------------------------------


def _cadre_count(faction_id: str, hex_id: str, influence: float) -> int:
    """Deterministic cadre count proportional to influence level."""
    seed = _hex_seed(hex_id)
    base = int(round(influence * 40))
    if base == 0:
        return 0
    jitter = _deterministic_int(seed, f"cadre:{faction_id}", 0, max(0, base // 4))
    return base + jitter


def _sympathizer_count(faction_id: str, hex_id: str, influence: float) -> int:
    """Deterministic sympathizer count proportional to influence level."""
    seed = _hex_seed(hex_id)
    base = int(round(influence * 400))
    if base == 0:
        return 0
    jitter = _deterministic_int(seed, f"sym:{faction_id}", 0, max(0, base // 4))
    return base + jitter


# ---------------------------------------------------------------------------
# Edge construction
# ---------------------------------------------------------------------------


def _build_edge(
    faction_id: str,
    hex_id: str,
    influence: float,
    support_type: str,
) -> dict[str, Any]:
    """Build a single INFLUENCES edge record."""
    return {
        "faction_id": faction_id,
        "territory_id": hex_id,
        "influence_level": influence,
        "support_type": support_type,
        "cadre_count": _cadre_count(faction_id, hex_id, influence),
        "sympathizer_count": _sympathizer_count(faction_id, hex_id, influence),
        "established_tick": 0,
    }


def _compute_hex_edges(
    hex_id: str,
    liberal_imperial_cap: float,
) -> list[dict[str, Any]]:
    """Compute all 4 faction edges for a single hex."""
    lat, lon = h3.cell_to_latlng(hex_id)
    distance = _haversine_km(DETROIT_CORE[0], DETROIT_CORE[1], lat, lon)
    zone = _classify_zone(distance)
    seed = _hex_seed(hex_id)

    workers = _workers_congress_influence(zone, seed)
    decolonial = _decolonial_influence(zone, seed)
    restorationist = _restorationist_influence(zone, seed)
    liberal = _liberal_imperial_influence(workers, decolonial, restorationist, liberal_imperial_cap)

    return [
        _build_edge(_FAC_WORKERS_CONGRESS, hex_id, workers, _SUPPORT_TYPE_LABOR),
        _build_edge(_FAC_DECOLONIAL, hex_id, decolonial, _SUPPORT_TYPE_IDEOLOGICAL),
        _build_edge(_FAC_RESTORATIONIST, hex_id, restorationist, _SUPPORT_TYPE_ELECTORAL),
        _build_edge(_FAC_LIBERAL_IMPERIAL, hex_id, liberal, _SUPPORT_TYPE_IDEOLOGICAL),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_seed_influences(
    bounds: dict[str, float] | None = None,
    resolution: int = H3_RESOLUTION,
    liberal_imperial_cap: float = DEFAULT_LIBERAL_IMPERIAL_CAP,
    qcew_vintage: str = FIXTURE_QCEW_VINTAGE,
    natural_earth_version: str = FIXTURE_NATURAL_EARTH_VERSION,
    election_source: str = FIXTURE_ELECTION_SOURCE,
    election_year: int = FIXTURE_ELECTION_YEAR,
) -> dict[str, Any]:
    """Compute the INFLUENCES edge seed payload for the Detroit tri-county area.

    Args:
        bounds: Optional bounding box override. Defaults to
            :data:`TRI_COUNTY_BOUNDS`.
        resolution: H3 resolution. Defaults to 7 (per spec R-004).
        liberal_imperial_cap: Cap on FAC_LIBERAL_IMPERIAL influence.
            Defaults to 0.4 (per ``BalkanizationDefines``).
        qcew_vintage: QCEW vintage string for provenance.
        natural_earth_version: Natural Earth version for provenance.
        election_source: Election data source (``MIT_ELECTION_LAB`` or
            ``CENSUS_BUREAU_FIXTURE``).
        election_year: Presidential election year.

    Returns:
        Schema-conformant payload dict with keys ``version``,
        ``computed_at_iso``, ``proxy_data_provenance``, ``edges``.

    Note:
        Output is byte-identical on re-computation (SC-011) given the
        same parameters.
    """
    if bounds is None:
        bounds = TRI_COUNTY_BOUNDS

    hexes = _generate_tri_county_hexes(bounds, resolution)

    edges: list[dict[str, Any]] = []
    for hex_id in hexes:
        edges.extend(_compute_hex_edges(hex_id, liberal_imperial_cap))

    return {
        "version": FIXTURE_VERSION,
        "computed_at_iso": FIXTURE_COMPUTED_AT,
        "proxy_data_provenance": {
            "qcew_vintage": qcew_vintage,
            "natural_earth_version": natural_earth_version,
            "election_source": election_source,
            "election_year": election_year,
        },
        "edges": edges,
    }


def write_seed_influences(
    output_path: Path | None = None,
    **kwargs: Any,
) -> Path:
    """Compute and write ``seed_influences.json``.

    Args:
        output_path: Optional output path. Defaults to the in-package
            ``seed_influences.json`` next to this module.
        **kwargs: Passed through to :func:`compute_seed_influences`.

    Returns:
        The path where the file was written.
    """
    if output_path is None:
        output_path = Path(__file__).resolve().parent / "seed_influences.json"

    payload = compute_seed_influences(**kwargs)
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    output_path.write_text(text, encoding="utf-8")
    return output_path


__all__ = [
    "compute_seed_influences",
    "write_seed_influences",
    "TRI_COUNTY_BOUNDS",
    "H3_RESOLUTION",
    "DEFAULT_LIBERAL_IMPERIAL_CAP",
    "FIXTURE_QCEW_VINTAGE",
    "FIXTURE_NATURAL_EARTH_VERSION",
    "FIXTURE_ELECTION_SOURCE",
    "FIXTURE_ELECTION_YEAR",
]
