"""Backend-agnostic result type for the optimization package.

:class:`Result` is the single shape every backend (headless Postgres-backed
runner, fast in-memory legacy engine, future backends) must reshape its raw
run output into. Algorithms (sweep, Monte Carlo, sensitivity, Bayesian
search — added in a later phase) consume only :class:`Result`, never a
backend-specific return type, so the backend is a swappable implementation
detail behind one contract.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Result(BaseModel):
    """One trial's outcome, normalized across all optimization backends.

    :ivar ticks_survived: Number of ticks the run completed before death,
        early termination, or reaching ``max_ticks``.
    :ivar outcome: ``"SURVIVED"`` or ``"DIED"`` (coarse legacy-compatible
        outcome discriminator; see ``terminal_outcome`` for the richer
        Track-A revolution/genocide bifurcation).
    :ivar max_tension: Maximum EXPLOITATION-edge tension observed across the
        run (0.0 if the backend does not track tension).
    :ivar final_wealth: Terminal-tick wealth/value aggregate (backend-defined
        proxy — see each backend's docstring for the precise definition).
    :ivar phase_milestones: Dict mapping Carceral Equilibrium phase name
        (``"superwage_crisis"``, ``"class_decomposition"``,
        ``"control_ratio_crisis"``, ``"terminal_decision"``) to the first
        tick it fired, or ``None`` if the backend cannot detect it (honest
        per Constitution III.11 — never fabricate a milestone).
    :ivar terminal_outcome: ``"revolution"``, ``"genocide"``, or ``None`` if
        the TERMINAL_DECISION event never fired / is not observable by this
        backend.
    :ivar defines_hash: SHA-256 over the canonical ``model_dump()`` of the
        ``GameDefines`` used for this trial (see
        ``docs/reference/determinism-contract.rst``).
    :ivar rng_seed: The RNG seed threaded through this trial.
    :ivar backend: Name of the backend that produced this result
        (``"headless"`` or ``"in_memory"``).
    :ivar extra: Backend-specific overflow fields not promoted to the core
        contract (e.g. artifact paths, session ids).
    """

    model_config = ConfigDict(frozen=True)

    ticks_survived: int = Field(ge=0)
    outcome: str
    max_tension: float
    final_wealth: float
    phase_milestones: dict[str, int | None] = Field(default_factory=dict)
    terminal_outcome: str | None = None
    defines_hash: str
    rng_seed: int
    backend: str
    extra: dict[str, object] = Field(default_factory=dict)


__all__ = ["Result"]
