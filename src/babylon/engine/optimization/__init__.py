"""Parameter optimization package for the Babylon simulation engine.

Provides the foundation for tuning :class:`~babylon.config.defines.GameDefines`
coefficients against simulation outcomes: parameter injection/introspection
(:mod:`.params`, ADR038), a backend-agnostic trial result
(:mod:`.backends.types`), two execution backends — the Postgres-backed
headless runner and the fast in-memory legacy engine (:mod:`.backends`) —
dispatched through one entry point (:mod:`.runner_api`), a unified
override/range grammar (:mod:`.ranges`), objective functions including the
Carceral Equilibrium scorer (:mod:`.objectives`), and a reproducibility
receipt for replaying any trial (:mod:`.reproducibility`).

It also exports the four algorithm entry points built on that foundation —
:func:`~babylon.engine.optimization.sweep.run_sweep`,
:func:`~babylon.engine.optimization.monte_carlo.run_monte_carlo`,
:func:`~babylon.engine.optimization.sensitivity.run_sensitivity`, and
:func:`~babylon.engine.optimization.bayesian.run_bayesian` — the same
callables ``python -m babylon.engine.optimization`` dispatches to.
``sensitivity`` and ``bayesian`` depend on optional heavy libraries (SALib,
Optuna respectively); both modules already guard those imports internally
(``HAS_SALIB`` / ``HAS_OPTUNA``) and raise a clean ``ImportError`` only when
their ``run_*`` function is *called* without the dependency installed. The
imports below add a second, defense-in-depth guard at the package boundary
itself — mirroring that same try/except pattern — so that
``import babylon.engine.optimization`` can never hard-fail from a missing
optional dependency, even if a future edit to one of those modules weakens
its own guard.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from babylon.engine.optimization.backends.types import Result
from babylon.engine.optimization.monte_carlo import run_monte_carlo
from babylon.engine.optimization.objectives import Objective, carceral_objective
from babylon.engine.optimization.params import (
    get_parameter_type,
    get_tunable_parameters,
    inject_parameter,
    inject_parameters,
)
from babylon.engine.optimization.reproducibility import ReproRecord
from babylon.engine.optimization.runner_api import run
from babylon.engine.optimization.sweep import run_sweep

run_sensitivity: Callable[..., Any] | None
try:
    from babylon.engine.optimization.sensitivity import run_sensitivity
except ImportError:  # pragma: no cover - exercised only in SALib-less envs
    run_sensitivity = None

run_bayesian: Callable[..., Any] | None
try:
    from babylon.engine.optimization.bayesian import run_bayesian
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
