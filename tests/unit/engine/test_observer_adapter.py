"""Unit tests for ProtocolObserverAdapter.

Feature: 006-gui-protocol-extension
Tests: T012-T015 (Adapter Infrastructure)

These tests verify the thread-safe observer adapter that bridges
simulation engine notifications to GUI callbacks.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from babylon.engine.observer_adapter import ProtocolObserverAdapter

if TYPE_CHECKING:
    from babylon.models.snapshots import SimulationSnapshot
    from babylon.protocols import ObserverCallback


class TestAdapterRegister:
    """T012: adapter.register() adds callback (thread-safe)."""

    def test_register_adds_callback(self) -> None:
        """Register adds callback to the list."""
        mock_sim = MagicMock()
        adapter = ProtocolObserverAdapter(mock_sim)

        callback: ObserverCallback = MagicMock()
        adapter.register(callback)

        # Verify callback is in list (access private for testing)
        assert callback in adapter._callbacks

    def test_register_idempotent(self) -> None:
        """Duplicate registration is idempotent (callback added once)."""
        mock_sim = MagicMock()
        adapter = ProtocolObserverAdapter(mock_sim)

        callback: ObserverCallback = MagicMock()
        adapter.register(callback)
        adapter.register(callback)  # Duplicate

        # Should only be in list once
        assert adapter._callbacks.count(callback) == 1

    def test_register_thread_safe(self) -> None:
        """Register is thread-safe under concurrent access."""
        mock_sim = MagicMock()
        adapter = ProtocolObserverAdapter(mock_sim)

        callbacks: list[ObserverCallback] = [MagicMock() for _ in range(100)]
        errors: list[Exception] = []

        def register_callback(cb: ObserverCallback) -> None:
            try:
                adapter.register(cb)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_callback, args=(cb,)) for cb in callbacks]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors during concurrent registration
        assert len(errors) == 0
        # All callbacks registered
        assert len(adapter._callbacks) == 100


class TestAdapterUnregister:
    """T013: adapter.unregister() removes callback (thread-safe)."""

    def test_unregister_removes_callback(self) -> None:
        """Unregister removes callback from the list."""
        mock_sim = MagicMock()
        adapter = ProtocolObserverAdapter(mock_sim)

        callback: ObserverCallback = MagicMock()
        adapter.register(callback)
        assert callback in adapter._callbacks

        adapter.unregister(callback)
        assert callback not in adapter._callbacks

    def test_unregister_unknown_noop(self) -> None:
        """Unregister of unknown callback is no-op (no error)."""
        mock_sim = MagicMock()
        adapter = ProtocolObserverAdapter(mock_sim)

        unknown_callback: ObserverCallback = MagicMock()

        # Should not raise
        adapter.unregister(unknown_callback)

    def test_unregister_thread_safe(self) -> None:
        """Unregister is thread-safe under concurrent access."""
        mock_sim = MagicMock()
        adapter = ProtocolObserverAdapter(mock_sim)

        callbacks: list[ObserverCallback] = [MagicMock() for _ in range(100)]
        for cb in callbacks:
            adapter.register(cb)

        errors: list[Exception] = []

        def unregister_callback(cb: ObserverCallback) -> None:
            try:
                adapter.unregister(cb)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=unregister_callback, args=(cb,)) for cb in callbacks]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors during concurrent unregistration
        assert len(errors) == 0
        # All callbacks removed
        assert len(adapter._callbacks) == 0


class TestAdapterNotifySnapshotFirst:
    """T014: adapter.notify() creates snapshot BEFORE iterating callbacks."""

    def test_notify_creates_snapshot_before_iteration(self) -> None:
        """Snapshot is created before callbacks are invoked."""
        mock_sim = MagicMock()
        mock_snapshot = MagicMock()
        mock_sim.get_snapshot.return_value = mock_snapshot

        adapter = ProtocolObserverAdapter(mock_sim)

        call_order: list[str] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            call_order.append("callback")

        # Wrap get_snapshot to track call order
        original_get_snapshot = mock_sim.get_snapshot

        def tracked_get_snapshot() -> SimulationSnapshot:
            call_order.append("get_snapshot")
            return original_get_snapshot()

        mock_sim.get_snapshot = tracked_get_snapshot

        adapter.register(callback)
        adapter.notify(tick=5)

        # Verify: get_snapshot called BEFORE callback
        assert call_order == ["get_snapshot", "callback"]

    def test_notify_passes_frozen_snapshot_not_simulation(self) -> None:
        """Callback receives snapshot, not simulation reference."""
        mock_sim = MagicMock()
        mock_snapshot = MagicMock()
        mock_sim.get_snapshot.return_value = mock_snapshot

        adapter = ProtocolObserverAdapter(mock_sim)

        received_args: list[tuple[int, SimulationSnapshot]] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            received_args.append((tick, snapshot))

        adapter.register(callback)
        adapter.notify(tick=42)

        assert len(received_args) == 1
        tick, snapshot = received_args[0]
        assert tick == 42
        assert snapshot is mock_snapshot  # Same object reference
        assert snapshot is not mock_sim  # NOT the simulation itself

    def test_notify_all_callbacks_same_snapshot(self) -> None:
        """All callbacks receive the same snapshot instance."""
        mock_sim = MagicMock()
        mock_snapshot = MagicMock()
        mock_sim.get_snapshot.return_value = mock_snapshot

        adapter = ProtocolObserverAdapter(mock_sim)

        snapshots: list[SimulationSnapshot] = []

        def callback1(tick: int, snapshot: SimulationSnapshot) -> None:
            snapshots.append(snapshot)

        def callback2(tick: int, snapshot: SimulationSnapshot) -> None:
            snapshots.append(snapshot)

        adapter.register(callback1)
        adapter.register(callback2)
        adapter.notify(tick=1)

        # Both received the same snapshot
        assert len(snapshots) == 2
        assert snapshots[0] is snapshots[1]
        # get_snapshot called only once
        assert mock_sim.get_snapshot.call_count == 1


class TestAdapterNotifyExceptionHandling:
    """T015: adapter.notify() catches callback exceptions and logs them."""

    def test_notify_catches_callback_exception(self) -> None:
        """Callback exception does not propagate to caller."""
        mock_sim = MagicMock()
        mock_sim.get_snapshot.return_value = MagicMock()

        adapter = ProtocolObserverAdapter(mock_sim)

        def bad_callback(tick: int, snapshot: SimulationSnapshot) -> None:
            raise RuntimeError("Callback failed!")

        adapter.register(bad_callback)

        # Should NOT raise
        adapter.notify(tick=1)

    def test_notify_logs_callback_exception(self, caplog: pytest.LogCaptureFixture) -> None:
        """Callback exception is logged as warning."""
        mock_sim = MagicMock()
        mock_sim.get_snapshot.return_value = MagicMock()

        adapter = ProtocolObserverAdapter(mock_sim)

        def bad_callback(tick: int, snapshot: SimulationSnapshot) -> None:
            raise RuntimeError("Oops!")

        adapter.register(bad_callback)

        with caplog.at_level(logging.WARNING):
            adapter.notify(tick=1)

        assert "Observer callback failed" in caplog.text
        assert "Oops!" in caplog.text

    def test_notify_continues_after_exception(self) -> None:
        """Exception in one callback does not prevent other callbacks."""
        mock_sim = MagicMock()
        mock_sim.get_snapshot.return_value = MagicMock()

        adapter = ProtocolObserverAdapter(mock_sim)

        results: list[str] = []

        def callback1(tick: int, snapshot: SimulationSnapshot) -> None:
            results.append("callback1")

        def bad_callback(tick: int, snapshot: SimulationSnapshot) -> None:
            raise RuntimeError("Fail!")

        def callback2(tick: int, snapshot: SimulationSnapshot) -> None:
            results.append("callback2")

        adapter.register(callback1)
        adapter.register(bad_callback)
        adapter.register(callback2)

        adapter.notify(tick=1)

        # Both good callbacks were invoked
        assert results == ["callback1", "callback2"]
