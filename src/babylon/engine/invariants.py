"""Invariant protocol and concrete invariants for the simulation engine.

Spec 040, Discipline 1: Invariants as First-Class Objects.
Spec 054 extends this with two new bound invariants (``ProbabilityInRange``,
``SimplexPreserved``) sitting alongside ``NonNegativeWealth`` and
``HeatNonNegativity``.

Every invariant in the constitution becomes an object implementing the
``Invariant`` protocol. Systems declare which invariants they preserve,
and the test harness checks them automatically via Hypothesis.

Usage::

    from babylon.engine.invariants import NonNegativeWealth, Invariant

    class VolumeOneProduction:
        invariants: ClassVar[list[Invariant]] = [NonNegativeWealth()]

        def step(self, state: WorldState) -> Result[WorldState, TransitionError]:
            ...
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from babylon.models.world_state import WorldState


@dataclass(frozen=True)
class InvariantResult:
    """Outcome of an invariant check.

    Use factory methods ``InvariantResult.ok()`` and ``InvariantResult.violated(msg)``
    rather than constructing directly.

    Attributes:
        passed: True if the invariant holds, False if violated.
        msg: Descriptive message (empty on success, diagnosis on failure).
    """

    passed: bool
    msg: str = ""

    @property
    def ok(self) -> bool:
        """Whether the invariant check passed."""
        return self.passed

    @classmethod
    def success(cls) -> InvariantResult:
        """Create a passing result.

        Returns:
            InvariantResult with passed=True.
        """
        return cls(passed=True, msg="")

    @classmethod
    def violated(cls, msg: str) -> InvariantResult:
        """Create a failing result with a diagnosis message.

        Args:
            msg: Description of the invariant violation.

        Returns:
            InvariantResult with passed=False.
        """
        return cls(passed=False, msg=msg)


@runtime_checkable
class Invariant(Protocol):
    """Protocol for simulation invariants.

    Every constitution invariant becomes an object implementing this protocol.
    Systems declare which invariants they preserve via a class-level list.
    The test harness runs declared invariants on (pre, post) state pairs.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this invariant."""
        ...

    def check(self, pre: WorldState, post: WorldState) -> InvariantResult:
        """Verify the invariant holds between pre and post states.

        Args:
            pre: WorldState before system step.
            post: WorldState after system step.

        Returns:
            InvariantResult indicating pass or violation.
        """
        ...


class NonNegativeWealth:
    """No entity has negative wealth after a system step.

    This invariant checks all social_class entities in the post-state
    and fails if any have wealth < 0.
    """

    @property
    def name(self) -> str:
        """Invariant identifier."""
        return "non_negative_wealth"

    def check(self, _pre: WorldState, post: WorldState) -> InvariantResult:
        """Check that no entity wealth is negative.

        Args:
            _pre: WorldState before step (unused for this invariant).
            post: WorldState after step.

        Returns:
            InvariantResult — violated if any entity has wealth < 0.
        """
        for entity_id, entity in post.entities.items():
            if entity.wealth < 0:
                return InvariantResult.violated(
                    f"Entity {entity_id} has negative wealth: {entity.wealth:.6f}"
                )
        return InvariantResult.success()


class HeatNonNegativity:
    """Territory heat fields must be >= 0 everywhere.

    Heat represents state repressive attention. Negative heat
    is physically meaningless.
    """

    @property
    def name(self) -> str:
        """Invariant identifier."""
        return "heat_non_negativity"

    def check(self, _pre: WorldState, post: WorldState) -> InvariantResult:
        """Check that no territory has negative heat.

        Args:
            _pre: WorldState before step (unused for this invariant).
            post: WorldState after step.

        Returns:
            InvariantResult — violated if any territory has heat < 0.
        """
        for territory_id, territory in post.territories.items():
            if territory.heat < 0:
                return InvariantResult.violated(
                    f"Territory {territory_id} has negative heat: {territory.heat:.6f}"
                )
        return InvariantResult.success()


# =============================================================================
# Spec 054 — Bound invariants
# =============================================================================
#
# Two new ``Invariant`` implementations supporting the spec-054 bound-invariant
# property test harness. See ``specs/054-bound-invariants/data-model.md`` and
# ``specs/054-bound-invariants/contracts/`` for the predicate specs.


def _iter_worldstate_collections(
    state: WorldState,
) -> Iterable[tuple[str, Any]]:
    """Yield ``(entity_id, entity)`` pairs across every WorldState collection
    that holds Pydantic-model entities.

    Walks the canonical collections enumerated in
    ``specs/054-bound-invariants/data-model.md §1.1``: entities, territories,
    relationships, organizations, key_figures, institutions, state_finances,
    contradiction_frames, industries. Relationships are keyed by their
    ``id`` attribute when present, otherwise by their list index.

    Sentinel rule: if a future ``WorldState`` field appears whose value is a
    Pydantic-model collection and is *not* surveyed here, the bound-invariant
    harness will not check it — extend this iterator first.
    """
    yield from state.entities.items()
    yield from state.territories.items()
    for idx, rel in enumerate(state.relationships):
        rel_id = getattr(rel, "id", None) or f"relationship[{idx}]"
        yield rel_id, rel
    yield from state.organizations.items()
    yield from state.key_figures.items()
    yield from state.institutions.items()
    yield from state.state_finances.items()
    yield from state.contradiction_frames.items()
    yield from state.industries.items()


@dataclass(frozen=True)
class ProbabilityInRange:
    """Every Probability-typed field on every entity stays in [0, 1].

    Spec 054 US1 (INV-006). Walks the post-state collections enumerated by
    ``_iter_worldstate_collections`` and asserts ``0.0 <= value <= 1.0``
    on every ``(ModelClass, field_name)`` pair listed in ``field_pairs``.

    Args:
        field_pairs: Sequence of (ModelClass, field_name) tuples to check.
            Defaults to the auto-discovered set from
            ``tests.property.harness.probability_discovery.discover_probability_fields()``
            but is parameterized so production code does not import test
            modules. The test harness instantiates this class with the
            discovered pairs.
        tolerance: Absolute slack on the bound. Defaults to ``0.0`` (exact
            comparison) per FR-008. The Probability constrained type's
            contract is the closed interval ``[0, 1]``; values at the
            boundary are legal.
    """

    field_pairs: Sequence[tuple[type[BaseModel], str]] = field(default_factory=tuple)
    tolerance: float = 0.0

    @property
    def name(self) -> str:
        """Invariant identifier."""
        return "probability_in_range"

    def check(self, _pre: WorldState, post: WorldState) -> InvariantResult:
        """Check that no Probability-typed field escapes [0 - tol, 1 + tol].

        Args:
            _pre: WorldState before step (unused for this invariant).
            post: WorldState after step.

        Returns:
            InvariantResult — violated on first out-of-range field encountered.
        """
        lower = -self.tolerance
        upper = 1.0 + self.tolerance
        for entity_id, entity in _iter_worldstate_collections(post):
            for cls, field_name in self.field_pairs:
                if not isinstance(entity, cls):
                    continue
                value = getattr(entity, field_name, None)
                if value is None:
                    continue
                # Probability is Annotated[float, ...]; values are floats.
                fvalue = float(value)
                if not (lower <= fvalue <= upper):
                    return InvariantResult.violated(
                        f"Field {cls.__name__}.{field_name} on entity "
                        f"{entity_id} = {fvalue:.6f} (out of [0, 1])"
                    )
        return InvariantResult.success()


@dataclass(frozen=True)
class SimplexPreserved:
    """Every TernaryConsciousness on every entity stays on the (r,l,f) simplex.

    Spec 054 US3 (INV-008). Walks every entity in the post-state and, for
    each one carrying a ``consciousness`` attribute that is a
    ``TernaryConsciousness`` instance, asserts:

        abs(c.r + c.l + c.f - 1.0) <= tolerance
        -tolerance <= c.r <= 1.0 + tolerance  (same for c.l, c.f)

    Args:
        tolerance: Slack on both the simplex sum and per-component bounds.
            Defaults to ``1e-4`` per spec acceptance scenario US3.1.
    """

    tolerance: float = 1e-4

    @property
    def name(self) -> str:
        """Invariant identifier."""
        return "simplex_preserved"

    def check(self, _pre: WorldState, post: WorldState) -> InvariantResult:
        """Check that every ternary consciousness still lies on the simplex.

        Args:
            _pre: WorldState before step (unused for this invariant).
            post: WorldState after step.

        Returns:
            InvariantResult — violated on first off-simplex consciousness.
        """
        # Lazy import to avoid a circular import between engine and models.
        from babylon.models.entities.consciousness import TernaryConsciousness

        tol = self.tolerance
        comp_lower = -tol
        comp_upper = 1.0 + tol
        for entity_id, entity in _iter_worldstate_collections(post):
            consciousness = getattr(entity, "consciousness", None)
            if not isinstance(consciousness, TernaryConsciousness):
                continue
            r, lc, f = float(consciousness.r), float(consciousness.l), float(consciousness.f)
            total = r + lc + f
            if abs(total - 1.0) > tol:
                return InvariantResult.violated(
                    f"Entity {entity_id} consciousness ({r:.6f}, {lc:.6f}, "
                    f"{f:.6f}) sums to {total:.6f} (simplex error "
                    f"{abs(total - 1.0):.3e})"
                )
            for label, value in (("r", r), ("l", lc), ("f", f)):
                if not (comp_lower <= value <= comp_upper):
                    return InvariantResult.violated(
                        f"Entity {entity_id} consciousness component "
                        f"{label}={value:.6f} out of [0, 1]"
                    )
        return InvariantResult.success()


# =============================================================================
# Spec 055 — Topological invariants
# =============================================================================
#
# Two new ``Invariant`` implementations supporting the spec-055 topology
# property test harness. See ``specs/055-topology-invariants/data-model.md``
# and ``specs/055-topology-invariants/contracts/`` for the predicate specs.


def _default_valid_arcs() -> frozenset[tuple[Any, Any]]:
    """Return the canonical legal-arc set from edge_transition.py.

    Lazy import to avoid an engine-systems → engine-invariants cycle.
    Single source of truth per spec-055 FR-002 and research §1.
    """
    from babylon.engine.systems.edge_transition import _VALID_TRANSITIONS

    return frozenset(_VALID_TRANSITIONS)


@dataclass(frozen=True)
class EdgeModeTrajectoryLegal:
    """Every edge-mode transition along a tick boundary is in the legal arc set.

    Spec 055 US1 (INV-009). For every relationship in the post-state that
    carries an ``edge_mode`` attribute, the pair ``(pre_mode, post_mode)``
    is either in ``valid_arcs`` (a real transition) OR equal (trivial
    no-transition). Trivial pairs are not counted as transitions; the
    explicit ``(ANTAGONISTIC, ANTAGONISTIC)`` persistence arc is in
    ``valid_arcs`` already.

    Args:
        valid_arcs: Frozen set of legal ``(EdgeMode, EdgeMode)`` arcs.
            Defaults to ``_VALID_TRANSITIONS`` from
            ``babylon.engine.systems.edge_transition`` — single source of
            truth. Tests that want to constrain the arc set can pass an
            explicit subset.
    """

    valid_arcs: frozenset[tuple[Any, Any]] = field(default_factory=_default_valid_arcs)

    @property
    def name(self) -> str:
        """Invariant identifier."""
        return "edge_mode_trajectory_legal"

    def check(self, pre: WorldState, post: WorldState) -> InvariantResult:
        """Check that every (pre_mode, post_mode) pair is legal.

        Args:
            pre: WorldState before step (provides previous edge modes).
            post: WorldState after step.

        Returns:
            InvariantResult — violated on first illegal arc encountered.
        """
        from babylon.models.enums import EdgeMode

        # Build pre-state edge_mode lookup keyed by (source, target, edge_type)
        pre_modes: dict[tuple[str, str, str], EdgeMode] = {}
        for rel in pre.relationships:
            mode_value = getattr(rel, "edge_mode", None)
            if mode_value is None:
                continue
            try:
                pre_modes[(rel.source_id, rel.target_id, str(rel.edge_type))] = EdgeMode(mode_value)
            except ValueError:
                return InvariantResult.violated(
                    f"Pre-state edge ({rel.source_id} -> {rel.target_id}, "
                    f"{rel.edge_type}): edge_mode={mode_value!r} is not a "
                    f"legal EdgeMode enum value"
                )

        for rel in post.relationships:
            post_mode_value = getattr(rel, "edge_mode", None)
            if post_mode_value is None:
                continue
            try:
                post_mode = EdgeMode(post_mode_value)
            except ValueError:
                return InvariantResult.violated(
                    f"Post-state edge ({rel.source_id} -> {rel.target_id}, "
                    f"{rel.edge_type}): edge_mode={post_mode_value!r} is "
                    f"not a legal EdgeMode enum value"
                )

            key = (rel.source_id, rel.target_id, str(rel.edge_type))
            pre_mode = pre_modes.get(key)
            if pre_mode is None:
                # New edge introduced this tick — no arc to check
                continue
            if pre_mode == post_mode:
                # Trivial no-transition tick; legal by definition
                continue
            if (pre_mode, post_mode) not in self.valid_arcs:
                return InvariantResult.violated(
                    f"Edge ({rel.source_id} -> {rel.target_id}, "
                    f"{rel.edge_type}): illegal arc ({pre_mode} -> "
                    f"{post_mode}) — not in _VALID_TRANSITIONS and "
                    f"pre_mode != post_mode"
                )
        return InvariantResult.success()


def _is_community_node_attr(node_attrs: dict[str, Any]) -> bool:
    """Return True iff the graph-node attribute ``_node_type == 'community'``.

    Inlined private helper per spec-055 T005 / F7. The test-side
    ``is_community_node(graph, node_id)`` helper in
    ``tests/property/harness/topology_harness.py`` shares this rule by
    convention, NOT by import — production code never depends on test code.
    """
    return node_attrs.get("_node_type") == "community"


@dataclass(frozen=True)
class NoCommunityFanOut:
    """No ``EdgeType.MEMBERSHIP`` edge has a community-node source.

    Spec 055 US2 (INV-010). Constitutional commitment II.7 (Edges vs
    Hyperedges) plus Anti-Pattern VIII.9 (Community as Pairwise Edge):
    community membership lives in the XGI hyperedge layer; the morphism
    graph MUST NOT carry community-to-member fan-outs.

    Walks every ``EdgeType.MEMBERSHIP`` edge in the post-graph
    (constructed via ``post.to_graph()``) and asserts that the source
    node's ``_node_type != "community"``.
    """

    @property
    def name(self) -> str:
        """Invariant identifier."""
        return "no_community_fan_out"

    def check(self, _pre: WorldState, post: WorldState) -> InvariantResult:
        """Check that no MEMBERSHIP edge has a community source.

        Args:
            _pre: WorldState before step (unused for this invariant).
            post: WorldState after step.

        Returns:
            InvariantResult — violated on first community-fan-out edge.
        """
        from babylon.models.enums import EdgeType

        graph = post.to_graph()
        for source_id, target_id, data in graph.edges(data=True):
            edge_type_raw = data.get("edge_type")
            if edge_type_raw is None:
                continue
            try:
                edge_type = (
                    edge_type_raw
                    if isinstance(edge_type_raw, EdgeType)
                    else EdgeType(edge_type_raw)
                )
            except ValueError:
                continue
            if edge_type != EdgeType.MEMBERSHIP:
                continue

            source_attrs = graph.nodes.get(source_id, {})
            if _is_community_node_attr(source_attrs):
                return InvariantResult.violated(
                    f"Community fan-out edge detected: ({source_id} -> "
                    f"{target_id}, MEMBERSHIP) — source node "
                    f"_node_type='community'. Membership MUST live in "
                    f"the XGI hyperedge layer (Anti-Pattern VIII.9)."
                )
        return InvariantResult.success()
