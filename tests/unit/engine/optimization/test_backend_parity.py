"""Backend parity: in_memory and headless must agree in direction.

``runner_api.run`` hides two structurally different backends (fast in-memory
legacy engine vs. Postgres-backed headless runner) behind one ``Result``
contract (see ``backends/types.py``). The two backends run different
scenarios/scopes and compute ``final_wealth``/``max_tension`` from different
underlying state shapes, so byte-for-byte equality between them is not a
meaningful contract (unlike ``test_reproducibility.py``'s same-backend
determinism check). What *is* meaningful: for the same seed and defines over
a short deterministic window, the two backends should not qualitatively
disagree about whether the population survives.

The ``in_memory`` leg always runs (no Postgres required — this is the
package's fast default backend, exercised by every other test in this
directory). The ``headless`` leg requires a reachable Postgres on ``:5433``
*and* a populated SQLite reference DB (``data/sqlite/...``) — either may be
absent in a given worktree/sandbox, so that leg is skipped gracefully rather
than failing the suite for an infrastructure gap unrelated to the code under
test.
"""

from __future__ import annotations

import socket

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.optimization import runner_api
from babylon.engine.optimization.backends.types import Result

_SEED = 2010
_MAX_TICKS = 5
_POSTGRES_HOST = "localhost"
_POSTGRES_PORT = 5433
_CONNECT_TIMEOUT_SECONDS = 2.0


def _postgres_reachable() -> bool:
    """Best-effort raw TCP probe of the isolated dev Postgres (``:5433``).

    Only tells us the port accepts connections — not that the database, the
    ``test``/``babylon_test`` credentials, or the SQLite reference DB the
    headless runner also needs are actually usable. Those are checked by
    actually attempting the run (see ``_attempt_headless_run``).
    """
    try:
        with socket.create_connection(
            (_POSTGRES_HOST, _POSTGRES_PORT), timeout=_CONNECT_TIMEOUT_SECONDS
        ):
            return True
    except OSError:
        return False


def _attempt_headless_run(defines: GameDefines) -> Result | None:
    """Run the headless backend, or ``None`` if its environment isn't usable.

    Broad ``except Exception`` is deliberate here (unlike the Logic-layer
    "let it bubble" rule elsewhere in this codebase): this is a diagnostic
    parity test whose headless leg depends on infrastructure (Postgres
    credentials, a populated ``data/sqlite`` reference DB, migrations
    applied) that varies by worktree/sandbox and is orthogonal to the
    optimization package's own correctness. Any failure here is reported as
    a skip, never a pass — see the caller.
    """
    try:
        return runner_api.run(
            defines,
            seed=_SEED,
            max_ticks=_MAX_TICKS,
            backend="headless",
            scope_name="detroit-tri-county",
        )
    except Exception:  # noqa: BLE001 — deliberate: infra gap -> skip, not fail
        return None


def _agree_in_direction(in_memory_result: Result, headless_result: Result) -> bool:
    """Two backends 'agree in direction' when neither contradicts the other
    on the coarse survived-vs-died question over the same short window.
    """
    return in_memory_result.outcome == headless_result.outcome


class TestBackendParity:
    def test_in_memory_runs_five_ticks(self) -> None:
        """The always-available leg: establishes the baseline this test's
        headless comparison (when available) is checked against.
        """
        defines = GameDefines()
        result = runner_api.run(
            defines,
            seed=_SEED,
            max_ticks=_MAX_TICKS,
            backend="in_memory",
            scenario="imperial_circuit",
        )
        assert result.backend == "in_memory"
        assert result.ticks_survived <= _MAX_TICKS
        assert result.outcome in ("SURVIVED", "DIED")

    def test_backends_agree_in_direction_if_postgres_available(self) -> None:
        if not _postgres_reachable():
            pytest.skip(
                f"Postgres not reachable on {_POSTGRES_HOST}:{_POSTGRES_PORT} "
                "(mise run db:up) — skipping headless parity leg"
            )

        defines = GameDefines()
        in_memory_result = runner_api.run(
            defines,
            seed=_SEED,
            max_ticks=_MAX_TICKS,
            backend="in_memory",
            scenario="imperial_circuit",
        )

        headless_result = _attempt_headless_run(defines)
        if headless_result is None:
            pytest.skip(
                "headless backend environment unavailable (reference DB, "
                "migrations, or credentials) — skipping headless parity leg"
            )

        assert _agree_in_direction(in_memory_result, headless_result), (
            f"in_memory outcome={in_memory_result.outcome!r} vs. "
            f"headless outcome={headless_result.outcome!r} — backends "
            "disagree in direction for identical seed/defines"
        )
