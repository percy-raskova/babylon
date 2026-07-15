"""Tests for babylon.models.entities.doctrine (Epoch 3, Wave 6 foundation).

TDD contract for the Doctrine Tree Phase-0 data models: frozen
construction, the bundled MVP data file loads and validates cleanly, and
the corpus's 3 trunks + root are all present.

NOTE on node count: ``ai/epochs/epoch3/doctrine-tree-mvp.yaml``'s
meta/header sections describe a "15-node" MVP, but the actual authored
``mvp_doctrine_tree.nodes`` mapping in that file contains exactly 11 node
definitions (root + trade_unionism + 3 nodes per trunk x 3 trunks). This
suite asserts against the real, authored 11 nodes.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.doctrine.loader import load_doctrine_tree
from babylon.domain.doctrine.validation import validate_doctrine_tree
from babylon.models.entities.doctrine import DoctrineNode, DoctrineTree
from babylon.models.enums.doctrine import DoctrineTag, DoctrineTrunk

EXPECTED_NODE_COUNT = 11


@pytest.mark.math
class TestDoctrineNodeConstruction:
    """DoctrineNode: frozen, immutable, faithful field shape."""

    def test_construct_minimal_root_node(self) -> None:
        """A root node needs no parents/trunk/tags — all default sanely."""
        node = DoctrineNode(
            id="class_consciousness",
            name="Class Consciousness",
            tier=0,
            description="Recognition that society is divided into classes.",
            cost_tl=0,
        )
        assert node.parents == ()
        assert node.tag_deltas == {}
        assert node.trunk is None
        assert node.unlocks == ()
        assert node.warning is None
        assert node.is_trap is False
        assert node.trap_condition is None
        assert node.narrative is None
        assert node.is_goal is False

    def test_construct_full_trap_node(self) -> None:
        """A trap node carries a trunk, negative deltas, condition, narrative."""
        node = DoctrineNode(
            id="liquidationism",
            name="Liquidationism",
            tier=4,
            parents=("coalition_politics",),
            description="The revolutionary party dissolves into the mass movement.",
            tag_deltas={
                DoctrineTag.MASS_LINK: 4,
                DoctrineTag.CLASS_ANALYSIS: -3,
                DoctrineTag.MILITANCY: -3,
            },
            cost_tl=0,
            trunk=DoctrineTrunk.REFORMIST,
            is_trap=True,
            trap_condition="CLASS_ANALYSIS <= 0 AND MILITANCY <= 0",
            narrative="THE APOCALYPSE CONTINUES, BUT NOW YOU MANAGE IT.",
        )
        assert node.is_trap is True
        assert node.trap_condition == "CLASS_ANALYSIS <= 0 AND MILITANCY <= 0"
        assert node.tag_deltas[DoctrineTag.MASS_LINK] == 4

    def test_node_is_frozen(self) -> None:
        """Attribute assignment after construction is rejected."""
        node = DoctrineNode(
            id="class_consciousness",
            name="Class Consciousness",
            tier=0,
            description="d",
            cost_tl=0,
        )
        with pytest.raises(ValidationError):
            node.tier = 1  # type: ignore[misc]

    def test_node_rejects_extra_fields(self) -> None:
        """extra='forbid' rejects unknown keys (e.g. the deferred special_action)."""
        with pytest.raises(ValidationError):
            DoctrineNode(
                id="x",
                name="X",
                tier=0,
                description="d",
                cost_tl=0,
                bogus_field="nope",
            )

    def test_node_rejects_negative_cost(self) -> None:
        """cost_tl must be >= 0."""
        with pytest.raises(ValidationError):
            DoctrineNode(id="x", name="X", tier=0, description="d", cost_tl=-1)

    def test_node_rejects_invalid_trunk_string(self) -> None:
        """trunk must be a genuine DoctrineTrunk member."""
        with pytest.raises(ValidationError):
            DoctrineNode(
                id="x",
                name="X",
                tier=0,
                description="d",
                cost_tl=0,
                trunk="autonomist",  # not in the MVP's 3 trunks
            )


@pytest.mark.math
class TestDoctrineTreeConstruction:
    """DoctrineTree: frozen container + lookup helpers."""

    def test_tree_is_frozen(self) -> None:
        """Attribute assignment after construction is rejected."""
        root = DoctrineNode(id="root", name="Root", tier=0, description="d", cost_tl=0)
        tree = DoctrineTree(nodes={"root": root}, root_id="root")
        with pytest.raises(ValidationError):
            tree.root_id = "other"  # type: ignore[misc]

    def test_node_lookup(self) -> None:
        """node() returns the matching node; unknown ids raise KeyError."""
        root = DoctrineNode(id="root", name="Root", tier=0, description="d", cost_tl=0)
        tree = DoctrineTree(nodes={"root": root}, root_id="root")
        assert tree.node("root") is root
        with pytest.raises(KeyError):
            tree.node("missing")

    def test_children_of(self) -> None:
        """children_of() is computed from parents, not from unlocks."""
        root = DoctrineNode(id="root", name="Root", tier=0, description="d", cost_tl=0)
        child = DoctrineNode(
            id="child",
            name="Child",
            tier=1,
            parents=("root",),
            description="d",
            cost_tl=5,
        )
        tree = DoctrineTree(nodes={"root": root, "child": child}, root_id="root")
        assert tree.children_of("root") == ("child",)
        assert tree.children_of("child") == ()


@pytest.mark.math
class TestDoctrineTreeMvpDataFile:
    """The bundled doctrine_tree_mvp.json loads and validates cleanly."""

    def test_load_doctrine_tree_succeeds(self) -> None:
        """load_doctrine_tree() does not raise for the canonical data file."""
        tree = load_doctrine_tree()
        # Re-validating an already-valid tree should also be a clean no-op.
        validate_doctrine_tree(tree)

    def test_node_count(self) -> None:
        """The corpus's actually-authored node count is 11 (see module docstring)."""
        tree = load_doctrine_tree()
        assert len(tree.nodes) == EXPECTED_NODE_COUNT

    def test_root_present(self) -> None:
        """class_consciousness is the free, parentless root."""
        tree = load_doctrine_tree()
        root = tree.node(tree.root_id)
        assert root.id == "class_consciousness"
        assert root.parents == ()
        assert root.cost_tl == 0

    def test_all_three_trunks_present(self) -> None:
        """reformist, scientific, and insurrectionist all appear."""
        tree = load_doctrine_tree()
        trunks_present = {node.trunk for node in tree.nodes.values() if node.trunk is not None}
        assert trunks_present == {
            DoctrineTrunk.REFORMIST,
            DoctrineTrunk.SCIENTIFIC,
            DoctrineTrunk.INSURRECTIONIST,
        }

    def test_exactly_one_goal_node(self) -> None:
        """united_front is the sole victory-condition leaf."""
        tree = load_doctrine_tree()
        goals = [node.id for node in tree.nodes.values() if node.is_goal]
        assert goals == ["united_front"]

    def test_exactly_two_trap_nodes(self) -> None:
        """liquidationism and adventurism are the 2 MVP traps."""
        tree = load_doctrine_tree()
        traps = sorted(node.id for node in tree.nodes.values() if node.is_trap)
        assert traps == ["adventurism", "liquidationism"]
