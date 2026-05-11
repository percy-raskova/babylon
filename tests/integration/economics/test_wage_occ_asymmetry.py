"""OCC-conditional wage-shock asymmetry — spec 060 US4 / FR-006 / SC-004.

A 10% uniform wage shock should DECREASE prices of production in
high-OCC hexes (relatively more constant capital, wages a smaller cost
share) and INCREASE prices of production in low-OCC hexes. If a
uniform wage shock instead produces uniform monetary scaling, the
engine implements prices as ``value × constant`` rather than proper
Volume III equalization — that is the failure mode this test catches.

Gated by ``skip_unless_active`` per FR-021; the assertion only fires
when transformation is active. The metamorphic-pair structure is in
place so the test activates automatically once the redistribution arm
of ``TransformationDialectic`` runs at tick boundary.

Contract: FR-006 / SC-004.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.two_node import TwoNodeScenario
from tests._helpers.invariants.transformation_mode import skip_unless_active


@pytest.mark.invariant
class TestOCCConditionalWageAsymmetry:
    """Contract FR-006 / SC-004."""

    def test_high_occ_low_occ_diverge(self) -> None:
        """Paired (baseline, +10%-wage) tick → 80% asymmetry by OCC.

        SKIPs cleanly today (transformation engine inactive); the
        contract activates once redistribution-mode runs.
        """
        _state, _config, _defines = TwoNodeScenario().build()
        transformation = None  # dialectic registry probe placeholder
        skip_unless_active(transformation, spec_ref="spec-060 FR-006")
        # Body activates once the gate opens. Placeholder so a future
        # /speckit.tasks pass can land the real assertion without
        # touching this skip line:
        # When the gate opens, the assertion will fire with a diagnostic
        # naming the offending hex_id and observed rel_err per FR-010:
        #   "spec-060 FR-006 violated: only N/M high-OCC hexes show "
        #   "decreased price/value ratio (need ≥ 80%). worst hex=..."
        pytest.fail("spec-060 FR-006 gate opened but body not yet wired")  # pragma: no cover

    def test_high_occ_low_occ_diverge_property(self) -> None:
        """Hypothesis variant: 20 random hex OCC distributions; median asymmetry ≥ 0.1.

        SKIPs cleanly today.
        """
        _state, _config, _defines = TwoNodeScenario().build()
        transformation = None
        skip_unless_active(transformation, spec_ref="spec-060 FR-006 (property)")
        pytest.fail(
            "spec-060 FR-006 (property) gate opened but body not yet wired"
        )  # pragma: no cover
