"""StubEngineBridge <-> EngineBridge parity guard (Constitution III.11).

``StubEngineBridge``'s class docstring claims "All methods match the
``EngineBridge`` interface so they can be used interchangeably" —
`web/game/stub_bridge.py`. This test makes that claim enforceable:

1. Every public ``get_*`` method on ``EngineBridge`` exists on
   ``StubEngineBridge`` (computed via inspection, never a hardcoded list, so
   future drift fails loudly with the missing names).
2. For every shared ``get_*`` name, the stub's signature is compatible —
   every REQUIRED real-bridge parameter is satisfiable on the stub. Extra
   optional stub parameters are fine; a required real parameter missing
   from the stub is not.
3. A smoke test: instantiate ``StubEngineBridge`` (no engine/DB needed) and
   call each of the 20 methods restored in this pass with minimal valid
   args, asserting no exception and a handful of key fields per the
   frontend's type contracts (``src/frontend/src/types/*.ts``).

Signature comparison normalizes a single leading underscore off parameter
names before comparing (``_session_id`` == ``session_id``): this file's own
established convention marks a stub parameter unused (never referenced in
the method body) with a leading underscore while the real bridge's
same-position parameter is genuinely read — see e.g.
``get_economy_dashboard(self, _session_id: UUID)`` vs. the real bridge's
``get_economy_dashboard(self, session_id: UUID)``. Treating that as a
divergence would fail dozens of pre-existing, working methods; the
convention is positional/semantic, not a real interface break.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _strip_leading_underscore(name: str) -> str:
    return name.lstrip("_")


def _public_get_methods(cls: type) -> set[str]:
    """Every public ``get_*`` method defined on ``cls`` (or inherited)."""
    return {
        name
        for name, _member in inspect.getmembers(cls, predicate=inspect.isfunction)
        if name.startswith("get_")
    }


def _stub_positional_params(sig: inspect.Signature) -> list[inspect.Parameter]:
    params = list(sig.parameters.values())[1:]  # drop `self`
    return [
        p
        for p in params
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]


def _stub_keyword_only_names(sig: inspect.Signature) -> set[str]:
    params = list(sig.parameters.values())[1:]  # drop `self`
    return {
        _strip_leading_underscore(p.name)
        for p in params
        if p.kind == inspect.Parameter.KEYWORD_ONLY
    }


def _signature_mismatches(real_cls: type, stub_cls: type, names: Iterable[str]) -> list[str]:
    """Return a human-readable mismatch message per incompatible signature."""
    mismatches: list[str] = []
    for name in sorted(names):
        real_sig = inspect.signature(getattr(real_cls, name))
        stub_sig = inspect.signature(getattr(stub_cls, name))
        stub_positional = _stub_positional_params(stub_sig)
        stub_kw_only = _stub_keyword_only_names(stub_sig)

        pos_index = 0
        for real_param in list(real_sig.parameters.values())[1:]:
            if real_param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            required = real_param.default is inspect.Parameter.empty
            if real_param.kind == inspect.Parameter.KEYWORD_ONLY:
                if required and _strip_leading_underscore(real_param.name) not in stub_kw_only:
                    mismatches.append(
                        f"{name}: real requires keyword-only {real_param.name!r}, "
                        f"stub has no matching keyword-only param"
                    )
                continue
            # POSITIONAL_ONLY / POSITIONAL_OR_KEYWORD: must line up by position.
            if required:
                if pos_index >= len(stub_positional):
                    mismatches.append(
                        f"{name}: real requires positional param #{pos_index} "
                        f"{real_param.name!r}, stub has too few positional params"
                    )
                else:
                    stub_param = stub_positional[pos_index]
                    if _strip_leading_underscore(stub_param.name) != _strip_leading_underscore(
                        real_param.name
                    ):
                        mismatches.append(
                            f"{name}: position #{pos_index} name mismatch — "
                            f"real={real_param.name!r} stub={stub_param.name!r}"
                        )
            pos_index += 1
    return mismatches


# --------------------------------------------------------------------- #
# Test 1: method existence
# --------------------------------------------------------------------- #


def test_every_engine_bridge_get_method_exists_on_stub() -> None:
    from game.engine_bridge import EngineBridge
    from game.stub_bridge import StubEngineBridge

    real_methods = _public_get_methods(EngineBridge)
    stub_methods = _public_get_methods(StubEngineBridge)

    missing = sorted(real_methods - stub_methods)
    assert not missing, f"StubEngineBridge is missing get_* methods: {missing}"


# --------------------------------------------------------------------- #
# Test 2: signature compatibility for every shared get_* method
# --------------------------------------------------------------------- #


def test_shared_get_method_signatures_are_compatible() -> None:
    from game.engine_bridge import EngineBridge
    from game.stub_bridge import StubEngineBridge

    shared = _public_get_methods(EngineBridge) & _public_get_methods(StubEngineBridge)
    mismatches = _signature_mismatches(EngineBridge, StubEngineBridge, shared)

    assert not mismatches, "Incompatible StubEngineBridge signatures:\n" + "\n".join(mismatches)


# --------------------------------------------------------------------- #
# Test 3: smoke test — the 20 methods restored in this pass
# --------------------------------------------------------------------- #

_ORG_ID = "ORG001"
_COUNTY_FIPS = "26163"
_NODE_ID = "C001"
_EDGE_ID = "C001->C004"


def _stub_session() -> Any:
    from game.stub_bridge import StubEngineBridge

    bridge = StubEngineBridge()
    session_id = bridge.create_game(scenario="wayne_county")
    return bridge, session_id


class TestSmokeTheTwentyRestoredMethods:
    def test_get_aid_targets(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_aid_targets(session_id, _ORG_ID)
        assert result["status"] == "ok"
        assert result["verb"] == "aid"
        assert isinstance(result["population_targets"], list)

    def test_get_attack_targets(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_attack_targets(session_id, _ORG_ID)
        assert result["status"] == "ok"
        assert result["verb"] == "attack"
        assert isinstance(result["targets"], dict)
        assert "organizations" in result["targets"]

    def test_get_class_history(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_class_history(session_id, _NODE_ID)
        assert result["class_id"] == _NODE_ID
        assert result["history"] == []
        assert result["ruptures"] == []

    def test_get_contradiction_snapshot(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_contradiction_snapshot(session_id)
        assert isinstance(result["tick"], int)
        assert result["regime"] == "reproduction"
        assert result["oppositions"] == []

    def test_get_economy(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_economy(session_id, territory_id="T001")
        assert result["territory_id"] == "T001"
        assert result["has_data"] is False

    def test_get_economy_no_territory_delegates_to_dashboard(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_economy(session_id)
        assert result == bridge.get_economy_dashboard(session_id)

    def test_get_edge_history(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_edge_history(session_id, _EDGE_ID)
        assert result["edge_id"] == _EDGE_ID
        assert result["history"] == []

    def test_get_educate_targets(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_educate_targets(session_id, _ORG_ID)
        assert result["status"] == "ok"
        assert result["verb"] == "educate"
        assert len(result["targets"]) >= 1

    def test_get_endgame_state(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_endgame_state(session_id)
        assert result["outcome"] is None
        assert "final_tick" in result["stats"]

    def test_get_infrastructure(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_infrastructure(session_id)
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_get_investigate_targets(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_investigate_targets(session_id, _ORG_ID)
        assert result["status"] == "ok"
        assert result["verb"] == "investigate"
        assert "territory_scans" in result["targets"]

    def test_get_journal_objectives(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_journal_objectives(session_id)
        assert len(result["objectives"]) == 5
        assert all(obj["status"] == "active" for obj in result["objectives"])

    def test_get_mobilize_targets(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_mobilize_targets(session_id, _ORG_ID)
        assert result["entity_id"] == _ORG_ID
        assert result["targets"] == []

    def test_get_move_targets(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_move_targets(session_id, _ORG_ID)
        assert result["status"] == "ok"
        assert result["verb"] == "move"

    def test_get_negotiate_targets(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_negotiate_targets(session_id, _ORG_ID)
        assert result["status"] == "ok"
        assert result["verb"] == "negotiate"

    def test_get_org_history(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_org_history(session_id, _ORG_ID)
        assert result["org_id"] == _ORG_ID
        assert result["history"] == []

    def test_get_org_status(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_org_status(session_id, _ORG_ID)
        assert result["id"] == _ORG_ID
        assert "resources" in result

    def test_get_org_status_unknown_org_is_honest_empty(self) -> None:
        bridge, session_id = _stub_session()
        assert bridge.get_org_status(session_id, "NOT-AN-ORG") == {}

    def test_get_pending_actions(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_pending_actions(session_id, 0)
        assert result == []

    def test_get_reproduce_targets(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_reproduce_targets(session_id, _ORG_ID)
        assert result["status"] == "ok"
        assert result["verb"] == "reproduce"

    def test_get_territory_history(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_territory_history(session_id, _COUNTY_FIPS)
        assert result["county_fips"] == _COUNTY_FIPS
        assert result["history"] == []

    def test_get_wire_feed(self) -> None:
        bridge, session_id = _stub_session()
        result = bridge.get_wire_feed(session_id)
        assert "meta" in result
        assert "index" in result
        assert "story" in result
