"""Tests for babylon.domain.doctrine.validation (Phase 0 foundation).

TDD contract for ``validate_doctrine_tree()``: rejects dangling
references, multiple/missing roots, cycles in the parent graph, traps
missing a ``trap_condition``, and non-leaf goal nodes; accepts the real
MVP corpus tree.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.domain.doctrine.loader import load_doctrine_tree
from babylon.domain.doctrine.validation import (
    DoctrineValidationError,
    validate_doctrine_tree,
)
from babylon.models.entities.doctrine import DoctrineNode, DoctrineTree


def _node(**overrides: Any) -> DoctrineNode:
    """Build a minimal DoctrineNode for hand-crafted broken-tree fixtures."""
    defaults: dict[str, Any] = {
        "id": "n",
        "name": "N",
        "tier": 0,
        "description": "d",
        "cost_tl": 0,
    }
    defaults.update(overrides)
    return DoctrineNode(**defaults)


@pytest.mark.math
class TestValidateRealMvpTree:
    """The real corpus tree must validate cleanly."""

    def test_accepts_real_mvp_tree(self) -> None:
        """load_doctrine_tree() already validates; re-validating is a no-op."""
        tree = load_doctrine_tree()
        validate_doctrine_tree(tree)


@pytest.mark.math
class TestValidateDanglingReferences:
    """Unknown parent/unlocks/root_id ids are rejected."""

    def test_rejects_dangling_parent(self) -> None:
        root = _node(id="root")
        child = _node(id="child", tier=1, parents=("ghost",), cost_tl=5)
        tree = DoctrineTree(nodes={"root": root, "child": child}, root_id="root")
        with pytest.raises(DoctrineValidationError) as exc_info:
            validate_doctrine_tree(tree)
        assert any("ghost" in v for v in exc_info.value.violations)

    def test_rejects_dangling_unlocks(self) -> None:
        root = _node(id="root", unlocks=("ghost",))
        tree = DoctrineTree(nodes={"root": root}, root_id="root")
        with pytest.raises(DoctrineValidationError) as exc_info:
            validate_doctrine_tree(tree)
        assert any("ghost" in v for v in exc_info.value.violations)

    def test_rejects_unknown_root_id(self) -> None:
        root = _node(id="root")
        tree = DoctrineTree(nodes={"root": root}, root_id="not_a_node")
        with pytest.raises(DoctrineValidationError) as exc_info:
            validate_doctrine_tree(tree)
        assert any("not_a_node" in v for v in exc_info.value.violations)


@pytest.mark.math
class TestValidateRootCount:
    """Exactly one parentless, cost-0 root is required."""

    def test_rejects_two_roots(self) -> None:
        root_a = _node(id="root_a")
        root_b = _node(id="root_b")
        tree = DoctrineTree(nodes={"root_a": root_a, "root_b": root_b}, root_id="root_a")
        with pytest.raises(DoctrineValidationError) as exc_info:
            validate_doctrine_tree(tree)
        assert any("exactly 1 root" in v for v in exc_info.value.violations)

    def test_rejects_zero_roots_and_reports_the_underlying_cycle(self) -> None:
        """No node has empty parents: a finite mutual-parent pair has no root

        AND is necessarily a cycle. Both violations should be reported —
        this is the "circular dependency" case the corpus calls out as THE
        guard case.
        """
        a = _node(id="a", parents=("b",), cost_tl=5)
        b = _node(id="b", parents=("a",), cost_tl=5)
        tree = DoctrineTree(nodes={"a": a, "b": b}, root_id="a")
        with pytest.raises(DoctrineValidationError) as exc_info:
            validate_doctrine_tree(tree)
        violations = exc_info.value.violations
        assert any("exactly 1 root" in v for v in violations)
        assert any("cycle detected" in v for v in violations)


@pytest.mark.math
class TestValidateCycle:
    """Cycles in the parent graph are rejected even with a valid root."""

    def test_rejects_cycle_among_non_root_nodes(self) -> None:
        root = _node(id="root")
        p = _node(id="p", tier=1, parents=("q",), cost_tl=5)
        q = _node(id="q", tier=1, parents=("p",), cost_tl=5)
        tree = DoctrineTree(nodes={"root": root, "p": p, "q": q}, root_id="root")
        with pytest.raises(DoctrineValidationError) as exc_info:
            validate_doctrine_tree(tree)
        assert any("cycle detected" in v for v in exc_info.value.violations)


@pytest.mark.math
class TestValidateTrapAndGoalFlags:
    """is_trap requires trap_condition; is_goal requires being a leaf."""

    def test_rejects_trap_without_condition(self) -> None:
        root = _node(id="root")
        trap = _node(
            id="trap",
            tier=1,
            parents=("root",),
            is_trap=True,
            trap_condition=None,
        )
        tree = DoctrineTree(nodes={"root": root, "trap": trap}, root_id="root")
        with pytest.raises(DoctrineValidationError) as exc_info:
            validate_doctrine_tree(tree)
        assert any("is_trap=True but no trap_condition" in v for v in exc_info.value.violations)

    def test_rejects_goal_that_is_not_a_leaf(self) -> None:
        root = _node(id="root")
        goal = _node(id="goal", tier=1, parents=("root",), cost_tl=5, is_goal=True)
        grandchild = _node(id="grandchild", tier=2, parents=("goal",), cost_tl=5)
        tree = DoctrineTree(
            nodes={"root": root, "goal": goal, "grandchild": grandchild},
            root_id="root",
        )
        with pytest.raises(DoctrineValidationError) as exc_info:
            validate_doctrine_tree(tree)
        assert any("is_goal=True but is not a leaf" in v for v in exc_info.value.violations)

    def test_accepts_goal_leaf(self) -> None:
        root = _node(id="root")
        goal = _node(id="goal", tier=1, parents=("root",), cost_tl=5, is_goal=True)
        tree = DoctrineTree(nodes={"root": root, "goal": goal}, root_id="root")
        validate_doctrine_tree(tree)  # should not raise
