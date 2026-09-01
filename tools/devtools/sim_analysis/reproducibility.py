"""Verification records for development-only analysis trials.

Given the same ``GameDefines``, RNG seed, backend, scenario, maximum tick,
and source revision, a trial should reproduce byte-identically
(Constitution III.7). :class:`ReproRecord` binds a result summary to the
canonical hash of those defines and the remaining run inputs. The hash is a
fingerprint, not an invertible coefficient snapshot: a standalone replay
also needs the base-defines payload or exact overrides stored by the parent
analysis artifact.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from tools.devtools.sim_analysis.backends.types import Result


class ReproRecord(BaseModel):
    """Frozen receipt for verifying one analysis trial's identity.

    :ivar defines_hash: SHA-256 over the canonical ``model_dump()`` of the
        trial's ``GameDefines`` — produced by
        :func:`babylon.config.defines.canonical_defines_hash` (see
        ``docs/reference/determinism-contract.rst`` for the canonical
        serialization contract). Two trials with the same ``defines_hash``
        ran against byte-identical coefficients.
    :ivar rng_seed: The RNG seed threaded through the trial.
    :ivar backend: ``"in_memory"``.
    :ivar scenario: In-memory scenario name for the trial.
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
    scenario: str
    max_ticks: int
    ticks_survived: int = Field(ge=0)
    outcome: str
    terminal_outcome: str | None = None


def build_repro_record(
    result: Result,
    *,
    scenario: str,
    max_ticks: int,
) -> ReproRecord:
    """Build a :class:`ReproRecord` from a trial's :class:`Result`.

    ``scenario`` and ``max_ticks`` are the caller's run parameters rather
    than fields on ``Result`` — the backend-agnostic ``Result`` contract
    intentionally does not carry them (see
    :class:`~tools.devtools.sim_analysis.backends.types.Result`), so the
    caller (which already has them, having passed them to
    ``runner_api.run``) supplies them here.

    :param result: The trial's normalized :class:`Result`.
    :param scenario: The in-memory scenario the trial ran under.
    :param max_ticks: The configured maximum ticks for the trial.
    :returns: A frozen :class:`ReproRecord` binding the trial inputs and
        outcome summary to the non-invertible defines fingerprint.
    """
    return ReproRecord(
        defines_hash=result.defines_hash,
        rng_seed=result.rng_seed,
        backend=result.backend,
        scenario=scenario,
        max_ticks=max_ticks,
        ticks_survived=result.ticks_survived,
        outcome=result.outcome,
        terminal_outcome=result.terminal_outcome,
    )


__all__ = ["ReproRecord", "build_repro_record"]
