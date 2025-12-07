"""Data models for Babylon.

This package re-exports models from the canonical locations:
- Entity models are in babylon.models.entities
- Database models (SQLAlchemy) are local

For new code, prefer importing directly from babylon.models.
"""

# Re-export Pydantic models from canonical location for backwards compatibility
from babylon.models.entities import Contradiction, Effect, Trigger

# Database models (SQLAlchemy) - local
from babylon.data.models.event import Event

__all__ = [
    "Contradiction",
    "Effect",
    "Event",
    "Trigger",
]
