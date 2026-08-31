"""Single entry point for an in-memory optimization trial."""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.engine.optimization.backends.types import Result

#: Backend names dispatched by :func:`run`.
_BACKENDS = ("in_memory",)


def run(
    defines: GameDefines,
    *,
    seed: int = 2010,
    max_ticks: int = 5200,
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
) -> Result:
    """Run one optimization trial and return its normalized :class:`Result`.

    :param defines: The (possibly swept) ``GameDefines`` for this trial.
    :param seed: RNG seed for this trial (Constitution III.7).
    :param max_ticks: Maximum ticks to run.
    :param backend: Must be ``"in_memory"``.
    :param scenario: ``"imperial_circuit"`` or ``"two_node"``.
    :returns: Backend-normalized :class:`Result`.
    :raises ValueError: If ``backend`` is not a recognized name.
    """
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
