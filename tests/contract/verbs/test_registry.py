"""Contract: the verb resolver registry (verb-dispatch engine).

Hard imports — a missing resolver is a COLLECTION FAILURE, not a skip. Pins:

* all 9 canonical ActionTypes are registered and callable;
* an unregistered ActionType resolves to a LOUD failure (never raises, never
  silent-succeeds);
* the web bridge's ``VERB_TO_ACTION_TYPE`` maps exactly onto the registry keys
  (keeps map and registry from drifting apart).
"""

from __future__ import annotations

import pytest
from web.game.engine_bridge import VERB_TO_ACTION_TYPE

from babylon.engine.actions import VERB_RESOLVERS, resolve_player_action
from babylon.engine.services import ServiceContainer
from babylon.models.enums import ActionType
from babylon.ooda.types import Action

pytestmark = pytest.mark.contract

_CANONICAL_ACTION_TYPES = {
    ActionType.EDUCATE,
    ActionType.RECRUIT,
    ActionType.ATTACK_INFRASTRUCTURE,
    ActionType.PROTEST,
    ActionType.PROPAGANDIZE,
    ActionType.PROVIDE_SERVICE,
    ActionType.MAP_NETWORK,
    ActionType.MOVE,
    ActionType.PROPOSE_ALLIANCE,
}


class TestRegistryShape:
    """The registry contains exactly the 9 canonical resolvers, all callable."""

    def test_has_nine_resolvers(self) -> None:
        assert len(VERB_RESOLVERS) == 9

    def test_all_canonical_action_types_registered(self) -> None:
        assert set(VERB_RESOLVERS.keys()) == _CANONICAL_ACTION_TYPES

    @pytest.mark.parametrize("action_type", sorted(_CANONICAL_ACTION_TYPES, key=lambda a: a.value))
    def test_resolver_is_callable(self, action_type: ActionType) -> None:
        assert callable(VERB_RESOLVERS[action_type])


class TestLoudFailure:
    """A missing resolver returns success=False with a reason — never silent."""

    def test_unregistered_action_type_fails_loud(self, verb_graph, services) -> None:
        action = Action(org_id="ORGP", action_type=ActionType.FUNDRAISE, target_id="C001")
        result = resolve_player_action(action, {}, verb_graph, services)
        assert result.success is False
        assert result.failure_reason is not None
        assert "fundraise" in result.failure_reason

    def test_unregistered_never_raises(self) -> None:
        # No graph/services access happens on the missing-resolver branch.
        action = Action(org_id="o", action_type=ActionType.DENOUNCE, target_id="t")
        result = resolve_player_action(action, {}, None, ServiceContainer.create())  # type: ignore[arg-type]
        assert result.success is False


class TestBridgeParity:
    """The web verb map and the engine registry must not drift apart."""

    def test_bridge_map_values_equal_registry_keys(self) -> None:
        assert set(VERB_TO_ACTION_TYPE.values()) == set(VERB_RESOLVERS.keys())

    def test_bridge_map_has_nine_verbs(self) -> None:
        assert len(VERB_TO_ACTION_TYPE) == 9
