"""Property-based tests for the frozen Pydantic discipline bound invariant
(INV-011 / spec-055 US3).

See ``specs/055-topology-invariants/contracts/frozen_discipline.md`` for
the full predicate specification. Encodes Constitution III.7 (Determinism
Hash and Replayability) — the engine's ``step(WorldState) -> WorldState``
purity claim.

Three predicates across two layers:

  Predicate A — Layer 1 static class-level frozen=True audit (T019)
  Predicate B — Layer 2 runtime per-tick id() identity check (T020)
  Predicate C — seeded dunder-bypass mutation is detected (T021)
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from pydantic import BaseModel

from babylon.engine.simulation_engine import SimulationEngine
from babylon.models.world_state import WorldState
from tests.property.harness.frozen_audit import (
    assert_no_in_place_mutation,
    snapshot_ids,
)
from tests.property.harness.model_class_registry import (
    assert_all_frozen,
    discover_state_bearing_models,
)
from tests.property.harness.system_registry import all_systems
from tests.property.strategies.worldstate import worldstate_strategy

# ---------------------------------------------------------------------------
# Pre-existing non-frozen state-bearing models — DEBT, not legitimate.
# ---------------------------------------------------------------------------
# These 19 classes were declared as plain Pydantic models without
# ``frozen=True`` before Spec 055 introduced the discipline. Each entry
# is a separate Constitution III.7 (Determinism) refactor — fixing them
# requires auditing every System that mutates them and replacing in-place
# writes with ``model_copy(update=...)``. Tracked here as a test-side
# skip list (NOT as production ``bypasses_topology_invariant`` markers,
# because these are bugs to fix, not legitimate exceptions).
#
# To reduce the debt: pick a class, add ``model_config = ConfigDict(frozen=True)``,
# fix any callers that mutate it in place, remove the entry from this set,
# and watch this test go from SKIPPED to PASSED for that class.
#
# Reconciliation (2026-05-07, refactor/frozen-discipline-debt branch): all
# 19 originally-listed classes are now frozen. The set is kept as an empty
# frozenset to preserve the import contract for downstream consumers and to
# document the reconciliation history. Any *new* state-bearing model class
# that needs to defer freezing for a justified reason should be added here
# with a brief comment explaining the deferral, NOT silently shipped
# without ``frozen=True``.
_PRE_EXISTING_NON_FROZEN_DEBT: frozenset[str] = frozenset()


@pytest.mark.unit
class TestFrozenDiscipline:
    """INV-011: state-bearing models are frozen + no per-tick in-place mutation."""

    @pytest.mark.parametrize(
        "model_cls",
        discover_state_bearing_models(),
        ids=lambda c: c.__qualname__,
    )
    def test_state_bearing_model_is_frozen(self, model_cls: type[BaseModel]) -> None:
        """Predicate A (Layer 1): every state-bearing model declares frozen=True.

        Delegates to ``assert_all_frozen()`` so the bypass-marker honoring +
        non-empty-justification logic lives in one place. Per-class
        parametrization keeps failures isolable to the single offending
        class.

        Pre-existing non-frozen classes are skipped via
        ``_PRE_EXISTING_NON_FROZEN_DEBT`` (NOT via production
        ``bypasses_topology_invariant`` markers — these are debt to fix,
        not legitimate exceptions per Constitution III.7).
        """
        if model_cls.__qualname__ in _PRE_EXISTING_NON_FROZEN_DEBT:
            pytest.skip(
                f"{model_cls.__qualname__} is pre-Spec-055 debt — not yet "
                f"frozen. Tracked in _PRE_EXISTING_NON_FROZEN_DEBT for "
                f"future Constitution III.7 reconciliation."
            )
        assert_all_frozen([model_cls])

    @given(pre_state=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_no_in_place_mutation_per_tick(
        self,
        pre_state: WorldState,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate B (Layer 2): SimulationEngine.run_tick produces no in-place mutations."""
        pre_ids = snapshot_ids(pre_state)
        systems = [cls() for cls in all_systems()]
        engine = SimulationEngine(systems=systems)

        graph = pre_state.to_graph()
        engine.run_tick(graph, service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]
        post_state = WorldState.from_graph(graph, tick=pre_state.tick + 1)

        assert_no_in_place_mutation(pre_state, post_state, pre_ids)

    def test_seeded_dunder_bypass_is_detected(self) -> None:
        """Predicate C (Layer 3): assert_no_in_place_mutation raises on a
        seeded dunder-bypass mutation.

        Simulates a System that holds onto the same entity object across a
        tick instead of routing through ``model_copy``/graph reconstruction,
        then bypasses ``frozen=True`` via a direct ``__dict__`` write.
        ``pre_state`` is an independent deep copy taken before the bypass —
        the ground truth a correctly-behaving caller retains — while
        ``pre_ids`` (via ``snapshot_ids``) records the identity of the
        live object that goes on to be mutated and reappear, same id but
        field-different, in ``post_state``. This is the operational
        signature ``assert_no_in_place_mutation`` exists to catch.
        """
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        live_worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=10.0,
        )
        live_state = WorldState(tick=0, entities={"C001": live_worker})
        pre_ids = snapshot_ids(live_state)

        # Ground-truth pre-tick snapshot: a deep copy decoupled from
        # `live_worker`, so it cannot be corrupted by the bypass below.
        pre_state = WorldState(tick=0, entities={"C001": live_worker.model_copy(deep=True)})

        # Dunder-bypass: mutate the live object in place instead of
        # producing a fresh instance via model_copy(update=...).
        live_worker.__dict__["wealth"] = 999.0

        # post_state reports the SAME (now-mutated) object under the same
        # id recorded in pre_ids.
        post_state = WorldState(tick=1, entities={"C001": live_worker})

        with pytest.raises(AssertionError, match="In-place mutation detected"):
            assert_no_in_place_mutation(pre_state, post_state, pre_ids)
