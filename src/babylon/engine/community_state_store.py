"""Community state store protocol and default implementation (Feature 033).

Decouples bifurcation analysis from CommunitySystem internals via a
read-only protocol. The default in-memory implementation wraps the
existing mutable dict maintained by CommunitySystem.

See Also:
    :mod:`babylon.engine.systems.community`: CommunitySystem that owns state.
    ``specs/033-bifurcation-topology/research.md``: R1 architecture decision.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from babylon.models.entities.community import CommunityState
from babylon.models.enums import CommunityType


@runtime_checkable
class CommunityStateStore(Protocol):
    """Read interface for community consciousness data.

    Default implementation wraps the existing in-memory dict.
    Future PostgreSQL adapter implements the same protocol.
    """

    def get_all(self) -> dict[CommunityType, CommunityState]:
        """Return current community states snapshot."""
        ...


class InMemoryCommunityStateStore:
    """Default store wrapping the existing in-memory community_states dict.

    Args:
        states: Reference to the mutable community_states dict
            maintained by CommunitySystem. Not copied — reads reflect
            live mutations.
    """

    def __init__(
        self,
        states: dict[CommunityType, CommunityState],
    ) -> None:
        self._states = states

    def get_all(self) -> dict[CommunityType, CommunityState]:
        """Return current community states snapshot."""
        return dict(self._states)
