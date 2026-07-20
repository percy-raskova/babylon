"""Dynamic gate-coverage truth probe (CLI key: gate-coverage-truth).

Runs each declared in-memory scenario at the EXACT cadence the byte-identical
gate uses (``step()``: to_graph → run_tick → from_graph per tick, with the
harness-held ``persistent_context`` AND the same
``tools.regression_test._build_vol3_calculator_overrides`` the gate's
``_run_scenario_ticks`` passes into every ``step()`` call — omitting it would
starve ``TickDynamicsSystem`` (``melt_calculator is None`` short-circuits its
whole annual pipeline) and diverge from what the gate actually exercises) and
verifies every ``SystemEvidence`` row: the declared observable actually
occurs in that scenario's run. A false declaration is a gating finding — the
static sentinel proves the estate is COMPLETE; this probe proves it is TRUE.

bundle_event/bundle_field rows are skipped here (verified statically against
the committed e2e baseline by ``babylon.sentinels.gate_coverage``). A
coverage entry whose declared ``systems`` are ALL bundle-kind (e.g.
``detroit_tri_county``, which is not a key in ``SCENARIOS`` and cannot be
run in-memory) is skipped silently. An entry with a *non-empty* ``systems``
tuple whose ``scenario`` is not in ``SCENARIOS`` is a real misconfiguration
and raises ``KeyError`` loudly — the empty-``systems`` case is the same
signal (nothing declared, unknown scenario) and raises too.

``event``-kind rows require the event's occurrence to carry real signal, not
merely the bare EventType being present in a tick's ``state.events`` — see
``_event_is_meaningful`` for the ORGANIZATIONAL_ACTION unconditional-summary
trap this closes (brief defect: the sample implementation's naive
presence-only check would pass a row like OODASystem/``organizational_action``
even though it is a documented ``COVERAGE_GAPS_DATA`` non-occurrence).

Runs the engine — advisory-speed, wired into the qa CI job, NOT the static
fast gate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Final

# ``tools.sentinel_check`` runs this module bare (script-directory sys.path,
# no repo root) when dispatching ``gate-coverage-truth`` — the same reason
# ``tools/regression_scenarios.py`` inserts src/tools onto sys.path at its
# own top. Do the same for the repo root so the dotted ``tools.`` imports
# below (matching ``tests/unit/tools/test_regression_scenarios.py``'s
# existing convention) resolve under pytest AND the CLI dispatcher alike.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.regression_scenarios import (  # noqa: E402
    SCENARIO_COVERAGE,
    SCENARIOS,
    ScenarioCoverage,
    create_scenario,
)
from tools.shared import PERIPHERY_WORKER_ID, is_dead  # noqa: E402

_DEFAULT_MAX_TICKS: Final[int] = 52
_STATIC_KINDS: Final[tuple[str, ...]] = ("bundle_event", "bundle_field")
#: SimulationEvent's own bookkeeping fields — never evidence of a claim.
_EVENT_BOOKKEEPING_FIELDS: Final[frozenset[str]] = frozenset({"event_type", "tick", "timestamp"})


def _event_is_meaningful(event: Any) -> bool:
    """True if ``event`` carries any signal beyond a periodic admin stamp.

    Some EventTypes (``ORGANIZATIONAL_ACTION`` is the live specimen — see
    ``OrganizationalActionEvent`` in ``babylon.models.events.ooda_payloads``)
    publish unconditionally EVERY tick as a summary of a resolution pass,
    with every domain field defaulting to its falsy value
    (``layer0_count=action_count=org_count=0``) when nothing organizational
    happened. Presence of the event TYPE in a tick's ``state.events`` alone
    does not prove the claimed logic exercised — the same "presence != truth"
    trap ``SystemEvidence.forbidden_values`` guards against statically for
    ``bundle_field`` rows. Every other declared ``event``-kind row's payload
    carries a real id/name/narrative string field that is truthy whenever the
    event legitimately fires (spot-checked: ``SparkEvent.node_id``,
    ``FascistDriftEvent.node_id``, ``LifecycleTransitionEvent.territory_id``,
    ``MarketCorrectionEvent``/``PrincipalContradictionShiftEvent``'s
    always-populated float/string fields, ``FascistRevanchismEvent
    .narrative_hint``), so this generic check does not regress them.
    """
    for name, value in event:
        if name in _EVENT_BOOKKEEPING_FIELDS:
            continue
        if value:
            return True
    return False


def _entity_attr(state: Any, dotted: str) -> Any:
    entity_id, _, attr = dotted.partition(".")
    entity = state.entities.get(entity_id)
    if entity is None:
        return None
    # Mirrors IdeologicalProfile's three fields exactly (class_consciousness,
    # national_identity, agitation). A future field added to IdeologicalProfile
    # that a coverage row references by dotted key will NOT match this tuple,
    # so _entity_attr falls through to plain getattr(entity, attr) below —
    # entity has no such attribute either, so it returns None and the row
    # reds as a false declaration. Loud-by-design: this tuple must be kept in
    # sync with IdeologicalProfile by hand, not silently miscounted as "no
    # such field, so the row is simply always false and always at fault."
    if attr in ("class_consciousness", "national_identity", "agitation"):
        return getattr(entity.ideology, attr, None)
    return getattr(entity, attr, None)


def run_probe(
    coverage: tuple[ScenarioCoverage, ...] = SCENARIO_COVERAGE,
    max_ticks: int = _DEFAULT_MAX_TICKS,
) -> list[str]:
    """Verify every runtime-verifiable evidence row; return findings."""
    from tools.regression_test import (  # heavy import, local; mirrors gate cadence
        _build_vol3_calculator_overrides,
    )

    from babylon.engine.simulation_engine import step  # heavy import, local

    findings: list[str] = []
    for cov in coverage:
        rows = [r for r in cov.systems if r.kind not in _STATIC_KINDS]
        # A coverage entry that declared systems but they are ALL bundle-kind
        # (e.g. detroit_tri_county) has nothing left for this probe to run —
        # skip it without ever needing a valid SCENARIOS entry. A coverage
        # entry with NO declared systems at all (or with real, runtime-kind
        # rows) against an unknown scenario name is a genuine misconfiguration
        # and must raise loudly, not vanish silently.
        bundle_only = bool(cov.systems) and not rows
        if cov.scenario not in SCENARIOS:
            if bundle_only:
                continue
            raise KeyError(f"declared scenario {cov.scenario!r} not in SCENARIOS")
        if not rows:
            continue
        state, sim_config, defines = create_scenario(cov.scenario)
        # Mirror _run_scenario_ticks exactly: calculator_overrides built ONCE
        # per scenario run and passed into every step() call, so
        # TickDynamicsSystem (and anything gated behind melt_calculator) sees
        # the same services the byte-identical gate exercises.
        calculator_overrides = _build_vol3_calculator_overrides(defines)
        context: dict[str, Any] = {}
        seen_events: set[str] = set()
        initial = {r.key: _entity_attr(state, r.key) for r in rows if r.kind == "entity_delta"}
        initial_econ = {
            r.key: getattr(state.economy, r.key, None) for r in rows if r.kind == "economy_delta"
        }
        changed: set[str] = set()
        for _ in range(max_ticks):
            state = step(
                state,
                sim_config,
                context,
                defines,
                calculator_overrides=calculator_overrides,
            )
            # SimulationEvent's discriminant field is `event_type` (an
            # EventType StrEnum) — verified against src/babylon/models/
            # events/_legacy.py and simulation_engine.py's
            # WorldState.from_graph(..., events=structured_events) call.
            # StrEnum.__str__ returns the bare value ("excessive_force"),
            # matching SystemEvidence.key's plain-string convention.
            # Only count occurrences carrying real signal (_event_is_meaningful) —
            # see its docstring for the ORGANIZATIONAL_ACTION trap this closes.
            seen_events.update(str(e.event_type) for e in state.events if _event_is_meaningful(e))
            for r in rows:
                if r.kind == "entity_delta" and r.key not in changed:
                    if _entity_attr(state, r.key) != initial[r.key]:
                        changed.add(r.key)
                if r.kind == "economy_delta" and r.key not in changed:
                    if getattr(state.economy, r.key, None) != initial_econ[r.key]:
                        changed.add(r.key)
            # Mirror _run_scenario_ticks's early-death break exactly (same
            # PERIPHERY_WORKER_ID / is_dead the gate uses, from tools.shared):
            # the gate stops stepping a scenario the tick the periphery worker
            # dies, so the probe must never certify evidence from ticks the
            # gate itself never executes.
            p_w = state.entities.get(PERIPHERY_WORKER_ID)
            if p_w and is_dead(p_w):
                break
        for r in rows:
            ok = (
                (r.kind == "event" and r.key in seen_events)
                or (r.kind in ("entity_delta", "economy_delta") and r.key in changed)
                or (r.kind == "state_presence" and getattr(state, r.key, None) is not None)
                or (r.kind == "context_presence" and r.key in context)
            )
            if not ok:
                findings.append(
                    f"[gate-blindness] {cov.scenario}: {r.system} evidence "
                    f"({r.kind}: {r.key!r}) did NOT occur in {max_ticks} ticks — "
                    f"claim was: {r.claim}. REMEDY: fix the declaration or the "
                    f"scenario; do not weaken the evidence."
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entry for the family dispatcher (lazy-imported wrapper)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="CI mode (no-op alias)")
    parser.add_argument("--max-ticks", type=int, default=_DEFAULT_MAX_TICKS)
    args = parser.parse_args(argv)
    findings = run_probe(max_ticks=args.max_ticks)
    for finding in findings:
        print(f"GATE-COVERAGE-TRUTH VIOLATION: {finding}", file=sys.stderr)
    if findings:
        return 1
    print(
        f"Gate coverage truth: all declared evidence verified over "
        f"{len(SCENARIO_COVERAGE)} scenarios."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
