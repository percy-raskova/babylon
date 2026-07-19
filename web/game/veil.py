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
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import NamedTuple


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


__all__ = ["VeilStatus", "compute_veil_status", "compute_veil_tier"]
