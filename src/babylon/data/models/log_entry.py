"""Log entry model for database logging."""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from babylon.data.database import Base


class LogEntry(Base):
    """SQLAlchemy model for log entries."""

    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    level: Mapped[str | None] = mapped_column(String, default=None)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    message: Mapped[str | None] = mapped_column(String, default=None)
    module: Mapped[str | None] = mapped_column(String, default=None)
    correlation_id: Mapped[str | None] = mapped_column(String, default=None)
