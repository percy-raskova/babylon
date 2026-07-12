"""Optimization execution backends.

Each backend module (``headless``, ``in_memory``) exposes one ``run_*``
function that drives a simulation trial and reshapes its raw output into
the shared :class:`~babylon.engine.optimization.backends.types.Result`
contract. ``babylon.engine.optimization.runner_api.run`` dispatches to
these by name; algorithms never call a backend directly.
"""

from __future__ import annotations

from babylon.engine.optimization.backends.types import Result

__all__ = ["Result"]
