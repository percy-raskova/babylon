"""SQLAlchemy models for metrics persistence.

These models store the historical record of the simulation's
performance and state metrics in the Ledger (SQLite).
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

# Create a separate Base for metrics to avoid circular imports
MetricsBase = declarative_base()


class Metric(MetricsBase):
    """A single metric measurement stored in the database.

    This is the materialized form of MetricEvent, persisted to SQLite
    for historical analysis and dashboard rendering.
    """

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    tags = Column(Text, nullable=True)  # JSON-serialized dict
    extra_data = Column(Text, nullable=True)  # JSON-serialized dict (renamed from metadata)

    def __repr__(self) -> str:
        return f"<Metric(name={self.name!r}, value={self.value}, timestamp={self.timestamp})>"


class Counter(MetricsBase):
    """A counter metric that only increases.

    Used for tracking cumulative counts like total events processed,
    total embeddings generated, etc.
    """

    __tablename__ = "counters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Counter(name={self.name!r}, value={self.value})>"


class TimeSeries(MetricsBase):
    """Time-series data point for dashboard visualization.

    Optimized for time-range queries and charting. This is where
    the simulation's history is recorded for player dashboards.
    """

    __tablename__ = "time_series"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tick = Column(Integer, nullable=False, index=True)  # Game turn
    metric = Column(String(255), nullable=False, index=True)
    value = Column(Float, nullable=False)
    region = Column(String(100), nullable=True)  # "core", "periphery", etc.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<TimeSeries(tick={self.tick}, metric={self.metric!r}, value={self.value})>"
