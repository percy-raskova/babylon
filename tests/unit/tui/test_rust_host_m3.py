"""Contract for the M3 "Tutorial gate" ``RustClientHost`` surface (Tasks
27-29, ADR150): ``tutorial_state_json``/``new_campaign`` (call1/call0), and
``load_campaign``'s ack gaining ``home_subject``.

Companion to ``test_host_contract.py`` (M0/M1) and ``test_rust_host_m2.py``
(M2 "Playable"): pinned against
``docs/superpowers/specs/2026-07-27-m3-tutorial-contracts.md`` §1/§2/§4/§7.
Unit tier only (no Postgres, no Textual, no real engine): every synthetic
:class:`~babylon.game.tutorial.TutorialStep` below is built LOCALLY, one per
closed :data:`~babylon.game.tutorial.CompletionPredicate` kind (never the
real 24-step ``WAYNE_OPENING_ARC`` — that authored script is pinned
separately, in ``tests/unit/game/test_tutorial.py`` and
``tests/unit/game/test_tutorial_runtime.py``), so each predicate's own
gating is exercised in isolation. ``_FakeSession``/``_FakeDriver`` mirror
``test_rust_host_m2.py``'s own ``_FakeSession``/``_FakeDriver`` convention —
only the members the M3 surface actually calls.

**A recorded assumption (no sibling implementation exists yet at write
time, per this file's own charter — these tests are RED-phase, written to
the contract):** the host's own multi-advance accumulator is exposed as a
PUBLIC ``host.completion_log`` attribute — a tuple of ``(step_id,
poll_ordinal)`` pairs — mirroring the contract's own literal naming ("the
host adapter keeps a ``completion_log`` of ``(step_id, poll_ordinal)``",
§5) applied to ``RustClientHost`` itself (the harness's own composition
paragraph constructs ``RustClientHost`` directly with no separate wrapper,
so the host IS "the host adapter" the contract names). If the real
implementation names or scopes this differently, that is a contract
deviation to reconcile at integration, not a defect in this pin.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

import pytest

from babylon.game.tutorial import (
    EventAcked,
    OnPage,
    PaneShowing,
    PausePending,
    PinnedInWatchlist,
    TickAtLeast,
    TutorialStep,
    VerbIssued,
)
from babylon.game.tutorial_runtime import TutorialRuntimeProgress
from babylon.projection.briefing import operation_codename
from babylon.tui.campaign_menu import InMemoryCampaignCatalog
from babylon.tui.host import RustClientHost
from babylon.tui.watchlist import InMemoryWatchlistPersistence

pytestmark = [pytest.mark.unit]

_DEFINES_HASH = "f00dface" * 8
_ENGINE_VERSION = "7.7.7"
_SESSION_ID = UUID("00000000-0000-0000-0000-0000000000f3")

#: The live campaign's own home dossier subject (``babylon.tui.app.
#: _SAMPLE_SUBJECT`` — ruling 3, "Wayne stays in lobby"). Hardcoded rather
#: than imported: no existing test module imports that private constant
#: directly (grep-verified), and the contract itself pins the literal
#: string.
_HOME_SUBJECT = "county/26163"


# --------------------------------------------------------------------------- #
# Fakes.                                                                       #
# --------------------------------------------------------------------------- #


@dataclass
class _FakeDriver:
    """A minimal ``PacedDriverHandle`` double — only ``awaiting_ack``
    matters to the tutorial evaluator's ``PausePending``/``EventAcked``."""

    awaiting_ack: bool = False


class _FakeSession:
    """A minimal ``CampaignHandle`` double covering only what M3's tutorial
    machinery + ``issue_verb``/``load_campaign`` touch (mirrors
    ``test_rust_host_m2.py``'s own ``_FakeSession`` convention: only the
    members actually exercised)."""

    def __init__(self, *, session_id: UUID = _SESSION_ID, tick: int = 0) -> None:
        self.session_id = session_id
        self.tick = tick
        self.issue_verb_calls: list[tuple[str, str | None, str | None]] = []

    def read_page(self, subject: str) -> str | None:
        return None

    def known_subjects(self) -> frozenset[str]:
        return frozenset()

    def subject_view(self, subject_id: str) -> None:
        return None

    def issue_verb(
        self,
        action_id: str,
        *,
        target_id: str | None = None,
        target_community: str | None = None,
    ) -> int:
        self.issue_verb_calls.append((action_id, target_id, target_community))
        return 1


def _always_on_factory(steps: Sequence[TutorialStep]) -> Callable[..., TutorialRuntimeProgress]:
    """A ``tutorial_progress_factory`` double that ALWAYS arms — the M3
    equivalent of ``cli.play._tutorial_progress_factory(True, steps)``
    (the tri-state ``True`` branch), built locally so this module never
    needs to import the composition root."""

    def _factory(
        campaign: object,
        driver: object,
        current_subject: Callable[[], str | None],
        current_pane: Callable[[], str | None],
        is_pinned: Callable[[str], bool],
        was_verb_issued: Callable[[str], bool],
    ) -> TutorialRuntimeProgress:
        return TutorialRuntimeProgress(
            steps=steps,
            campaign=campaign,  # type: ignore[arg-type]
            driver=driver,  # type: ignore[arg-type]
            current_subject=current_subject,
            current_pane=current_pane,
            is_pinned=is_pinned,
            was_verb_issued=was_verb_issued,
        )

    return _factory


def _armed_host(
    steps: Sequence[TutorialStep],
    *,
    session: _FakeSession | None = None,
    driver: _FakeDriver | None = None,
    watchlist_persistence: InMemoryWatchlistPersistence | None = None,
    factory: Callable[..., TutorialRuntimeProgress | None] | None = None,
) -> tuple[RustClientHost, _FakeSession, _FakeDriver]:
    """Build a ``RustClientHost`` with the M3 tutorial seam wired and a
    session already bound (arming the factory at bind time, per contract
    §1's "Arming happens at bind_session time")."""
    resolved_session = session if session is not None else _FakeSession()
    resolved_driver = driver if driver is not None else _FakeDriver()
    host = RustClientHost(
        InMemoryCampaignCatalog(),
        defines_hash=_DEFINES_HASH,
        engine_version=_ENGINE_VERSION,
        tutorial_steps=tuple(steps),
        tutorial_progress_factory=factory if factory is not None else _always_on_factory(steps),
        watchlist_persistence=watchlist_persistence,
    )
    host.bind_session(resolved_session, resolved_driver)  # type: ignore[arg-type]
    return host, resolved_session, resolved_driver


def _view(
    *, subject: str | None = None, pane: str = "wiki", chrome_verbs: Sequence[str] = ()
) -> str:
    """The Rust-built ``view_state_json`` argument (§1's pinned field order)."""
    return json.dumps({"subject": subject, "pane": pane, "chrome_verbs": list(chrome_verbs)})


def _tiny_steps() -> tuple[TutorialStep, ...]:
    """A single-step synthetic arc for isolated envelope/field-order pins."""
    return (
        TutorialStep(
            id="alpha",
            given="a fresh campaign shell",
            when="the player reads the county dossier",
            then="the wiki pane shows county/26163",
            anchor="page:county/26163",
            completion=OnPage(subject="county/26163"),
            patches="Patches says hello.",
        ),
    )


# --------------------------------------------------------------------------- #
# tutorial_state_json — inactive.                                             #
# --------------------------------------------------------------------------- #


class TestTutorialStateJsonInactive:
    def test_no_tutorial_wired_even_when_bound_is_inactive(self) -> None:
        host = RustClientHost(
            InMemoryCampaignCatalog(), defines_hash=_DEFINES_HASH, engine_version=_ENGINE_VERSION
        )
        host.bind_session(_FakeSession(), None)  # type: ignore[arg-type]
        assert json.loads(host.tutorial_state_json(_view())) == {"active": False}

    def test_unbound_host_with_tutorial_wired_is_inactive(self) -> None:
        steps = _tiny_steps()
        host = RustClientHost(
            InMemoryCampaignCatalog(),
            defines_hash=_DEFINES_HASH,
            engine_version=_ENGINE_VERSION,
            tutorial_steps=steps,
            tutorial_progress_factory=_always_on_factory(steps),
        )
        assert json.loads(host.tutorial_state_json(_view())) == {"active": False}

    def test_factory_returning_none_stays_inactive_forever(self) -> None:
        steps = _tiny_steps()

        def _off(*_args: object) -> None:
            return None

        host, _session, _driver = _armed_host(steps, factory=_off)
        assert json.loads(host.tutorial_state_json(_view())) == {"active": False}
        # Even with the subject/pane that would otherwise finish the arc.
        assert json.loads(host.tutorial_state_json(_view(subject="county/26163", pane="wiki"))) == {
            "active": False
        }


# --------------------------------------------------------------------------- #
# tutorial_state_json — the active/finished envelope, field order + strings.  #
# --------------------------------------------------------------------------- #


class TestTutorialStateJsonActiveEnvelope:
    def test_active_envelope_field_order_and_exact_strings(self) -> None:
        steps = _tiny_steps()
        host, _session, _driver = _armed_host(steps)

        raw = host.tutorial_state_json(_view(subject=None, pane="wiki"))
        payload = json.loads(raw)

        assert list(payload.keys()) == [
            "active",
            "finished",
            "step_index",
            "total",
            "step_id",
            "heading",
            "patches",
            "body",
        ]
        step = steps[0]
        assert payload == {
            "active": True,
            "finished": False,
            "step_index": 0,
            "total": 1,
            "step_id": "alpha",
            "heading": f"Step 1/1: {step.scenario_name}",
            "patches": step.patches,
            "body": step.overlay_text,
        }
        # Belt-and-suspenders: the RAW string's own key sequence too (the
        # contract's field order is load-bearing for Rust's serde parse).
        assert (
            raw.index('"active"')
            < raw.index('"finished"')
            < raw.index('"step_index"')
            < raw.index('"total"')
            < raw.index('"step_id"')
            < raw.index('"heading"')
            < raw.index('"patches"')
            < raw.index('"body"')
        )

    def test_finished_envelope_exact_strings(self) -> None:
        steps = _tiny_steps()
        host, _session, _driver = _armed_host(steps)

        payload = json.loads(host.tutorial_state_json(_view(subject="county/26163", pane="wiki")))

        assert payload == {
            "active": True,
            "finished": True,
            "step_index": 1,
            "total": 1,
            "step_id": None,
            "heading": "Opening arc complete.",
            "patches": None,
            "body": "Press Escape to dismiss this tutorial.",
        }


# --------------------------------------------------------------------------- #
# tutorial_state_json — one test class per closed predicate kind.             #
# --------------------------------------------------------------------------- #


class TestTutorialStateJsonPredicates:
    def test_on_page_requires_the_subject_and_the_wiki_pane(self) -> None:
        steps = (
            TutorialStep(
                id="on_page_step",
                given="g",
                when="w",
                then="t",
                anchor="page:county/26163",
                completion=OnPage(subject="county/26163"),
                patches="Patches watches the county.",
            ),
        )
        host, _session, _driver = _armed_host(steps)

        # Right subject, WRONG pane — not complete (the navigate-pane-couple
        # conjunct: subject match alone is not enough).
        payload = json.loads(host.tutorial_state_json(_view(subject="county/26163", pane="map")))
        assert payload["finished"] is False

        payload = json.loads(host.tutorial_state_json(_view(subject="county/26163", pane="wiki")))
        assert payload["finished"] is True

    def test_tick_at_least(self) -> None:
        steps = (
            TutorialStep(
                id="tick_step",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:t",
                completion=TickAtLeast(tick=5),
                patches="Patches counts the ticks.",
            ),
        )
        session = _FakeSession(tick=4)
        host, session, _driver = _armed_host(steps, session=session)

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        session.tick = 5
        assert json.loads(host.tutorial_state_json(_view()))["finished"] is True

    def test_pause_pending(self) -> None:
        steps = (
            TutorialStep(
                id="pause_step",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:r",
                completion=PausePending(),
                patches="Patches waits for the pause.",
            ),
        )
        driver = _FakeDriver(awaiting_ack=False)
        host, _session, driver = _armed_host(steps, driver=driver)

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        driver.awaiting_ack = True
        assert json.loads(host.tutorial_state_json(_view()))["finished"] is True

    def test_event_acked(self) -> None:
        steps = (
            TutorialStep(
                id="ack_step",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:a",
                completion=EventAcked(),
                patches="Patches nods once acknowledged.",
            ),
        )
        driver = _FakeDriver(awaiting_ack=True)
        host, _session, driver = _armed_host(steps, driver=driver)

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        driver.awaiting_ack = False
        assert json.loads(host.tutorial_state_json(_view()))["finished"] is True

    def test_pane_showing(self) -> None:
        steps = (
            TutorialStep(
                id="pane_step",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:2",
                completion=PaneShowing(pane="map"),
                patches="Patches points at the map pane.",
            ),
        )
        host, _session, _driver = _armed_host(steps)

        assert json.loads(host.tutorial_state_json(_view(pane="wiki")))["finished"] is False
        assert json.loads(host.tutorial_state_json(_view(pane="map")))["finished"] is True

    def test_pinned_in_watchlist(self) -> None:
        steps = (
            TutorialStep(
                id="pin_step",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:p",
                completion=PinnedInWatchlist(subject="social_class/C001"),
                patches="Patches celebrates the pin.",
            ),
        )
        persistence = InMemoryWatchlistPersistence()
        host, _session, _driver = _armed_host(steps, watchlist_persistence=persistence)

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        host.pin_watchlist(json.dumps({"subject": "social_class/C001", "pinned": True}))
        assert json.loads(host.tutorial_state_json(_view()))["finished"] is True

    def test_verb_issued_via_the_host_verb_log(self) -> None:
        steps = (
            TutorialStep(
                id="verb_step",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:f6",
                completion=VerbIssued(verb="aid"),
                patches="Patches cheers the first real act.",
            ),
        )
        host, session, _driver = _armed_host(steps)

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        host.issue_verb(json.dumps({"verb": "aid", "target_id": None, "target_community": None}))

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is True
        assert session.issue_verb_calls == [("aid", None, None)]

    def test_verb_issued_via_chrome_verbs(self) -> None:
        steps = (
            TutorialStep(
                id="peek_step",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:K",
                completion=VerbIssued(verb="peek_wikilink"),
                patches="Patches shrugs — no wikilinks yet, but the path works.",
            ),
        )
        host, _session, _driver = _armed_host(steps)

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        payload = json.loads(host.tutorial_state_json(_view(chrome_verbs=["peek_wikilink"])))
        assert payload["finished"] is True


# --------------------------------------------------------------------------- #
# R5-TEST: session-scoped evaluator read vs. host-lifetime dispatch-proof.    #
# --------------------------------------------------------------------------- #


class TestVerbLogSessionScopedVsLifetime:
    """R5 regression (the M3 defect fix, ``host.py``'s own
    ``_session_verb_log``/``verb_log`` split): a ``VerbIssued`` step's own
    completion must be scoped to the BOUND SESSION, never leak from a PRIOR
    campaign's dispatch — while the harness's own tier-2 dispatch-proof
    surface (:meth:`~babylon.tui.host.RustClientHost.was_verb_issued`) is a
    HOST-LIFETIME log that must never forget a verb once dispatched, even
    across a rebind. Both halves of the split are exercised by ONE re-bind
    below (the reachable second-campaign scenario only the Rust client's own
    lobby round trip can hit — Textual never returns to the lobby)."""

    def test_rebind_resets_the_evaluators_own_read_but_not_the_lifetime_surface(self) -> None:
        steps = (
            TutorialStep(
                id="verb_step",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:f6",
                completion=VerbIssued(verb="aid"),
                patches="Patches cheers the first real act.",
            ),
        )
        host, _session, driver = _armed_host(steps)

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        host.issue_verb(json.dumps({"verb": "aid", "target_id": None, "target_community": None}))
        assert json.loads(host.tutorial_state_json(_view()))["finished"] is True
        assert host.was_verb_issued("aid") is True

        # Re-bind a FRESH session — a second campaign.
        new_session = _FakeSession(session_id=UUID(int=99))
        host.bind_session(new_session, driver)  # type: ignore[arg-type]

        # The evaluator's own SESSION-scoped read (`_session_verb_log`) never
        # leaks the prior campaign's dispatch: the freshly (re)built
        # evaluator has not observed "aid" issued THIS session, so the same
        # VerbIssued('aid') step is honestly incomplete again.
        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        # The harness's own tier-2 dispatch-proof surface is a HOST-LIFETIME
        # log (`verb_log`) — it must never forget, even across the rebind
        # that just reset the evaluator's own session-scoped view.
        assert host.was_verb_issued("aid") is True


# --------------------------------------------------------------------------- #
# tutorial_state_json — multi-advance + completion_log.                       #
# --------------------------------------------------------------------------- #


class TestTutorialStateJsonMultiAdvance:
    def test_two_adjacent_identical_predicates_complete_in_one_poll(self) -> None:
        steps = (
            TutorialStep(
                id="dup_a",
                given="g",
                when="w",
                then="t",
                anchor="palette:economy/USA",
                completion=OnPage(subject="economy/USA"),
                patches="a",
            ),
            TutorialStep(
                id="dup_b",
                given="g",
                when="w",
                then="t",
                anchor="page:economy/USA",
                completion=OnPage(subject="economy/USA"),
                patches="b",
            ),
            TutorialStep(
                id="tail",
                given="g",
                when="w",
                then="t",
                anchor="binding:ArchiveApp:t",
                completion=TickAtLeast(tick=100),
                patches="c",
            ),
        )
        host, _session, _driver = _armed_host(steps)

        payload = json.loads(host.tutorial_state_json(_view(subject="economy/USA", pane="wiki")))

        assert payload["finished"] is False
        assert payload["step_index"] == 2
        assert payload["step_id"] == "tail"

        completed_ids = [step_id for step_id, _ordinal in host.completion_log]
        assert completed_ids == ["dup_a", "dup_b"]
        ordinals = {ordinal for _step_id, ordinal in host.completion_log}
        assert len(ordinals) == 1  # both completed in the SAME poll


class TestCompletionLog:
    def test_empty_before_any_poll(self) -> None:
        steps = (
            TutorialStep(
                id="s1",
                given="g",
                when="w",
                then="t",
                anchor="page:a",
                completion=OnPage(subject="a"),
                patches="x",
            ),
        )
        host, _session, _driver = _armed_host(steps)
        assert host.completion_log == []

    def test_records_every_completed_step_once_in_arc_order_across_separate_polls(self) -> None:
        steps = (
            TutorialStep(
                id="s1",
                given="g",
                when="w",
                then="t",
                anchor="page:a",
                completion=OnPage(subject="a"),
                patches="1",
            ),
            TutorialStep(
                id="s2",
                given="g",
                when="w",
                then="t",
                anchor="page:b",
                completion=OnPage(subject="b"),
                patches="2",
            ),
            TutorialStep(
                id="s3",
                given="g",
                when="w",
                then="t",
                anchor="page:c",
                completion=OnPage(subject="c"),
                patches="3",
            ),
        )
        host, _session, _driver = _armed_host(steps)

        host.tutorial_state_json(_view(subject="a", pane="wiki"))
        host.tutorial_state_json(_view(subject="b", pane="wiki"))
        host.tutorial_state_json(_view(subject="c", pane="wiki"))

        log = host.completion_log
        assert [step_id for step_id, _ordinal in log] == ["s1", "s2", "s3"]
        ordinals = [ordinal for _step_id, ordinal in log]
        assert ordinals == sorted(ordinals)
        assert ordinals[0] < ordinals[1] < ordinals[2]  # three separate polls


# --------------------------------------------------------------------------- #
# tutorial_state_json — reset on re-bind, malformed input.                    #
# --------------------------------------------------------------------------- #


class TestResetOnRebind:
    def test_rebinding_resets_completion_log_and_progress(self) -> None:
        steps = (
            TutorialStep(
                id="s1",
                given="g",
                when="w",
                then="t",
                anchor="page:a",
                completion=OnPage(subject="a"),
                patches="x",
            ),
            TutorialStep(
                id="s2",
                given="g",
                when="w",
                then="t",
                anchor="page:b",
                completion=OnPage(subject="b"),
                patches="y",
            ),
        )
        host, _session, driver = _armed_host(steps)

        payload = json.loads(host.tutorial_state_json(_view(subject="a", pane="wiki")))
        assert payload["step_index"] == 1
        assert host.completion_log != []

        new_session = _FakeSession(session_id=UUID(int=77))
        host.bind_session(new_session, driver)  # type: ignore[arg-type]

        assert host.completion_log == []
        payload = json.loads(host.tutorial_state_json(_view(subject=None, pane="wiki")))
        assert payload["step_index"] == 0


class TestMalformedViewState:
    def test_malformed_json_raises_value_error(self) -> None:
        steps = _tiny_steps()
        host, _session, _driver = _armed_host(steps)

        with pytest.raises(ValueError):
            host.tutorial_state_json("{not valid json")


# --------------------------------------------------------------------------- #
# new_campaign() (call0).                                                     #
# --------------------------------------------------------------------------- #


class TestNewCampaign:
    def test_ok_envelope_field_order(self) -> None:
        host = RustClientHost(
            InMemoryCampaignCatalog(), defines_hash=_DEFINES_HASH, engine_version=_ENGINE_VERSION
        )
        payload = json.loads(host.new_campaign())
        assert list(payload.keys()) == ["ok", "campaign_id", "codename"]
        assert payload["ok"] is True

    def test_catalog_row_actually_created(self) -> None:
        catalog = InMemoryCampaignCatalog()
        host = RustClientHost(catalog, defines_hash=_DEFINES_HASH, engine_version=_ENGINE_VERSION)
        assert catalog.list_campaigns() == ()

        host.new_campaign()

        assert len(catalog.list_campaigns()) == 1

    def test_codename_derives_from_the_minted_id(self) -> None:
        catalog = InMemoryCampaignCatalog()
        host = RustClientHost(catalog, defines_hash=_DEFINES_HASH, engine_version=_ENGINE_VERSION)

        payload = json.loads(host.new_campaign())
        minted_id = UUID(payload["campaign_id"])

        assert payload["codename"] == operation_codename(minted_id)
        rows = catalog.list_campaigns()
        assert rows[0].campaign_id == minted_id

    def test_new_campaign_is_recorded_for_was_verb_issued(self) -> None:
        steps = (
            TutorialStep(
                id="s_new_campaign",
                given="a fresh boot with no campaign chosen yet",
                when="the player presses 'n' to mint a new campaign",
                then="a freshly minted campaign row appears in the lobby",
                anchor="binding:LobbyScreen:n",
                completion=VerbIssued(verb="new_campaign"),
                patches="Patches cheers the mint.",
            ),
        )
        host, _session, _driver = _armed_host(steps)

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is False

        host.new_campaign()

        assert json.loads(host.tutorial_state_json(_view()))["finished"] is True

    def test_catalog_failure_propagates(self) -> None:
        class _RaisingCatalog:
            def create_campaign(
                self, *, slug: str, engine_version: str, defines_hash: str
            ) -> object:
                msg = "catalog unavailable"
                raise RuntimeError(msg)

        host = RustClientHost(
            _RaisingCatalog(),  # type: ignore[arg-type]
            defines_hash=_DEFINES_HASH,
            engine_version=_ENGINE_VERSION,
        )

        with pytest.raises(RuntimeError, match="catalog unavailable"):
            host.new_campaign()


# --------------------------------------------------------------------------- #
# load_campaign — home_subject (§4).                                          #
# --------------------------------------------------------------------------- #


class TestLoadCampaignHomeSubject:
    def test_ack_carries_the_home_subject_with_pinned_field_order(self) -> None:
        session = _FakeSession(session_id=_SESSION_ID, tick=3)
        host = RustClientHost(
            InMemoryCampaignCatalog(),
            defines_hash=_DEFINES_HASH,
            engine_version=_ENGINE_VERSION,
            campaign_loader=lambda _campaign_id: session,  # type: ignore[arg-type, return-value]
        )

        raw = host.load_campaign(str(_SESSION_ID))
        payload = json.loads(raw)

        assert list(payload.keys()) == ["ok", "campaign_id", "tick", "home_subject"]
        assert payload == {
            "ok": True,
            "campaign_id": str(_SESSION_ID),
            "tick": 3,
            "home_subject": _HOME_SUBJECT,
        }
