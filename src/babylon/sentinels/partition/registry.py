"""Declared invariants of the emergent class partition (Program 19, ADR070).

The partition sentinel's registry: the ONE canonical derived-cell vocabulary
(the engine's ``ContradictionSystem`` imports :data:`CELL_AXIS_NAMES` /
:func:`cell_name` from here, so writer and sentinel cannot drift — single
source of truth, not duplicate-and-sync) and the declared crosswalk from
derived cells to the seeded ``SocialRole`` vocabulary.

The crosswalk is the sentinel's HYPOTHESIS, not the engine's input: it states
which seeded roles a derived cell is *expected* to contain if the seeded
typology and the flow-derived partition agree. Phase 1 measures that
agreement; nothing adjudicates on it. Two seeded roles map to NO cell by
design — ``LUMPENPROLETARIAT`` and ``CARCERAL_ENFORCER`` sit structurally
outside the wage relation (no ``(w_paid, v_produced)`` accounting), so a
cell-bearing node carrying either is always reported divergent.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from babylon.models.enums.social import SocialRole

__all__ = [
    "CELL_AXIS_NAMES",
    "CELL_TO_SEEDED_ROLES",
    "KNOWN_CELLS",
    "PRINCIPAL_AXES",
    "cell_name",
]

#: The two principal axes whose product forms the derived class cell —
#: the k=2 special case of Constitution I.19's emergent partitions.
PRINCIPAL_AXES: Final[tuple[str, str]] = ("capital_labor", "wage")

#: Pole-side display vocabulary per principal axis. Side ``a``/``b`` follow
#: the opposition's own pole order (capital_labor: wage-labor ⇄ capital;
#: wage: value-produced ⇄ price-of-labor-power, where pole B dominant means
#: the wage exceeds the value produced — the imperial bribe).
CELL_AXIS_NAMES: Final[Mapping[str, Mapping[str, str]]] = {
    "capital_labor": {"a": "labor", "b": "capital"},
    "wage": {"a": "exploited", "b": "bribed"},
}


def cell_name(sides: Mapping[str, str]) -> str | None:
    """Compose the derived class cell from per-axis sides.

    :param sides: Mapping of axis key to side (``"a"``/``"b"``) for the node.
    :returns: The cell string (e.g. ``"labor:bribed"``) when BOTH principal
        axes are present, else ``None`` — a partially-positioned node has no
        cell (Constitution III.11: absence over fabrication).
    """
    parts: list[str] = []
    for axis in PRINCIPAL_AXES:
        side = sides.get(axis)
        if side is None:
            return None
        parts.append(CELL_AXIS_NAMES[axis][side])
    return ":".join(parts)


#: All four derivable cells — the axis-name product.
KNOWN_CELLS: Final[frozenset[str]] = frozenset(
    f"{capital_labor}:{wage}"
    for capital_labor in CELL_AXIS_NAMES["capital_labor"].values()
    for wage in CELL_AXIS_NAMES["wage"].values()
)

#: The declared crosswalk: which seeded roles each derived cell is expected
#: to contain when seeds and flows agree. Values are ``SocialRole.value``
#: strings (what the graph's ``role`` attr stringifies to).
CELL_TO_SEEDED_ROLES: Final[Mapping[str, frozenset[str]]] = {
    # Capital side, net wage-over-value inflow: the rent-collecting poles.
    "capital:bribed": frozenset(
        {SocialRole.CORE_BOURGEOISIE.value, SocialRole.COMPRADOR_BOURGEOISIE.value}
    ),
    # Capital side yet value-exceeds-wage: the contradictory small-owner
    # position (squeezed from above, propped from below).
    "capital:exploited": frozenset({SocialRole.PETTY_BOURGEOISIE.value}),
    # Labor side receiving the bribe: the superwaged stratum.
    "labor:bribed": frozenset({SocialRole.LABOR_ARISTOCRACY.value}),
    # Labor side, net exploited: the revolutionary subject positions.
    "labor:exploited": frozenset(
        {SocialRole.PERIPHERY_PROLETARIAT.value, SocialRole.INTERNAL_PROLETARIAT.value}
    ),
}
