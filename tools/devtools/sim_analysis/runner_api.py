"""Single entry point for an in-memory frozen-reference analysis trial."""

from __future__ import annotations

from tools.devtools.sim_analysis.backends.types import Result

from babylon.config.defines import GameDefines

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
    """Run one frozen-reference analysis trial and return its normalized result.

    :param defines: The (possibly swept) ``GameDefines`` for this trial.
    :param seed: RNG seed for this trial (Constitution III.7).
    :param max_ticks: Maximum ticks to run.
    :param backend: Must be ``"in_memory"``.
    :param scenario: ``"imperial_circuit"`` or ``"two_node"``.
    :returns: Backend-normalized :class:`Result`.
    :raises ValueError: If ``max_ticks`` is not positive or ``backend`` is
        not a recognized name.
    """
    if isinstance(max_ticks, bool) or not isinstance(max_ticks, int) or max_ticks < 1:
        raise ValueError(f"max_ticks must be a positive integer, got: {max_ticks!r}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an integer, got: {seed!r}")
    if backend == "in_memory":
        from tools.devtools.sim_analysis.backends.in_memory import run_in_memory

        return run_in_memory(
            defines=defines,
            seed=seed,
            max_ticks=max_ticks,
            scenario=scenario,
        )

    raise ValueError(f"Unknown backend {backend!r}; expected one of: {_BACKENDS}")


__all__ = ["run"]
