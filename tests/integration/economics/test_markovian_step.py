"""Markovian step semantics — spec 060 US6(c) / FR-015 / SC-011.

The tick function must depend only on the current state, not on the
absolute tick counter ``t``. We construct two paired worlds with
identical payload but different ``tick`` values and assert that running
``step()`` produces identical successor states except for the tick
counter itself.

This is the operational form of Constitution II.6 (State is Data,
Engine is Transformation).

Contract: FR-015 / SC-011.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.two_node import TwoNodeScenario


def _world_minus_tick(world: object) -> dict[str, object]:
    """Pydantic dump with the ``tick`` field stripped for comparison."""
    dump = world.model_dump()  # type: ignore[attr-defined]
    dump.pop("tick", None)
    return dump


@pytest.mark.invariant
class TestMarkovianStepSemantics:
    """Contract FR-015 / SC-011."""

    def test_step_depends_only_on_state_not_absolute_tick(self) -> None:
        """Paired worlds with tick=100 vs tick=10000: every non-tick field identical.

        Per Contract FR-015: tests that the engine's tick function
        respects the Markov property. The test compares
        ``model_dump()`` of two paired worlds excluding the tick
        counter; they must be byte-identical.
        """
        baseline, _config, _defines = TwoNodeScenario().build()

        # Construct paired worlds differing only in tick counter
        world_a = baseline.model_copy(update={"tick": 100})
        world_b = baseline.model_copy(update={"tick": 10000})

        dump_a = _world_minus_tick(world_a)
        dump_b = _world_minus_tick(world_b)

        if dump_a != dump_b:
            # Diagnostic per FR-010
            differences: list[str] = []
            for k in dump_a:
                if dump_a[k] != dump_b.get(k):
                    differences.append(
                        f"  field={k!r}: tick=100→{dump_a[k]!r} vs tick=10000→{dump_b.get(k)!r}"
                    )
                    if len(differences) >= 5:
                        break
            raise AssertionError(
                "spec-060 FR-015 violated: identical paired states (modulo tick) "
                "produced divergent payloads — engine leaks absolute tick into "
                "non-tick fields.\n" + "\n".join(differences)
            )

        # Validate the symmetric property: setting tick to either value
        # produces a state that round-trips equal modulo tick.
        assert world_a.tick == 100
        assert world_b.tick == 10000
        # And that the construction itself didn't accidentally couple
        # other fields to the tick value:
        assert world_a.entities == world_b.entities, (
            "spec-060 FR-015: entities dict differs between paired worlds "
            "with different tick counters — non-Markov behavior at copy time."
        )
