"""Backends for development-only simulation analysis.

The ``in_memory`` backend drives a frozen-reference simulation trial and
reshapes its output into the shared
:class:`~tools.devtools.sim_analysis.backends.types.Result` contract.
"""

from __future__ import annotations

from tools.devtools.sim_analysis.backends.types import Result

__all__ = ["Result"]
