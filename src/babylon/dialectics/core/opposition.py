"""The opposition registry: contradictions as measured adjunction defects.

This is the successor to BOTH of Babylon's previous contradiction
representations — the saturating edge-``tension`` scalar (which pinned
at 1.0 and carried no information) and the dormant dialectics layer's
``weight`` float. An :class:`OppositionSpec` names the two poles and
their unity; a :class:`GapMeasure` reports, from live inputs, how far
the opposition currently is from closure (``gap`` — Laclau: the measured
failure of an identity to fully constitute itself) and which pole
dominates (``balance``). The registry derives the rate of development
and Mao's **principal contradiction**: the contradiction whose
development leads all others, operationalized as
``score = gap * (1 + rate_weight * |rate|)``.

Contract with the engine (Phase C): registry states map onto the
existing :class:`babylon.models.entities.contradiction.Contradiction`
fields as intensity ← gap, aspect_balance ← rate,
principal_aspect ← leading_pole. Balance is the signed dominance of
pole B over pole A; at exactly zero the leading pole is INERT — it
holds its previous value, because a principal aspect persists until it
is actually overturned.

See Also:
    :class:`babylon.dialectics.core.cylinder.AdjointCylinder`: supplies
    balance readings for interval-shaped oppositions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models import Intensity

Balance = Annotated[
    float,
    Field(ge=-1.0, le=1.0, description="Signed dominance of pole B over pole A"),
]

_DEFAULT_RATE_WEIGHT = 10.0
"""Weight of |rate| in principal-contradiction scoring.

Phase C wires this from GameDefines (Constitution III.1); the default
makes a gap developing at 0.1/tick outrank a static gap twice its size.
"""

MAX_NESTING_DEPTH = 4
"""Maximum length of a pole-nesting (or governance) chain.

The static loop bound for the depth check: the fractal recursion
``{Core,Periphery} × {Bourgeoisie,Proletariat}`` is depth 2, so 4 leaves
head-room while keeping the validation traversal trivially finite.
"""

__all__ = [
    "MAX_NESTING_DEPTH",
    "BoundOpposition",
    "GapMeasure",
    "GapReading",
    "OppositionRegistry",
    "OppositionSpec",
    "OppositionState",
    "PoleBinding",
]


class GapReading(BaseModel):
    """One opposition's instantaneous measurement.

    Example:
        >>> GapReading(gap=0.4, balance=-0.2).gap
        0.4
    """

    gap: Intensity = Field(..., description="Distance from closure: 0 resolved, 1 maximal")
    balance: Balance = Field(..., description="Signed dominance of pole B over pole A")

    model_config = ConfigDict(frozen=True, extra="forbid")


class GapMeasure[I](Protocol):
    """Measures an opposition against live inputs of type ``I``."""

    def __call__(self, inputs: I) -> GapReading:
        """Return the current :class:`GapReading` for these inputs."""
        ...


class PoleBinding(BaseModel):
    """What a single pole of an opposition actually refers to.

    A pole is a plain named aspect unless it BINDS one of two richer things:
    another opposition (``opposition_key`` — the fractal nesting that makes
    ``{Core,Periphery} × {Bourgeoisie,Proletariat}`` expressible) or a
    collective formation (``community_id`` — an XGI hyperedge id). The two are
    mutually exclusive: a pole is a nested opposition XOR a community, never
    both. This is the VIII.9 n-ary protection in type form — reducing an
    internal nation (a community) to a bare dyadic pole string is forbidden.

    Example:
        >>> PoleBinding(label="Core", opposition_key="capital_labor").opposition_key
        'capital_labor'
    """

    label: str = Field(..., min_length=1, description="Display name for this pole")
    opposition_key: str = Field(
        default="",
        description="Nesting: this pole IS the opposition registered under this key",
    )
    community_id: str = Field(
        default="",
        description="n-ary formation: this pole is the community with this XGI hyperedge id",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def _reference_is_exclusive(self) -> PoleBinding:
        """A pole nests an opposition XOR references a community — never both."""
        if self.opposition_key and self.community_id:
            raise ValueError("PoleBinding.opposition_key and community_id are mutually exclusive")
        return self


class OppositionSpec(BaseModel):
    """The static identity of an opposition: poles, unity, placement."""

    key: str = Field(..., min_length=1, description="Registry-unique identifier")
    pole_a: str = Field(..., min_length=1, description="One aspect of the opposition")
    pole_b: str = Field(..., min_length=1, description="The other aspect")
    unity: str = Field(
        default="",
        description="What holds the poles together (mutual presupposition)",
    )
    level_name: str = Field(
        default="",
        description="Level-lattice placement (Phase E); empty = unplaced",
    )
    antagonistic: bool = Field(
        default=False,
        description="Laclau: cannot close within its current level",
    )
    component_keys: tuple[str, ...] = Field(
        default=(),
        description="Composition provenance: keys of the combined components (empty = atomic)",
    )
    composition: Literal["", "product", "sum"] = Field(
        default="",
        description="Combinator that produced this spec ('' = atomic, not composed)",
    )
    binding_a: PoleBinding | None = Field(
        default=None,
        description="Rich binding for pole A (None = plain named pole)",
    )
    binding_b: PoleBinding | None = Field(
        default=None,
        description="Rich binding for pole B (None = plain named pole)",
    )
    flavor: Literal["contradiction", "apparatus"] = Field(
        default="contradiction",
        description="'apparatus' = institutional exclusion with no oppressor community",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def _apparatus_pole_has_no_community(self) -> OppositionSpec:
        """Apparatus flavor: the apparatus pole (B) is never a community."""
        if (
            self.flavor == "apparatus"
            and self.binding_b is not None
            and self.binding_b.community_id
        ):
            raise ValueError(
                "apparatus flavor forbids a community on the apparatus pole (binding_b)"
            )
        return self


@dataclass(frozen=True)
class BoundOpposition[I]:
    """An :class:`OppositionSpec` bound to its :class:`GapMeasure`."""

    spec: OppositionSpec
    measure: GapMeasure[I]


class OppositionState(BaseModel):
    """One opposition's per-tick dynamic state."""

    key: str = Field(..., min_length=1)
    tick: int = Field(..., ge=0)
    gap: Intensity = Field(..., description="Current distance from closure")
    balance: Balance = Field(..., description="Signed dominance of pole B over pole A")
    rate: float = Field(..., description="gap - previous gap (0.0 on first step)")
    leading_pole: Literal["a", "b"] = Field(..., description="The principal aspect")
    is_principal: bool = Field(
        default=False,
        description="Whether this is the principal contradiction this tick",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


def _nesting_refs(specs: Sequence[OppositionSpec]) -> dict[str, tuple[str, ...]]:
    """Adjacency of the pole-nesting graph: ``key -> referenced opposition keys``.

    Raises:
        KeyError: If any pole nests a key that is not in ``specs``.
    """
    registered = {spec.key for spec in specs}
    refs: dict[str, tuple[str, ...]] = {}
    for spec in specs:
        children = tuple(
            binding.opposition_key
            for binding in (spec.binding_a, spec.binding_b)
            if binding is not None and binding.opposition_key
        )
        for child in children:
            if child not in registered:
                raise KeyError(f"opposition {spec.key!r} nests unregistered key {child!r}")
        refs[spec.key] = children
    return refs


def _reject_nesting_cycles(refs: Mapping[str, tuple[str, ...]]) -> None:
    """Raise ValueError naming the cycle if the nesting graph has one.

    Three-colour depth-first search. Recursion depth and total edge visits are
    each bounded by ``len(refs)`` (a simple path cannot repeat a node), so the
    traversal is statically finite.
    """
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def walk(node: str) -> None:
        visiting.add(node)
        path.append(node)
        for child in refs[node]:  # <= 2 children per spec
            if child in visiting:
                cycle = [*path[path.index(child) :], child]
                raise ValueError(f"nesting cycle: {' -> '.join(cycle)}")
            if child not in visited:
                walk(child)
        visiting.discard(node)
        path.pop()
        visited.add(node)

    for root in refs:  # <= len(refs) roots
        if root not in visited:
            walk(root)


def _reject_excess_nesting_depth(refs: Mapping[str, tuple[str, ...]]) -> None:
    """Raise ValueError if any nesting chain is deeper than ``MAX_NESTING_DEPTH``.

    Longest-downward-chain by relaxation. The graph is already proven acyclic,
    so the longest chain is at most ``len(refs)`` and relaxation converges in at
    most that many rounds — the ``for`` bound below.
    """
    depth = dict.fromkeys(refs, 1)
    for _ in range(len(refs)):  # bounded by node count (acyclic => converges)
        changed = False
        for key, children in refs.items():
            best = max((depth[child] + 1 for child in children), default=1)
            if best > depth[key]:
                depth[key] = best
                changed = True
        if not changed:
            break
    worst = max(depth.values(), default=0)
    if worst > MAX_NESTING_DEPTH:
        deepest = max(refs, key=lambda key: depth[key])
        raise ValueError(
            f"nesting depth {worst} exceeds MAX_NESTING_DEPTH={MAX_NESTING_DEPTH} "
            f"(deepest chain rooted at {deepest!r})"
        )


def _validate_nesting(specs: Sequence[OppositionSpec]) -> None:
    """Validate the pole-nesting graph: references registered, acyclic, bounded.

    Raises:
        KeyError: If a pole nests an unregistered opposition key.
        ValueError: On a nesting cycle or a chain deeper than
            ``MAX_NESTING_DEPTH``.
    """
    refs = _nesting_refs(specs)
    _reject_nesting_cycles(refs)
    _reject_excess_nesting_depth(refs)


class OppositionRegistry[I]:
    """Steps a family of oppositions and ranks the principal contradiction.

    Args:
        bindings: The oppositions to track; keys must be unique.
        rate_weight: Weight of |rate| in principal scoring (>= 0).

    Raises:
        ValueError: On duplicate keys, negative ``rate_weight``, a nesting
            cycle, or a nesting chain deeper than ``MAX_NESTING_DEPTH``.
        KeyError: If a pole nests an opposition key that is not registered.
    """

    def __init__(
        self,
        bindings: Sequence[BoundOpposition[I]],
        rate_weight: float = _DEFAULT_RATE_WEIGHT,
    ) -> None:
        if rate_weight < 0.0:
            raise ValueError(f"rate_weight must be non-negative, got {rate_weight}")
        keys = [binding.spec.key for binding in bindings]
        duplicates = sorted({k for k in keys if keys.count(k) > 1})
        if duplicates:
            raise ValueError(f"Duplicate opposition keys: {duplicates}")
        self._bindings: tuple[BoundOpposition[I], ...] = tuple(
            sorted(bindings, key=lambda binding: binding.spec.key)
        )
        self._rate_weight = rate_weight
        _validate_nesting([binding.spec for binding in self._bindings])

    @property
    def keys(self) -> tuple[str, ...]:
        """Registered opposition keys, lexicographically ordered."""
        return tuple(binding.spec.key for binding in self._bindings)

    def spec_for(self, key: str) -> OppositionSpec:
        """Look up a spec by key.

        Raises:
            KeyError: If the key is not registered.
        """
        for binding in self._bindings:
            if binding.spec.key == key:
                return binding.spec
        raise KeyError(key)

    def step(
        self,
        inputs: I,
        tick: int,
        previous: Mapping[str, OppositionState] | None = None,
    ) -> tuple[OppositionState, ...]:
        """Measure every opposition and mark the principal contradiction.

        Args:
            inputs: Live inputs handed to every bound measure.
            tick: The current tick, stamped onto each state.
            previous: Last tick's states by key, for rate and pole inertia.

        Returns:
            One state per binding, lexicographic by key, with exactly one
            ``is_principal=True`` (none if the registry is empty). Ties
            in score break toward the lexicographically first key.
        """
        drafts: list[OppositionState] = []
        for binding in self._bindings:
            reading = binding.measure(inputs)
            prior = previous.get(binding.spec.key) if previous else None
            rate = reading.gap - prior.gap if prior is not None else 0.0
            drafts.append(
                OppositionState(
                    key=binding.spec.key,
                    tick=tick,
                    gap=reading.gap,
                    balance=reading.balance,
                    rate=rate,
                    leading_pole=self._lead(reading.balance, prior),
                )
            )
        if not drafts:
            return ()
        principal_key = self._principal_key(drafts)
        return tuple(
            draft.model_copy(update={"is_principal": draft.key == principal_key})
            for draft in drafts
        )

    def _score(self, state: OppositionState) -> float:
        """Mao's principal-contradiction ranking: sharp AND fast-developing."""
        return state.gap * (1.0 + self._rate_weight * abs(state.rate))

    def _principal_key(self, drafts: Sequence[OppositionState]) -> str:
        """Highest score wins; ties break to the lexicographically first key."""
        best = drafts[0]
        best_score = self._score(best)
        for candidate in drafts[1:]:
            score = self._score(candidate)
            if score > best_score:
                best, best_score = candidate, score
        return best.key

    @staticmethod
    def _lead(balance: float, prior: OppositionState | None) -> Literal["a", "b"]:
        """Sign of balance selects the pole; zero holds the previous pole."""
        if balance < 0.0:
            return "a"
        if balance > 0.0:
            return "b"
        return prior.leading_pole if prior is not None else "a"
