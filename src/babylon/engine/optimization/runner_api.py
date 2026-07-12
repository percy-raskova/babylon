"""Single entry point dispatching an optimization trial to a backend.

This is the one function every optimization algorithm (sweep, Monte Carlo,
sensitivity, Bayesian search — wired in a later phase) should call. It hides
backend selection and default resolution behind one signature so an
algorithm never has to know whether a trial ran against Postgres or the
in-memory legacy engine.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from babylon.config.defines import GameDefines
from babylon.engine.optimization.backends.types import Result

#: Backend names dispatched by :func:`run`.
_BACKENDS = ("headless", "in_memory")


def run(
    defines: GameDefines,
    *,
    seed: int = 2010,
    max_ticks: int = 5200,
    scope_fips: frozenset[str] | None = None,
    scope_name: str = "detroit-tri-county",
    backend: str = "headless",
    output_dir: Path | None = None,
    scenario: str = "imperial_circuit",
) -> Result:
    """Run one optimization trial and return its normalized :class:`Result`.

    :param defines: The (possibly swept) ``GameDefines`` for this trial.
    :param seed: RNG seed for this trial (Constitution III.7).
    :param max_ticks: Maximum ticks to run.
    :param scope_fips: County FIPS codes in scope. ``backend="headless"``
        only — resolved from ``scope_name`` via
        :func:`babylon.engine.headless_runner.scopes.resolve_scope` when
        ``None``. Ignored for ``backend="in_memory"``.
    :param scope_name: Predefined scope name (default: the Detroit
        tri-county fixture — Wayne/Oakland/Macomb, ``26163``/``26125``/
        ``26099``). ``backend="headless"`` only.
    :param backend: ``"headless"`` (Postgres-backed, spec-064/065/066) or
        ``"in_memory"`` (fast legacy engine, spec-064's predecessor path).
    :param output_dir: Artifact directory. ``backend="headless"`` only —
        defaults to a fresh temp directory when ``None`` (the caller
        doesn't need the artifact bundle for a bare optimization trial).
    :param scenario: ``"imperial_circuit"`` or ``"two_node"``.
        ``backend="in_memory"`` only.
    :returns: Backend-normalized :class:`Result`.
    :raises ValueError: If ``backend`` is not a recognized name.
    """
    if backend == "headless":
        from babylon.engine.headless_runner.scopes import resolve_scope
        from babylon.engine.optimization.backends.headless import run_headless

        resolved_scope_fips = (
            scope_fips if scope_fips is not None else resolve_scope(scope_name).scope_fips
        )
        resolved_output_dir = (
            output_dir
            if output_dir is not None
            else Path(tempfile.mkdtemp(prefix="babylon-optimization-"))
        )
        return run_headless(
            defines=defines,
            seed=seed,
            max_ticks=max_ticks,
            scope_fips=resolved_scope_fips,
            scope_name=scope_name,
            output_dir=resolved_output_dir,
        )

    if backend == "in_memory":
        from babylon.engine.optimization.backends.in_memory import run_in_memory

        return run_in_memory(
            defines=defines,
            seed=seed,
            max_ticks=max_ticks,
            scenario=scenario,
        )

    raise ValueError(f"Unknown backend {backend!r}; expected one of: {_BACKENDS}")


__all__ = ["run"]
