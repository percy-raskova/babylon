"""Attention thread intelligence system (Feature 039).

Manages the state's finite pool of intelligence resources (attention threads)
that track targets, accumulate partial knowledge, and enable Sparrow-grounded
network vulnerability analysis.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: FR-A01 through FR-A08.
    :mod:`babylon.ooda.state_ai`: State AI decision system.
"""

from babylon.ooda.attention.observation import build_g_observed, compute_observation_ceiling
from babylon.ooda.attention.sparrow import analyze_network
from babylon.ooda.attention.thread_manager import (
    advance_thread_phase,
    allocate_threads,
    update_thread_tick,
)

__all__ = [
    "advance_thread_phase",
    "allocate_threads",
    "analyze_network",
    "build_g_observed",
    "compute_observation_ceiling",
    "update_thread_tick",
]
