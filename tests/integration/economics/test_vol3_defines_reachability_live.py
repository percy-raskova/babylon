"""Finding U2.3-1: which ``capital_vol3`` knobs a live run actually reads.

U2.3 migrated five module-level ``Final`` constants onto GameDefines-backed
accessors "so ``defines.yaml`` edits actually take effect". Its unit tests are
mutation-hardened at the CONSUMER boundary — they prove the computed field
reads the accessor — but every consumer they drive turned out to be itself
unreachable during a tick, so the suite stayed green whether or not the
feature was live. That is the "correct but INERT" class this program exists to
eliminate, and a construction test cannot see it.

This file measures the thing directly: it instruments each accessor with a
counting wrapper, drives U1.9's real Wayne run through the real engine against
the real reference DB, and pins the OBSERVED call count for each coefficient.

It is a **ledger, not an aspiration**. Coefficients whose consumers are wired
are asserted strictly positive; coefficients whose consumers are measured dead
are asserted zero WITH the tracking owner named. Either direction going red is
information:

* a live count dropping to zero means a consumer went dark (the U2.3 defect
  recurring);
* a dead count going positive means a tracked consumer got wired, and the row
  must move up to ``_EXPECTED_LIVE`` in the same commit that wired it.

Do not "fix" a red here by loosening the assertion to ``>= 0``. That is
precisely the green-over-dead-feature state the file exists to prevent.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

pytestmark = [pytest.mark.integration, pytest.mark.requires_reference_db]

#: ``(module path, accessor name)`` for every GameDefines-backed accessor U2.3
#: created, keyed by the module the CONSUMER resolves it through — not
#: necessarily the module that declares it.
#:
#: This distinction is load-bearing and cost one red to learn. ``from x import
#: f`` binds a new name in the importing module's globals at import time, so
#: patching ``x.f`` afterwards is invisible to that consumer. Where the
#: consumer lives in the declaring module (the two computed fields) the
#: declaring module IS the right target; where it imports the accessor
#: (``credit_cycle``, ``assessment``) the importing module is.
_ACCESSORS: tuple[tuple[str, str], ...] = (
    # Consumed by SurplusValueDistribution.distribution_complete, in-module.
    ("babylon.domain.economics.distribution.types", "distribution_epsilon"),
    # No consumer at all; the declaring module is the only possible target.
    ("babylon.domain.economics.distribution.types", "debt_spiral_threshold"),
    # Consumed by CounterTendencyStrength.net_counter_tendency, in-module.
    ("babylon.domain.economics.counter_tendencies.types", "counter_tendency_weights"),
    ("babylon.domain.economics.counter_tendencies.types", "imperial_rent_reference_scale"),
    # Imported by the detector from credit.types — patch the importer.
    ("babylon.domain.economics.credit.credit_cycle", "stagnation_credit_growth"),
    # Imported by the assessor from credit.types — patch the importer.
    ("babylon.domain.economics.financial_crisis.assessment", "credit_fragility_threshold"),
)

#: Accessors a live tick MUST invoke. A zero here is a dark consumer.
_EXPECTED_LIVE: frozenset[str] = frozenset(
    {
        # Read by DefaultFinancialCrisisAssessor.assess, called per county-year
        # from TickDynamicsSystem._assess_county_financial_crisis.
        "credit_fragility_threshold",
    }
)

#: Accessors measured dead, each with the task that owes the wiring. These are
#: player-editable knobs in defines.yaml that currently change nothing, and
#: they must NOT be described to players as if they did (see the
#: "NOT YET READ" descriptions in config/defines/capital_vol3.py).
_EXPECTED_DEAD: dict[str, str] = {
    # Reached only through SurplusValueDistribution.distribution_complete, a
    # computed field with no production reader: graph_bridge.py publishes
    # interest_payments / ground_rent / rentier_share / profit_of_enterprise /
    # financialization_share / claims_exceed_surplus and never this one, and
    # no county-state model_dump() occurs in the tick or persistence path.
    "distribution_epsilon": "U3 (publish the financial state to the graph)",
    # U5.10 wired a LIVE consumer — ContradictionSystem._county_money_ratios
    # reads services.defines.capital_vol3.debt_spiral_threshold directly as
    # a GameDefines field access, bypassing this module's
    # debt_spiral_threshold() accessor entirely. This row therefore stays
    # correctly dead by THIS ledger's own narrow instrumentation (it only
    # counts calls to the accessor function above, not direct field reads),
    # but "No consumer of any kind in src/" is no longer true of the field
    # itself — see capital_vol3.py's description and
    # tests/unit/engine/systems/test_contradiction_money_inputs.py for the
    # real consumer.
    "debt_spiral_threshold": "U5 (debt_spiral opposition) — DONE via direct field access, not this accessor",
    # Both sit behind CounterTendencyStrength.net_counter_tendency, whose owner
    # counter_tendency_calculator is constructed in factory.py and injected in
    # services.py but never called anywhere in src/.
    "counter_tendency_weights": "U5 (counter-tendency opposition)",
    "imperial_rent_reference_scale": "U5 (counter-tendency opposition)",
    # Sits behind DefaultCreditCycleDetector.evaluate(), likewise constructed
    # and never called; graph_bridge.py hardcodes the literal string
    # "expansion" for credit_cycle_phase instead of asking the detector.
    "stagnation_credit_growth": "U6 (close the scissors loop)",
}


def _install_counters(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, int]:
    """Wrap every accessor in a counting proxy; return the live count map."""
    import importlib

    counts: dict[str, int] = {name: 0 for _module, name in _ACCESSORS}

    def _make_counter(module: ModuleType, name: str) -> Callable[..., object]:
        original = getattr(module, name)

        def _counting(*args: object, **kwargs: object) -> object:
            counts[name] += 1
            return original(*args, **kwargs)

        return _counting

    for module_path, name in _ACCESSORS:
        module = importlib.import_module(module_path)
        monkeypatch.setattr(module, name, _make_counter(module, name), raising=True)
    return counts


def test_defines_reachability_ledger_matches_the_measured_wiring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin the observed per-accessor invocation count of a real Wayne tick."""
    from tests.integration.economics.test_vol3_surplus_distribution_live import (
        _run_to_year_boundary_capturing_graph,
    )

    counts = _install_counters(monkeypatch)
    graph, _registry = _run_to_year_boundary_capturing_graph()
    assert graph is not None, "the run produced no graph — nothing was measured"

    live_failures = [
        f"{name}: expected a live tick to invoke it, observed {counts[name]} calls"
        for name in sorted(_EXPECTED_LIVE)
        if counts[name] == 0
    ]
    assert not live_failures, (
        "A wired capital_vol3 coefficient went dark — its consumer is no "
        "longer reached during a tick, so defines.yaml edits to it are now "
        "silently inert:\n  " + "\n  ".join(live_failures)
    )

    resurrected = [
        f"{name}: observed {counts[name]} calls, but the ledger records it dead (owed by {owner})"
        for name, owner in sorted(_EXPECTED_DEAD.items())
        if counts[name] > 0
    ]
    assert not resurrected, (
        "A coefficient the ledger records as dead is now being invoked. This "
        "is good news, but the ledger must move with the wiring: promote the "
        "row into _EXPECTED_LIVE and drop the 'NOT YET READ' wording from its "
        "defines.yaml description in the SAME commit.\n  " + "\n  ".join(resurrected)
    )


def test_every_migrated_accessor_appears_in_exactly_one_ledger_column() -> None:
    """No accessor may be silently omitted from the reachability ledger.

    Without this, adding a sixth accessor and forgetting to classify it would
    leave it unmeasured — which is how the original defect survived review.
    """
    declared = {name for _module, name in _ACCESSORS}
    classified = _EXPECTED_LIVE | set(_EXPECTED_DEAD)
    assert declared == classified, (
        f"unclassified accessors: {sorted(declared - classified)}; "
        f"classified but not declared: {sorted(classified - declared)}"
    )
    overlap = _EXPECTED_LIVE & set(_EXPECTED_DEAD)
    assert not overlap, f"accessors in both columns: {sorted(overlap)}"
