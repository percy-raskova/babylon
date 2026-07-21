"""Pure per-county aggregation math — the projection layer's own helpers.

RELOCATED verbatim from ``babylon.persistence.county_aggregation``
(Program 24 P2 WO-45 layering fix): these three helpers are pure functions
over :class:`~babylon.models.world_state.WorldState` entities and never
touch a database, but their old home made every projection module that
rolls counties up (county/state/national/social_class) drag
``babylon.persistence`` into any client import chain — which the
import-linter contract "tui client reads projections only" rightly
rejects the moment the TUI composes those projections (WO-45's
kind-dispatch registry). ``babylon.persistence.county_aggregation``
re-exports these names unchanged, so every existing bridge/persistence
caller is untouched.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.models.entities.consciousness import TernaryConsciousness
from babylon.models.types import Probability

if TYPE_CHECKING:
    from babylon.models.world_state import WorldState

__all__ = [
    "BridgeMappingError",
    "aggregate_consciousness_for_county",
    "aggregate_survival_for_county",
]


# Simplex tolerance: tighter than TernaryConsciousness._SIMPLEX_TOLERANCE
# (1e-4) because the bridge mapping is algebraically exact and any drift
# above 1e-9 indicates a numerical bug worth surfacing.
_SIMPLEX_ASSERT_TOL = 1e-9


class BridgeMappingError(RuntimeError):
    """Raised when the IdeologicalProfile → TernaryConsciousness mapping
    produces a non-simplex result (should never happen given the
    algebra; raised as a defensive runtime check)."""


# ---------------------------------------------------------------------------
# Bridge mapping: IdeologicalProfile (2-axis) → TernaryConsciousness (3-simplex)
# ---------------------------------------------------------------------------


def _ideology_to_ternary(
    class_consciousness: float,
    national_identity: float,
) -> tuple[float, float, float]:
    """Convert a 2-axis IdeologicalProfile point to a 3-simplex point.

    Bridge mapping (research.md §R10):

        r = class_consciousness × (1 - national_identity)   # revolutionary
        f = national_identity × (1 - class_consciousness)   # fascist
        l = max(0, 1 - r - f)                                # liberal (remainder)

    Algebraic properties (verified by unit tests):

    * ``r + l + f == 1`` by construction (l is the remainder).
    * All three are in ``[0, 1]`` since cc and ni are each in [0, 1] and
      products of two numbers in [0, 1] are in [0, 1], and ``r + f ≤ 1``
      so the ``max(0, ...)`` for l is never load-bearing in non-degenerate
      cases (it's purely a defensive clamp against float drift).
    * Corner mapping:
      - (1, 0) → (r=1, l=0, f=0)   pure revolutionary
      - (0, 1) → (r=0, l=0, f=1)   pure fascist
      - (0, 0) → (r=0, l=1, f=0)   pure liberal (Jackson's unorganized default)
      - (1, 1) → (r=0, l=1, f=0)   "national revolutionary" routes to liberal

    Args:
        class_consciousness: Relationship to Capital, [0.0, 1.0].
        national_identity:   Relationship to State/Tribe, [0.0, 1.0].

    Returns:
        ``(r, l, f)`` simplex coordinates.

    Raises:
        BridgeMappingError: If the computed simplex doesn't sum to 1.0
            within :data:`_SIMPLEX_ASSERT_TOL`. Indicates a numerical bug.
    """
    cc = class_consciousness
    ni = national_identity
    r = cc * (1.0 - ni)
    f = ni * (1.0 - cc)
    l_ = max(0.0, 1.0 - r - f)  # noqa: E741 — l is the natural simplex coordinate name
    total = r + l_ + f
    if abs(total - 1.0) > _SIMPLEX_ASSERT_TOL:
        raise BridgeMappingError(
            f"Bridge mapping produced non-simplex result: "
            f"r={r}, l={l_}, f={f}, sum={total} "
            f"(from cc={cc}, ni={ni})"
        )
    return (r, l_, f)


# ---------------------------------------------------------------------------
# Engine-state aggregators
# ---------------------------------------------------------------------------


def aggregate_survival_for_county(
    world: WorldState,
    county_fips: str,
) -> tuple[float, float, int]:
    """Population-weighted means of ``(p_acquiescence, p_revolution)``.

    Iterates ``world.entities.values()`` and filters to entities where
    ``entity.county_fips == county_fips``. Computes population-weighted
    means over the filtered set. If no entities match the FIPS, returns
    ``(0.0, 0.0, 0)`` — the caller is expected to emit a ``warning``
    severity audit row when ``total_population == 0`` for a county
    that was supposed to have attribution.

    Args:
        world:        Current in-memory WorldState.
        county_fips:  5-digit US county FIPS (e.g., ``"26163"`` for Wayne).

    Returns:
        ``(mean_p_acquiescence, mean_p_revolution, total_population)``.
        Both probabilities are floats in [0, 1]; population is a
        non-negative int.

    See Also:
        :func:`aggregate_consciousness_for_county`: companion helper for
        ideology r/l/f.
    """
    total_population = 0
    sum_p_acq_weighted = 0.0
    sum_p_rev_weighted = 0.0

    for entity in world.entities.values():
        if entity.county_fips != county_fips:
            continue
        pop = int(entity.population)
        if pop <= 0:
            continue
        total_population += pop
        sum_p_acq_weighted += float(entity.p_acquiescence) * pop
        sum_p_rev_weighted += float(entity.p_revolution) * pop

    if total_population == 0:
        return (0.0, 0.0, 0)

    mean_p_acq = sum_p_acq_weighted / total_population
    mean_p_rev = sum_p_rev_weighted / total_population
    return (mean_p_acq, mean_p_rev, total_population)


def aggregate_consciousness_for_county(
    world: WorldState,
    county_fips: str,
) -> TernaryConsciousness:
    """Population-weighted ``(r, l, f)`` over entities in a county.

    For each entity with ``entity.county_fips == county_fips``, applies
    the bridge mapping (see :func:`_ideology_to_ternary`) to convert the
    entity's ``IdeologicalProfile`` to a 3-simplex point, then takes a
    population-weighted mean.

    If the county has no matching entities, returns the
    ``TernaryConsciousness`` substrate default
    (``r=0.3, l=0.6, f=0.1`` — Jackson's "unorganized default,
    liberal-leaning"). This matches spec-034's substrate-floor
    semantics without requiring the substrate-floor machinery.

    Args:
        world:        Current in-memory WorldState.
        county_fips:  5-digit US county FIPS.

    Returns:
        :class:`TernaryConsciousness` with simplex invariant
        ``abs(r + l + f - 1.0) < 1e-9`` (asserted before return).

    Raises:
        BridgeMappingError: If the per-entity simplex mapping fails
            (algebraically should never happen; raised as a defensive
            runtime check).
    """
    total_population = 0
    sum_r_weighted = 0.0
    sum_l_weighted = 0.0
    sum_f_weighted = 0.0

    for entity in world.entities.values():
        if entity.county_fips != county_fips:
            continue
        pop = int(entity.population)
        if pop <= 0:
            continue
        cc = float(entity.ideology.class_consciousness)
        ni = float(entity.ideology.national_identity)
        r_i, l_i, f_i = _ideology_to_ternary(cc, ni)
        total_population += pop
        sum_r_weighted += r_i * pop
        sum_l_weighted += l_i * pop
        sum_f_weighted += f_i * pop

    if total_population == 0:
        # No matching entities; return the substrate default.
        # TernaryConsciousness() with no args uses (0.3, 0.6, 0.1).
        return TernaryConsciousness()

    r = sum_r_weighted / total_population
    l_ = sum_l_weighted / total_population  # noqa: E741
    f = sum_f_weighted / total_population

    # Floating-point drift across many entities could push the sum a
    # few ULPs off 1.0; renormalize defensively.
    total = r + l_ + f
    if abs(total - 1.0) > _SIMPLEX_ASSERT_TOL:
        # Renormalize. If total is effectively zero (shouldn't be —
        # every per-entity mapping produces a valid simplex), fall
        # back to substrate default.
        if total < _SIMPLEX_ASSERT_TOL:
            return TernaryConsciousness()
        r = r / total
        l_ = l_ / total
        f = f / total

    return TernaryConsciousness(
        r=Probability(r),
        l=Probability(l_),
        f=Probability(f),
    )
