"""Structural validity checks for the Doctrine Tree (Phase 0 foundation).

Validates that a :class:`~babylon.models.entities.doctrine.DoctrineTree` is
a well-formed DAG with a single root, monotonically increasing tiers,
referentially intact ``parents``/``unlocks``, and consistent trap/goal
node flags. This module intentionally does NOT evaluate ``trap_condition``
expressions or wire acquisition side effects — that is gated engine work,
out of scope for the data-foundation layer.
"""

from __future__ import annotations

from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.enums.doctrine import DoctrineTrunk


class DoctrineValidationError(ValueError):
    """Raised when a :class:`DoctrineTree` fails structural validation.

    Collects every independent structural defect found across a single
    validation pass so a caller sees the full picture instead of a
    fix-one-rerun loop.

    Attributes:
        violations: All violation messages found, in the order the checks
            ran. Never empty when this exception is raised.
    """

    def __init__(self, violations: list[str]) -> None:
        """Initialize the exception.

        Args:
            violations: Non-empty list of human-readable violation
                descriptions.
        """
        message = "Doctrine tree validation failed:\n" + "\n".join(f"  - {v}" for v in violations)
        super().__init__(message)
        self.violations = tuple(violations)


def _check_referential_integrity(tree: DoctrineTree) -> list[str]:
    """Check that every ``parents``/``unlocks`` id resolves to a real node.

    Args:
        tree: The tree to check.

    Returns:
        Violation messages (empty if all references resolve).
    """
    violations: list[str] = []
    known_ids = set(tree.nodes.keys())
    for node in tree.nodes.values():
        for parent_id in node.parents:
            if parent_id not in known_ids:
                violations.append(f"node '{node.id}' declares unknown parent id '{parent_id}'")
        for child_id in node.unlocks:
            if child_id not in known_ids:
                violations.append(f"node '{node.id}' declares unknown unlocks id '{child_id}'")
    if tree.root_id not in known_ids:
        violations.append(f"tree.root_id '{tree.root_id}' is not a known node id")
    return violations


def _check_single_root(tree: DoctrineTree) -> list[str]:
    """Check for exactly one root node (empty ``parents``, ``cost_tl`` 0).

    Args:
        tree: The tree to check.

    Returns:
        Violation messages (empty if exactly one valid root is found and
        it matches ``tree.root_id``).
    """
    violations: list[str] = []
    roots = [node for node in tree.nodes.values() if not node.parents]
    if len(roots) != 1:
        found = sorted(node.id for node in roots)
        violations.append(
            f"expected exactly 1 root node (empty parents), found {len(roots)}: {found}"
        )
        return violations
    root = roots[0]
    if root.cost_tl != 0:
        violations.append(f"root node '{root.id}' must have cost_tl == 0, got {root.cost_tl}")
    if root.id != tree.root_id:
        violations.append(
            f"tree.root_id '{tree.root_id}' does not match the computed root node '{root.id}'"
        )
    return violations


def _check_dag_and_tiers(tree: DoctrineTree) -> list[str]:
    """Check for cycles and strictly-increasing tiers along parent edges.

    Depth-first search bounded by ``len(tree.nodes)`` (finite, known at
    call time) using a recursion stack to detect back-edges (cycles).
    Skipped when referential integrity already failed, since traversal
    assumes every ``parents`` id resolves to a real node.

    Args:
        tree: The tree to check.

    Returns:
        Violation messages (empty if the parent graph is an acyclic,
        tier-monotonic DAG).
    """
    violations: list[str] = []
    visited: set[str] = set()
    on_stack: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in on_stack:
            violations.append(f"cycle detected involving node '{node_id}'")
            return
        if node_id in visited:
            return
        visited.add(node_id)
        on_stack.add(node_id)
        node = tree.nodes[node_id]
        for parent_id in node.parents:
            parent = tree.nodes[parent_id]
            if parent.tier >= node.tier:
                violations.append(
                    f"tier is not strictly increasing from parent '{parent_id}' "
                    f"(tier {parent.tier}) to child '{node_id}' (tier {node.tier})"
                )
            visit(parent_id)
        on_stack.discard(node_id)

    for node_id in tree.nodes:
        visit(node_id)
    return violations


def _children_by_parent(tree: DoctrineTree) -> dict[str, list[str]]:
    """Build a parent-id -> child-ids adjacency map from ``parents``.

    Args:
        tree: The tree to index.

    Returns:
        Mapping of node id to the ids of nodes that declare it as a parent.
    """
    children: dict[str, list[str]] = {node_id: [] for node_id in tree.nodes}
    for node in tree.nodes.values():
        for parent_id in node.parents:
            if parent_id in children:
                children[parent_id].append(node.id)
    return children


def _check_trap_and_goal_flags(tree: DoctrineTree) -> list[str]:
    """Check ``is_trap``/``is_goal`` node-level invariants.

    Args:
        tree: The tree to check.

    Returns:
        Violation messages: traps missing a ``trap_condition``, and goal
        nodes that are not leaves (have children).
    """
    violations: list[str] = []
    children = _children_by_parent(tree)
    for node in tree.nodes.values():
        if node.is_trap and node.trap_condition is None:
            violations.append(f"node '{node.id}' has is_trap=True but no trap_condition")
        if node.is_goal and children.get(node.id):
            violations.append(
                f"node '{node.id}' has is_goal=True but is not a leaf "
                f"(children: {sorted(children[node.id])})"
            )
    return violations


def _check_trunk_values(tree: DoctrineTree) -> list[str]:
    """Defense-in-depth check that ``trunk`` is a valid :class:`DoctrineTrunk`.

    Pydantic already enforces this at construction time for any node built
    via normal validation; this guards the case of a node constructed via
    ``model_construct()`` or an equivalent validation-bypassing path.

    Args:
        tree: The tree to check.

    Returns:
        Violation messages (empty when every node's ``trunk`` is ``None``
        or a genuine :class:`DoctrineTrunk` member).
    """
    violations: list[str] = []
    for node in tree.nodes.values():
        if node.trunk is not None and not isinstance(node.trunk, DoctrineTrunk):
            violations.append(f"node '{node.id}' has an invalid trunk value: {node.trunk!r}")
    return violations


def validate_doctrine_tree(tree: DoctrineTree) -> None:
    """Validate a :class:`DoctrineTree` for structural integrity.

    Guards against:

    - Unknown ``parents``/``unlocks``/``root_id`` references.
    - Zero or multiple root nodes (empty ``parents``); a root with
      ``cost_tl != 0``; ``root_id`` not matching the computed root.
    - Cycles in the parent graph.
    - Non-monotonic tiers (a child's ``tier`` must exceed its parent's).
    - ``is_trap`` nodes missing a ``trap_condition``.
    - ``is_goal`` nodes that are not leaves.
    - ``trunk`` values that are not a genuine :class:`DoctrineTrunk` member.

    Args:
        tree: The tree to validate.

    Raises:
        DoctrineValidationError: If any of the checks above fail. Carries
            every violation found, not just the first.
    """
    referential_violations = _check_referential_integrity(tree)
    violations = list(referential_violations)
    violations.extend(_check_single_root(tree))
    # Cycle/tier checks assume every parent id resolves to a real node; only
    # skip them if referential integrity itself failed (would KeyError
    # mid-DFS). A root-count problem alone does not make the graph unsafe
    # to traverse, and cycle detection must still run in that case — a
    # tree with zero roots because every node points into a cycle is
    # exactly the "circular dependency" case the corpus calls out as THE
    # guard case, and should be reported as a cycle, not just "no root".
    if not referential_violations:
        violations.extend(_check_dag_and_tiers(tree))
    violations.extend(_check_trap_and_goal_flags(tree))
    violations.extend(_check_trunk_values(tree))
    if violations:
        raise DoctrineValidationError(violations)


__all__ = [
    "DoctrineValidationError",
    "validate_doctrine_tree",
]
