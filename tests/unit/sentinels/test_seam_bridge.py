"""Efficacy proofs for the seam bridge-serialization sweep (Sensor 3).

Each test injects a tiny fixture wiring — a ``urls.py`` route, an ``api.py``
view, an ``engine_bridge.py`` serializer, a ``endpoints.ts`` manifest row, and a
``types/*.ts`` interface — and asserts that :func:`check_bridge_serialization`
discovers the pairing from that wiring alone (no hand table) and reds on a real
defect: a planted phantom field, an unrouted serializer, an ``Untyped`` contract,
a list/absent return, or a dead endpoint. The TDD red phase for the autonomous
whole-wire emission gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.seam.bridge import check_bridge_serialization

pytestmark = pytest.mark.unit


def _write_wiring(
    root: Path,
    *,
    urls: str,
    api: str,
    engine: str,
    endpoints: str,
    game_ts: str,
) -> dict[str, Path]:
    """Materialise a minimal engine->bridge->frontend wiring under ``root``.

    :returns: The keyword paths to pass straight into
        :func:`check_bridge_serialization`.
    """
    types_dir = root / "types"
    types_dir.mkdir(parents=True, exist_ok=True)
    urls_path = root / "urls.py"
    api_path = root / "api.py"
    engine_path = root / "engine_bridge.py"
    endpoints_path = root / "endpoints.ts"
    urls_path.write_text(urls, encoding="utf-8")
    api_path.write_text(api, encoding="utf-8")
    engine_path.write_text(engine, encoding="utf-8")
    endpoints_path.write_text(endpoints, encoding="utf-8")
    (types_dir / "game.ts").write_text(game_ts, encoding="utf-8")
    return {
        "urls_path": urls_path,
        "api_path": api_path,
        "engine_path": engine_path,
        "endpoints_path": endpoints_path,
        "ts_dir": types_dir,
    }


#: A route -> view -> ``get_economy`` -> ``EconomyDashboardPayload`` wiring whose
#: serializer emits exactly the interface's fields (the honest baseline).
_URLS = 'urlpatterns = [path("games/<str:game_id>/economy/", api.game_economy)]\n'
_API = "def game_economy(request, game_id):\n    return bridge.get_economy(session)\n"
_ENGINE = "class EngineBridge:\n    def get_economy(self, s):\n        return {'a': 1, 'b': 2}\n"
_ENDPOINTS = 'export const endpoints = {\n  economy: ep<EconomyDashboardPayload>("/api/games/:id/economy/"),\n} as const;\n'
_GAME_TS = "export interface EconomyDashboardPayload {\n  a: number;\n  b: number;\n}\n"


def test_derives_pair_and_is_clean_when_honest(tmp_path: Path) -> None:
    """A serializer emitting exactly its interface's fields yields no finding."""
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=_ENGINE, endpoints=_ENDPOINTS, game_ts=_GAME_TS
    )
    assert check_bridge_serialization(**paths) == []


def test_reds_on_planted_phantom(tmp_path: Path) -> None:
    """A declared field the serializer never emits is reported by name (red phase)."""
    game_ts = "export interface EconomyDashboardPayload {\n  a: number;\n  b: number;\n  ghost: number;\n}\n"
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=_ENGINE, endpoints=_ENDPOINTS, game_ts=game_ts
    )
    findings = check_bridge_serialization(**paths)
    assert len(findings) == 1
    assert "'ghost'" in findings[0]
    assert "get_economy" in findings[0]


def test_unrouted_serializer_is_loud(tmp_path: Path) -> None:
    """A serializer reaching the wire with no manifest entry is a loud blind spot."""
    empty_manifest = "export const endpoints = {\n} as const;\n"
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=_ENGINE, endpoints=empty_manifest, game_ts=_GAME_TS
    )
    findings = check_bridge_serialization(**paths)
    assert any("unrouted to a typed UI contract" in f for f in findings)


def test_untyped_endpoint_is_loud(tmp_path: Path) -> None:
    """An ``ep<Untyped>`` row is surfaced as a punch-list item, not skipped."""
    untyped = 'export const endpoints = {\n  economy: ep<Untyped>("/api/games/:id/economy/"),\n} as const;\n'
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=_ENGINE, endpoints=untyped, game_ts=_GAME_TS
    )
    findings = check_bridge_serialization(**paths)
    assert any("no field-checkable interface yet" in f for f in findings)


def test_list_return_is_blind_spot(tmp_path: Path) -> None:
    """A serializer returning a list has no top-level dict shape — reported, not diffed."""
    engine = "class EngineBridge:\n    def get_economy(self, s):\n        return [{'a': 1}]\n"
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
    )
    findings = check_bridge_serialization(**paths)
    assert any("returns a list shape" in f for f in findings)


def test_absent_serializer_is_blind_spot_not_error(tmp_path: Path) -> None:
    """A view calling a serializer the bridge lacks is a finding, never an abort."""
    engine = "class EngineBridge:\n    def get_something_else(self, s):\n        return {'a': 1}\n"
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
    )
    findings = check_bridge_serialization(**paths)
    assert any("defines no such serializer" in f for f in findings)


def test_dead_endpoint_reverse_direction(tmp_path: Path) -> None:
    """A manifest path with no backend route is reported (drift the other way)."""
    manifest = (
        "export const endpoints = {\n"
        '  economy: ep<EconomyDashboardPayload>("/api/games/:id/economy/"),\n'
        '  ghostEndpoint: ep<EconomyDashboardPayload>("/api/games/:id/ghost/"),\n'
        "} as const;\n"
    )
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=_ENGINE, endpoints=manifest, game_ts=_GAME_TS
    )
    findings = check_bridge_serialization(**paths)
    assert any("no backend route serves this path" in f and "ghost" in f for f in findings)


def test_doc_comment_example_is_not_parsed_as_endpoint(tmp_path: Path) -> None:
    """An ``ep<...>("...")`` example inside a comment must not leak in as a route."""
    manifest = (
        "/**\n"
        ' * Example in a doc comment: ep<Phantom>("/api/games/:id/commented/").\n'
        " */\n"
        "export const endpoints = {\n"
        '  economy: ep<EconomyDashboardPayload>("/api/games/:id/economy/"),\n'
        "} as const;\n"
    )
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=_ENGINE, endpoints=manifest, game_ts=_GAME_TS
    )
    findings = check_bridge_serialization(**paths)
    assert not any("commented" in f or "Phantom" in f for f in findings)


def test_non_get_serializer_is_discovered_and_checked(tmp_path: Path) -> None:
    """A view whose only bridge call is not ``get_``-prefixed is still a seam.

    The ``actions/preview`` shape: ``bridge.preview_economy(...)`` IS the wire
    payload, so a declared-but-unemitted field must red exactly like a ``get_*``
    serializer's phantom — never vanish in a silent skip.
    """
    api = "def game_economy(request, game_id):\n    return bridge.preview_economy(session)\n"
    engine = (
        "class EngineBridge:\n    def preview_economy(self, s):\n        return {'a': 1, 'b': 2}\n"
    )
    game_ts = (
        "export interface EconomyDashboardPayload {\n  a: number;\n  b: number;\n"
        "  ghost: number;\n}\n"
    )
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=api, engine=engine, endpoints=_ENDPOINTS, game_ts=game_ts
    )
    findings = check_bridge_serialization(**paths)
    assert len(findings) == 1
    assert "'ghost'" in findings[0]
    assert "preview_economy" in findings[0]


def test_typed_endpoint_with_no_bridge_call_is_loud(tmp_path: Path) -> None:
    """A typed manifest row whose view never touches the bridge is a blind spot.

    The manifest promises a field-checkable shape, but there is no serializer to
    check it against — that unverifiability must be reported, not skipped.
    """
    api = "def game_economy(request, game_id):\n    return _envelope(rows_from_db(game_id))\n"
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=api, engine=_ENGINE, endpoints=_ENDPOINTS, game_ts=_GAME_TS
    )
    findings = check_bridge_serialization(**paths)
    assert any("calls no bridge serializer" in f for f in findings)


def test_untyped_endpoint_with_no_bridge_call_stays_silent(tmp_path: Path) -> None:
    """No serializer AND no typed promise = not a serializer seam — the one
    declared silence (a POST resolver / DB listing with an ``Untyped`` row)."""
    api = "def game_economy(request, game_id):\n    return _envelope(rows_from_db(game_id))\n"
    untyped = 'export const endpoints = {\n  economy: ep<Untyped>("/api/games/:id/economy/"),\n} as const;\n'
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=api, engine=_ENGINE, endpoints=untyped, game_ts=_GAME_TS
    )
    assert check_bridge_serialization(**paths) == []


def test_missing_source_is_loud(tmp_path: Path) -> None:
    """A missing discovery source is an infrastructure failure, never a false clean."""
    paths = _write_wiring(
        tmp_path, urls=_URLS, api=_API, engine=_ENGINE, endpoints=_ENDPOINTS, game_ts=_GAME_TS
    )
    paths["urls_path"] = tmp_path / "does_not_exist.py"
    with pytest.raises(SentinelCheckError):
        check_bridge_serialization(**paths)


def test_live_tree_runs_without_raising() -> None:
    """The check runs against the real repo tree and returns a list (no exact count)."""
    findings = check_bridge_serialization()
    assert isinstance(findings, list)
    assert all(isinstance(f, str) for f in findings)


class TestSingleHopDelegationFollowed:
    """G4 Task C: the delegation-blindness class the audit found — a serializer
    whose ENTIRE body is ``return self.other_method(...)`` (the real
    ``get_economy`` -> ``get_economy_dashboard`` shape) used to report a
    "delegated" blind spot and harvest ZERO keys, so a declared-but-unemitted
    field on the DELEGATE could never be caught through this route. Fixed
    generically in ``_returned_dict_keys`` (single-hop ``self.<method>()``
    resolution) — not special-cased to ``get_economy`` by name."""

    def test_pure_delegation_resolves_the_delegates_keys(self, tmp_path: Path) -> None:
        """A serializer that ONLY delegates is checked against the delegate's
        real emitted keys, not reported as an unverifiable blind spot."""
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s):\n"
            "        return self.get_economy_dashboard(s)\n"
            "    def get_economy_dashboard(self, s):\n"
            "        return {'a': 1, 'b': 2}\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
        )
        assert check_bridge_serialization(**paths) == []

    def test_pure_delegation_still_catches_a_phantom_on_the_delegate(self, tmp_path: Path) -> None:
        """The whole point: a field the DELEGATE never emits must still red
        through the delegating serializer's route — this is the exact defect
        class ``rent_extracted``/``exploitation_rate`` risked going uncaught."""
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s):\n"
            "        return self.get_economy_dashboard(s)\n"
            "    def get_economy_dashboard(self, s):\n"
            "        return {'a': 1}\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
        )
        findings = check_bridge_serialization(**paths)
        assert len(findings) == 1
        assert "'b'" in findings[0]
        assert "get_economy" in findings[0]

    def test_mixed_literal_and_delegated_branches_union_both(self, tmp_path: Path) -> None:
        """``get_economy``'s REAL shape: one branch a literal dict (the
        per-territory case), one branch delegating to ``get_economy_
        dashboard`` (the no-``territory_id`` case) — both branches' keys are
        unioned, not just whichever return statement is scanned first."""
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s, territory_id=None):\n"
            "        if territory_id is None:\n"
            "            return self.get_economy_dashboard(s)\n"
            "        return {'a': 1}\n"
            "    def get_economy_dashboard(self, s):\n"
            "        return {'a': 1, 'b': 2}\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
        )
        assert check_bridge_serialization(**paths) == []

    def test_multi_hop_delegation_is_not_followed_past_one_hop(self, tmp_path: Path) -> None:
        """ "Single-hop" is a deliberate limit, not an oversight — a 2-hop chain
        (``get_economy`` -> ``_a`` -> ``_b``) still reports as a blind spot
        rather than silently resolving arbitrarily deep chains (and risking
        infinite recursion on an accidental cycle)."""
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s):\n"
            "        return self._a(s)\n"
            "    def _a(self, s):\n"
            "        return self._b(s)\n"
            "    def _b(self, s):\n"
            "        return {'a': 1, 'b': 2}\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
        )
        findings = check_bridge_serialization(**paths)
        assert any("delegated shape" in f for f in findings)

    def test_delegating_to_a_serializer_the_bridge_lacks_is_a_blind_spot(
        self, tmp_path: Path
    ) -> None:
        """Delegating to a nonexistent method degrades to the existing
        "absent" blind-spot report, never a crash."""
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s):\n"
            "        return self.get_economy_dashboard(s)\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
        )
        findings = check_bridge_serialization(**paths)
        assert any("returns a delegated shape" in f for f in findings)


class TestLocalVariablePayloadResolved:
    """G4 Task C companion fix: the "build a payload across statements, then
    return the variable" idiom (`payload = {...}; payload = gate_fn(payload,
    tier); payload['veil'] = {...}; return payload` — the EXACT shape G4's own
    veil-gating changes gave ``get_economy_dashboard``) must resolve the same
    way a literal ``return {...}`` does, not regress to a delegated blind spot
    just because the dict passes through a local variable and a masking call
    on its way out."""

    def test_return_of_a_locally_built_dict_resolves_its_keys(self, tmp_path: Path) -> None:
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s):\n"
            "        payload = {'a': 1, 'b': 2}\n"
            "        return payload\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
        )
        assert check_bridge_serialization(**paths) == []

    def test_subscript_assignment_after_the_literal_adds_its_key(self, tmp_path: Path) -> None:
        """``payload['veil'] = {...}`` after the initial literal must count
        ``veil`` among the emitted keys — the exact ``get_economy_dashboard``
        pattern (the ``veil`` sub-object is added after the gate call)."""
        game_ts = (
            "export interface EconomyDashboardPayload {\n"
            "  a: number;\n  b: number;\n  veil: number;\n}\n"
        )
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s):\n"
            "        payload = {'a': 1, 'b': 2}\n"
            "        payload = gate_value_axis_fields(payload, tier)\n"
            "        payload['veil'] = {}\n"
            "        return payload\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=game_ts
        )
        assert check_bridge_serialization(**paths) == []

    def test_still_catches_a_phantom_through_a_local_variable(self, tmp_path: Path) -> None:
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s):\n"
            "        payload = {'a': 1}\n"
            "        return payload\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
        )
        findings = check_bridge_serialization(**paths)
        assert len(findings) == 1
        assert "'b'" in findings[0]

    def test_variable_reassigned_from_an_unrelated_call_stays_a_blind_spot(
        self, tmp_path: Path
    ) -> None:
        """Only a same-variable masking reassignment (``x = f(x, ...)``) is
        trusted to preserve the key set — reassignment from an unrelated
        expression must NOT inherit the old (now possibly stale) key set."""
        engine = (
            "class EngineBridge:\n"
            "    def get_economy(self, s):\n"
            "        payload = {'a': 1, 'b': 2}\n"
            "        payload = build_something_else()\n"
            "        return payload\n"
        )
        paths = _write_wiring(
            tmp_path, urls=_URLS, api=_API, engine=engine, endpoints=_ENDPOINTS, game_ts=_GAME_TS
        )
        findings = check_bridge_serialization(**paths)
        assert any("delegated shape" in f for f in findings)
