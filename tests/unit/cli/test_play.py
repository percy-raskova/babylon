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

    def load(self, _session_id: str) -> list[str]:
        """``WatchlistPersistence.load`` — the M3 pin-cache hydrates at
        :meth:`RustClientHost.bind_session` now (verify-panel R13a), so a
        catalog double must answer it like the real ``BabylonMetaStore``."""
        return []


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


def test_run_wires_the_same_catalog_as_watchlist_persistence(
    _patched_composition_root: None,
) -> None:
    """Program 24 P6: ``run()`` threads the SAME ``BabylonMetaStore`` catalog
    in as ``ArchiveApp``'s ``watchlist_persistence=`` — no second store, no
    second schema (``BabylonMetaStore.load``/``.save`` structurally satisfy
    ``WatchlistPersistence``, the same WO-37 trick the campaign-catalog wire
    above already uses)."""
    play_cmd.run()

    kwargs = _captured[0].kwargs
    campaign_menu_catalog = kwargs["campaign_menu"].catalog
    assert kwargs["watchlist_persistence"] is campaign_menu_catalog
    _runtime, loader_catalog = kwargs["campaign_loader"].args
    assert kwargs["watchlist_persistence"] is loader_catalog


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


def test_run_wires_tutorial_steps_and_a_callable_progress_factory(
    _patched_composition_root: None,
) -> None:
    """T6 Unit U4: ``run()`` always threads ``tutorial_steps=``/
    ``tutorial_progress_factory=`` into ``ArchiveApp(...)`` — the Wayne
    opening arc's own step slice (skipping the two pre-shell beats), and a
    callable seam factory."""
    from babylon.game.tutorial import WAYNE_OPENING_ARC

    play_cmd.run()

    kwargs = _captured[0].kwargs
    assert kwargs["tutorial_steps"] == WAYNE_OPENING_ARC.steps[2:]
    assert callable(kwargs["tutorial_progress_factory"])


class _FakeCampaignForFactory:
    """A minimal ``CampaignHandle``-shaped double — just ``tick``, all this
    factory's own gating heuristic reads."""

    def __init__(self, tick: int) -> None:
        self.tick = tick


class TestTutorialProgressFactoryGating:
    """Exercises :func:`babylon.cli.play._tutorial_progress_factory`'s own
    resolution logic directly (unit-tier, no ``ArchiveApp``/Textual needed).

    The 6th positional argument (``was_verb_issued``) is the M3 defect-fix
    widening (contract §0, the ``VerbIssued`` live-crash fix) — every call
    below threads a harmless always-``False`` stand-in unless the test is
    itself exercising it."""

    def test_explicit_true_shows_regardless_of_tick(self) -> None:
        factory = play_cmd._tutorial_progress_factory(True, steps=(object(),))
        result = factory(
            _FakeCampaignForFactory(tick=99),
            None,
            lambda: None,
            lambda: None,
            lambda _s: False,
            lambda _v: False,
        )
        assert result is not None

    def test_explicit_false_hides_regardless_of_tick(self) -> None:
        factory = play_cmd._tutorial_progress_factory(False, steps=(object(),))
        result = factory(
            _FakeCampaignForFactory(tick=0),
            None,
            lambda: None,
            lambda: None,
            lambda _s: False,
            lambda _v: False,
        )
        assert result is None

    def test_default_none_shows_for_a_fresh_campaign_at_tick_zero(self) -> None:
        factory = play_cmd._tutorial_progress_factory(None, steps=(object(),))
        result = factory(
            _FakeCampaignForFactory(tick=0),
            None,
            lambda: None,
            lambda: None,
            lambda _s: False,
            lambda _v: False,
        )
        assert result is not None

    def test_default_none_hides_for_a_campaign_already_past_tick_zero(self) -> None:
        factory = play_cmd._tutorial_progress_factory(None, steps=(object(),))
        result = factory(
            _FakeCampaignForFactory(tick=1),
            None,
            lambda: None,
            lambda: None,
            lambda _s: False,
            lambda _v: False,
        )
        assert result is None

    def test_shown_result_is_built_over_the_exact_steps_given(self) -> None:
        from babylon.game.tutorial_runtime import TutorialRuntimeProgress

        steps = tuple(range(3))  # placeholder objects, never dispatched in this test
        factory = play_cmd._tutorial_progress_factory(True, steps=steps)
        result = factory(
            _FakeCampaignForFactory(tick=0),
            None,
            lambda: None,
            lambda: None,
            lambda _s: False,
            lambda _v: False,
        )
        assert isinstance(result, TutorialRuntimeProgress)
        assert result._steps == steps  # noqa: SLF001 - white-box wiring check

    def test_was_verb_issued_threads_through_to_the_built_evaluator(self) -> None:
        """The M3 defect fix (contract §0): the SAME ``was_verb_issued``
        callable this factory is handed must reach the evaluator it builds
        — never dropped, never replaced with a harmless stand-in."""
        factory = play_cmd._tutorial_progress_factory(True, steps=(object(),))
        issued = {"aid"}
        result = factory(
            _FakeCampaignForFactory(tick=0),
            None,
            lambda: None,
            lambda: None,
            lambda _s: False,
            lambda verb: verb in issued,
        )
        assert result is not None
        assert result._was_verb_issued("aid") is True  # noqa: SLF001
        assert result._was_verb_issued("peek_wikilink") is False  # noqa: SLF001


def test_tutorial_steps_skips_the_two_pre_shell_beats() -> None:
    """:func:`babylon.cli.play._tutorial_steps` slices off ``boot_into_lobby``/
    ``begin_the_operation`` — both already necessarily true by the time the
    campaign shell (and the overlay) exist (module docstring)."""
    from babylon.game.tutorial import WAYNE_OPENING_ARC

    steps = play_cmd._tutorial_steps()

    assert steps == WAYNE_OPENING_ARC.steps[2:]
    assert steps[0].id == "read_the_county_dossier"
    ids = [step.id for step in steps]
    assert "boot_into_lobby" not in ids
    assert "begin_the_operation" not in ids


class TestClientRustLane:
    """M0 Task 7 (the raster cutover, ADR150): the ``--client rust`` branch.

    The lane is opt-in (``uv sync --group tui``): without the extension the
    branch must fail LOUDLY and actionably before touching Postgres; with it,
    ``run()`` composes a :class:`~babylon.tui.host.RustClientHost` over the
    real catalog and hands the terminal to ``babylon_tui.run`` — the exact
    seam ``ArchiveApp(...).run()`` occupies on the textual path.
    """

    def test_rust_without_extension_raises_actionable_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``sys.modules[name] = None`` makes ``import babylon_tui`` raise
        ImportError — the not-installed shape, even in a venv that HAS the
        opt-in group built."""
        import sys

        monkeypatch.setitem(sys.modules, "babylon_tui", None)
        with pytest.raises(RuntimeError, match="--group tui"):
            play_cmd.run(client=play_cmd.ClientKind.RUST)

    def test_rust_composes_host_and_hands_off_to_babylon_tui_run(
        self, monkeypatch: pytest.MonkeyPatch, _patched_composition_root: None
    ) -> None:
        import json
        import sys

        from babylon.tui.host import RustClientHost

        handoffs: list[tuple[object, str]] = []
        fake = SimpleNamespace(run=lambda host, config_json: handoffs.append((host, config_json)))
        monkeypatch.setitem(sys.modules, "babylon_tui", fake)

        play_cmd.run(client=play_cmd.ClientKind.RUST, narrator_enabled=False)

        assert len(handoffs) == 1
        host, config_json = handoffs[0]
        assert isinstance(host, RustClientHost)
        cfg = json.loads(config_json)
        assert cfg["render_tier"] == "glyph"
        assert cfg["headless"] is False
        assert cfg["narrator_enabled"] is False
        # DEFECT 1: the host handed to the Rust client must expose a real
        # campaign-loading seam — the M1 wiring closing the gap where
        # RustClientHost.bind_session had zero production caller.
        assert callable(host.load_campaign)
        # The textual app must never boot on the rust lane.
        assert _captured == []

    def test_rust_lane_takes_over_the_terminal_during_run(
        self, monkeypatch: pytest.MonkeyPatch, _patched_composition_root: None
    ) -> None:
        """Gate 3 blocker (2026-07-27): while ``babylon_tui.run`` owns the
        terminal, NOTHING Python-side may write to it — dulwich DEBUG
        records sprayed over the alternate screen on every vault touch,
        and the immediate-mode client only repaints on input, so one
        stray line wrecks the frame until the next keypress. The Textual
        App captured stdout/logging implicitly; the Rust lane must do it
        explicitly: console logging handlers detached and
        ``sys.stdout``/``sys.stderr`` redirected for exactly the run."""
        import logging
        import sys

        root = logging.getLogger()
        console = logging.StreamHandler(sys.stdout)
        root.addHandler(console)
        outer_stdout, outer_stderr = sys.stdout, sys.stderr
        seen: dict[str, object] = {}

        def fake_run(_host: object, _config_json: str) -> None:
            seen["console_detached"] = console not in logging.getLogger().handlers
            seen["stdout_redirected"] = sys.stdout is not outer_stdout
            seen["stderr_redirected"] = sys.stderr is not outer_stderr

        try:
            monkeypatch.setitem(sys.modules, "babylon_tui", SimpleNamespace(run=fake_run))
            play_cmd.run(client=play_cmd.ClientKind.RUST, narrator_enabled=False)
            assert seen == {
                "console_detached": True,
                "stdout_redirected": True,
                "stderr_redirected": True,
            }
            assert console in root.handlers, "console handler restored after the run"
            assert sys.stdout is outer_stdout and sys.stderr is outer_stderr
        finally:
            root.removeHandler(console)

    def test_rust_lane_restores_the_terminal_when_the_client_raises(
        self, monkeypatch: pytest.MonkeyPatch, _patched_composition_root: None
    ) -> None:
        """A panicking client (PanicException reaches this seam, the M1
        III.11 path) must still hand back a working console — handlers
        and streams restore on the raise path too."""
        import logging
        import sys

        root = logging.getLogger()
        console = logging.StreamHandler(sys.stdout)
        root.addHandler(console)
        outer_stdout = sys.stdout

        def raising_run(_host: object, _config_json: str) -> None:
            raise RuntimeError("client died mid-frame")

        try:
            monkeypatch.setitem(sys.modules, "babylon_tui", SimpleNamespace(run=raising_run))
            with pytest.raises(RuntimeError, match="client died mid-frame"):
                play_cmd.run(client=play_cmd.ClientKind.RUST, narrator_enabled=False)
            assert console in root.handlers
            assert sys.stdout is outer_stdout
        finally:
            root.removeHandler(console)

    def test_rust_host_load_campaign_binds_a_real_session(
        self, monkeypatch: pytest.MonkeyPatch, _patched_composition_root: None
    ) -> None:
        """DEFECT 1 (no production caller for ``bind_session``): the host
        ``run(client=rust)`` composes must carry a REAL ``campaign_loader`` —
        built exactly the way the textual path builds ``ArchiveApp``'s own
        ``campaign_loader=`` (a partial over :func:`play_cmd._load_campaign`).
        Fakes :func:`play_cmd._load_campaign` itself (the same seam the
        textual-path tests above pin by identity) to avoid touching
        Postgres/the engine, then drives the captured host's own
        ``load_campaign`` exactly as the Rust lobby would and confirms
        ``bind_session`` actually took effect — reads no longer serve
        absence."""
        import json
        import sys
        from uuid import UUID

        from babylon.config.defines import GameDefines
        from babylon.tui.host import RustClientHost

        handoffs: list[tuple[object, str]] = []
        fake = SimpleNamespace(run=lambda host, config_json: handoffs.append((host, config_json)))
        monkeypatch.setitem(sys.modules, "babylon_tui", fake)

        class _FakeSession:
            """A minimal session-shaped double: enough for ``_load_campaign``'s
            fake to return and for ``_driver_factory`` to wrap (it reads
            ``services.defines`` — see ``_driver_factory``'s own docstring)."""

            def __init__(self, campaign_id: UUID) -> None:
                self.session_id = campaign_id
                self.tick = 0
                self.services = SimpleNamespace(defines=GameDefines())
                self._pages = {"county/26163": "# Wayne County"}

            def read_page(self, subject: str) -> str | None:
                return self._pages.get(subject)

            def known_subjects(self) -> frozenset[str]:
                return frozenset(self._pages)

            def subject_view(self, _subject_id: str) -> None:
                return None

        def _fake_load_campaign(
            _runtime: object, _catalog: object, campaign_id: UUID, *, narrator_enabled: bool = True
        ) -> _FakeSession:
            return _FakeSession(campaign_id)

        monkeypatch.setattr(play_cmd, "_load_campaign", _fake_load_campaign)

        play_cmd.run(client=play_cmd.ClientKind.RUST)

        assert len(handoffs) == 1
        host, _config_json = handoffs[0]
        assert isinstance(host, RustClientHost)

        campaign_id = UUID("00000000-0000-0000-0000-000000000009")
        result = json.loads(host.load_campaign(str(campaign_id)))
        # M2: the ack carries the session tick (honest HUD counter on resume).
        # M3 §4: it also carries home_subject (babylon.tui.app._SAMPLE_SUBJECT,
        # ruling 3 "Wayne stays in lobby") — additive field order.
        assert result == {
            "ok": True,
            "campaign_id": str(campaign_id),
            "tick": 0,
            "home_subject": "county/26163",
        }
        # bind_session actually took effect: reads no longer serve absence.
        assert json.loads(host.read_page_json("county/26163")) == "# Wayne County"
        assert host.session is not None
        assert host.session.session_id == campaign_id

    def test_textual_default_still_boots_archive_app(self, _patched_composition_root: None) -> None:
        """The default lane is byte-identical to before: ArchiveApp boots."""
        play_cmd.run()

        assert len(_captured) == 1
        assert _captured[0].ran is True


class TestRustClientTutorialWiring:
    """M3 (the raster cutover, ADR150; contract §1's Constructor seam
    paragraph): ``_run_rust_client`` threads the SAME ``tutorial_steps=``/
    ``tutorial_progress_factory=`` seams the textual path builds for
    ``ArchiveApp`` — "the identical objects the Textual path gets" — into
    ``RustClientHost``, and the config's own ``tutorial_enabled`` follows
    the tri-state "possibly on" rule (``tutorial_enabled is not False``),
    not a plain ``bool()`` coercion (which would collapse ``None`` to
    ``False``, losing the tri-state entirely)."""

    def test_rust_client_threads_tutorial_steps_and_progress_factory(
        self, monkeypatch: pytest.MonkeyPatch, _patched_composition_root: None
    ) -> None:
        import sys

        from babylon.game.tutorial import WAYNE_OPENING_ARC
        from babylon.tui.host import RustClientHost

        handoffs: list[tuple[object, str]] = []
        fake = SimpleNamespace(run=lambda host, config_json: handoffs.append((host, config_json)))
        monkeypatch.setitem(sys.modules, "babylon_tui", fake)

        play_cmd.run(client=play_cmd.ClientKind.RUST)

        assert len(handoffs) == 1
        host, _config_json = handoffs[0]
        assert isinstance(host, RustClientHost)
        assert host._tutorial_steps == WAYNE_OPENING_ARC.steps[2:]  # noqa: SLF001
        assert callable(host._tutorial_progress_factory)  # noqa: SLF001

    def test_config_tutorial_enabled_is_the_flag_is_not_false_rule(
        self, monkeypatch: pytest.MonkeyPatch, _patched_composition_root: None
    ) -> None:
        import json
        import sys

        handoffs: list[tuple[object, str]] = []
        fake = SimpleNamespace(run=lambda host, config_json: handoffs.append((host, config_json)))
        monkeypatch.setitem(sys.modules, "babylon_tui", fake)

        play_cmd.run(client=play_cmd.ClientKind.RUST, tutorial_enabled=None)
        assert json.loads(handoffs[-1][1])["tutorial_enabled"] is True  # None is not False

        handoffs.clear()
        play_cmd.run(client=play_cmd.ClientKind.RUST, tutorial_enabled=True)
        assert json.loads(handoffs[-1][1])["tutorial_enabled"] is True

        handoffs.clear()
        play_cmd.run(client=play_cmd.ClientKind.RUST, tutorial_enabled=False)
        assert json.loads(handoffs[-1][1])["tutorial_enabled"] is False
