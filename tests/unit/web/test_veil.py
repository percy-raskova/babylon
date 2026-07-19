"""``web/game/veil.py`` — the Veil of Money's pure tier computation (D7, spec-117 §5d).

The veil gates conceptual visibility of value-theoretic economic categories
(as opposed to money/price categories, always visible) behind an org's
doctrine acquisitions. Three properties this suite pins:

1. **Correctness** — tier is exactly a membership test against the two
   configured doctrine-node-id thresholds.
2. **Monotonicity** — ``compute_veil_tier`` is non-decreasing under any
   superset of ``acquired_doctrine_ids`` (Hypothesis property test). This is
   the behavioral contract the spec's §7 "unlocks are monotonic" acceptance
   gate names; gating on set-membership (not the decaying ``doctrine_tags``
   accumulator, not the spendable ``theoretical_labor`` balance which drops
   when a node is bought) is what makes the property hold *by construction*.
3. **The landmine** — ``DoctrineSystem``'s Party Congress can REMOVE a node
   from ``acquired_doctrine_ids`` (a successful purge of a held trap,
   ``congress.run_congress``'s ``escaped`` branch strips ``trap_id`` back
   out — see that module). Monotonicity holds only because the two
   configured gate nodes (``VeilDefines`` defaults) are non-trap nodes that
   no mechanic ever un-holds; this suite pins that invariant directly
   against the real tree so a future defines change that points a tier at a
   trap node fails loudly here rather than silently breaking the veil weeks
   later.

``game.veil`` itself is import-pure (no ``babylon.*`` imports — the web
import-boundary test, ``test_import_boundary.py``, allows only
``game/engine_bridge.py`` and a short documented allowlist to cross into
``babylon.config``/``babylon.models``/etc.; every other bridge-sibling
helper, e.g. ``game/fog/*.py``, stays on plain strings/dicts the same way).
This suite therefore resolves ``VeilDefines``/the real doctrine tree itself
and hands ``game.veil``'s pure functions plain values — the same shape
``EngineBridge.get_economy_dashboard`` assembles them in.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from babylon.config.defines import VeilDefines
from babylon.domain.doctrine import load_doctrine_tree
from game.veil import compute_veil_status, compute_veil_tier

pytestmark = pytest.mark.unit

_DEFINES = VeilDefines()
_TREE = load_doctrine_tree()
_ALL_NODE_IDS = tuple(_TREE.nodes)
_NODE_LABELS = {node_id: node.name for node_id, node in _TREE.nodes.items()}
_TIER1 = _DEFINES.tier1_doctrine_node_id
_TIER2 = _DEFINES.tier2_doctrine_node_id


class TestComputeVeilTierCorrectness:
    def test_empty_acquired_is_tier_zero(self) -> None:
        assert compute_veil_tier((), _TIER1, _TIER2) == 0

    def test_tier1_node_acquired_is_tier_one(self) -> None:
        assert compute_veil_tier(("class_consciousness",), _TIER1, _TIER2) == 1

    def test_both_nodes_acquired_is_tier_two(self) -> None:
        assert compute_veil_tier(("class_consciousness", "trade_unionism"), _TIER1, _TIER2) == 2

    def test_tier2_node_alone_is_still_tier_two(self) -> None:
        """Independent membership tests (spec: gate on set membership, not
        acquisition ORDER) — a hand-built acquired set naming only the tier-2
        node still reads tier 2, even though the real tree makes
        ``trade_unionism`` unreachable without its parent held."""
        assert compute_veil_tier(("trade_unionism",), _TIER1, _TIER2) == 2

    def test_unrelated_nodes_do_not_unlock(self) -> None:
        assert compute_veil_tier(("democratic_centralism", "armed_vanguard"), _TIER1, _TIER2) == 0

    def test_accepts_a_list_not_just_a_tuple(self) -> None:
        """``Organization.acquired_doctrine_ids`` is a tuple at rest, but a
        caller may reasonably hand a list (e.g. a hand-built test fixture)."""
        assert compute_veil_tier(["class_consciousness"], _TIER1, _TIER2) == 1


class TestComputeVeilStatus:
    def test_tier_zero_names_the_tier1_node_as_next_unlock(self) -> None:
        status = compute_veil_status((), _TIER1, _TIER2, _NODE_LABELS)
        assert status.tier == 0
        assert status.next_unlock_node_id == "class_consciousness"
        assert status.next_unlock_label == "Class Consciousness"

    def test_tier_one_names_the_tier2_node_as_next_unlock(self) -> None:
        status = compute_veil_status(("class_consciousness",), _TIER1, _TIER2, _NODE_LABELS)
        assert status.tier == 1
        assert status.next_unlock_node_id == "trade_unionism"
        assert status.next_unlock_label == "Trade Unionism"

    def test_tier_two_has_no_next_unlock(self) -> None:
        status = compute_veil_status(
            ("class_consciousness", "trade_unionism"), _TIER1, _TIER2, _NODE_LABELS
        )
        assert status.tier == 2
        assert status.next_unlock_node_id is None
        assert status.next_unlock_label is None

    def test_falls_back_to_the_raw_id_when_label_unknown(self) -> None:
        """Honest degrade (Constitution III.11): an unresolvable node id
        (e.g. a stale defines override naming a retired node) still returns
        SOMETHING usable rather than crashing or fabricating a label."""
        status = compute_veil_status((), "ghost_node", _TIER2, {})
        assert status.next_unlock_node_id == "ghost_node"
        assert status.next_unlock_label == "ghost_node"


class TestGateNodesAreNeverUnacquirable:
    """The landmine: ``congress.run_congress`` can strip a HELD TRAP back out
    of ``acquired_doctrine_ids`` on a successful purge (see module docstring).
    Both configured gate nodes must be real, non-trap tree nodes so the veil
    can never regress via that path."""

    def test_default_tier1_node_exists_and_is_not_a_trap(self) -> None:
        node = _TREE.nodes[_TIER1]
        assert node.is_trap is False

    def test_default_tier2_node_exists_and_is_not_a_trap(self) -> None:
        node = _TREE.nodes[_TIER2]
        assert node.is_trap is False


class TestMonotonicity:
    """Property: growing the acquired set never lowers the tier."""

    @given(
        base=st.sets(st.sampled_from(_ALL_NODE_IDS)),
        extra=st.sets(st.sampled_from(_ALL_NODE_IDS)),
    )
    def test_superset_never_regresses_the_tier(self, base: set[str], extra: set[str]) -> None:
        grown = base | extra
        assert compute_veil_tier(tuple(grown), _TIER1, _TIER2) >= compute_veil_tier(
            tuple(base), _TIER1, _TIER2
        )
