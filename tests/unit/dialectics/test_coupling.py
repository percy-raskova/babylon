"""Unit tests for :mod:`babylon.dialectics.core.coupling` and the default graph.

Two concerns:

- the typed coupling graph (:class:`Coupling`, :class:`CouplingGraph`) and its
  validation laws — registered endpoints, symmetric ``antagonizes``, and
  ``contains`` edges auto-derived from nesting (never added by hand);
- the production :func:`build_default_coupling_graph` topology — the ratified
  crisis-producer map, with the couplings whose endpoints are not yet bound
  skipped (logged) rather than invented as null bindings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from babylon.dialectics.core.coupling import Coupling, CouplingGraph
from babylon.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
    PoleBinding,
)
from babylon.dialectics.instances.catalog import (
    build_default_coupling_graph,
    build_default_registry,
)

pytestmark = [pytest.mark.unit, pytest.mark.math]


@dataclass(frozen=True)
class _Inputs:
    """Empty input carrier — coupling tests never invoke measures."""


def _bo(key: str, *, a_ref: str = "", b_ref: str = "") -> BoundOpposition[_Inputs]:
    spec = OppositionSpec(
        key=key,
        pole_a=f"{key}-A",
        pole_b=f"{key}-B",
        binding_a=PoleBinding(label=f"{key}-A", opposition_key=a_ref) if a_ref else None,
        binding_b=PoleBinding(label=f"{key}-B", opposition_key=b_ref) if b_ref else None,
    )
    return BoundOpposition(spec=spec, measure=lambda _inp: GapReading(gap=0.0, balance=0.0))


def _reg(*keys: str) -> OppositionRegistry[_Inputs]:
    return OppositionRegistry(bindings=[_bo(k) for k in keys])


def _triple(coupling: Coupling) -> tuple[str, str, str]:
    return (coupling.source, coupling.target, coupling.kind)


class TestCouplingModel:
    def test_coupling_is_frozen(self) -> None:
        c = Coupling(source="a", target="b", kind="feeds")
        with pytest.raises(ValidationError):
            c.source = "z"  # type: ignore[misc]


class TestEndpointValidation:
    def test_registered_endpoints_are_accepted(self) -> None:
        graph = CouplingGraph([Coupling(source="a", target="b", kind="feeds")], _reg("a", "b"))
        assert _triple(graph.couplings[0]) == ("a", "b", "feeds")

    def test_unregistered_source_rejected(self) -> None:
        with pytest.raises(KeyError, match="ghost"):
            CouplingGraph([Coupling(source="ghost", target="b", kind="feeds")], _reg("b"))

    def test_unregistered_target_rejected(self) -> None:
        with pytest.raises(KeyError, match="ghost"):
            CouplingGraph([Coupling(source="a", target="ghost", kind="feeds")], _reg("a"))


class TestAntagonizesSymmetry:
    def test_one_direction_implies_the_reverse_on_query(self) -> None:
        graph = CouplingGraph(
            [Coupling(source="capital_labor", target="imperial", kind="antagonizes")],
            _reg("capital_labor", "imperial"),
        )
        # The reverse edge is materialized so BOTH endpoints see the antagonism.
        downstream_imperial = graph.downstream_of("imperial")
        assert any(
            c.source == "imperial" and c.target == "capital_labor" and c.kind == "antagonizes"
            for c in downstream_imperial
        )
        upstream_capital = graph.upstream_for("capital_labor")
        assert any(c.source == "imperial" and c.kind == "antagonizes" for c in upstream_capital)

    def test_symmetry_does_not_duplicate_when_both_given(self) -> None:
        graph = CouplingGraph(
            [
                Coupling(source="a", target="b", kind="antagonizes"),
                Coupling(source="b", target="a", kind="antagonizes"),
            ],
            _reg("a", "b"),
        )
        antagonisms = [c for c in graph.couplings if c.kind == "antagonizes"]
        assert len(antagonisms) == 2  # exactly the two directions, no dupes


class TestContainsAutoDerivation:
    def test_manual_contains_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="contains"):
            CouplingGraph([Coupling(source="a", target="b", kind="contains")], _reg("a", "b"))

    def test_contains_is_derived_from_nesting(self) -> None:
        # outer nests inner on pole A -> a contains edge inner -> outer.
        reg = OppositionRegistry(bindings=[_bo("inner"), _bo("outer", a_ref="inner")])
        graph = CouplingGraph([], reg)
        contains = [c for c in graph.couplings if c.kind == "contains"]
        assert _triple(contains[0]) == ("inner", "outer", "contains")

    def test_nesting_and_contains_correspond_exactly(self) -> None:
        # No nesting -> no contains edges (contains iff nesting).
        graph = CouplingGraph([Coupling(source="a", target="b", kind="feeds")], _reg("a", "b"))
        assert not [c for c in graph.couplings if c.kind == "contains"]


class TestDefaultCouplingGraph:
    """The ratified crisis-producer map, skipping unbound endpoints."""

    def test_registered_couplings_are_kept(self) -> None:
        graph = build_default_coupling_graph(build_default_registry())
        triples = {_triple(c) for c in graph.couplings}
        assert ("wage", "capital_labor", "feeds") in triples
        assert ("capital_labor", "imperial", "antagonizes") in triples
        assert ("imperial", "capital_labor", "antagonizes") in triples  # symmetric

    def test_only_the_bound_edges_survive(self) -> None:
        graph = build_default_coupling_graph(build_default_registry())
        # Exactly: wage->capital_labor feeds + the symmetric capital_labor<->imperial.
        non_contains = {_triple(c) for c in graph.couplings if c.kind != "contains"}
        assert non_contains == {
            ("wage", "capital_labor", "feeds"),
            ("capital_labor", "imperial", "antagonizes"),
            ("imperial", "capital_labor", "antagonizes"),
        }

    def test_unbound_transforms_are_skipped_and_logged(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="babylon.dialectics.instances.catalog"):
            build_default_coupling_graph(build_default_registry())
        skipped = [r for r in caplog.records if "Skipping coupling" in r.getMessage()]
        # The four crisis-producer transforms reference Phase D/E keys not yet bound.
        assert len(skipped) == 4
        joined = " ".join(r.getMessage() for r in skipped)
        for endpoint in ("realization", "disproportionality", "debt_spiral", "financial"):
            assert endpoint in joined
