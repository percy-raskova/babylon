r"""Level lattices: the spatial and social hierarchies as executable Aufhebung.

Phase E grounds :class:`~babylon.domain.dialectics.core.level.LevelLattice` in
Babylon's two real hierarchies:

- **spatial** ``hex ≺ county ≺ state ≺ nation``
- **social** ``individual ≺ community ≺ class ≺ bloc``

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

from collections.abc import Mapping, Sequence

from babylon.domain.dialectics.core.level import Level, LevelLattice, LevelOperators
from babylon.domain.dialectics.instances.scale import ScaleAdjunction

__all__ = [
    "LEVEL_INDEX",
    "SOCIAL_LEVEL_NAMES",
    "SPATIAL_LEVEL_NAMES",
    "build_lattice_from_maps",
    "level_index_for",
    "social_lattice_from_memberships",
    "spatial_lattice_for_counties",
]

#: The keyed field the lattices operate over (entity id → scalar).
KeyedField = Mapping[str, float]

_RESOLUTION_TOL = 1e-9
"""Elementwise tolerance for the resolution equality on keyed fields."""

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
        "state": {fips: fips[:2] for fips in unique},
        "nation": dict.fromkeys(unique, "US"),
    }
    return build_lattice_from_maps(
        ("county", "state", "nation"),
        parent_maps,
        populations=populations,
        tol=tol,
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
