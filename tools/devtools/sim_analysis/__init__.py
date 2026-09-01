"""Development-only analysis suite for Babylon's frozen Python simulation.

This package lives under ``tools`` so it cannot ship in the ``babylon`` game
wheel. It deliberately imports the frozen Python engine as an analysis subject;
it does not define current game authority or write authoritative game state.

Provides the foundation for tuning :class:`~babylon.config.defines.GameDefines`
coefficients against simulation outcomes: parameter injection/introspection
(:mod:`.params`, ADR038), a backend-agnostic trial result
(:mod:`.backends.types`), the retained in-memory periphery backend
(:mod:`.backends`), one entry point (:mod:`.runner_api`), a unified
override/range grammar (:mod:`.ranges`), objective functions including the
Carceral Equilibrium scorer (:mod:`.objectives`), and a reproducibility
receipt for replaying any trial (:mod:`.reproducibility`).

It also exports the four algorithm entry points built on that foundation —
:func:`~tools.devtools.sim_analysis.sweep.run_sweep`,
:func:`~tools.devtools.sim_analysis.monte_carlo.run_monte_carlo`,
:func:`~tools.devtools.sim_analysis.sensitivity.run_sensitivity`, and
:func:`~tools.devtools.sim_analysis.bayesian.run_bayesian` — the same
callables ``python -m tools.devtools.sim_analysis`` dispatches to.
``sensitivity`` and ``bayesian`` depend on optional heavy libraries (SALib,
Optuna respectively); both modules already guard those imports internally
(``HAS_SALIB`` / ``HAS_OPTUNA``) and raise a clean ``ImportError`` only when
their ``run_*`` function is *called* without the dependency installed. The
imports below add a second, defense-in-depth guard at the package boundary
itself — mirroring that same try/except pattern — so that
``import tools.devtools.sim_analysis`` can never hard-fail from a missing
optional dependency, even if a future edit to one of those modules weakens
its own guard.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.monte_carlo import run_monte_carlo
from tools.devtools.sim_analysis.objectives import Objective, carceral_objective
from tools.devtools.sim_analysis.params import (
    get_parameter_type,
    get_tunable_parameters,
    inject_parameter,
    inject_parameters,
)
from tools.devtools.sim_analysis.reproducibility import ReproRecord
from tools.devtools.sim_analysis.runner_api import run
from tools.devtools.sim_analysis.sweep import run_sweep

run_sensitivity: Callable[..., Any] | None
try:
    from tools.devtools.sim_analysis.sensitivity import run_sensitivity
except ImportError:  # pragma: no cover - exercised only in SALib-less envs
    run_sensitivity = None

run_bayesian: Callable[..., Any] | None
try:
    from tools.devtools.sim_analysis.bayesian import run_bayesian
except ImportError:  # pragma: no cover - exercised only without the dev group installed
    run_bayesian = None

__all__ = [
    "Result",
    "run",
    "inject_parameter",
    "inject_parameters",
    "get_tunable_parameters",
    "get_parameter_type",
    "Objective",
    "carceral_objective",
    "ReproRecord",
    "run_sweep",
    "run_monte_carlo",
    "run_sensitivity",
    "run_bayesian",
]
