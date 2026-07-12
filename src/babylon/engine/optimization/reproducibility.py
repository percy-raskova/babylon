"""Reproducibility record for optimization trials.

Every trial run through :func:`babylon.engine.optimization.runner_api.run`
should be replayable: given the same ``GameDefines``, RNG seed, backend, and
run parameters, the same trial must reproduce byte-identically (Constitution
III.7). :class:`ReproRecord` is the frozen, minimal receipt that captures
exactly those inputs plus a summary of what the trial produced, so a trial
can be logged, diffed, and replayed later without needing the full
:class:`~babylon.engine.optimization.backends.types.Result` object kept
around.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.optimization.backends.types import Result


class ReproRecord(BaseModel):
    """Minimal, frozen receipt for replaying one optimization trial.

    :ivar defines_hash: SHA-256 over the canonical ``model_dump()`` of the
        trial's ``GameDefines`` — the same hash
        ``babylon.engine.headless_runner.runner._defines_hash`` computes
        (see ``docs/reference/determinism-contract.rst`` for the canonical
        serialization contract). Two trials with the same ``defines_hash``
        ran against byte-identical coefficients.
    :ivar rng_seed: The RNG seed threaded through the trial.
    :ivar backend: ``"headless"`` or ``"in_memory"``.
    :ivar scope_name: Scope label the trial ran under (backend-defined;
        e.g. ``"detroit-tri-county"`` for headless, the scenario name for
        in-memory).
    :ivar max_ticks: Configured maximum ticks for the trial.
    :ivar ticks_survived: Ticks actually completed (may be less than
        ``max_ticks`` on death or early termination).
    :ivar outcome: ``"SURVIVED"`` or ``"DIED"``.
    :ivar terminal_outcome: ``"revolution"``, ``"genocide"``, or ``None``.
    """

    model_config = ConfigDict(frozen=True)

    defines_hash: str
    rng_seed: int
    backend: str
    scope_name: str
    max_ticks: int
    ticks_survived: int = Field(ge=0)
    outcome: str
    terminal_outcome: str | None = None


def build_repro_record(
    result: Result,
    *,
    scope_name: str,
    max_ticks: int,
) -> ReproRecord:
    """Build a :class:`ReproRecord` from a trial's :class:`Result`.

    ``scope_name`` and ``max_ticks`` are the caller's run parameters rather
    than fields on ``Result`` — the backend-agnostic ``Result`` contract
    intentionally does not carry them (see
    :class:`~babylon.engine.optimization.backends.types.Result`), so the
    caller (which already has them, having passed them to
    ``runner_api.run``) supplies them here.

    :param result: The trial's normalized :class:`Result`.
    :param scope_name: The scope/scenario label the trial ran under.
    :param max_ticks: The configured maximum ticks for the trial.
    :returns: A frozen :class:`ReproRecord` capturing the trial's replay
        inputs and outcome summary.
    """
    return ReproRecord(
        defines_hash=result.defines_hash,
        rng_seed=result.rng_seed,
        backend=result.backend,
        scope_name=scope_name,
        max_ticks=max_ticks,
        ticks_survived=result.ticks_survived,
        outcome=result.outcome,
        terminal_outcome=result.terminal_outcome,
    )


__all__ = ["ReproRecord", "build_repro_record"]
