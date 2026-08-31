"""Optimization execution backends.

The ``in_memory`` backend drives a frozen-reference simulation trial and
reshapes its output into the shared
:class:`~babylon.engine.optimization.backends.types.Result` contract.
"""

from __future__ import annotations

from babylon.engine.optimization.backends.types import Result

__all__ = ["Result"]
