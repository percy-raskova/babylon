"""The Veil of Money — theoretical disclosure tier computation (D7, spec-117 §5d).

Commodity fetishism as a mechanic: the player sees only prices — the
money-form — until theory lets them see through it. Conceptual visibility is
a **pure function** of the player org's ``acquired_doctrine_ids`` (the
ADR073 accumulator), evaluated here at the serialization boundary, the same
place :mod:`game.fog` enforces the *spatial* visibility axis (see that
package's docstrings). No engine change, no Unit 6 dependency: this reads
state the DoctrineSystem already writes.

**Import-pure by construction.** This module takes plain ``str``/``dict``
values, never a ``VeilDefines`` or ``DoctrineTree`` object — like every other
bridge-sibling helper (``game/fog/filter.py`` takes ``node_type: str``,
never a ``NodeType`` enum), it may not import
``babylon.config``/``babylon.models`` (``tests/unit/web/
test_import_boundary.py`` allows only ``game/engine_bridge.py`` and a short
documented allowlist to cross that boundary).
:meth:`EngineBridge.get_economy_dashboard` resolves ``GameDefines().veil``
and the doctrine tree, then calls :func:`compute_veil_status` with the plain
values.

**Gate on MONOTONIC quantities — the implementation trap this design avoids.**
``Organization.acquired_doctrine_ids`` is append-only and dedup-checked
(:func:`babylon.domain.doctrine.mechanics.acquire`) for ordinary acquisition.
The ONE mechanic that can remove a node is the Party Congress: a successful
purge of a held TRAP strips that trap id back out
(:func:`babylon.domain.doctrine.congress.run_congress`'s ``escaped`` branch).
Both configured gate nodes (``VeilDefines.tier1_doctrine_node_id`` /
``tier2_doctrine_node_id``) are non-trap nodes in the shipped tree, so they
can never be un-acquired that way — pinned directly in
``tests/unit/web/test_veil.py``. Gating on the decaying ``doctrine_tags``
accumulator (0.55%/tick decay, and several tree nodes carry NEGATIVE tag
deltas — see ``data/game/doctrine_tree_mvp.json``) or the spendable
``theoretical_labor`` balance (drops to near-zero the instant a node is
bought) would let an unlocked tier flicker or regress, violating the spec's
own §7 monotonicity acceptance gate. Set-membership against an append-only
tuple is monotonic *by construction* — no accumulator arithmetic to get
wrong.

**Reachability arithmetic (I-15 calibration).** ``DoctrineSystem`` accrues
``theoretical_labor += cadre_level * study_allocation`` each tick
(``study_allocation`` fixed at the midpoint of the ratified band, 0.20 —
:mod:`babylon.engine.systems.doctrine`). The nationwide Cadre Council seeds
at ``cadre_level=0.25``:

- Tier 1 (``class_consciousness``, ``cost_tl=0``): the DoctrineSystem
  bootstraps the free root once ``theoretical_labor >= 0``, which holds from
  the first tick it ever runs, for ANY ``cadre_level`` including 0. Reachable
  tick 1.
- Tier 2 (``trade_unionism``, ``cost_tl=25``): ``25 / (0.25 * 0.20) = 500``
  ticks — reachable inside the 520-tick nationwide campaign, but only in its
  final stretch ("the meter is earned", spec-117 §5b). At ``cadre_level=0.1``
  (the legacy ``wayne_county`` dev fixture) that is ``25 / (0.1 * 0.20) =
  1250`` ticks — never reached in one 520-tick campaign; ``wayne_county``
  reverting to a dev fixture (D3) means this is an accepted, documented
  limitation of that fixture, not a bug.

**§5d field -> tier table (G4).** The tier sketch above (money-form / value
relations / scissors) is a category description; this is the literal,
canonical field-name registry every serialization endpoint gates against —
:data:`TIER1_VALUE_RELATION_FIELDS` / :data:`TIER2_SCISSORS_FIELDS`, applied
uniformly by :func:`gate_value_axis_fields`. A field's tier is a property of
its NAME, not of which endpoint happens to emit it — the same
``exploitation_rate`` gates identically whether it appears on the economy
dashboard, a map-lens hex feature, or the social-class inspector.

Tier >= 1 — wage-vs-value-produced axis and the imperial-rent family
(:data:`TIER1_VALUE_RELATION_FIELDS`):

- ``value_produced`` / ``v_value_produced``, ``surplus``,
  ``exploitation_rate`` — the wage-vs-value-produced axis itself.
- ``rent_extracted``, ``imperial_rent`` / ``imperial_rent_pool``,
  ``imperial_rent_gap``, ``imperial_rent_gap_by_region`` — the imperial-rent
  family (Φ = W_c − V_c and its accumulator).
- ``profit_rate`` (s/(c+v)) and ``occ`` (c/v) — value relations built from
  the same surplus-value decomposition, gated identically to
  ``exploitation_rate``.

Tier >= 2 — the price<->value divergence instruments
(:data:`TIER2_SCISSORS_FIELDS`):

- ``price_divergence``, ``fictitious_ratio`` — the scissors themselves.
- ``price_index`` — MELT drift (``price_index - 1``): a dollar's command
  over labor time, the same phenomenal-form-vs-substance reading.
- ``market_corrections`` — the scissors-snap chart marker (cumulative
  correction count), meaningless without the chart it annotates.

Money-form quantities NEVER in either registry, deliberately left ungated
(tier 0, always visible) at every site audited in G4, with the one-line
reasoning a reviewer would otherwise have to re-derive: dollar-denominated
``wealth``/``wealth_by_class_role`` (the money-form itself, spec-117 §5b
precedent — ``wealth_by_class_role``'s CircuitPage relocation); real dollar
flows ``wage_flow_total``/``tribute_flow_total`` (money paid, not a
value-theoretic ratio); ``current_super_wage_rate`` (a wage RATE, same
money-form family as the dollar wages it is a percentage of); ecological or
political axes that were never value-theoretic to begin with — ``heat``,
``biocapacity``, ``consciousness``, ``solidarity``, ``crisis_pop_share``,
``bifurcation_score_mean``, ``wage_compression_mean``,
``capital_stock_total``, ``unemployment_rate_mean``, and
``extraction_intensity`` (metabolic-rift ecological pressure, not a Marxian
value ratio, despite the name).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, NamedTuple


class VeilStatus(NamedTuple):
    """The veil's serialized status for one player org.

    :param tier: ``0``, ``1``, or ``2`` — see module docstring.
    :param next_unlock_node_id: The doctrine node id whose acquisition
        advances the tier, or ``None`` at tier 2 (fully unlocked).
    :param next_unlock_label: That node's human-readable display name, or
        ``None`` at tier 2 — grounds the "Study: X" CTA in real tree data
        rather than a fabricated label (Constitution's Aleksandrov Test).
    """

    tier: int
    next_unlock_node_id: str | None
    next_unlock_label: str | None


def compute_veil_tier(
    acquired_doctrine_ids: Iterable[str],
    tier1_node_id: str,
    tier2_node_id: str,
) -> int:
    """The veil tier: a pure set-membership test, independent per threshold.

    :param acquired_doctrine_ids: The player org's acquired doctrine node
        ids (any order; a tuple, list, or set is accepted).
    :param tier1_node_id: The doctrine node id gating Tier 1
        (``VeilDefines.tier1_doctrine_node_id``).
    :param tier2_node_id: The doctrine node id gating Tier 2
        (``VeilDefines.tier2_doctrine_node_id``).
    :returns: ``2`` if ``tier2_node_id`` is held, else ``1`` if
        ``tier1_node_id`` is held, else ``0``. The tier-2 check is
        independent of tier-1 (a hand-built acquired set naming only the
        tier-2 node still reads tier 2) — real play always holds both,
        since ``trade_unionism``'s only parent is ``class_consciousness``,
        but this function does not assume tree-shape invariants it does not
        need.
    """
    acquired = set(acquired_doctrine_ids)
    if tier2_node_id in acquired:
        return 2
    if tier1_node_id in acquired:
        return 1
    return 0


def compute_veil_status(
    acquired_doctrine_ids: Iterable[str],
    tier1_node_id: str,
    tier2_node_id: str,
    node_labels: Mapping[str, str],
) -> VeilStatus:
    """The full veil status, including the next-unlock study hint.

    :param acquired_doctrine_ids: The player org's acquired doctrine node ids.
    :param tier1_node_id: The doctrine node id gating Tier 1.
    :param tier2_node_id: The doctrine node id gating Tier 2.
    :param node_labels: ``{node_id: display_name}`` for the doctrine tree
        (the caller already holds a loaded tree for other payloads — this
        avoids this import-pure module needing to load one itself). A
        missing id falls back to the raw id itself rather than crashing or
        fabricating a label.
    :returns: The :class:`VeilStatus` for this org.
    """
    tier = compute_veil_tier(acquired_doctrine_ids, tier1_node_id, tier2_node_id)
    if tier >= 2:
        return VeilStatus(tier=2, next_unlock_node_id=None, next_unlock_label=None)

    next_id = tier1_node_id if tier == 0 else tier2_node_id
    label = node_labels.get(next_id, next_id)
    return VeilStatus(tier=tier, next_unlock_node_id=next_id, next_unlock_label=label)


#: Tier >= 1 — the wage-vs-value-produced axis + the imperial-rent family.
#: See the module docstring's "§5d field -> tier table" for the reasoning
#: behind each name. One registry, reused by every G4-audited serialization
#: endpoint via :func:`gate_value_axis_fields`, so a field's tier can never
#: silently drift between two composers that both happen to emit it.
TIER1_VALUE_RELATION_FIELDS: frozenset[str] = frozenset(
    {
        "value_produced",
        "v_value_produced",
        "surplus",
        "exploitation_rate",
        "rent_extracted",
        "imperial_rent",
        "imperial_rent_pool",
        "imperial_rent_gap",
        "imperial_rent_gap_by_region",
        "profit_rate",
        "occ",
    }
)

#: Tier >= 2 — the price<->value divergence instruments (the scissors).
TIER2_SCISSORS_FIELDS: frozenset[str] = frozenset(
    {
        "price_divergence",
        "price_index",
        "fictitious_ratio",
        "market_corrections",
    }
)


def _masked_like(value: Any) -> Any:
    """A same-shape masked replacement for one gated field's value.

    A scalar (float/int/``None``) masks to ``None``. A list of scalars (a
    timeseries payload's parallel array) masks element-wise to a same-length
    list of ``None`` — preserving index-alignment against a sibling
    ``ticks`` array. A list of dicts (a rows-of-regions payload, e.g.
    ``imperial_rent_gap_by_region``) masks to the empty list — the same
    "no region reaches" honest-absence convention that field's own producer
    already uses for a genuine no-data case.
    """
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            return []
        return [None] * len(value)
    return None


def gate_value_axis_fields(payload: Mapping[str, Any], tier: int) -> dict[str, Any]:
    """Null out this payload's ungated value-axis fields below their tier.

    Server-enforced per §5d/D7: a field named in
    :data:`TIER1_VALUE_RELATION_FIELDS` masks below tier 1; one named in
    :data:`TIER2_SCISSORS_FIELDS` masks below tier 2. Every other key in
    ``payload`` (``tick``, ``has_data``, money-form fields, the fog's
    political fields, ...) passes through unchanged — this function only
    ever touches keys it recognizes by name, so it composes safely with
    :func:`~game.fog.filter.apply_fog` (an orthogonal spatial gate) applied
    to the same dict, in either order.

    :param payload: A flat dict about to cross the wire — may itself carry
        list-valued fields (a timeseries payload's parallel arrays); see
        :func:`_masked_like` for how those are masked.
    :param tier: The requesting player org's veil tier (0/1/2,
        :func:`compute_veil_tier`).
    :returns: A new dict; ``payload`` itself is never mutated.
    """
    result = dict(payload)
    for field in TIER1_VALUE_RELATION_FIELDS:
        if field in result and tier < 1:
            result[field] = _masked_like(result[field])
    for field in TIER2_SCISSORS_FIELDS:
        if field in result and tier < 2:
            result[field] = _masked_like(result[field])
    return result


__all__ = [
    "TIER1_VALUE_RELATION_FIELDS",
    "TIER2_SCISSORS_FIELDS",
    "VeilStatus",
    "compute_veil_status",
    "compute_veil_tier",
    "gate_value_axis_fields",
]
