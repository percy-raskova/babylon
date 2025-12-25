"""Metrics data models for simulation observation and analysis.

These Pydantic models define the contract for MetricsCollector output,
enabling unified metrics collection between the parameter sweeper and
dashboard components.

Sprint 4.1: Phase 4 Dashboard/Sweeper unification.

RED PHASE STUB: This module contains minimal stubs that raise
NotImplementedError. The GREEN phase will provide implementations.
"""

from __future__ import annotations

from pydantic import BaseModel


class EntityMetrics(BaseModel):
    """Metrics snapshot for a single entity at a specific tick.

    Captures wealth, consciousness, and survival probabilities for
    analysis and visualization.

    RED PHASE: Stub that raises NotImplementedError on instantiation.
    """

    def __init__(self, **data: object) -> None:
        """Stub: raises NotImplementedError."""
        raise NotImplementedError("EntityMetrics not yet implemented (RED phase)")


class EdgeMetrics(BaseModel):
    """Metrics snapshot for relationship edges at a specific tick.

    Captures tension, value flows, and solidarity strength for
    analysis and visualization.

    RED PHASE: Stub that raises NotImplementedError on instantiation.
    """

    def __init__(self, **data: object) -> None:
        """Stub: raises NotImplementedError."""
        raise NotImplementedError("EdgeMetrics not yet implemented (RED phase)")


class TickMetrics(BaseModel):
    """Complete metrics snapshot for a single simulation tick.

    Aggregates entity and edge metrics for comprehensive tick analysis.

    RED PHASE: Stub that raises NotImplementedError on instantiation.
    """

    def __init__(self, **data: object) -> None:
        """Stub: raises NotImplementedError."""
        raise NotImplementedError("TickMetrics not yet implemented (RED phase)")


class SweepSummary(BaseModel):
    """Summary statistics for a completed simulation run.

    Aggregates metrics across all ticks for parameter sweep analysis.

    RED PHASE: Stub that raises NotImplementedError on instantiation.
    """

    def __init__(self, **data: object) -> None:
        """Stub: raises NotImplementedError."""
        raise NotImplementedError("SweepSummary not yet implemented (RED phase)")
