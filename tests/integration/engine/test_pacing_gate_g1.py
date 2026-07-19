"""G1 — standing 520-tick nationwide null-play pacing gate (spec-116 gate 1).

Citation / traceability
------------------------
- ``docs/superpowers/plans/2026-07-17-playability-spine.md`` spec §7 line 250:
  "null-play nationwide survives past the calibrated tick".
- ``reports/pacing-calibration-2026-07-17.md`` (ADR079, commit ``ba13e902``):
  the analytic 260-tick ``us`` sample + full 5200-tick ``wayne_county`` run
  that grounded the calibration; the full ``us`` 5200-tick (100-year)
  confirmatory run was deliberately KILLED and DEFERRED by the owner
  ("I don't want to complete a century run yet — there's a lot of work to be
  done before I put that kind of work into it.").
- Owner ruling, 2026-07-19: the standing AUTOMATED gate is bound at
  **520 ticks / 10 years** — ``us_nationwide``'s own canonical campaign
  horizon (see ``src/babylon/engine/scenarios/_legacy.py``'s
  ``create_us_scenario`` docstring comment: "the ``us_nationwide`` canonical
  520-tick campaign"). The century (5200-tick) run stays owner-deferred;
  this gate does NOT attempt it.

What this asserts (the null-play survival contract)
----------------------------------------------------
Reuses the existing ``pacing_probe`` instrument (``web/game/management/
commands/pacing_probe.py``) unmodified — this test wraps it, it does not
reimplement it. ``assert_null_play_survival`` (same module) is the shared,
independently unit-tested (``tests/unit/web/test_pacing_gate_assertions.py``,
red-first with a stubbed ``ProbeResult``) assertion wrapper:

1. ``ticks_completed == 520`` — the run completes the full horizon without
   crashing.
2. Every recognizer axis's ``first_recognition`` stays ``None`` — no
   endgame pattern spuriously locks in under null play (no player actions).
3. Every recognizer axis's progress stays ``< 1.0`` at every sampled tick
   (not just the final one) — an independent check of the same underlying
   metric ``EndgameDetector.recognized_pattern`` is derived from, since the
   detector only surfaces one first-matched axis per tick (FR-033 priority
   order) and could otherwise mask a second axis quietly completing
   alongside it ("gate-blindness").

Placement judgment (measured, not assumed)
-------------------------------------------
Per-tick cost was measured directly on this worktree before deciding
placement (brief step 3), not assumed from the (older, pre-ADR086 Business-
seeding) calibration report: a bounded 20-tick ``us`` sample measured
**117.49s wall-clock** (``time poetry run python manage.py pacing_probe
--scenario us --ticks 20 --seed 0``). Fitting the calibration report's own
linear cost model (intercept ~3.8s, from the 5-tick/260-tick ``us`` data
points) to this sample gives a marginal rate of ~5.68s/tick, i.e. a 520-tick
run is expected to cost **~3.8 + 5.68 x 520 ~= 2960s (~49 minutes)** —
solidly in the "minutes-heavy" band the brief anticipated for a nationwide
graph. This is why the gate:

- lives in the INTEGRATION tier (``tests/integration/engine/``), never
  ``tests/unit`` (repo law: heavy/slow tests never the fast unit gate);
- carries the dedicated ``pacing_gate`` marker (registered in
  ``pyproject.toml``) so it is positively EXCLUDED from every existing
  automatic sweep that would otherwise catch it by directory alone —
  ``mise run check`` / ``test:unit`` (different directory, unaffected),
  ``mise run test:rest-ci`` (marker-excluded: ``-m '... and not
  pacing_gate'``), and the nightly ``py313-forward-compat`` leg
  (same marker exclusion) — and is invoked ONLY via the dedicated
  ``mise run qa:pacing`` task, wired into its own job in
  ``.github/workflows/nightly.yml``;
- is never part of the PR-blocking ``ci.yml`` path (that workflow only
  invokes ``test:unit-ci`` and ``qa:regression``, neither of which touches
  this file or directory).

Determinism
------------
Fixed ``rng_seed`` (Constitution III.7 — ``SimulationConfig`` carries only
``rng_seed``, no other run-scoped state); single-flight (no xdist parametrization,
no parallel sims — this file is invoked directly by ``qa:pacing`` without
``-n``).

No baseline movement: this is read-only instrumentation over the existing,
unmodified ``pacing_probe``/engine — it asserts on the probe's *output*, it
never touches ``qa:regression``'s scenarios or baselines.
"""

from __future__ import annotations

import pytest

from game.management.commands.pacing_probe import assert_null_play_survival, run_probe

pytestmark = pytest.mark.pacing_gate

_TICKS = 520
_SEED = 0


def test_g1_520_tick_nationwide_null_play_survives() -> None:
    """Run the real 520-tick ``us`` null-play probe once and assert survival.

    This is the acceptance evidence for G1: a genuine engine run (no stubs,
    no mocks — ``run_probe`` drives the real ``step()`` loop against the
    real ``us`` nationwide scenario), asserted against the shared
    ``assert_null_play_survival`` contract.
    """
    result = run_probe(scenario="us", ticks=_TICKS, seed=_SEED)
    assert_null_play_survival(result, expected_ticks=_TICKS)
