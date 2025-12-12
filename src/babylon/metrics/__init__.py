"""Metrics collection and analysis for Babylon/Babylon.

Metrics are the nervous system of the simulation.
They provide feedback on the health of all subsystems.
"""

from babylon.metrics.collector import MetricsCollector
from babylon.metrics.interfaces import MetricsCollectorProtocol

__all__ = ["MetricsCollector", "MetricsCollectorProtocol"]
