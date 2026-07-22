"""County-grain INFLUENCES seed computation pipeline (T112; P25 U6/ADR132).

Computes ``seed_influences.json`` for the Detroit tri-county area
(Wayne 26163 + Oakland 26125 + Macomb 26099) per FR-039 + data-model.md §8,
keyed by **county FIPS** — the Amendment-U substrate contract (county_fips
is the sole spatial key the engine reads via ``resolve_county_identity``).
The original res-7 H3 hex keying was retired with this re-key: at county
grain the LODES residential-density proration step disappears, because the
county-level source data applies directly.

Component provenance (honest, per component):

- **FAC_RESTORATIONIST** (``support_type=electoral``) is DATA-DRIVEN: the
  real 2024 presidential Republican vote share per county from the committed
  MIT Election Lab artifact
  (``src/babylon/data/reference/election/mit_countypres_rep_share.csv``,
  registered as ``mit_countypres_rep_share`` in ``data-artifacts.yaml``;
  ADR049 ratified). No jitter — real data needs none.
- **FAC_WORKERS_CONGRESS** (``labor``) and **FAC_DECOLONIAL**
  (``ideological``) remain FIXTURE-GRADE pending their own data programs
  (QCEW union-employment share; AIANNH intersection — minimal in tri-county
  per research.md R-001): a county-centroid zone model against publicly
  known tri-county demographics (Wayne: UAW-legacy union density; the
  Oakland/Macomb ring: lower), with deterministic SHA-256 jitter keyed by
  county FIPS.
- **FAC_LIBERAL_IMPERIAL** (``ideological``) is the complement, clamped to
  ``liberal_imperial_influence_cap``.

Determinism (FR-044 + SC-011): given the same county set + cap + provenance
constants + committed election artifact, the output is byte-identical on
every run. The ``computed_at_iso`` timestamp is fixed (never
``datetime.now()``). Cadre/sympathizer counts use a SHA-256-based
deterministic RNG seeded from ``county_fips + faction_id``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Detroit tri-county FIPS: Wayne, Oakland, Macomb. Mirrors the headless
#: runner's ``DETROIT_TRI_COUNTY_FIPS`` (engine/headless_runner/scopes.py) —
#: duplicated here because the data layer must not import the engine.
TRI_COUNTY_FIPS: tuple[str, ...] = ("26163", "26125", "26099")

#: The committed census atom (county names/centroids) and the MIT Election
#: Lab derivative — both in-repo, so the pipeline never reads the drive.
_DATA_ROOT = Path(__file__).resolve().parents[2]
_COUNTY_ATOM_PATH = _DATA_ROOT / "game" / "us_county_territories.json"
_ELECTION_ARTIFACT_PATH = _DATA_ROOT / "reference" / "election" / "mit_countypres_rep_share.csv"

# Downtown Detroit core (the reference point for zone classification)
DETROIT_CORE: tuple[float, float] = (42.3314, -83.0458)

# Zone distance thresholds (km from Detroit core), applied to county
# centroids. Wayne's centroid falls in the core/inner band; Oakland's and
# Macomb's fall in the outer band — matching the tri-county demographics the
# retired hex fixture encoded.
_CORE_RADIUS_KM: float = 10.0
_INNER_SUBURB_RADIUS_KM: float = 25.0
_OUTER_SUBURB_RADIUS_KM: float = 45.0

DEFAULT_LIBERAL_IMPERIAL_CAP: float = 0.4

# Provenance (per schema seed_influences.schema.json). The election component
# is real (MIT_ELECTION_LAB, ADR049 ratified); qcew/natural_earth remain
# fixture-grade markers for the two zone-model components.
FIXTURE_QCEW_VINTAGE: str = "2024"
FIXTURE_NATURAL_EARTH_VERSION: str = "5.1.2"
FIXTURE_ELECTION_SOURCE: str = "MIT_ELECTION_LAB"
FIXTURE_ELECTION_YEAR: int = 2024

# Fixed timestamp for byte-identical determinism (SC-011)
FIXTURE_COMPUTED_AT: str = "2026-07-22T00:00:00Z"
FIXTURE_VERSION: str = "2.0.0"

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
    """Classify a county centroid by distance from Detroit core."""
    if distance_km < _CORE_RADIUS_KM:
        return _ZONE_CORE
    if distance_km < _INNER_SUBURB_RADIUS_KM:
        return _ZONE_INNER
    if distance_km < _OUTER_SUBURB_RADIUS_KM:
        return _ZONE_OUTER
    return _ZONE_EXURBAN


# ---------------------------------------------------------------------------
# Committed-data readers (in-repo only; never the drive)
# ---------------------------------------------------------------------------


def _county_centroids(county_fips: tuple[str, ...]) -> dict[str, tuple[float, float]]:
    """Read (lat, lon) centroids for the requested counties from the atom."""
    payload = json.loads(_COUNTY_ATOM_PATH.read_text(encoding="utf-8"))
    wanted = set(county_fips)
    centroids: dict[str, tuple[float, float]] = {}
    for county in payload["counties"]:
        if county["fips"] in wanted:
            centroids[county["fips"]] = (county["centroid_lat"], county["centroid_lon"])
    missing = wanted - set(centroids)
    if missing:
        raise KeyError(f"census atom missing counties: {sorted(missing)}")
    return centroids


def _republican_vote_share(county_fips: tuple[str, ...]) -> dict[str, float]:
    """Read the real 2024 Republican vote share from the committed artifact."""
    wanted = set(county_fips)
    shares: dict[str, float] = {}
    with _ELECTION_ARTIFACT_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["county_fips"] in wanted:
                shares[row["county_fips"]] = float(row["rep_vote_share"])
    missing = wanted - set(shares)
    if missing:
        raise KeyError(f"election artifact missing counties: {sorted(missing)}")
    return shares


# ---------------------------------------------------------------------------
# Deterministic RNG (FR-044 + SC-011)
# ---------------------------------------------------------------------------


def _county_seed(county_fips: str) -> int:
    """Deterministic 32-bit integer seed from county FIPS."""
    return int(hashlib.sha256(county_fips.encode("utf-8")).hexdigest()[:8], 16)


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
# Influence level computation
# ---------------------------------------------------------------------------

# Fixture-grade zone bases for the two components without a landed data
# program yet (see module docstring). The values approximate publicly known
# tri-county demographics: Wayne (core/inner) carries the UAW-legacy union
# density; the outer ring carries less; AIANNH intersection is minimal
# everywhere in tri-county (research.md R-001).
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

# Jitter amplitude (±) per fixture-grade faction — keeps totals bounded.
_JITTER_WORKERS: float = 0.04
_JITTER_DECOLONIAL: float = 0.02


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _workers_congress_influence(zone: str, seed: int) -> float:
    """Fixture-grade union-density zone model (QCEW program pending)."""
    base = _BASE_WORKERS[zone]
    jitter = _deterministic_float(seed, "wc") * _JITTER_WORKERS
    return round(_clamp(base + jitter, 0.0, 1.0), 4)


def _decolonial_influence(zone: str, seed: int) -> float:
    """Fixture-grade AIANNH-intersection zone model (minimal per R-001)."""
    base = _BASE_DECOLONIAL[zone]
    jitter = _deterministic_float(seed, "dec") * _JITTER_DECOLONIAL
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


def _cadre_count(faction_id: str, county_fips: str, influence: float) -> int:
    """Deterministic cadre count proportional to influence level."""
    seed = _county_seed(county_fips)
    base = int(round(influence * 40))
    if base == 0:
        return 0
    jitter = _deterministic_int(seed, f"cadre:{faction_id}", 0, max(0, base // 4))
    return base + jitter


def _sympathizer_count(faction_id: str, county_fips: str, influence: float) -> int:
    """Deterministic sympathizer count proportional to influence level."""
    seed = _county_seed(county_fips)
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
    county_fips: str,
    influence: float,
    support_type: str,
) -> dict[str, Any]:
    """Build a single INFLUENCES edge record keyed by county FIPS."""
    return {
        "faction_id": faction_id,
        "territory_id": county_fips,
        "influence_level": influence,
        "support_type": support_type,
        "cadre_count": _cadre_count(faction_id, county_fips, influence),
        "sympathizer_count": _sympathizer_count(faction_id, county_fips, influence),
        "established_tick": 0,
    }


def _compute_county_edges(
    county_fips: str,
    centroid: tuple[float, float],
    rep_share: float,
    liberal_imperial_cap: float,
) -> list[dict[str, Any]]:
    """Compute all 4 faction edges for a single county."""
    distance = _haversine_km(DETROIT_CORE[0], DETROIT_CORE[1], centroid[0], centroid[1])
    zone = _classify_zone(distance)
    seed = _county_seed(county_fips)

    workers = _workers_congress_influence(zone, seed)
    decolonial = _decolonial_influence(zone, seed)
    restorationist = round(_clamp(rep_share, 0.0, 1.0), 4)
    liberal = _liberal_imperial_influence(workers, decolonial, restorationist, liberal_imperial_cap)

    return [
        _build_edge(_FAC_WORKERS_CONGRESS, county_fips, workers, _SUPPORT_TYPE_LABOR),
        _build_edge(_FAC_DECOLONIAL, county_fips, decolonial, _SUPPORT_TYPE_IDEOLOGICAL),
        _build_edge(_FAC_RESTORATIONIST, county_fips, restorationist, _SUPPORT_TYPE_ELECTORAL),
        _build_edge(_FAC_LIBERAL_IMPERIAL, county_fips, liberal, _SUPPORT_TYPE_IDEOLOGICAL),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_seed_influences(
    county_fips: tuple[str, ...] = TRI_COUNTY_FIPS,
    liberal_imperial_cap: float = DEFAULT_LIBERAL_IMPERIAL_CAP,
    qcew_vintage: str = FIXTURE_QCEW_VINTAGE,
    natural_earth_version: str = FIXTURE_NATURAL_EARTH_VERSION,
    election_source: str = FIXTURE_ELECTION_SOURCE,
    election_year: int = FIXTURE_ELECTION_YEAR,
) -> dict[str, Any]:
    """Compute the county-FIPS-keyed INFLUENCES edge seed payload.

    Args:
        county_fips: Counties to seed. Defaults to :data:`TRI_COUNTY_FIPS`
            (Wayne + Oakland + Macomb, the spec-070 fixture scope).
        liberal_imperial_cap: Cap on FAC_LIBERAL_IMPERIAL influence.
            Defaults to 0.4 (per ``BalkanizationDefines``).
        qcew_vintage: QCEW vintage string for provenance (fixture-grade
            component marker).
        natural_earth_version: Natural Earth version for provenance
            (fixture-grade component marker).
        election_source: Election data source. ``MIT_ELECTION_LAB`` since
            ADR049's ratification (the committed artifact backs it).
        election_year: Presidential election year (2024 — FR-039's
            most-recent-election clause).

    Returns:
        Schema-conformant payload dict with keys ``version``,
        ``computed_at_iso``, ``proxy_data_provenance``, ``edges``.

    Raises:
        KeyError: If a requested county is missing from the census atom or
            the committed election artifact (loud failure, never a default).

    Note:
        Output is byte-identical on re-computation (SC-011) given the same
        parameters and committed inputs.
    """
    centroids = _county_centroids(county_fips)
    rep_shares = _republican_vote_share(county_fips)

    edges: list[dict[str, Any]] = []
    for fips in sorted(county_fips):
        edges.extend(
            _compute_county_edges(fips, centroids[fips], rep_shares[fips], liberal_imperial_cap)
        )

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
    "TRI_COUNTY_FIPS",
    "DEFAULT_LIBERAL_IMPERIAL_CAP",
    "FIXTURE_QCEW_VINTAGE",
    "FIXTURE_NATURAL_EARTH_VERSION",
    "FIXTURE_ELECTION_SOURCE",
    "FIXTURE_ELECTION_YEAR",
]
