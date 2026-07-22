"""Contract tests for the Capital Vol I ∥ Vol II parallel-build fork gate (ADR103).

Pins the reserved-slot contract established by the T1.0 contract commit: the two
volumes' opposition keys are RESERVED — named, and wired as *dead* coupling slots
— without any live binding, so the production registry (and therefore the tick
hash) is untouched while the two lanes build in parallel worktrees. See the
``=== CAPITAL VOL I ∥ VOL II CONTRACT ===`` block in ``instances/catalog.py`` and
the §10 parallel protocol in the volume program prompts.

The load-bearing guarantee at the contract commit was physics-neutrality by
CONSTRUCTION (it registered nothing) — proved by a dormancy test over BOTH
volumes' reserved keys. Vol I's lane has since bound its three keys (U6):
:func:`test_vol2_reserved_oppositions_remain_dormant` now checks ONLY Vol II's
still-genuinely-reserved set, and :func:`test_vol1_reserved_oppositions_are_now_registered`
gives the positive confirmation the ADR's consequences section called for —
the loud signal that a reserved key going live is meant to be.
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

    def test_vol2_reserved_oppositions_remain_dormant(self) -> None:
        """Vol II's four keys stay genuinely reserved-but-unregistered: its lane
        has not yet bound them, so the registry shape (and the deterministic
        tick hash) is untouched by Vol II's portion of the contract."""
        registered = set(build_default_registry().keys)
        assert registered.isdisjoint(set(VOL_II_RESERVED_OPPOSITIONS))

    def test_vol1_reserved_oppositions_are_now_registered(self) -> None:
        """Vol I's lane has bound its three reserved keys (U6): the ADR's own
        consequences section calls a reserved key going live "the loud signal
        the contract intended" — this is that signal, checked positively."""
        registered = set(build_default_registry().keys)
        assert set(VOL_I_RESERVED_OPPOSITIONS) <= registered

    def test_vol1_coupling_skeleton_now_lit(self) -> None:
        """The three Vol I production edges are DECLARED in the coupling map and
        now SURVIVE the builder (U6 bound both endpoints of each) — the wiring
        skeleton the contract reserved is now lit, exactly as the two Volume
        III ``transforms`` edges lit when THEIR endpoints were bound. The third
        edge bridges the newly-bound surplus axis into the LIVE ``wage`` axis
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
        assert expected <= survivors, "bound Vol I edges must now survive"
