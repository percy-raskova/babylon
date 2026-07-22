"""``babylon.cli.play.run()`` composition-root wiring (Program v1.0.0 Unit C3).

Pins the exact defect a review pass caught: :func:`~babylon.game.pacing.
paced_driver_for_session` shipped fully built and fully tested
(``tests/unit/game/test_pacing.py``, ``tests/unit/tui/test_app_pacing_driver.
py``) but :func:`~babylon.cli.play.run` — the ONLY production entry point
that constructs :class:`~babylon.tui.app.ArchiveApp` for a real ``babylon
play`` boot — never passed a ``driver_factory=`` in at all. Without this
wire, ``ArchiveApp.driver`` stays ``None`` on every real boot, so the
``t``/``r``/``a`` bindings never route through :class:`~babylon.game.pacing.
PacedTickDriver` and its permanent endgame lock never engages in the shipped
game — the exact "seam only the tests construct" failure mode.

``run()`` wires :func:`~babylon.cli.play._driver_factory` — a thin adapter,
not ``paced_driver_for_session`` passed straight through (mypy correctly
rejects that: ``paced_driver_for_session`` needs a full ``GameSession``,
strictly more than the ``CampaignHandle`` a ``DriverFactory`` promises; see
``_driver_factory``'s own docstring). This file pins both halves: ``run()``
wires the adapter in, and the adapter itself does the right thing with a
session-shaped object.

No Postgres, no Textual app loop: every collaborator :func:`~babylon.cli.
play.run` touches (``open_runtime``, ``ensure_schema``, ``BabylonMetaStore``,
``CampaignMenu``, ``ArchiveApp``) is faked at the module attribute
:func:`run` imports it from, mirroring how ``tests/unit/cli/test_app.py``
already fakes ``play_cmd.run`` one layer up.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import babylon.cli.play as play_cmd

pytestmark = pytest.mark.unit


class _FakeRuntime:
    """A ``PostgresRuntime`` double: ``run()`` only ever reads ``.pool``."""

    def __init__(self) -> None:
        self.pool = object()


class _FakeMetaStore:
    """A ``BabylonMetaStore`` double: records construction, no-ops schema."""

    def __init__(self, pool: object) -> None:
        self.pool = pool
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True


class _FakeCampaignMenu:
    """A ``CampaignMenu`` double: captures the kwargs ``run()`` built it with."""

    def __init__(self, catalog: object, *, engine_version: str, defines_hash: str) -> None:
        self.catalog = catalog
        self.engine_version = engine_version
        self.defines_hash = defines_hash


class _FakeArchiveApp:
    """An ``ArchiveApp`` double: captures every kwarg ``run()`` passed, and
    records the ``.run()`` call rather than starting a real Textual app."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.ran = False
        _captured.append(self)

    def run(self) -> None:
        self.ran = True


#: The single ``_FakeArchiveApp`` instance ``run()`` constructed, filled in
#: by :func:`_patched_composition_root` and cleared before every test.
_captured: list[_FakeArchiveApp] = []


@pytest.fixture
def _patched_composition_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake every collaborator ``babylon.cli.play.run()`` touches, at the
    exact module attribute its own local ``from ... import ...`` reads —
    ``run()`` re-imports these on every call, so patching the attribute is
    enough; no need to patch ``play_cmd`` itself."""
    _captured.clear()
    monkeypatch.setattr("babylon.game.session.open_runtime", lambda: _FakeRuntime())
    monkeypatch.setattr("babylon.game.session.ensure_schema", lambda _runtime: None)
    monkeypatch.setattr("babylon.persistence.babylon_meta.BabylonMetaStore", _FakeMetaStore)
    monkeypatch.setattr("babylon.tui.campaign_menu.CampaignMenu", _FakeCampaignMenu)
    monkeypatch.setattr("babylon.tui.app.ArchiveApp", _FakeArchiveApp)


def test_run_wires_the_driver_factory_adapter(_patched_composition_root: None) -> None:
    """The regression pin: ``ArchiveApp(...)`` in ``run()`` MUST receive
    ``driver_factory=play_cmd._driver_factory`` — the reviewer's finding was
    that NO ``driver_factory`` was ever passed at all, leaving
    ``ArchiveApp.driver`` permanently ``None`` in the shipped game."""
    play_cmd.run()

    assert len(_captured) == 1
    assert _captured[0].kwargs["driver_factory"] is play_cmd._driver_factory
    assert _captured[0].ran is True


def test_driver_factory_adapts_a_session_shaped_object_into_a_paced_driver() -> None:
    """``_driver_factory`` is the honest reason ``paced_driver_for_session``
    can't be wired in directly (mypy correctly rejects it — see the
    function's own docstring): this exercises what the adapter actually
    DOES with a session-shaped object, so the wiring pin above can never
    degrade into asserting an adapter that silently breaks the campaign
    it's handed."""
    from babylon.config.defines import GameDefines
    from babylon.game.pacing import PacedTickDriver

    session = SimpleNamespace(tick=3, services=SimpleNamespace(defines=GameDefines()))

    driver = play_cmd._driver_factory(session)  # type: ignore[arg-type]

    assert isinstance(driver, PacedTickDriver)
    assert driver.last_tick == 3


def test_run_still_wires_campaign_menu_and_loader(_patched_composition_root: None) -> None:
    """Unrelated to the driver-factory regression: confirms the pre-existing
    ``campaign_menu``/``campaign_loader`` wiring (Unit C2) survives
    alongside the new ``driver_factory=`` kwarg, so this file stands as the
    one place ``run()``'s full ``ArchiveApp`` call is pinned."""
    play_cmd.run()

    assert len(_captured) == 1
    kwargs = _captured[0].kwargs
    assert isinstance(kwargs["campaign_menu"], _FakeCampaignMenu)
    loader = kwargs["campaign_loader"]
    assert loader.func is play_cmd._load_campaign
    runtime, catalog = loader.args
    assert isinstance(runtime, _FakeRuntime)
    assert isinstance(catalog, _FakeMetaStore)
    assert catalog.pool is runtime.pool


def test_run_threads_narrator_enabled_default_true_into_the_loader(
    _patched_composition_root: None,
) -> None:
    """T5 Unit U1: ``run()`` with no argument threads ``narrator_enabled=True``
    (the sensible ON default, R4) into ``_load_campaign``'s partial — never
    silently dropped."""
    play_cmd.run()

    loader = _captured[0].kwargs["campaign_loader"]
    assert loader.keywords == {"narrator_enabled": True}


def test_run_threads_narrator_enabled_false_into_the_loader(
    _patched_composition_root: None,
) -> None:
    """``run(narrator_enabled=False)`` — the ``--no-narrator`` path — threads
    straight through, unweakened."""
    play_cmd.run(narrator_enabled=False)

    loader = _captured[0].kwargs["campaign_loader"]
    assert loader.keywords == {"narrator_enabled": False}
