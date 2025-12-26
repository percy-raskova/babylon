"""Async simulation runner for non-blocking UI integration.

This module provides AsyncSimulationRunner, which decouples the UI from the
simulation engine by running simulation steps in a background thread and
pushing WorldState snapshots to an async queue.

The runner enables:
- Non-blocking UI updates during simulation steps
- Continuous play mode without freezing the GUI
- Queue-based state consumption for flexible UI update strategies

Usage Example:
    >>> from babylon.engine.runner import AsyncSimulationRunner
    >>> from babylon.engine.simulation import Simulation
    >>>
    >>> runner = AsyncSimulationRunner(simulation, tick_interval=1.0)
    >>> await runner.start()  # Begin continuous simulation
    >>>
    >>> # UI can poll for states without blocking
    >>> state = await runner.get_state()
    >>> if state:
    ...     update_ui(state)
    >>>
    >>> await runner.stop()

See Also:
    - ``ai-docs/asyncio-patterns.yaml`` for async best practices
    - ``src/babylon/ui/main.py`` for UI integration patterns
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from babylon.models.world_state import WorldState

if TYPE_CHECKING:
    from babylon.engine.simulation import Simulation


class AsyncSimulationRunner:
    """Async runner that decouples UI from simulation engine.

    The runner wraps a Simulation instance and provides:

    1. **Non-blocking steps**: Uses ``asyncio.to_thread()`` to run
       ``simulation.step()`` without blocking the event loop.

    2. **State queue**: Pushes WorldState snapshots to an async queue
       for the UI to consume at its own pace.

    3. **Continuous play**: ``start()``/``stop()`` manage a background
       loop that steps the simulation at configurable intervals.

    4. **Queue overflow handling**: Drops oldest states when queue is full
       (MAX_QUEUE_SIZE=10) to prevent memory issues.

    Attributes:
        MAX_QUEUE_SIZE: Maximum states to buffer before dropping oldest.

    Example:
        >>> runner = AsyncSimulationRunner(sim, tick_interval=0.5)
        >>> state = await runner.step_once()  # Single step
        >>> print(f"Now at tick {state.tick}")

    Thread Safety:
        The runner uses an asyncio.Lock to serialize step_once() calls,
        ensuring simulation state consistency even with concurrent access.
    """

    MAX_QUEUE_SIZE: int = 10

    def __init__(
        self,
        simulation: Simulation,
        tick_interval: float = 1.0,
    ) -> None:
        """Initialize the async runner with a simulation.

        Args:
            simulation: The Simulation facade to run.
            tick_interval: Seconds between steps in continuous mode.
                           Must be positive.

        Raises:
            ValueError: If tick_interval is not positive.
        """
        if tick_interval <= 0:
            msg = "tick_interval must be positive"
            raise ValueError(msg)

        self._simulation = simulation
        self._tick_interval = tick_interval
        self._queue: asyncio.Queue[WorldState] = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._step_lock = asyncio.Lock()

    @property
    def simulation(self) -> Simulation:
        """Return the wrapped Simulation instance."""
        return self._simulation

    @property
    def tick_interval(self) -> float:
        """Return the interval between steps in continuous mode."""
        return self._tick_interval

    @tick_interval.setter
    def tick_interval(self, value: float) -> None:
        """Set the interval between steps.

        Args:
            value: New interval in seconds. Must be positive.

        Raises:
            ValueError: If value is not positive.
        """
        if value <= 0:
            msg = "tick_interval must be positive"
            raise ValueError(msg)
        self._tick_interval = value

    @property
    def is_running(self) -> bool:
        """Return True if continuous mode is active."""
        return self._running

    @property
    def queue(self) -> asyncio.Queue[WorldState]:
        """Return the state queue for direct access.

        Returns:
            The asyncio.Queue containing WorldState snapshots.
        """
        return self._queue

    async def start(self) -> None:
        """Start continuous simulation mode.

        Creates a background task that steps the simulation at
        ``tick_interval`` intervals. Idempotent - calling start()
        when already running is a no-op.

        The task reference is stored to prevent garbage collection.
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop continuous simulation mode.

        Cancels the background task and waits for it to finish.
        Idempotent - calling stop() when not running is a no-op.
        """
        if not self._running:
            return

        self._running = False

        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def step_once(self) -> WorldState:
        """Execute a single simulation step without blocking.

        Uses ``asyncio.to_thread()`` to run ``simulation.step()``
        in a thread pool, keeping the event loop responsive.

        The new state is pushed to the queue. If the queue is full,
        the oldest state is dropped to make room.

        Returns:
            The new WorldState after the step.

        Note:
            Uses an asyncio.Lock to serialize concurrent calls,
            ensuring simulation state consistency.
        """
        async with self._step_lock:
            new_state = await asyncio.to_thread(self._simulation.step)
            await self._put_state(new_state)
            return new_state

    async def get_state(self) -> WorldState | None:
        """Get a state from the queue without blocking.

        Returns:
            The next WorldState if available, None otherwise.
        """
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def get_state_blocking(
        self,
        timeout: float | None = None,
    ) -> WorldState:
        """Get a state from the queue, waiting if necessary.

        Args:
            timeout: Maximum seconds to wait. None means wait forever.

        Returns:
            The next WorldState from the queue.

        Raises:
            asyncio.TimeoutError: If timeout expires before a state is available.
        """
        if timeout is None:
            return await self._queue.get()
        return await asyncio.wait_for(self._queue.get(), timeout)

    async def drain_queue(self) -> list[WorldState]:
        """Remove and return all states from the queue.

        Returns:
            List of all WorldState objects that were in the queue,
            in order from oldest to newest. Empty list if queue was empty.
        """
        states: list[WorldState] = []
        while True:
            try:
                state = self._queue.get_nowait()
                states.append(state)
            except asyncio.QueueEmpty:
                break
        return states

    async def reset(self, new_simulation: Simulation) -> None:
        """Reset the runner with a new simulation.

        Stops the runner if running, drains the queue, and
        assigns the new simulation for future steps.

        Args:
            new_simulation: The new Simulation instance to use.
        """
        await self.stop()
        await self.drain_queue()
        self._simulation = new_simulation

    async def _run_loop(self) -> None:
        """Background loop for continuous mode.

        Steps the simulation and sleeps for tick_interval.
        Continues until _running becomes False or task is cancelled.
        """
        while self._running:
            await self.step_once()
            await asyncio.sleep(self._tick_interval)

    async def _put_state(self, state: WorldState) -> None:
        """Put a state on the queue, dropping oldest if full.

        This implements the overflow policy: when the queue is full,
        the oldest state is removed to make room for the new one.

        Args:
            state: The WorldState to add to the queue.
        """
        try:
            self._queue.put_nowait(state)
        except asyncio.QueueFull:
            # Drop oldest state to make room
            with contextlib.suppress(asyncio.QueueEmpty):
                self._queue.get_nowait()
            # Now there's room
            self._queue.put_nowait(state)
