"""SQLAlchemy models for metrics persistence.

These models store the historical record of the simulation's
performance and state metrics in the Ledger (SQLite).
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class MetricsBase(DeclarativeBase):
    """Base class for metrics models. Separate from main app to avoid circular imports."""

    pass


class Metric(MetricsBase):
    """A single metric measurement stored in the database.

    This is the materialized form of MetricEvent, persisted to SQLite
    for historical analysis and dashboard rendering.
    """

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-serialized dict
    extra_data: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON-serialized dict (renamed from metadata)

    def __repr__(self) -> str:
        return f"<Metric(name={self.name!r}, value={self.value}, timestamp={self.timestamp})>"


class Counter(MetricsBase):
    """A counter metric that only increases.

    Used for tracking cumulative counts like total events processed,
    total embeddings generated, etc.
    """

    __tablename__ = "counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Counter(name={self.name!r}, value={self.value})>"


class TimeSeries(MetricsBase):
    """Time-series data point for dashboard visualization.

    Optimized for time-range queries and charting. This is where
    the simulation's history is recorded for player dashboards.
    """

    __tablename__ = "time_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tick: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # Game turn
    metric: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "core", "periphery"
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<TimeSeries(tick={self.tick}, metric={self.metric!r}, value={self.value})>"
