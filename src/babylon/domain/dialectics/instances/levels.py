r"""Level lattices: the spatial and social hierarchies as executable Aufhebung.

Phase E grounds :class:`~babylon.domain.dialectics.core.level.LevelLattice` in
Babylon's two real hierarchies:

- **spatial** ``hex ≺ county ≺ state ≺ nation``
- **social** ``individual ≺ community ≺ class ≺ bloc``

Amendment U (#39 T3) adds two PARALLEL county-aggregation rungs above county
that never nest into ``state``: the commuting zone (:func:`cz_adjunction`,
TOTAL) and the metropolitan statistical area (:func:`msa_adjunction`,
PARTIAL) -- both cross state lines by construction, so they sit alongside the
``county ≺ state ≺ nation`` chain rather than inside it. See
:func:`spatial_lattice_rungs_for_counties` for the bundle T6's SubstrateSystem
binding consumes.

The ambient object for BOTH chains is a **keyed field** ``Mapping[str, float]``
(entity id → value, e.g. county fips → capital_labor edge tension). Each level's
skeleton/sheaf modality is the **closure** that broadcasts a field to its
share-weighted regional mean, built from a
:class:`~babylon.domain.dialectics.instances.scale.ScaleAdjunction` over the carrier's
finest entities. For uniform shares this is exactly the design's
``allocate ∘ aggregate`` (sum ÷ n, redistributed 1/n); in general it is
:meth:`ScaleAdjunction.aggregate_intensive` (a contradiction gap is a RATIO,
which must be aggregated by weighted mean, never summed) broadcast back over the
child→parent map. Broadcasting a constant-per-region field again changes
nothing, so the closure is idempotent — a genuine projection onto the
"flat-per-region" subspace, which is Lawvere's skeleton/sheaf closure.

**Resolution = variance decomposition.** With both skeleton and sheaf at a level
equal to that level's closure, Lawvere's condition
``sheaf_higher(skeleton_lower(x)) == skeleton_lower(x)`` (see
:meth:`LevelLattice.is_resolved_at`) reduces to: *smoothing the L-smoothed field
again at level L+1 changes nothing* — i.e. the within-(L+1)-region variance of
the L-aggregates is zero. The contradiction now LIVES at or above L+1. A field
constant within each state but differing between states is therefore *resolved at
county* (county aggregates are flat per state) yet *not resolved at hex* (hexes
still vary within their county); a spatially-uniform field resolves everywhere.

**Shares** are population-weighted where populations are supplied, else uniform
(documented). **NoCommunityFanOut (Constitution II.7 / VIII.9) is honored**: the
social lattice READS the XGI membership layer, it never adds MEMBERSHIP edges.
The individual→community step is single-membership here; the multi-membership
``1/k`` normalized-share generalization is Phase E4's fractal-check concern.

See Also:
    :class:`babylon.domain.dialectics.core.level.LevelLattice`: the generic operator.
    :class:`babylon.domain.dialectics.instances.scale.ScaleAdjunction`: the closure source.
"""

from __future__ import annotations

import csv
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from babylon.domain.dialectics.core.level import Level, LevelLattice, LevelOperators
from babylon.domain.dialectics.instances.scale import ScaleAdjunction

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

__all__ = [
    "LEVEL_INDEX",
    "SOCIAL_LEVEL_NAMES",
    "SPATIAL_LEVEL_NAMES",
    "SpatialLatticeRungs",
    "build_lattice_from_maps",
    "cz_adjunction",
    "level_index_for",
    "msa_adjunction",
    "social_lattice_from_memberships",
    "spatial_lattice_for_counties",
    "spatial_lattice_rungs_for_counties",
]

#: The keyed field the lattices operate over (entity id → scalar).
KeyedField = Mapping[str, float]

_RESOLUTION_TOL = 1e-9
"""Elementwise tolerance for the resolution equality on keyed fields."""

_NATION_ID: Final[str] = "US"
"""The constant every county maps to at the nation rung."""

_BRIDGE_COUNTY_CZ_CSV = (
    Path(__file__).resolve().parents[3] / "data" / "reference" / "bridge_county_cz.csv"
)
"""The committed 1990 USDA ERS commuting-zone crosswalk (Amendment U / #39 T1;
``data-artifacts.yaml`` entry ``bridge_county_cz``; 3141 counties, 741 CZs)."""

_FIPS_VINTAGE_BRIDGES: dict[str, str] = {
    "12086": "12025",  # Miami-Dade County, FL -- renamed from Dade County, 1997.
    "46102": "46113",  # Oglala Lakota County, SD -- renamed from Shannon County, 2015.
    "08014": "08013",  # Broomfield County, CO -- carved from Boulder County, 2001;
    # Broomfield inherits Boulder's CZ (no 1990 CZ exists for a county that
    # did not exist in 1990).
}
"""Modern FIPS -> the 1990-vintage FIPS whose CZ it inherits (Amendment U binding
rule). The 1990 ERS crosswalk predates these three county changes; every OTHER
county absent from the crosswalk is a genuine gap and fails loud (see
:func:`cz_adjunction`'s docstring for the empirically-verified extent of that
gap -- Puerto Rico municipios and post-1990 Alaska/Connecticut reorganizations
-- which this map deliberately does NOT paper over)."""

SPATIAL_LEVEL_NAMES: tuple[str, ...] = ("hex", "county", "state", "nation")
SOCIAL_LEVEL_NAMES: tuple[str, ...] = ("individual", "community", "class", "bloc")

#: Level name → chain index, spanning both hierarchies (names are disjoint, so
#: one map serves both). ``OppositionSpec.level_name`` values index into this.
LEVEL_INDEX: dict[str, int] = {
    "hex": 0,
    "county": 1,
    "state": 2,
    "nation": 3,
    "individual": 0,
    "community": 1,
    "class": 2,
    "bloc": 3,
}


def level_index_for(level_name: str) -> int | None:
    """Return the chain index of a level name, or None if it is unplaced.

    Args:
        level_name: A spatial or social level name (or ``""``/unknown).

    Returns:
        The 0-based chain index, or None when the name is empty or unknown.

    Example:
        >>> level_index_for("county")
        1
        >>> level_index_for("") is None
        True
    """
    return LEVEL_INDEX.get(level_name)


def _fields_equal(a: KeyedField, b: KeyedField, tol: float = _RESOLUTION_TOL) -> bool:
    """Elementwise equality of two keyed fields within ``tol`` (keys must match)."""
    if set(a) != set(b):
        return False
    return all(abs(float(a[key]) - float(b[key])) <= tol for key in a)


def _shares_for(
    mapping: Mapping[str, str],
    populations: Mapping[str, float] | None,
) -> dict[str, float]:
    """Per-child share of its parent: population-weighted, else uniform.

    A parent whose children have no positive population falls back to the uniform
    ``1/n`` split, so the ScaleAdjunction unit-sum law always holds.

    Args:
        mapping: Total function ``child -> parent``.
        populations: Optional per-child weight; None or all-zero-in-group → uniform.

    Returns:
        ``child -> share`` with each parent's shares summing to 1.
    """
    groups: dict[str, list[str]] = {}
    for child, parent in mapping.items():
        groups.setdefault(parent, []).append(child)

    shares: dict[str, float] = {}
    for children in groups.values():
        weights: list[float] | None = None
        if populations is not None:
            candidate = [max(0.0, float(populations.get(child, 0.0))) for child in children]
            if sum(candidate) > 0.0:
                weights = candidate
        if weights is not None:
            total = sum(weights)
            for child, weight in zip(children, weights, strict=True):
                shares[child] = weight / total
        else:
            count = len(children)
            for child in children:
                shares[child] = 1.0 / count
    return shares


def _closure_operator(adj: ScaleAdjunction) -> LevelOperators[KeyedField]:
    """Wrap "broadcast the regional mean" as a level's skeleton/sheaf pair.

    The closure smooths a field to its share-weighted regional value: each child
    is replaced by the mean of its parent's children (:meth:`aggregate_intensive`,
    then broadcast back over the child→parent map). For UNIFORM shares this is
    exactly the design's ``allocate ∘ aggregate`` (sum ÷ n, redistributed 1/n);
    the intensive mean is used because a contradiction gap is a RATIO, which
    :mod:`scale` mandates be aggregated by weighted mean, never summed — this is
    what makes "smooths within-parent variation" (variance → 0) hold for
    population weighting too, not only the uniform law-test case.

    Both modalities are the same closure at this level; the resolution test picks
    ``skeleton`` at the lower level and ``sheaf`` at the higher, so the two ends
    are distinct closures even though each level carries one function.
    """

    def closure(field: KeyedField) -> dict[str, float]:
        regional_mean = adj.aggregate_intensive(field)
        return {child: regional_mean[parent] for child, parent in adj.mapping.items()}

    return LevelOperators(skeleton=closure, sheaf=closure)


def build_lattice_from_maps(
    level_names: Sequence[str],
    parent_maps: Mapping[str, Mapping[str, str]],
    *,
    populations: Mapping[str, float] | None = None,
    tol: float = _RESOLUTION_TOL,
) -> LevelLattice[KeyedField]:
    """Assemble a level lattice from per-level finest→ancestor maps.

    Every map is keyed by the SAME finest entities (the carrier's keys); the
    finest level's map is the identity ``{id: id}``. Each level becomes the
    closure of a :class:`ScaleAdjunction` with population-weighted (else uniform)
    shares.

    Args:
        level_names: The chain, finest first (e.g. ``["county", "state",
            "nation"]``); reordered by chain index internally.
        parent_maps: ``level_name -> {finest_id -> ancestor_id at that level}``.
        populations: Optional per-finest-entity weight for shares.
        tol: Elementwise resolution tolerance.

    Returns:
        A :class:`LevelLattice` over keyed fields.

    Raises:
        ValueError: If ``level_names`` is empty or names an unknown level.
        KeyError: If a level lacks a parent map.
    """
    if not level_names:
        raise ValueError("build_lattice_from_maps requires at least one level")

    ordered = sorted(level_names, key=lambda name: _require_index(name))
    levels: list[Level] = []
    operators: dict[int, LevelOperators[KeyedField]] = {}
    for name in ordered:
        if name not in parent_maps:
            raise KeyError(f"missing parent map for level {name!r}")
        index = _require_index(name)
        mapping = dict(parent_maps[name])
        adj = ScaleAdjunction(mapping=mapping, shares=_shares_for(mapping, populations))
        operators[index] = _closure_operator(adj)
        levels.append(Level(index=index, name=name))
    return LevelLattice(levels, operators, eq=lambda a, b: _fields_equal(a, b, tol))


def _require_index(level_name: str) -> int:
    """Chain index of a level name or ValueError (used where the name must place)."""
    index = LEVEL_INDEX.get(level_name)
    if index is None:
        raise ValueError(f"unknown level name {level_name!r}")
    return index


def _state_parent_map(counties: Sequence[str]) -> dict[str, str]:
    """``county_fips -> 2-digit state prefix`` for every county (TOTAL).

    Shared by :func:`spatial_lattice_for_counties` (the ``chain``'s
    ``state`` level) and :func:`spatial_lattice_rungs_for_counties` (the
    standalone ``state`` :class:`ScaleAdjunction` rung) so the two never
    drift apart.
    """
    return {fips: fips[:2] for fips in counties}


def _nation_parent_map(counties: Sequence[str]) -> dict[str, str]:
    """``county_fips -> "US"`` (the constant nation parent) for every county.

    Shared by :func:`spatial_lattice_for_counties` and
    :func:`spatial_lattice_rungs_for_counties` (see :func:`_state_parent_map`).
    """
    return dict.fromkeys(counties, _NATION_ID)


def spatial_lattice_for_counties(
    counties: Sequence[str],
    *,
    populations: Mapping[str, float] | None = None,
    tol: float = _RESOLUTION_TOL,
) -> LevelLattice[KeyedField]:
    """County-rooted spatial lattice ``county ≺ state ≺ nation``.

    The carrier is county-keyed (the granularity of the per-county capital_labor
    field the regime classifier reads). ``county -> state`` is the 2-digit FIPS
    prefix; ``state -> nation`` is the constant ``"US"``.

    Args:
        counties: County FIPS codes (deduplicated + sorted internally).
        populations: Optional per-county population for share weighting.
        tol: Elementwise resolution tolerance.

    Returns:
        A :class:`LevelLattice` whose finest level (index 1, ``county``) carries
        the identity closure.

    Raises:
        ValueError: If ``counties`` is empty.

    Example:
        >>> lat = spatial_lattice_for_counties(["26001", "26002", "27001"])
        >>> [lvl.name for lvl in lat.levels]
        ['county', 'state', 'nation']
    """
    unique = sorted(set(counties))
    if not unique:
        raise ValueError("spatial_lattice_for_counties requires at least one county")
    parent_maps: dict[str, Mapping[str, str]] = {
        "county": {fips: fips for fips in unique},
        "state": _state_parent_map(unique),
        "nation": _nation_parent_map(unique),
    }
    return build_lattice_from_maps(
        ("county", "state", "nation"),
        parent_maps,
        populations=populations,
        tol=tol,
    )


def _cz_mapping_from_csv(csv_path: Path) -> dict[str, str]:
    """``county_fips -> cz_id`` from the committed crosswalk, vintage-bridged.

    Reads the raw 1990 ERS rows verbatim, then adds one entry per
    :data:`_FIPS_VINTAGE_BRIDGES` key so the three post-1990 counties resolve
    through the county whose CZ they inherited. ``cz_id`` values are carried
    through exactly as stored (already zero-padded 5-char strings in the
    committed CSV) -- the Chetty mobility-atlas tables store the same codes
    unpadded (``int``), a join-format note that lives in the CSV's provenance
    (``data-artifacts.yaml`` / T1's provenance report), not this function.

    Args:
        csv_path: Path to ``bridge_county_cz.csv``.

    Returns:
        Sorted ``{county_fips: cz_id}`` covering the crosswalk's 3141 counties
        plus the 3 bridged modern FIPS (3144 keys total).

    Raises:
        KeyError: If a :data:`_FIPS_VINTAGE_BRIDGES` target is itself absent
            from the crosswalk (would indicate the CSV changed shape).
    """
    mapping: dict[str, str] = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            mapping[row["county_fips"]] = row["cz_id"]
    for modern_fips, vintage_fips in _FIPS_VINTAGE_BRIDGES.items():
        try:
            mapping[modern_fips] = mapping[vintage_fips]
        except KeyError as exc:
            raise KeyError(
                f"_FIPS_VINTAGE_BRIDGES entry {modern_fips!r} -> {vintage_fips!r} but "
                f"{vintage_fips!r} is absent from {csv_path}"
            ) from exc
    return dict(sorted(mapping.items()))


def cz_adjunction() -> ScaleAdjunction:
    """The county -> commuting-zone rung (Amendment U): TOTAL, uniform shares.

    Built from the committed 1990 USDA ERS crosswalk
    (``src/babylon/data/reference/bridge_county_cz.csv``, #39 T1), vintage-
    bridged per :data:`_FIPS_VINTAGE_BRIDGES`. Every commuting zone crosses
    state lines by construction (Amendment U) -- this rung is PARALLEL to
    ``county -> state``, never nested under it.

    ``allocate()`` is even-split (:meth:`ScaleAdjunction.uniform`) until a
    population weighting is deliberately chosen; ``aggregate()`` -- the
    direction T6's SubstrateSystem binding uses -- is share-independent for
    extensive quantities, so the uniform choice does not affect it.

    Totality is real but SCOPED, not universal: this rung resolves every one
    of the crosswalk's 3141 counties plus the 3 vintage-bridged modern FIPS
    (3144 keys). It does NOT cover: Puerto Rico's 78 municipios (CZs are a
    CONUS+AK+HI concept; the 1990 ERS delineation never covered the
    territories), the 51 synthetic ``{state}999`` "rest-of-state" placeholder
    rows the reference DB carries (excluded from "the county universe" the
    same way ``engine.headless_runner.scopes._load_national_fips`` already
    excludes them), and 19 counties created by post-1990 geography changes the
    crosswalk necessarily predates and that have no natural 1:1 predecessor to
    bridge to: Connecticut's 2022 county -> planning-region switch (9 regions,
    each spanning parts of the old counties) and Alaska's repeated borough/
    census-area reorganizations (10 areas, e.g. Kusilvak split from Wade
    Hampton, Chugach/Copper River split from Valdez-Cordova). Indexing
    ``.mapping`` directly for one of those 19 raises Python's own
    ``KeyError`` -- never a silent skip (Constitution III.11).
    :func:`spatial_lattice_rungs_for_counties` -- the caller that must build
    a rung over a real, possibly-gapped county set (#39 T6 M1) -- handles
    this honestly by EXCLUDING those counties from its ``cz`` rung and
    naming them on ``cz_excluded``, rather than propagating the raw
    ``KeyError``. Closing the residual gap itself is a follow-up
    data-acquisition decision (a sourced CT/AK remap or an explicit scope
    carve-out in Amendment U), not something this function fabricates.

    Returns:
        A :class:`ScaleAdjunction` with 3144 counties as children and 741
        commuting zones as parents.
    """
    mapping = _cz_mapping_from_csv(_BRIDGE_COUNTY_CZ_CSV)
    return ScaleAdjunction.uniform(mapping)


def _msa_mapping_from_session(session: Session) -> dict[str, str]:
    """``county_fips -> cbsa_code`` for counties with a Metropolitan Statistical Area.

    Restricted to ``dim_metro_area.area_type == 'msa'`` (excluding
    'micropolitan' and 'csa' rows) -- ``bridge_county_metro`` is a genuine
    many-to-many bridge (a county can sit in an MSA AND a containing CSA), so
    without this filter a county could carry more than one parent, which
    :class:`ScaleAdjunction` forbids (a total function child -> parent). The
    ``msa``-only filter is empirically a clean partition: 0 of the 1252
    MSA-covered counties have more than one ``area_type='msa'`` row.

    Args:
        session: An open reference-DB session (read-only by convention).

    Returns:
        Sorted ``{county_fips: cbsa_code}``, one entry per MSA-covered county
        (partial -- non-metro counties are simply absent).
    """
    from babylon.reference.schema import BridgeCountyMetro, DimCounty, DimMetroArea

    rows = (
        session.query(DimCounty.fips, DimMetroArea.cbsa_code)
        .join(BridgeCountyMetro, BridgeCountyMetro.county_id == DimCounty.county_id)
        .join(DimMetroArea, DimMetroArea.metro_area_id == BridgeCountyMetro.metro_area_id)
        .filter(DimMetroArea.area_type == "msa")
        .order_by(DimCounty.fips)
        .all()
    )
    mapping = {fips: cbsa_code for fips, cbsa_code in rows if cbsa_code is not None}
    return dict(sorted(mapping.items()))


def msa_adjunction() -> ScaleAdjunction:
    """The county -> metro-area rung (Amendment U): PARTIAL, uniform shares.

    Built from the reference DB's ``bridge_county_metro`` / ``dim_metro_area``
    (OMB delineation, ``area_type='msa'``), keyed by ``cbsa_code`` (matches the
    ``msa_code`` field the web layer already carries per territory,
    ``web/game/models.py``/``postgres_schema.py``). Every MSA crosses state
    lines by construction (Amendment U) -- this rung is PARALLEL to
    ``county -> state``, never nested under it.

    Non-metro counties are simply absent from the mapping -- MSA coverage is
    PARTIAL by design (unlike :func:`cz_adjunction`'s totality), and
    :meth:`ScaleAdjunction.aggregate` over a mixed covered/uncovered set
    therefore sums only the covered counties. This is a documented partial
    cover, never grossed up to look total.

    ``allocate()`` is even-split (:meth:`ScaleAdjunction.uniform`) until a
    population weighting is deliberately chosen; ``aggregate()`` -- the
    direction T6's SubstrateSystem binding uses -- is share-independent for
    extensive quantities.

    Returns:
        A :class:`ScaleAdjunction` with the MSA-covered counties (~1252) as
        children and their CBSA codes (~393 distinct MSAs) as parents.
    """
    from babylon.reference.database import get_reference_session

    with get_reference_session() as session:
        mapping = _msa_mapping_from_session(session)
    return ScaleAdjunction.uniform(mapping)


@dataclass(frozen=True)
class SpatialLatticeRungs:
    """All four Amendment U county-aggregation rungs, plus the resolution-law chain.

    ``chain`` is the existing intensive-closure ``county -> state -> nation``
    nesting (identical to calling :func:`spatial_lattice_for_counties` with
    the same arguments) -- for the skeleton/sheaf resolution law
    (:meth:`~babylon.domain.dialectics.core.level.LevelLattice.is_resolved_at`).

    ``cz``, ``msa``, ``state``, and ``nation`` are the four EXTENSIVE-
    aggregatable :class:`ScaleAdjunction` rungs a caller sums a per-county
    stock/flow over (:meth:`ScaleAdjunction.aggregate`, never
    ``aggregate_intensive`` -- shares are irrelevant to an extensive sum, so
    all four use uniform shares regardless of ``populations``). ``state``
    and ``nation`` are TOTAL over every requested county (every FIPS
    resolves to a 2-digit state prefix / the constant ``"US"``). ``cz`` and
    ``msa`` sit ALONGSIDE the state/nation chain, not nested under it --
    both commuting zones and metro areas cross state lines by construction
    (Amendment U). ``msa`` is PARTIAL by design (an uncovered county is
    simply absent, no exclusion bookkeeping needed). ``cz`` is TOTAL over
    the crosswalk, but a requested county absent from it (even after
    vintage-bridge reconciliation) is EXCLUDED from ``cz`` rather than
    raising -- see ``cz_excluded``.

    ``cz_excluded`` names the (possibly empty) subset of requested counties
    with no commuting-zone mapping, sorted for determinism -- derived by
    testing membership in the real crosswalk (never a hardcoded county
    list), so it stays correct if the crosswalk's coverage ever changes.
    """

    chain: LevelLattice[KeyedField]
    cz: ScaleAdjunction
    msa: ScaleAdjunction
    state: ScaleAdjunction
    nation: ScaleAdjunction
    cz_excluded: tuple[str, ...]


def spatial_lattice_rungs_for_counties(
    counties: Sequence[str],
    *,
    populations: Mapping[str, float] | None = None,
    tol: float = _RESOLUTION_TOL,
    cz_adjunction_fn: Callable[[], ScaleAdjunction] = cz_adjunction,
    msa_adjunction_fn: Callable[[], ScaleAdjunction] = msa_adjunction,
) -> SpatialLatticeRungs:
    """All four Amendment U rungs for a county subset, plus the chain.

    Serves the one real shape a production caller needs (#39 T6's
    SubstrateSystem binding, the first and so far only caller): ``state``/
    ``nation`` stay TOTAL over every requested county, so a nationwide sum
    is never silently short, while ``cz`` is SCOPED to the counties the
    crosswalk actually covers -- the rest are named on ``cz_excluded``
    instead of raising. This replaces an earlier design (single shared
    ``counties`` arg feeding both chain AND cz, raising on any cz gap) that
    could not express "total chain + scoped cz" in one call: passing the
    full requested set raised on the first cz-gap county, while passing a
    cz-safe reduced set would ALSO have shrunk ``state``/``nation`` (#39 T6
    M1). ``msa`` is restricted to the SUBSET of requested counties present
    in ``bridge_county_metro`` -- absent counties are simply dropped
    (documented partial-cover semantics, never grossed up).

    Args:
        counties: County FIPS codes (deduplicated + sorted internally, same
            contract as :func:`spatial_lattice_for_counties`).
        populations: Optional per-county population, forwarded to ``chain``
            only. ``cz``/``msa``/``state``/``nation`` always use uniform
            shares (Amendment U binding rule; irrelevant to an extensive
            sum regardless) -- unaffected by ``populations``.
        tol: Elementwise resolution tolerance, forwarded to ``chain``.
        cz_adjunction_fn: Returns the full county -> CZ adjunction (default:
            the real, reference-DB-free :func:`cz_adjunction`). Injectable
            so a caller (e.g. SubstrateSystem) can forward its own
            test-injected source without duplicating this function's logic.
        msa_adjunction_fn: Returns the full county -> MSA adjunction
            (default: the real :func:`msa_adjunction`, which opens a
            reference-DB session). Injectable for the same reason.

    Returns:
        A :class:`SpatialLatticeRungs` bundling ``chain`` with the four
        EXTENSIVE rungs (``cz``, ``msa``, ``state``, ``nation``) and
        ``cz_excluded``, each freshly recomputed over exactly this county
        subset (so every :class:`ScaleAdjunction`'s per-parent shares
        validly sum to 1 -- a global/nationwide share would NOT sum to 1
        over a partial subset).

    Raises:
        ValueError: If ``counties`` is empty (from ``chain``'s construction).
    """
    unique = sorted(set(counties))
    chain = spatial_lattice_for_counties(unique, populations=populations, tol=tol)

    full_cz = cz_adjunction_fn().mapping
    cz_covered = [fips for fips in unique if fips in full_cz]
    cz_excluded = tuple(sorted(set(unique) - set(cz_covered)))
    cz_rung = ScaleAdjunction.uniform({fips: full_cz[fips] for fips in cz_covered})

    full_msa = msa_adjunction_fn().mapping
    msa_rung = ScaleAdjunction.uniform(
        {fips: full_msa[fips] for fips in unique if fips in full_msa}
    )

    state_rung = ScaleAdjunction.uniform(_state_parent_map(unique))
    nation_rung = ScaleAdjunction.uniform(_nation_parent_map(unique))

    return SpatialLatticeRungs(
        chain=chain,
        cz=cz_rung,
        msa=msa_rung,
        state=state_rung,
        nation=nation_rung,
        cz_excluded=cz_excluded,
    )


def social_lattice_from_memberships(
    memberships: Mapping[str, str],
    community_class: Mapping[str, str],
    class_bloc: Mapping[str, str],
    *,
    populations: Mapping[str, float] | None = None,
    tol: float = _RESOLUTION_TOL,
) -> LevelLattice[KeyedField]:
    """Individual-rooted social lattice ``individual ≺ community ≺ class ≺ bloc``.

    Reads the XGI membership span WITHOUT mutating it (NoCommunityFanOut): the
    caller passes the single-membership ``agent -> community`` span, the
    dominant-``SocialRole`` ``community -> class`` fold (this is where
    LUMPENPROLETARIAT folds into the proletarian pole), and the
    ``class -> bloc`` (core/periphery) assignment.

    The individual→community step is single-membership here; an agent in
    multiple communities (normalized ``1/k`` stochastic allocate) is Phase E4's
    fractal-check concern and is not required by this builder.

    Args:
        memberships: ``agent_id -> community_id`` (the XGI span, single-valued).
        community_class: ``community_id -> class-pole`` (dominant member role).
        class_bloc: ``class-pole -> bloc`` (core/periphery).
        populations: Optional per-agent weight for share weighting.
        tol: Elementwise resolution tolerance.

    Returns:
        A :class:`LevelLattice` over agent-keyed fields.

    Raises:
        KeyError: If a membership's community, or a community's class, is absent
            from the fold maps (the logic layer fails loud, never fabricating a
            pole).
    """
    agents = sorted(memberships)
    community_of = {agent: memberships[agent] for agent in agents}
    class_of = {
        agent: _lookup(community_class, community_of[agent], "community") for agent in agents
    }
    bloc_of = {agent: _lookup(class_bloc, class_of[agent], "class") for agent in agents}
    parent_maps: dict[str, Mapping[str, str]] = {
        "individual": {agent: agent for agent in agents},
        "community": community_of,
        "class": class_of,
        "bloc": bloc_of,
    }
    return build_lattice_from_maps(
        ("individual", "community", "class", "bloc"),
        parent_maps,
        populations=populations,
        tol=tol,
    )


def _lookup(fold: Mapping[str, str], key: str, kind: str) -> str:
    """Fold-map lookup that fails loud rather than fabricating a parent."""
    try:
        return fold[key]
    except KeyError as exc:
        raise KeyError(f"{kind} {key!r} has no fold-map entry") from exc
