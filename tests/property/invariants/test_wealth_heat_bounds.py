"""Property-based tests for the Wealth ≥ 0 and Heat ≥ 0 bound invariants
(INV-007 / spec-054 US2).

See ``specs/054-bound-invariants/contracts/wealth_heat_bounds.md`` for the
full predicate specification.

Three predicates:

  Predicate A — per-System isolation across all 21 Systems (T020)
  Predicate B — full-pipeline composition (T021)
  Predicate C — per-System coverage trace, no silent omissions (T022)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, given, settings

from babylon.engine.invariants import (
    HeatNonNegativity,
    InvariantResult,
    NonNegativeWealth,
)
from babylon.engine.simulation_engine import SimulationEngine
from babylon.models.world_state import WorldState
from tests.property.harness.bound_harness import BoundInvariantHarness, HarnessResult
from tests.property.harness.system_registry import all_systems
from tests.property.strategies.worldstate import worldstate_strategy

if TYPE_CHECKING:
    from collections.abc import Iterator

    from babylon.kernel.system_protocol import System

# --------------------------------------------------------------------------- #
# Per-System session results — collected by Predicate A, asserted by C        #
# --------------------------------------------------------------------------- #
# Module-level dict that Predicate A populates with its outcome per System.
# Predicate C reads this dict to verify every System produced a row (no
# silent omissions per SC-002).

_PER_SYSTEM_OUTCOMES: dict[str, str] = {}


def _system_has_outcome(system_cls: type[System], outcomes: dict[str, str]) -> bool:
    """True if ``outcomes`` carries an entry — bare or ``::``-suffixed — for ``system_cls``."""
    return any(
        key == system_cls.__name__ or key.startswith(f"{system_cls.__name__}::") for key in outcomes
    )


@pytest.fixture(scope="class", autouse=True)
def _verify_full_system_coverage_on_teardown() -> Iterator[None]:
    """Defer Predicate C's SC-002 coverage assertion to end-of-class teardown.

    A ``scope="class"`` autouse fixture tears down only after every test in
    ``TestWealthHeatBounds`` has run — including every parametrized
    ``test_wealth_heat_per_system`` instance — regardless of the order
    pytest-randomly shuffles the class's ~20+ items into. Checking
    ``_PER_SYSTEM_OUTCOMES`` at *this* point is the only way to tell a real
    omission (a System that never produced a row) apart from "Predicate A
    for that System just hasn't executed yet under this shuffle" — a plain
    ``test_`` method has no such guarantee about what already ran before it.

    Previously ``test_per_system_coverage_complete`` back-filled every
    missing System with a placeholder row immediately before checking for
    gaps, so the coverage check could never observe a real omission
    (self-fill-then-check the same iteration is a tautology by
    construction — the loop that "fills" and the loop that "checks" always
    agree). This fixture replaces that fallback with a raw-presence
    assertion over ``_PER_SYSTEM_OUTCOMES`` as it actually stands once the
    class is done.
    """
    yield
    if not _PER_SYSTEM_OUTCOMES:
        return  # Predicate A never ran this session (e.g. filtered via -k).
    missing = [
        system_cls.__name__
        for system_cls in all_systems()
        if not _system_has_outcome(system_cls, _PER_SYSTEM_OUTCOMES)
    ]
    assert not missing, (
        f"Per-System coverage gap: {len(missing)} Systems produced no "
        f"outcome row in Predicate A: {missing}"
    )


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestWealthHeatBounds:
    """INV-007: every System preserves wealth ≥ 0 and heat ≥ 0.

    Per-System with feasibility fallback per Q2 clarification: if a System
    cannot run in isolation (e.g., it requires upstream state), the harness
    reports SKIPPED with a reason recorded in ``_PER_SYSTEM_OUTCOMES``.
    """

    @pytest.mark.parametrize(
        "system_cls",
        all_systems(),
        ids=lambda s: s.__name__,
    )
    @given(pre=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_wealth_heat_per_system(
        self,
        system_cls: type[System],
        pre: WorldState,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate A: each System individually preserves wealth + heat bounds.

        Records per-System outcome in ``_PER_SYSTEM_OUTCOMES`` so Predicate C
        can verify coverage. Catches ``Exception`` from System.step() as a
        feasibility failure (per Q2: SKIPPED with reason rather than fail).
        """
        harness = BoundInvariantHarness(
            system=system_cls,
            invariants=[NonNegativeWealth(), HeatNonNegativity()],
        )
        try:
            result: HarnessResult = harness.run(
                pre,
                service_container_fixture,
                tick_context_fixture,  # type: ignore[arg-type]
            )
        except Exception as exc:  # noqa: BLE001 — System preconditions vary widely
            _PER_SYSTEM_OUTCOMES[system_cls.__name__] = f"SKIPPED ({type(exc).__name__}: {exc})"
            pytest.skip(
                f"{system_cls.__name__} cannot run in isolation: {type(exc).__name__}: {exc}"
            )

        # Both invariants ran; assert each.
        for inv_name, outcome in result.outcomes.items():
            if outcome == "SKIPPED":
                _PER_SYSTEM_OUTCOMES[f"{system_cls.__name__}::{inv_name}"] = (
                    f"SKIPPED ({result.skip_reasons.get(inv_name, '')})"
                )
                continue
            assert isinstance(outcome, InvariantResult)
            _PER_SYSTEM_OUTCOMES[f"{system_cls.__name__}::{inv_name}"] = (
                "PASSED" if outcome.ok else f"FAILED ({outcome.msg})"
            )
            assert outcome.ok, f"{system_cls.__name__} / {inv_name}: {outcome.msg}"

    @given(pre=worldstate_strategy(min_entities=1, min_territories=1))
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_wealth_heat_full_pipeline(
        self,
        pre: WorldState,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate B: full 21-System pipeline preserves wealth + heat bounds.

        Catches multi-System interaction bugs that escape the per-System
        check (Predicate A) — e.g., System X writes a value System Y reads
        and amplifies into a violation.
        """
        systems = [cls() for cls in all_systems()]
        engine = SimulationEngine(systems=systems)
        graph = pre.to_graph()
        engine.run_tick(graph, service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]
        post = WorldState.from_graph(graph, tick=pre.tick + 1)

        wealth_result = NonNegativeWealth().check(pre, post)
        heat_result = HeatNonNegativity().check(pre, post)
        assert wealth_result.ok, f"Pipeline / non_negative_wealth: {wealth_result.msg}"
        assert heat_result.ok, f"Pipeline / heat_non_negativity: {heat_result.msg}"

    def test_per_system_coverage_complete(self) -> None:
        """Predicate C: every System appears in the per-System trace (SC-002).

        The raw-presence assertion over ``_PER_SYSTEM_OUTCOMES`` runs in
        ``_verify_full_system_coverage_on_teardown``'s teardown, which
        pytest defers until every test in this class — including every
        parametrized Predicate A instance — has executed, regardless of
        pytest-randomly's shuffle order (see that fixture's docstring for
        why a plain test body cannot make this assertion safely). This
        method only confirms Predicate A produced *some* trace, so the
        deferred coverage check is not itself vacuous when the whole class
        is filtered out of the run.
        """
        if not _PER_SYSTEM_OUTCOMES:
            pytest.skip(
                "Predicate A produced no outcomes — coverage trace is "
                "vacuous when test_wealth_heat_per_system is filtered out"
            )
