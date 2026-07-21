"""Contract tests for the Capital Vol I ∥ Vol II parallel-build fork gate (ADR103).

Pins the reserved-slot contract established by the T1.0 contract commit: the two
volumes' opposition keys are RESERVED — named, and wired as *dead* coupling slots
— without any live binding, so the production registry (and therefore the tick
hash) is untouched while the two lanes build in parallel worktrees. See the
``=== CAPITAL VOL I ∥ VOL II CONTRACT ===`` block in ``instances/catalog.py`` and
the §10 parallel protocol in the volume program prompts.

The load-bearing guarantee: this commit is physics-neutral by CONSTRUCTION (it
registers nothing), not merely by ceremony — :func:`test_reserved_oppositions_are_dormant`
proves the registry shape is disjoint from every reserved key.
"""

from __future__ import annotations

import pytest

from babylon.domain.dialectics.instances.catalog import (
    _DEFAULT_COUPLINGS,
    VOL_I_RESERVED_OPPOSITIONS,
    VOL_II_RESERVED_OPPOSITIONS,
    build_default_coupling_graph,
    build_default_registry,
)

pytestmark = [pytest.mark.unit, pytest.mark.math]


class TestReservedContract:
    def test_vol1_reserved_keys(self) -> None:
        """The three Capital Vol I production-layer oppositions, in canonical order."""
        assert VOL_I_RESERVED_OPPOSITIONS == (
            "value_usevalue",
            "labor_laborpower",
            "absolute_relative_surplus",
        )

    def test_vol2_reserved_keys(self) -> None:
        """The four Capital Vol II circulation-layer oppositions (the two existing
        dead ``transforms`` slots plus the two they connect)."""
        assert VOL_II_RESERVED_OPPOSITIONS == (
            "circulation",
            "realization",
            "reproduction",
            "disproportionality",
        )

    def test_reserved_oppositions_are_dormant(self) -> None:
        """The contract adds NO live binding: no reserved key is registered, so the
        registry shape — and the deterministic tick hash — is unchanged by T1.0."""
        registered = set(build_default_registry().keys)
        reserved = set(VOL_I_RESERVED_OPPOSITIONS) | set(VOL_II_RESERVED_OPPOSITIONS)
        assert registered.isdisjoint(reserved)

    def test_vol1_coupling_skeleton_declared_but_dead(self) -> None:
        """The three Vol I production edges are DECLARED in the coupling map but
        SKIPPED by the builder (their source opposition is not yet bound) — the
        wiring skeleton the Vol I lane lights up when it registers the axes. The
        third edge bridges the dormant surplus axis into the LIVE ``wage`` axis
        (the Fundamental Theorem Wᶜ > Vᶜ)."""
        expected = {
            ("value_usevalue", "labor_laborpower"),
            ("labor_laborpower", "absolute_relative_surplus"),
            ("absolute_relative_surplus", "wage"),
        }
        declared = {(c.source, c.target) for c in _DEFAULT_COUPLINGS}
        assert expected <= declared, "Vol I coupling skeleton must be declared"

        survivors = {
            (c.source, c.target)
            for c in build_default_coupling_graph(build_default_registry()).couplings
        }
        assert survivors.isdisjoint(expected), "reserved Vol I edges must stay dead"
