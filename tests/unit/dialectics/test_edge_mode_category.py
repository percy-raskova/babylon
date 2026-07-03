"""E3: edge modes as a presented category (§9.1 earn-its-keep target).

The 17 ``EdgeModeTransition``s plus the ANTAGONISTIC self-loop ARE the presented
category's generating morphisms. No new class — these are law tests over the
existing ``_TRANSITION_MAP`` / ``_VALID_TRANSITIONS`` as data.

Design-vs-code note (flagged for review): §9.1/E3 asserts "EXTRACTIVE ->
SOLIDARISTIC must transit TRANSACTIONAL" as *every such path transits
TRANSACTIONAL*. That universal does NOT hold against the shipped 17: the table
also carries ANTAGONISTIC -> SOLIDARISTIC (``shared_enemy_alliance``, the I.15
united front) and CO_OPTIVE -> SOLIDARISTIC (``co_optation_recognized``), so
EXTRACTIVE -> {ANTAGONISTIC, CO_OPTIVE} -> SOLIDARISTIC reach solidarity without
TRANSACTIONAL. The TRUE, faithful law tested here is: there is NO direct
EXTRACTIVE -> SOLIDARISTIC morphism, and the market de-escalation route DOES
transit TRANSACTIONAL. (Not faked as a false universal — §9.4 honesty clause.)
"""

from __future__ import annotations

from collections import deque

import pytest

from babylon.engine.systems.edge_transition._legacy import (
    _TRANSITION_MAP,
    _VALID_TRANSITIONS,
)
from babylon.models.enums import EdgeMode

pytestmark = pytest.mark.topology

_ALL_MODES = frozenset(EdgeMode)
_MAX_MODES = 5  # BFS node bound: there are exactly five edge modes.


def _successors(mode: EdgeMode) -> set[EdgeMode]:
    return {t.to_mode for t in _TRANSITION_MAP.get(mode, [])}


def _shortest_path(start: EdgeMode, goal: EdgeMode) -> list[EdgeMode] | None:
    """BFS over the transition graph (bounded by the five modes)."""
    queue: deque[list[EdgeMode]] = deque([[start]])
    seen: set[EdgeMode] = {start}
    for _ in range(_MAX_MODES + 1):  # static bound: no simple path exceeds 5 nodes
        if not queue:
            break
        path = queue.popleft()
        node = path[-1]
        if node == goal and len(path) > 1:
            return path
        for nxt in sorted(_successors(node), key=lambda m: m.value):
            if nxt not in seen or nxt == goal:
                seen.add(nxt)
                queue.append([*path, nxt])
    return None


class TestPresentedCategory:
    def test_no_direct_extractive_to_solidaristic(self) -> None:
        """The forbidden jump: no generating morphism EXTRACTIVE -> SOLIDARISTIC."""
        assert (EdgeMode.EXTRACTIVE, EdgeMode.SOLIDARISTIC) not in _VALID_TRANSITIONS

    def test_extractive_reaches_solidaristic_through_transactional(self) -> None:
        """A path exists, and the market de-escalation route transits TRANSACTIONAL.

        EXTRACTIVE -> TRANSACTIONAL -> SOLIDARISTIC are both generating morphisms,
        so solidarity IS reachable from extraction — never in one step.
        """
        assert _shortest_path(EdgeMode.EXTRACTIVE, EdgeMode.SOLIDARISTIC) is not None
        assert (EdgeMode.EXTRACTIVE, EdgeMode.TRANSACTIONAL) in _VALID_TRANSITIONS
        assert (EdgeMode.TRANSACTIONAL, EdgeMode.SOLIDARISTIC) in _VALID_TRANSITIONS

    def test_extractive_to_solidaristic_needs_an_intermediate(self) -> None:
        """The shortest EXTRACTIVE -> SOLIDARISTIC path has length >= 3 nodes."""
        path = _shortest_path(EdgeMode.EXTRACTIVE, EdgeMode.SOLIDARISTIC)
        assert path is not None
        assert len(path) >= 3  # start + >=1 intermediate + goal

    def test_all_transition_endpoints_are_edge_modes(self) -> None:
        """Closure of the presentation: every arc's endpoints are objects."""
        for src, dst in _VALID_TRANSITIONS:
            assert src in _ALL_MODES
            assert dst in _ALL_MODES

    def test_antagonistic_self_loop_is_present(self) -> None:
        """The ANTAGONISTIC self-loop (persistence) is a generating morphism."""
        assert (EdgeMode.ANTAGONISTIC, EdgeMode.ANTAGONISTIC) in _VALID_TRANSITIONS
