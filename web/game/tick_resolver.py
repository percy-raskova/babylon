"""Tick resolver — thin orchestrator calling EngineBridge.

Provides a single entry point for resolving a tick from a view,
keeping view logic focused on HTTP concerns.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID


def resolve_game_tick(
    bridge: Any,
    session_id: UUID,
    persistent_context: dict[str, Any] | None = None,
    *,
    force_endgame_test_hook: bool = False,
) -> dict[str, Any]:
    """Resolve one tick for a game session via the engine bridge.

    Args:
        bridge: An EngineBridge instance (or StubEngineBridge for dev/test).
        session_id: The game session UUID.
        persistent_context: Optional cross-tick context.
        force_endgame_test_hook: G7-crisis test-only hook — see
            ``EngineBridge.resolve_tick``'s docstring. Defaults to False, so
            every existing caller is byte-identical.

    Returns:
        JSON-serializable snapshot dict of the new game state.
    """
    result: dict[str, Any] = cast(
        dict[str, Any],
        bridge.resolve_tick(
            session_id,
            persistent_context=persistent_context,
            force_endgame_test_hook=force_endgame_test_hook,
        ),
    )
    return result
