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
