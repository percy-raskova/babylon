"""Typed couplings between oppositions: how contradictions relate, not just co-vary.

The dormant design replaced "oppositions couple only through shared inputs" with
a **typed morphism graph**. Five ratified coupling kinds (verbatim from the
dormant ``world.py``):

- ``feeds`` — the target's step reads the source's observation;
- ``constrains`` — the source limits the target's reachable state space;
- ``transforms`` — the source's output becomes the target's input prices;
- ``contains`` — the source is one of the target's poles (nesting);
- ``antagonizes`` — mutual (stored symmetric).

:class:`CouplingGraph` is built against an :class:`OppositionRegistry` and
enforces three laws: endpoints must be registered keys; ``antagonizes`` edges
are materialized in both directions so either endpoint sees the antagonism; and
``contains`` edges are AUTO-DERIVED from :class:`PoleBinding` nesting and may not
be added by hand (nesting ⇔ ``contains`` edge, exactly). Phase E's sublation
rules consume this graph; C2 only asserts the topology.

See Also:
    :func:`babylon.dialectics.instances.catalog.build_default_coupling_graph`:
    the production crisis-producer map over this graph.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from babylon.dialectics.core.opposition import OppositionRegistry

__all__ = ["Coupling", "CouplingGraph", "CouplingKind"]

CouplingKind = Literal["feeds", "constrains", "transforms", "contains", "antagonizes"]
"""The five ratified ways one opposition can relate to another."""


class Coupling(BaseModel):
    """A single typed edge ``source --kind--> target`` between two oppositions.

    Example:
        >>> Coupling(source="wage", target="capital_labor", kind="feeds").kind
        'feeds'
    """

    source: str = Field(..., min_length=1, description="Key of the upstream opposition")
    target: str = Field(..., min_length=1, description="Key of the downstream opposition")
    kind: CouplingKind = Field(..., description="The relation type")

    model_config = ConfigDict(frozen=True, extra="forbid")


def _derive_contains(registry: OppositionRegistry[Any]) -> list[Coupling]:
    """One ``contains`` edge (nested pole -> container) per nesting binding."""
    derived: list[Coupling] = []
    for key in registry.keys:
        spec = registry.spec_for(key)
        for binding in (spec.binding_a, spec.binding_b):
            if binding is not None and binding.opposition_key:
                derived.append(Coupling(source=binding.opposition_key, target=key, kind="contains"))
    return derived


def _directed_forms(coupling: Coupling) -> Iterable[Coupling]:
    """Yield the edge, plus its reverse when the relation is symmetric."""
    yield coupling
    if coupling.kind == "antagonizes" and coupling.source != coupling.target:
        yield Coupling(source=coupling.target, target=coupling.source, kind="antagonizes")


def _symmetric_closure(couplings: Iterable[Coupling]) -> tuple[Coupling, ...]:
    """Materialize reverse ``antagonizes`` edges, de-duplicating exact repeats."""
    result: list[Coupling] = []
    seen: set[tuple[str, str, str]] = set()
    for coupling in couplings:
        for edge in _directed_forms(coupling):
            identity = (edge.source, edge.target, edge.kind)
            if identity not in seen:
                seen.add(identity)
                result.append(edge)
    return tuple(result)


class CouplingGraph:
    """A validated typed-morphism graph over one registry's oppositions.

    Args:
        couplings: The manual edges (``feeds`` / ``constrains`` / ``transforms``
            / ``antagonizes``). ``contains`` edges are derived, not passed.
        registry: The registry whose keys the endpoints must belong to.

    Raises:
        ValueError: If any manual coupling is of kind ``contains``.
        KeyError: If any endpoint is not a registered opposition key.
    """

    def __init__(
        self,
        couplings: Sequence[Coupling],
        registry: OppositionRegistry[Any],
    ) -> None:
        keys = set(registry.keys)
        for coupling in couplings:
            if coupling.kind == "contains":
                raise ValueError(
                    "`contains` couplings are auto-derived from nesting; add them via "
                    "PoleBinding.opposition_key, not by hand"
                )
            if coupling.source not in keys:
                raise KeyError(
                    f"coupling source {coupling.source!r} is not a registered opposition"
                )
            if coupling.target not in keys:
                raise KeyError(
                    f"coupling target {coupling.target!r} is not a registered opposition"
                )
        self._couplings = _symmetric_closure([*couplings, *_derive_contains(registry)])

    @property
    def couplings(self) -> tuple[Coupling, ...]:
        """Every stored edge, including derived ``contains`` and reverse antagonisms."""
        return self._couplings

    def upstream_for(self, key: str) -> tuple[Coupling, ...]:
        """Edges pointing INTO ``key`` (its sources are upstream of it)."""
        return tuple(coupling for coupling in self._couplings if coupling.target == key)

    def downstream_of(self, key: str) -> tuple[Coupling, ...]:
        """Edges pointing OUT of ``key`` (its targets are downstream of it)."""
        return tuple(coupling for coupling in self._couplings if coupling.source == key)
