"""JSON round-trip serialization identity — spec 060 US6(b) / FR-014 / SC-010.

Asserts that ``WorldState.model_dump_json()`` followed by
``model_validate_json()`` produces a semantically-equal state.

Contract: FR-014 / SC-010. Distinct from the graph round-trip (covered
by spec 055 / `tests/property/invariants/test_round_trip_identity.py`),
which exercises ``to_graph()`` / ``from_graph()`` with documented
exclusions.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.two_node import TwoNodeScenario
from tests._helpers.invariants.serialization import roundtrip_via_json

# Tolerance: structural equality on frozen Pydantic models is exact;
# this test uses ``==`` on the model itself, not a numeric tolerance.


@pytest.mark.invariant
class TestSerializationRoundtrip:
    """Contract FR-014 / SC-010."""

    def test_json_roundtrip_preserves_state(self) -> None:
        """``model_dump_json`` → ``model_validate_json`` is identity on a frozen Pydantic model.

        Diagnostic on failure: enumerates the first field where the
        round-tripped state diverges from the baseline.
        """
        baseline, _config, _defines = TwoNodeScenario().build()
        round_tripped = roundtrip_via_json(baseline)

        if baseline != round_tripped:
            # Build a field-level diff diagnostic per FR-010
            base_dump = baseline.model_dump()
            rt_dump = round_tripped.model_dump()
            differences: list[str] = []
            for field in base_dump:
                if base_dump[field] != rt_dump.get(field):
                    differences.append(
                        f"  field={field!r}: "
                        f"baseline={base_dump[field]!r} "
                        f"round-tripped={rt_dump.get(field)!r}"
                    )
                    if len(differences) >= 5:
                        differences.append(f"  ... ({len(base_dump)} total)")
                        break
            raise AssertionError(
                "spec-060 FR-014 violated: WorldState JSON round-trip "
                "lost structural equality. First divergences:\n" + "\n".join(differences)
            )
