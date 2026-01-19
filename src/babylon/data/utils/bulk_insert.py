"""Bulk insert utilities for data loaders."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import insert
from sqlalchemy.orm import Session


@dataclass
class BatchWriter:
    """Chunked INSERT helper for SQLAlchemy sessions."""

    session: Session
    batch_size: int = 10_000

    def write(self, model: type, rows: Iterable[dict[str, Any]]) -> int:
        """Write rows in batches and return the number of rows written."""
        buffer: list[dict[str, Any]] = []
        total = 0

        for row in rows:
            buffer.append(row)
            if len(buffer) >= self.batch_size:
                total += self._flush(model, buffer)

        if buffer:
            total += self._flush(model, buffer)

        return total

    def _flush(self, model: type, rows: list[dict[str, Any]]) -> int:
        """Execute a batch insert and clear the buffer."""
        self.session.execute(insert(model), rows)
        count = len(rows)
        rows.clear()
        return count
