"""Contract tests for the Capital Vol I ∥ Vol II parallel-build fork gate (ADR103).

Pins the reserved-slot contract established by the T1.0 contract commit: the two
volumes' opposition keys are RESERVED — named, and wired as *dead* coupling slots
— without any live binding, so each lane may register (or not) inside its own
namespace without touching the other's. See the
``=== CAPITAL VOL I ∥ VOL II CONTRACT ===`` block in ``instances/catalog.py`` and
the §10 parallel protocol in the volume program prompts.

The T1.0 contract commit itself was physics-neutral by CONSTRUCTION (it
registered nothing). Since then the Vol II lane's U5 Oppositions unit has bound
its four reserved keys (SHADOW-first, so the CANONICAL registry/tick hash stay
untouched — see ``BoundOpposition.shadow`` in ``instances/catalog.py``);
Vol I's three keys remain dormant. :func:`test_vol1_reserved_oppositions_are_dormant`
and :func:`test_vol2_reserved_oppositions_are_now_bound` pin exactly that split.
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

    def test_vol1_reserved_oppositions_are_dormant(self) -> None:
        """Vol I's three reserved keys stay dormant: no live binding registered,
        so the registry shape — and the deterministic tick hash — is
        unchanged for that lane."""
        registered = set(build_default_registry().keys)
        assert registered.isdisjoint(set(VOL_I_RESERVED_OPPOSITIONS))

    def test_vol2_reserved_oppositions_are_now_bound(self) -> None:
        """Vol II's four reserved keys are now LIVE (SHADOW-bound by the Vol
        II lane's U5 Oppositions unit) — registering a reserved key flips
        this set arithmetic, which is the loud signal ADR103's contract
        commit designed this test to give."""
        registered = set(build_default_registry().keys)
        assert set(VOL_II_RESERVED_OPPOSITIONS) <= registered

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
