"""Object lifecycle management for the RAG system.

This module provides lifecycle state tracking for RAG objects,
allowing monitoring of object states through their lifetime.
"""

import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ObjectState(Enum):
    """Possible states for RAG objects in their lifecycle."""

    CREATED = "created"
    PREPROCESSED = "preprocessed"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    STORED = "stored"
    RETRIEVED = "retrieved"
    REMOVED_FROM_CONTEXT = "removed_from_context"
    ARCHIVED = "archived"
    ERROR = "error"


@dataclass
class PerformanceMetrics:
    """Performance metrics for RAG operations."""

    hot_objects: list[str] = field(default_factory=list)
    cache_hit_rate: dict[str, float] = field(default_factory=dict)
    avg_token_usage: float = 0.0
    latency_stats: dict[str, float] = field(default_factory=dict)
    memory_profile: dict[str, float] = field(default_factory=dict)


class LifecycleManager:
    """Manages the lifecycle of RAG objects.

    Tracks object states, transitions, and provides metrics
    for monitoring system health.
    """

    def __init__(self) -> None:
        """Initialize the lifecycle manager."""
        self._objects: dict[str, dict[str, Any]] = {}
        self._state_history: dict[str, list[tuple[ObjectState, datetime]]] = {}

    def register_object(
        self, object_id: str, initial_state: ObjectState = ObjectState.CREATED
    ) -> None:
        """Register a new object for lifecycle tracking.

        Args:
            object_id: Unique identifier for the object
            initial_state: Initial state for the object
        """
        now = datetime.now()
        self._objects[object_id] = {
            "state": initial_state,
            "created_at": now,
            "updated_at": now,
        }
        self._state_history[object_id] = [(initial_state, now)]

    def update_object_state(self, object_id: str, new_state: ObjectState | str) -> None:
        """Update the state of a tracked object.

        Args:
            object_id: Unique identifier for the object
            new_state: New state for the object (ObjectState enum or string)
        """
        if object_id not in self._objects:
            self.register_object(object_id)

        if isinstance(new_state, str):
            with contextlib.suppress(ValueError):
                new_state = ObjectState(new_state.lower())

        now = datetime.now()
        self._objects[object_id]["state"] = new_state
        self._objects[object_id]["updated_at"] = now

        if isinstance(new_state, ObjectState):
            self._state_history[object_id].append((new_state, now))

    def get_object_state(self, object_id: str) -> ObjectState | str | None:
        """Get the current state of an object.

        Args:
            object_id: Unique identifier for the object

        Returns:
            Current state or None if object not found
        """
        if object_id not in self._objects:
            return None
        state: ObjectState | str = self._objects[object_id]["state"]
        return state

    def get_object(self, object_id: str) -> dict[str, Any] | None:
        """Get full object information.

        Args:
            object_id: Unique identifier for the object

        Returns:
            Object data dict or None if not found
        """
        return self._objects.get(object_id)

    def get_state_history(self, object_id: str) -> list[tuple[ObjectState, datetime]]:
        """Get the state transition history for an object.

        Args:
            object_id: Unique identifier for the object

        Returns:
            List of (state, timestamp) tuples
        """
        return self._state_history.get(object_id, [])

    def get_objects_in_state(self, state: ObjectState) -> list[str]:
        """Get all objects currently in a given state.

        Args:
            state: The state to filter by

        Returns:
            List of object IDs in the specified state
        """
        return [obj_id for obj_id, obj_data in self._objects.items() if obj_data["state"] == state]

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics.

        Returns:
            PerformanceMetrics dataclass with current stats
        """
        # Calculate basic metrics from tracked objects
        total_objects = len(self._objects)
        state_counts: dict[str, int] = {}

        for obj_data in self._objects.values():
            state = obj_data["state"]
            state_name = state.value if isinstance(state, ObjectState) else str(state)
            state_counts[state_name] = state_counts.get(state_name, 0) + 1

        # Convert state_counts to float values for memory_profile
        memory_profile: dict[str, float] = {k: float(v) for k, v in state_counts.items()}

        return PerformanceMetrics(
            hot_objects=list(self._objects.keys())[:10],  # Top 10 objects
            cache_hit_rate={},
            avg_token_usage=0.0,
            latency_stats={"total_objects": float(total_objects)},
            memory_profile=memory_profile,
        )

    def clear(self) -> None:
        """Clear all tracked objects and history."""
        self._objects.clear()
        self._state_history.clear()
