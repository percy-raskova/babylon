"""Metrics collection and analysis for Babylon/Babylon.

Metrics are the nervous system of the simulation.
They provide feedback on the health of all subsystems.
"""

from babylon.metrics.collector import MetricsCollector

# MetricsCollectorProtocol moved to babylon.kernel.metrics (Program 14
# Phase 3a) — import it from the kernel directly.
__all__ = ["MetricsCollector"]
