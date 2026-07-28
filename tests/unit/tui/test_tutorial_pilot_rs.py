"""The headless Rust-client parity harness for the tutorial-as-BDD suite
(Program v1.0.0 T6 continued; M3 Tutorial gate, Task 28).

Contracts: ``docs/superpowers/specs/2026-07-27-m3-tutorial-contracts.md``
§5 (this module's own normative anchor→script mapping table and its four
assertion tiers) and ``docs/superpowers/specs/2026-07-27-m2-seam-contracts.md``
(the envelope / ``RecordingHost`` conventions this module also drives
through, unchanged since M2).

**What is ported.** The composition ``tests/unit/tui/test_tutorial_pilot.py``
already proved out: a REAL :class:`~babylon.game.session.GameSession` over
the real 30-system engine, a real vault bake
(:class:`~babylon.projection.vault.tick_baker.ArchiveTickBaker` over a
``dulwich``-backed temp directory), and exactly ONE faked seam — Postgres
itself, via :class:`_InMemoryGameStore` (mirrored verbatim below,
mirror-not-import: see its own docstring). Onto that SAME composition, this
module drives the RUST client instead of Textual: one
:func:`babylon_tui.run` call replays the WHOLE 24-step
:data:`~babylon.game.tutorial.WAYNE_OPENING_ARC` as a scripted key sequence
and returns every intermediate rendered frame plus the host-call log in one
shot (the FFI contract ``tests/unit/tui/test_rust_client_ffi.py`` already
exercises for M0/M1/M2).

**Deliberately NOT copied — Textual ``Pilot`` mechanics.** No
``ArchiveApp``, no ``textual.pilot.Pilot``, no widget queries
(``query_one``/``OptionList``/``Label``/``Content.from_markup``), no
``pilot.pause()``/settle-retry loop (the pilot's own ``_settled``), no
deferred-exception surfacing (``_raise_deferred_app_exception``), no
per-step ``mock.patch.object`` spy on an ``action_*`` method. The Rust FFI
is fully synchronous: ``babylon_tui.run`` blocks until the entire scripted
replay finishes and hands back every frame already rendered — there is no
async message pump to settle, so none of the pilot's own tier-2
"structural Pilot state" retry plumbing has a Rust-side counterpart to
port.

**RECORDED IMPROVEMENT over the pilot** (contract §5 tier 2). The pilot
proves a ``VerbIssued`` completion's own dispatch by wrapping
``ArchiveApp.action_issue_verb`` in a ``mock.patch.object`` spy — a
Textual-specific instrumentation trick with no Rust-side method to spy on
in the first place. Here, :class:`~babylon.tui.host.RustClientHost` itself
IS the dispatch seam (contract §1: ``issue_verb``/``new_campaign`` record
dispatch-proof names on method entry; the client's own cumulative
``chrome_verbs`` report rides the SAME ``tutorial_state_json`` poll
argument) — dispatch is proven by asking the host whether it happened
(``host.was_verb_issued(...)``) once the whole run is over, never by
spying on a method call.

**Honest gaps inherited from the pilot, unchanged by the port.** Wayne's
own material state autopauses on literally every tick from tick 1 onward
(``ECOLOGICAL_OVERSHOOT``/``PERIPHERAL_REVOLT`` fire critical-tier every
single tick under this exact scenario/seed — the pilot's own module
docstring verified this empirically, not assumed) — so
``advance_a_tick``'s own ``t`` press already leaves the paced driver
``awaiting_ack``, and ``run_until_autopause``'s own ``r`` press is
observably a NO-OP refusal (the SAME pre-check-ladder string M2 already
renders: ``"autopause pending (...) — press 'a' to acknowledge"``), never a
genuine multi-tick auto-run through uneventful ticks. ``run_until_autopause``'s
own ``PausePending`` completion still holds — it was already true from the
PRIOR ``advance_a_tick`` press, and the SAME bounded multi-advance-per-poll
accumulator :data:`~babylon.game.tutorial_runtime.TutorialRuntimeProgress`'s
evaluator (mirroring ``TutorialOverlay.check_progress``) uses means
``run_until_autopause``'s own completion can log in the SAME poll as
``advance_a_tick``'s — before ``r`` is ever pressed. See
:func:`TestWayneOpeningArcOnRust.test_completion_log_poll_ordinals_are_nondecreasing`'s
own docstring for why this is asserted as non-decreasing rather than
strictly increasing.

**RECORDED DEVIATION (frame-text rendering, verified against the real
rendering pipeline, never assumed).** The pilot's own statblock-row regexes
(e.g. ``r"wage_balance\\s+-?\\d+\\.\\d+"``, no colon) match the TEXTUAL
client's own POST-PROCESSED row form — ``babylon.tui.directives``' fenced
``{statblock}`` dispatcher strips the baked fence body's ``": "`` at render
time. The Rust client has no directive-fence dispatcher at all
(``rust/crates/babylon-tui/src/wiki_render.rs`` is a thin
``babylon_md``-only renderer; since the ksbc stylesheet,
``BabylonStyleSheet::code_block_fence`` renders a directive fence as a
``▌``-prefixed header line over an untouched body — never a parsed
directive), so the vault's own baked fence body — every
``*.md.j2`` template's identical ``{{ label }}: {{ value }}`` line, read
directly off ``src/babylon/projection/vault/templates/`` for this module —
survives UNCHANGED into the rendered frame, colon included. This module's
own regexes below require that colon rather than porting the Textual-side
stripped form byte-for-byte: ported faithfully in substance (same field
names, same numeric-shaped-not-value-pinned reasoning — a coefficient
retune must not regress this suite), not in punctuation.

**Composition (contract §5).** :class:`_InMemoryGameStore` mirrored
verbatim from the pilot; an EMPTY
:class:`~babylon.tui.campaign_menu.InMemoryCampaignCatalog` (the arc's own
``boot_into_lobby.given`` — a fresh boot with no campaign chosen yet); real
:class:`~babylon.tui.watchlist.InMemoryWatchlistPersistence`/
:class:`~babylon.tui.nav.InMemoryNavPersistence` stores (the same fakes
``tests/unit/tui/test_rust_host_m2.py`` already uses); a ``_loader``
mirroring the pilot's own (:func:`~babylon.game.session.create_new_campaign`
over :class:`~babylon.engine.scenarios.WayneCountyScenario` plus
``vault_page_source``/``vault_known_subjects``/``bake_briefing``,
``narrator=None``); ``_driver_factory`` mirroring
``babylon.cli.play._driver_factory``'s own documented cast (that module's
own docstring explains why the cast is sound); a
:class:`~babylon.tui.host.RustClientHost` wired with every M0-M3 seam,
including ``tutorial_steps=play_cmd._tutorial_steps()`` and
``tutorial_progress_factory=play_cmd._tutorial_progress_factory(True,
steps=...)`` — the SAME composition-root objects the real ``babylon play
--client rust --tutorial`` boot wires, imported rather than re-derived, so
this harness can never silently drift from what a real tutorial-enabled
boot actually does. Mint determinism:
``mock.patch("babylon.tui.campaign_menu.uuid4",
return_value=UUID(int=99))`` — the pilot's own ``_PINNED_CAMPAIGN_ID``
trick, unchanged.

**A forward-looking spec, not a test against shipped code.** As of this
module's own authoring, none of the M3 surface it drives exists yet:
``RustClientHost`` has no ``tutorial_steps=``/``tutorial_progress_factory=``
constructor keywords, no ``tutorial_state_json``/``new_campaign``/
``completion_log``/``was_verb_issued``; ``AppConfig`` (``config.rs``) has no
``headless_size`` field and ``babylon-tui-python/src/lib.rs`` hardcodes an
80×24 ``TestBackend``; ``app.rs`` has no pane model, no real lobby mint (`n`
still refuses loudly), and ``K`` only toggles the peek depth with no
refusal string or ``chrome_verbs`` tracking. This module is the target
contract Task 27's Python/Rust work must satisfy — it is EXPECTED red until
that work lands, exactly like a red-phase TDD test written before its
production code.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast
from unittest import mock
from uuid import UUID

import pytest

import babylon.cli.play as play_cmd
from babylon.engine.scenarios import WayneCountyScenario
from babylon.game.pacing import PacedTickDriver, paced_driver_for_session
from babylon.game.session import (
    GameSession,
    create_new_campaign,
    vault_known_subjects,
    vault_page_source,
)
from babylon.game.tutorial import WAYNE_OPENING_ARC, TutorialStep
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.projection.briefing import project_briefing
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.tick_baker import ArchiveTickBaker
from babylon.topology import BabylonGraph
from babylon.tui.app import CampaignHandle
from babylon.tui.campaign_menu import InMemoryCampaignCatalog
from babylon.tui.host import RustClientHost
from babylon.tui.nav import InMemoryNavPersistence
from babylon.tui.watchlist import InMemoryWatchlistPersistence

# All imports above are pure Python (no Rust extension needed); the skip
# guard sits AFTER them — mirroring test_rust_client_ffi.py's own module-
# level `pytest.importorskip` convention, kept as a plain assignment (not an
# import statement) so no import ever follows non-import code (ruff E402).
babylon_tui = pytest.importorskip(
    "babylon_tui",
    reason="opt-in tui group not installed (uv sync --group tui + maturin develop)",
)

pytestmark = pytest.mark.unit

_WAYNE_FIPS: Final = "26163"
#: The pilot's own headless viewport (``test_tutorial_pilot.py``'s
#: ``_PILOT_SIZE``) — wide/tall enough that the economy dossier's statblock
#: rows and the play chrome's four regions are never truncated. Threaded
#: through as ``AppConfig.headless_size`` (contract §5) rather than the
#: FFI's own 80×24 default.
_PILOT_SIZE: Final[tuple[int, int]] = (120, 50)
#: The lobby mints a campaign id via a bare ``uuid4()`` call
#: (``CampaignMenu.new_campaign`` -> ``InMemoryCampaignCatalog.
#: create_campaign``); pinning it (the pilot's own ``_PINNED_CAMPAIGN_ID``
#: trick) keeps the lobby row's derived codename identical across two
#: independent runs, without touching the engine's own ``rng_seed``
#: determinism (``WayneCountyScenario``'s default is already ``rng_seed=0``).
_PINNED_CAMPAIGN_ID: Final = UUID(int=99)


# --------------------------------------------------------------------------- #
# The in-memory GameRuntimeStore double — mirrored verbatim from the pilot.  #
# --------------------------------------------------------------------------- #


class _InMemoryGameStore:
    """A minimal in-memory double satisfying ``GameRuntimeStore`` structurally.

    Mirrored VERBATIM from ``tests/unit/tui/test_tutorial_pilot.py``'s own
    ``_InMemoryGameStore`` (mirror-not-import: that class is private to its
    own test module, and both harnesses need the identical structural
    double, so it is copied here rather than re-derived from scratch — the
    WO-37 structural-Protocol trick means :mod:`babylon.game.session` cannot
    tell this apart from a real
    :class:`~babylon.persistence.postgres_runtime.PostgresRuntime`). If
    ``GameRuntimeStore``'s own protocol ever changes, BOTH copies need the
    same fix — there is no shared base to update once.
    """

    def __init__(self) -> None:
        self._sessions: dict[UUID, dict[str, Any]] = {}
        self._graphs: dict[tuple[UUID | None, int], BabylonGraph] = {}
        self._last_committed: dict[UUID, int] = {}
        self.submitted_turns: list[dict[str, Any]] = []
        """Every ``submit_turn`` call recorded verbatim — the arc's own
        ``issue_aid_on_the_proletariat`` step is the first (and only) step
        in this arc to actually reach this seam, so this list's own
        extra-content check is what proves the WRITE PATH itself carried
        the honest target, not merely that dispatch happened."""

    def create_session(
        self,
        scenario: str,
        config_json: dict[str, Any],
        game_defines_json: dict[str, Any],
        rng_seed: int,
        *,
        trace_level: str = "NONE",
        player_id: int | None = None,
        session_id: UUID | None = None,
    ) -> UUID:
        """See ``GameRuntimeStore.create_session``."""
        resolved = session_id if session_id is not None else UUID(int=len(self._sessions))
        self._sessions[resolved] = {
            "id": resolved,
            "scenario": scenario,
            "config_json": config_json,
            "game_defines_json": game_defines_json,
            "rng_seed": rng_seed,
            "trace_level": trace_level,
            "player_id": player_id,
        }
        return resolved

    def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        """See ``GameRuntimeStore.get_session``."""
        return self._sessions.get(session_id)

    def get_pending_turns(self, session_id: UUID, tick: int) -> list[dict[str, Any]]:
        """See ``GameRuntimeStore.get_pending_turns`` — honestly always
        empty: this arc's ``issue_aid_on_the_proletariat`` step DOES submit a
        real turn (see :attr:`submitted_turns`), but it is the arc's own last
        write — no further tick ever advances to read a pending queue back."""
        return []

    def mark_turns_resolved(self, session_id: UUID, tick: int) -> int:
        """See ``GameRuntimeStore.mark_turns_resolved``."""
        return 0

    def persist_tick(
        self,
        tick: int,
        graph: BabylonGraph,
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """See ``GameRuntimeStore.persist_tick``."""
        self._graphs[(session_id, tick)] = graph

    def persist_tick_summary(
        self,
        tick: int,
        summary: dict[str, Any],
        *,
        session_id: UUID,
    ) -> None:
        """See ``GameRuntimeStore.persist_tick_summary``."""

    def hydrate_graph(
        self, tick: int | None = None, *, session_id: UUID | None = None
    ) -> BabylonGraph:
        """See ``GameRuntimeStore.hydrate_graph`` — unused (this harness
        never crash-resumes), kept only for structural completeness."""
        if tick is None:
            tick = max(t for sid, t in self._graphs if sid == session_id)
        return self._graphs[(session_id, tick)]

    def persist_tick_atomic(
        self, envelope: PerTickTransactionEnvelope, *, write_commit_marker: bool = True
    ) -> None:
        """See ``GameRuntimeStore.persist_tick_atomic``."""
        if write_commit_marker:
            self._last_committed[envelope.session_id] = envelope.tick

    def get_last_committed_tick(self, session_id: UUID) -> int | None:
        """See ``GameRuntimeStore.get_last_committed_tick``."""
        return self._last_committed.get(session_id)

    def submit_turn(
        self,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        *,
        action_type: str | None = None,
        target_id: str | None = None,
        target_community: str | None = None,
        params_json: dict[str, Any] | None = None,
    ) -> int:
        """See ``TurnSink.submit_turn`` — records the call onto
        :attr:`submitted_turns`."""
        self.submitted_turns.append(
            {
                "session_id": session_id,
                "tick": tick,
                "org_id": org_id,
                "verb": verb,
                "action_type": action_type,
                "target_id": target_id,
                "target_community": target_community,
                "params_json": params_json,
            }
        )
        return len(self.submitted_turns)


# --------------------------------------------------------------------------- #
# The composition-root harness — mirrors babylon.cli.play's REAL wiring.      #
# --------------------------------------------------------------------------- #


def _driver_factory(campaign: CampaignHandle) -> PacedTickDriver:
    """The ``babylon.tui.app.DriverFactory`` seam.

    Mirrors ``babylon.cli.play._driver_factory`` exactly (that module's own
    docstring explains the cast): :func:`~babylon.game.pacing.
    paced_driver_for_session` needs a full ``GameSession`` (specifically
    ``session.services.defines``), strictly more than ``CampaignHandle``
    structurally promises, so mypy correctly refuses the function directly.
    The cast is sound for the same reason production's is — this harness's
    own ``_loader`` (below) always resolves to a real ``GameSession``.
    """
    return paced_driver_for_session(cast(GameSession, campaign))


def _build_harness(vault_root: Path) -> tuple[RustClientHost, _InMemoryGameStore]:
    """Wire a fresh ``RustClientHost`` against a REAL composed campaign.

    The same ``babylon.game.session``/``babylon.game.pacing`` composition
    idiom the pilot's own ``_build_harness`` (and the real ``babylon.cli.
    play`` composition root) use, minus Postgres (see
    :class:`_InMemoryGameStore`) — real engine, real ``PacedTickDriver``,
    real vault baking, so ``county/26163``/``economy/USA``/
    ``organization/ORG002``/``social_class/C001`` are all REAL rendered
    pages, never a fixture lookalike. Narrator OFF (``narrator=None``) and
    Wayne's own fixed ``rng_seed=0`` default keep the whole session
    deterministic.

    ``tutorial_steps``/``tutorial_progress_factory`` are threaded straight
    from ``babylon.cli.play`` (:func:`babylon.cli.play._tutorial_steps`,
    :func:`babylon.cli.play._tutorial_progress_factory`) rather than
    re-derived here — the SAME objects a real ``babylon play --client rust
    --tutorial`` boot wires, so this harness can never silently drift from
    what tutorial-enabled production actually does. ``True`` is passed
    explicitly (never the tri-state ``None`` heuristic) so the overlay arms
    regardless of this harness's own campaign-tick approximation.

    :param vault_root: a fresh, empty directory (a test's own ``tmp_path``)
        for this campaign's baked vault.
    :returns: the freshly constructed host, plus the in-memory store it
        writes through (so callers can inspect ``submitted_turns`` directly,
        without reaching through the host/session at all).
    """
    store = _InMemoryGameStore()
    # EMPTY catalog: "a fresh boot with no campaign chosen yet" — WAYNE_OPENING_ARC's
    # own boot_into_lobby.given.
    catalog = InMemoryCampaignCatalog()
    materializer = VaultMaterializer(vault_root)
    baker = ArchiveTickBaker(materializer, (_WAYNE_FIPS,))

    def _loader(campaign_id: UUID) -> GameSession:
        session = create_new_campaign(
            store,
            scenario=WayneCountyScenario(),
            session_id=campaign_id,
            tick_commit_observer=baker,
            pages=vault_page_source(vault_root),
            known_subjects=vault_known_subjects(vault_root),
            narrator=None,
        )
        view = project_briefing(
            session.session_id, tick=session.tick, defines=session.services.defines
        )
        materializer.bake_briefing(view, tick=session.tick)
        return session

    steps = play_cmd._tutorial_steps()
    host = RustClientHost(
        catalog,
        defines_hash="d" * 16,
        engine_version="m3-tutorial-pilot-rs",
        campaign_loader=_loader,
        driver_factory=_driver_factory,
        watchlist_persistence=InMemoryWatchlistPersistence(),
        nav_persistence=InMemoryNavPersistence(),
        tutorial_steps=steps,
        tutorial_progress_factory=play_cmd._tutorial_progress_factory(True, steps=steps),
    )
    return host, store


# --------------------------------------------------------------------------- #
# The normative anchor→script mapping (contract §5) — a list of              #
# (arc step id | None, [Rust ScriptStep entries]) pairs, in arc order.       #
# ``None`` marks bridging glue the authored arc itself does not script (the  #
# pilot's own ``_load_the_minted_campaign`` analog: after minting, the       #
# lobby's freshly-added (and only) row must be confirmed with Enter before   #
# ``begin_the_operation`` can run).                                         #
# --------------------------------------------------------------------------- #


def _type_subject_id(subject: str) -> list[dict[str, str]]:
    """One ``{"key": ch}`` script entry per character of ``subject``.

    Rust's ``ScriptStep::Key`` (``config.rs``) only names single characters
    or a small closed set of named keys — there is no "paste a string" step,
    so typing a full subject id is one keypress per character.
    """
    return [{"key": ch} for ch in subject]


def _palette_pick(subject: str) -> list[dict[str, str]]:
    """Drive the command palette open, type ``subject`` in full, press Enter.

    Per contract §5's own mapping-table note: typing the FULL subject id
    (never a partial query) is a deliberate deviation from the pilot (which
    posts ``EntityNavigated`` directly, bypassing the palette's own fuzzy
    filter entirely) — the Rust palette is driven for real here. The exact
    string typed is guaranteed the sole top-ranked match once the LAST
    character lands: ``palette.rs``'s own ``fuzzy_score`` gives an EXACT
    (case-insensitive) match its highest ×2.0 multiplier (that module's own
    doctest-pinned ``56.0`` for ``"county/26163"`` scored against itself),
    and ``PaletteView::refilter`` resets ``selected`` back to ``0`` on
    EVERY keystroke — so Enter right after the final character opens
    exactly ``subject``, deterministically, independent of the palette's
    fuzzy-ranking behavior over any OTHER candidate.
    """
    return [{"key": "/"}, *_type_subject_id(subject), {"key": "enter"}]


#: ``app.rs``'s own ``ChromeFocus`` cycle order (read directly off
#: ``handle_key``'s ``KeyCode::Tab`` arm): ``Center -> Chronicle -> Watchlist
#: -> Center``, wrapping. Both rail-open steps below need the FIXED tab
#: count from wherever focus already sits — traced by hand against the
#: FULL scripted arc (chrome starts at ``Center``; every pane key ('1'-'4')
#: returns focus to ``Center`` per contract §3; nothing else moves it before
#: either rail-open step runs): ``open_the_pinned_row_from_the_watchlist``
#: needs 2 tabs (``Center -> Chronicle -> Watchlist``);
#: ``open_the_chronicle_rails_highlighted_row`` needs 1 tab
#: (``Center -> Chronicle`` — the prior rail-open's own successful Enter
#: already reset focus to ``Center``, per ``app.rs``'s own
#: ``RailAction::Route`` arm).
_ARC_SCRIPT: Final[list[tuple[str | None, list[dict[str, object]]]]] = [
    ("boot_into_lobby", [{"key": "n"}]),  # §2: n -> host.new_campaign()
    (None, [{"key": "enter"}]),  # bridging: load the freshly minted (only) row
    ("begin_the_operation", [{"key": "enter"}]),  # §4: Enter, no link cursor -> home_subject
    ("read_the_county_dossier", []),  # page: anchor, pure read
    ("advance_a_tick", [{"key": "t"}]),
    ("run_until_autopause", [{"key": "r"}]),  # honest-gap no-op refusal (module docstring)
    ("acknowledge_the_pause", [{"key": "a"}]),
    ("palette_to_the_economy_dossier", _palette_pick("economy/USA")),
    ("read_the_theorem_verdict", []),
    # jump_back_to_wayne's own arc anchor IS ctrl+o, and wiki.rs binds
    # ctrl-o/ctrl-i as LIVE secondary aliases for the primary [/] pair — no
    # RECORDED DEVIATION needed here (unlike the contract's own hedge),
    # confirmed by reading wiki.rs's handle_key directly.
    ("jump_back_to_wayne", [{"key": "ctrl-o"}]),
    ("jump_forward_with_brackets", [{"key": "]"}]),
    ("jump_back_with_brackets", [{"key": "["}]),
    ("palette_to_the_state_apparatus_dossier", _palette_pick("organization/ORG002")),
    ("read_the_state_apparatus_dossier", []),
    ("palette_to_the_repression_ledger", _palette_pick("social_class/C001")),
    ("read_the_repression_ledger", []),
    ("learn_the_map_pane", [{"key": "2"}]),
    ("learn_the_wiki_pane", [{"key": "3"}]),
    ("learn_the_topology_pane", [{"key": "4"}]),
    ("learn_the_dashboard_pane", [{"key": "1"}]),
    # RECORDED DEVIATION (contract §5, already pinned by the M2 ruling):
    # Rust's pin key is capital 'P' — lowercase 'p' stays the wiki
    # link-cursor-previous key.
    ("pin_the_proletariat_to_the_watchlist", [{"key": "P"}]),
    (
        "open_the_pinned_row_from_the_watchlist",
        [{"key": "tab"}, {"key": "tab"}, {"key": "enter"}],
    ),
    ("issue_aid_on_the_proletariat", [{"key": "f6"}]),
    ("peek_a_wikilink_with_the_keyboard", [{"key": "K"}]),
    ("open_the_chronicle_rails_highlighted_row", [{"key": "tab"}, {"key": "enter"}]),
]


def _flatten_script(
    arc_script: list[tuple[str | None, list[dict[str, object]]]],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Flatten ``arc_script`` into the Rust ``script`` list, recording each
    named step's own frame index by construction.

    ``babylon_tui.run``'s headless path renders ONE initial frame (index 0,
    before any script entry applies) then one MORE frame per script entry,
    in order (``babylon-tui-python/src/lib.rs``): frame ``k`` is the state
    right after ``k`` script entries have cumulatively applied. A step
    contributing NO entries of its own (the arc's pure ``page:``-anchored
    "read" steps) therefore shares its immediately PRECEDING step's own
    frame index — no new render happens for a step that presses no key,
    mirroring the pilot's own empty-anchor ``page:`` convention.

    :returns: ``(script, frame_index)`` — the flattened script for
        ``AppConfig``, and ``{step_id: frame_index}`` for every NAMED
        (non-``None``) entry.
    """
    script: list[dict[str, object]] = []
    frame_index: dict[str, int] = {}
    for step_id, entries in arc_script:  # loop bound: len(_ARC_SCRIPT), a fixed literal
        script.extend(entries)
        if step_id is not None:
            frame_index[step_id] = len(script)
    return script, frame_index


#: The tutorial-tracked slice this harness's ``completion_log``/frame-index
#: assertions cover — the SAME slice ``babylon.cli.play._tutorial_steps()``
#: (and therefore ``_build_harness``'s own ``RustClientHost``) is built
#: against, so there is no risk of this module's own expectations drifting
#: from what the host was actually wired with.
_TRACKED_STEPS: Final[tuple[TutorialStep, ...]] = play_cmd._tutorial_steps()

#: ``_TRACKED_STEPS``' own ids, as a set — used below to tell a tracked step
#: (one the host's tutorial evaluator actually walks) apart from the arc's
#: two pre-slice beats (``boot_into_lobby``/``begin_the_operation``), which
#: ``_ARC_SCRIPT`` still names for scripting purposes but which never appear
#: in ``host.completion_log`` at all (:func:`play_cmd._tutorial_steps`'s own
#: docstring explains why they're sliced off).
_TRACKED_STEP_IDS: Final[frozenset[str]] = frozenset(step.id for step in _TRACKED_STEPS)

#: The arc's own two pre-slice beats (``boot_into_lobby``,
#: ``begin_the_operation``) that ``_TRACKED_STEPS`` drops — the host's
#: tutorial evaluator never observes them, so they never appear in
#: ``host.completion_log`` at all, but the transcript artifact (R19 review
#: fix pass) still records them honestly as ``completed_poll: null``.
_UNTRACKED_STEP_IDS: Final[frozenset[str]] = frozenset(
    step.id for step in WAYNE_OPENING_ARC.steps[:2]
)


def _derive_first_post_bind_frame_index() -> int:
    """Derive OFFSET: the first frame index at which the tutorial poll seam
    goes live — never hardcoded.

    ``app.rs``'s own ``poll_tutorial`` (read directly off that module) is a
    no-op until ``self.chrome`` exists, which happens exactly once: at the
    bridging (``None``-marked) entry in ``_ARC_SCRIPT`` that loads the
    freshly minted campaign (the sole ``bind_session`` call this whole arc
    ever makes). From that frame onward, EVERY subsequent ``render_frame``
    call polls exactly once (one call per remaining script entry), so poll
    ordinals and frame indices are related by this ONE additive constant for
    the rest of the run: ``completed_poll + OFFSET == frame_index`` for any
    step whose own scripted input is what caused its completion.

    Computed here by summing ``_ARC_SCRIPT``'s own flattened entry counts
    through and including that bridging entry — so a future script reshuffle
    that moves the bind point earlier or later updates this constant
    automatically, instead of silently invalidating every downstream
    causality assertion below.

    :raises AssertionError: ``_ARC_SCRIPT`` has no bridging entry — a
        malformed script this module's own construction should never
        produce, so a loud failure here is a real authoring bug, not a
        player-reachable state.
    """
    total = 0
    for step_id, entries in _ARC_SCRIPT:  # loop bound: len(_ARC_SCRIPT), a fixed literal
        total += len(entries)
        if step_id is None:
            return total
    msg = "_ARC_SCRIPT has no bridging (None) entry to derive the bind-frame offset from"
    raise AssertionError(msg)


#: The documented gate-condition semantics (module docstring's own HONEST
#: GAP section; mirrors the Textual overlay's own bounded
#: multi-advance-per-poll accumulator, contract §5's "Advance loop =
#: TutorialOverlay.check_progress verbatim ... bounded multi-advance through
#: consecutive TRUE predicates ... per poll"): both of these steps' own
#: completion predicates are ALREADY true from an EARLIER step's own action,
#: before this step's own scripted key(s) are ever applied —
#: ``run_until_autopause``'s ``PausePending`` from ``advance_a_tick``'s own
#: 't' press (Wayne's own material state autopauses every tick), and
#: ``open_the_chronicle_rails_highlighted_row``'s ``OnPage(social_class/
#: C001)`` from the subject/pane already settled by
#: ``peek_a_wikilink_with_the_keyboard`` (nothing between them ever
#: navigates away from social_class/C001 or leaves the Wiki pane). Both
#: therefore complete one or more polls BEFORE their own scripted frame,
#: never at or after it — the sole, named exception to the causality
#: assertion below.
_EARLY_COMPLETION_EXEMPT_STEP_IDS: Final[frozenset[str]] = frozenset(
    {"run_until_autopause", "open_the_chronicle_rails_highlighted_row"}
)


# --------------------------------------------------------------------------- #
# Content-check patterns — ported from the pilot's own                       #
# ``_EXTRA_CONTENT_CHECK_BY_STEP_ID`` regexes, colon-adjusted (module         #
# docstring's own RECORDED DEVIATION note).                                  #
# --------------------------------------------------------------------------- #

#: (The pilot's ``class_composition.labor_aristocracy`` county row is
#: DELIBERATELY not pinned here — it is fixture-fed on the Textual side
#: (the "not-yet-live" dossier statblock seam, ``app.py``'s own docstring);
#: the live ``CountyView`` at tick 0 is epistemically unattributed. See
#: ``test_county_dossier_shows_wayne_real_state``'s docstring.)

#: ``wage_balance``'s own baked fence-body row —
#: ``babylon/projection/vault/templates/economy.md.j2``'s literal
#: ``"{{ label }}: {{ value }}"`` line, UNSTRIPPED (module docstring's own
#: RECORDED DEVIATION: Rust's ``babylon-md`` renders an unrecognized fenced
#: code-block language, ``{statblock}``, as a literal code block — the
#: colon the Textual-side ``babylon.tui.directives`` dispatcher strips at
#: render time is never touched here). The numeric value itself is NOT
#: pinned — a genuine coefficient retune could shift the float without
#: being a regression this step's own Then cares about; what the Then
#: advertises is "renders as a real number", which a numeric-shaped regex
#: proves without over-pinning.
#:
#: WIDENED (review fix pass, R18): the colon is now OPTIONAL rather than
#: required — matching BOTH the raw-fence form above (``"key: value"``,
#: today's Rust render) AND the Textual-dispatched, colon-stripped form
#: (``"key<padding>value"``, ``test_tutorial_pilot.py``'s own patterns) —
#: so a future M4/M5 dispatcher unification cannot spuriously flip this
#: suite red over punctuation alone; the fence-line assert just below still
#: pins today's literal raw-fence renderer and is expected to need
#: updating (golden included) whenever that dispatcher lands.
_WAGE_BALANCE_ROW_PATTERN: Final = re.compile(r"wage_balance:?\s+-?\d+\.\d+")

#: ``labor_aristocracy_verdict``'s own row — same rendering contract (and
#: same R18 colon-optional widening) as above; the value is the literal
#: ``str(bool)`` render (``"True"``/``"False"``).
_LABOR_ARISTOCRACY_VERDICT_ROW_PATTERN: Final = re.compile(
    r"labor_aristocracy_verdict:?\s+(True|False)"
)

#: ``organization/ORG002``'s own ``heat`` row
#: (``render_organization.py``'s ``f"{heat:.6f}"`` render). Numeric-shaped
#: rather than pinning one specific float, same reasoning as
#: ``_WAGE_BALANCE_ROW_PATTERN`` above. Same R18 colon-optional widening.
_STATE_APPARATUS_HEAT_ROW_PATTERN: Final = re.compile(r"heat:?\s+-?\d+\.\d+")

#: ``social_class/C001``'s own ``repression_faced`` row
#: (``render_state.py``'s identical ``.6f`` render). Numeric-shaped for the
#: same reason as the heat pattern above; same R18 colon-optional widening.
_REPRESSION_FACED_ROW_PATTERN: Final = re.compile(r"repression_faced:?\s+-?\d+\.\d+")


# --------------------------------------------------------------------------- #
# One full-arc run — the shared expensive fixture every assertion reads      #
# from, per contract §5's own "Drive ONE babylon_tui.run(host, config)      #
# call" instruction.                                                         #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _ArcRun:
    """The full result of one scripted ``babylon_tui.run`` replay."""

    host: RustClientHost
    store: _InMemoryGameStore
    frames: list[str]
    host_calls: list[str]
    frame_index: dict[str, int]


def _run_full_arc(vault_root: Path) -> _ArcRun:
    """Boot a fresh harness and drive the WHOLE 24-step arc through ONE
    ``babylon_tui.run`` call.

    :param vault_root: a fresh, empty directory for this run's own baked
        vault (every caller passes its own — see the determinism test,
        which needs two INDEPENDENT vaults to prove byte-identity is real,
        not a shared-state artifact).
    """
    host, store = _build_harness(vault_root)
    script, frame_index = _flatten_script(_ARC_SCRIPT)
    config = json.dumps(
        {
            "campaign_id": "",
            "campaign_name": "Lobby",
            "render_tier": "glyph",
            "tutorial_enabled": True,
            "narrator_enabled": False,
            "headless": True,
            "headless_size": list(_PILOT_SIZE),
            "script": script,
        }
    )
    with mock.patch("babylon.tui.campaign_menu.uuid4", return_value=_PINNED_CAMPAIGN_ID):
        raw = babylon_tui.run(host, config)
    transcript = json.loads(raw)
    return _ArcRun(
        host=host,
        store=store,
        frames=transcript["frames"],
        host_calls=transcript["host_calls"],
        frame_index=frame_index,
    )


def _transcript_payload(run: _ArcRun) -> dict[str, object]:
    """Build the tier-4 transcript artifact: ``{"arc_id", "steps": [...]}``
    (contract §5), one entry per step in the AUTHORED arc's own full order.

    WIDENED (review fix pass, R19): now includes the two pre-slice beats
    (``boot_into_lobby``, ``begin_the_operation`` — :data:`_UNTRACKED_STEP_IDS`)
    the host's tutorial evaluator never tracks (:func:`play_cmd._tutorial_steps`'s
    own docstring explains why they're sliced off) — recorded honestly as
    ``completed_poll: null`` (there is no completion to log for them) with
    their own real ``frame`` (``_flatten_script`` records a frame index for
    every NAMED ``_ARC_SCRIPT`` entry, tracked or not).

    :raises KeyError: ``run.host.completion_log`` is missing a TRACKED
        step's own id — a loud, attributable failure (never silently
        padded), since a well-formed run always covers every tracked step
        exactly once (this module's own tier-1 test pins that separately).
    """
    completed_poll = dict(run.host.completion_log)
    steps_payload = [
        {
            "index": index,
            "id": step.id,
            "scenario_name": step.scenario_name,
            "completed_poll": (None if step.id in _UNTRACKED_STEP_IDS else completed_poll[step.id]),
            "frame": run.frames[run.frame_index[step.id]],
        }
        # loop bound: len(WAYNE_OPENING_ARC.steps) <= TutorialScript's own
        # _MAX_SCRIPT_STEPS (64) — the arc is fixed at 24 steps today.
        for index, step in enumerate(WAYNE_OPENING_ARC.steps, start=1)
    ]
    return {"arc_id": WAYNE_OPENING_ARC.id, "steps": steps_payload}


@pytest.fixture(scope="module")
def arc_run(tmp_path_factory: pytest.TempPathFactory) -> _ArcRun:
    """The ONE full-arc replay every assertion tier below reads from.

    Module-scoped: the underlying run is a real 30-system-engine session
    over two real ticks plus a real vault bake — expensive enough that
    every tier-1/2/3 assertion in this module sharing ONE freshly-booted
    run, rather than re-running the whole scripted arc per assertion, is
    the honest reading of contract §5's own "Drive ONE
    ``babylon_tui.run(host, config)`` call" instruction. The determinism
    test below deliberately does NOT use this fixture — it needs its OWN
    pair of independently-booted runs to prove byte-identity is real, not
    an artifact of sharing one host.
    """
    return _run_full_arc(tmp_path_factory.mktemp("vault"))


# --------------------------------------------------------------------------- #
# A cheap, engine-free self-check on this module's own script construction.  #
# --------------------------------------------------------------------------- #


def test_arc_script_names_every_authored_step_exactly_once_in_order() -> None:
    """``_ARC_SCRIPT``'s own named entries, in order, must exactly match
    ``WAYNE_OPENING_ARC.steps``'s own ids — a typo here would silently
    strand a step with no scripted input at all, never caught by anything
    else in this module (this check needs no host/engine, so it runs even
    when the later, expensive fixture-backed tests are still red)."""
    named_ids = [step_id for step_id, _ in _ARC_SCRIPT if step_id is not None]
    assert named_ids == [step.id for step in WAYNE_OPENING_ARC.steps]


# --------------------------------------------------------------------------- #
# Tier 1+2+3 (contract §5): completion order, dispatch proof, content.       #
# --------------------------------------------------------------------------- #


class TestWayneOpeningArcOnRust:
    """The four-tier parity proof (contract §5), all read from the SAME
    ``arc_run`` fixture (one ``babylon_tui.run`` call for the whole class).
    """

    # --- Tier 1: in-order completion. --------------------------------- #

    def test_completion_log_covers_tracked_steps_exactly_once_in_arc_order(
        self, arc_run: _ArcRun
    ) -> None:
        """``host.completion_log``'s own step-id sequence, taken in log
        order, must equal the tracked slice's ids in arc order — a single
        list-equality check that pins BOTH "every id appears" and "exactly
        once" and "in arc order" simultaneously (a duplicate, a missing
        id, or an out-of-order id all break this same equality).

        **Honest scope (review fix pass):** this proves completion
        COVERAGE and order-BY-CONSTRUCTION — the evaluator's own
        ``_tutorial_index`` walks the tracked slice strictly sequentially,
        so a completion log that covers every id exactly once can only
        ever come out in arc order; a shuffled log is not a reachable
        failure mode this check could catch. It proves nothing about
        CAUSALITY — whether a step's own scripted input is what actually
        made its predicate true, as opposed to an earlier step's input
        already having done so. That is
        :meth:`test_non_exempt_completions_never_precede_their_own_scripted_frame`'s
        own job, immediately below.
        """
        logged_ids = [step_id for step_id, _poll in arc_run.host.completion_log]
        assert logged_ids == [step.id for step in _TRACKED_STEPS]

    def test_non_exempt_completions_never_precede_their_own_scripted_frame(
        self, arc_run: _ArcRun
    ) -> None:
        """The real tier-1 causality check (review fix pass, replacing a
        ``poll_ordinal`` sorted()-tautology: that list is built by
        appending strictly-advancing ordinals by construction —
        ``host.py``'s own ``tutorial_state_json`` only ever appends the
        CURRENT poll's ordinal, in one poll-scoped batch, so it can never
        NOT come out sorted, regardless of what the arc actually did).

        Poll ordinals map onto frame indices by one fixed additive offset,
        :func:`_derive_first_post_bind_frame_index` (derived from
        ``_ARC_SCRIPT`` itself, never hardcoded): every frame from the
        first post-bind one onward triggers exactly one tutorial poll
        (``app.rs``'s own ``poll_tutorial``, called once per
        ``render_frame``). For every TRACKED step that has its own
        scripted input (excluding the arc's pure ``page:``-anchored read
        steps, which contribute no script entries of their own and so have
        no frame to be causally later than, and excluding the two untracked
        pre-slice beats), its completion must never be logged EARLIER than
        the poll corresponding to its own scripted frame — proof that the
        step's own input is what could plausibly have caused it, not merely
        that some order was preserved (contract §5's "each completion
        at-or-after its step's frame span start").

        :data:`_EARLY_COMPLETION_EXEMPT_STEP_IDS` is the sole, named,
        commented exception (module docstring's HONEST GAP): those two
        steps' own predicates are already true from an EARLIER step's
        action, so they complete strictly BEFORE their own scripted frame —
        asserted directly below as the honest gap itself, so a future
        change that stops them completing early (or makes them complete
        even earlier) flips this test red.
        """
        offset = _derive_first_post_bind_frame_index()
        completed_poll_by_id = dict(arc_run.host.completion_log)
        for step_id, entries in _ARC_SCRIPT:  # loop bound: len(_ARC_SCRIPT), a fixed literal
            if step_id is None or step_id not in _TRACKED_STEP_IDS or not entries:
                continue  # bridging glue / untracked pre-slice beats / pure "page:" reads
            completed_frame = completed_poll_by_id[step_id] + offset
            own_frame = arc_run.frame_index[step_id]
            if step_id in _EARLY_COMPLETION_EXEMPT_STEP_IDS:
                assert completed_frame < own_frame, (
                    f"{step_id}: expected the documented honest-gap EARLY completion "
                    f"(completed frame {completed_frame} < own scripted frame {own_frame})"
                )
            else:
                assert completed_frame >= own_frame, (
                    f"{step_id}: completed at frame {completed_frame}, BEFORE its own "
                    f"scripted frame {own_frame} — its own input cannot be what caused it"
                )

    # --- Tier 2: dispatch-proof (RECORDED IMPROVEMENT — no spies). ----- #

    def test_new_campaign_aid_and_peek_wikilink_were_dispatched(self, arc_run: _ArcRun) -> None:
        """``host.was_verb_issued`` proves dispatch for the lobby mint, the
        Aid verb, and the keyboard peek — reading the host's own dispatch
        log, never a ``mock.patch.object`` spy (module docstring's
        RECORDED IMPROVEMENT)."""
        assert arc_run.host.was_verb_issued("new_campaign")
        assert arc_run.host.was_verb_issued("aid")
        assert arc_run.host.was_verb_issued("peek_wikilink")

    # --- Tier 3: the pilot's extra content checks, verbatim ported. ---- #

    def test_county_dossier_shows_wayne_real_state(self, arc_run: _ArcRun) -> None:
        """``read_the_county_dossier``'s own extra Then-check — DELIBERATELY
        NOT the pilot's fixture-fed row (RECORDED DEVIATION, M3 contract §5).

        The Textual pilot asserts ``class_composition.labor_aristocracy``
        — but that row comes from the DOSSIER STATBLOCK SEAM'S COMMITTED
        FIXTURE (``babylon.tui.app._default_statblocks``; app.py's own
        docstring calls it "a separate, not-yet-live seam"), NOT from the
        live campaign: the REAL ``CountyView`` at tick 0 carries
        ``class_composition=None`` — epistemically unattributed until a
        Census verb runs (fog is epistemic, the engine is material). Wayne's
        REAL rendered state at this beat is therefore the honest one this
        test pins instead: the county's own FIPS, the live (honestly empty
        at tick 0) statblock fence, and the epistemic absence fence naming
        the REAL remedy verb — content no fixture page carries. The Textual
        seam's fixture-fed "not a fixture" check is flagged for Gate 3.
        """
        frame = arc_run.frames[arc_run.frame_index["read_the_county_dossier"]]
        assert _WAYNE_FIPS in frame
        # R18 note: this literal fence-line assert deliberately pins the
        # CURRENT renderer (babylon-md rendering an unrecognized fenced
        # code-block language verbatim, module docstring's own RECORDED
        # DEVIATION) — it WILL need updating once the M4/M5 dispatcher
        # lands (the golden transcript regenerates then anyway, so this is
        # expected drift, not a latent bug to pre-empt now).
        assert "{statblock} county/26163" in frame
        assert "class_composition — Census(Territory) to attribute class" in frame

    def test_theorem_verdict_shows_real_numbers(self, arc_run: _ArcRun) -> None:
        """``read_the_theorem_verdict``'s own extra Then-check, ported: the
        wage balance and the labor-aristocracy verdict both render as real,
        numeric-shaped rows."""
        frame = arc_run.frames[arc_run.frame_index["read_the_theorem_verdict"]]
        assert _WAGE_BALANCE_ROW_PATTERN.search(frame)
        assert _LABOR_ARISTOCRACY_VERDICT_ROW_PATTERN.search(frame)

    def test_state_apparatus_dossier_shows_real_numbers(self, arc_run: _ArcRun) -> None:
        """``read_the_state_apparatus_dossier``'s own extra Then-check,
        ported: the org type and a real, numeric-shaped heat row."""
        frame = arc_run.frames[arc_run.frame_index["read_the_state_apparatus_dossier"]]
        assert "org_type" in frame
        assert "state_apparatus" in frame
        assert _STATE_APPARATUS_HEAT_ROW_PATTERN.search(frame)

    def test_repression_ledger_shows_real_number(self, arc_run: _ArcRun) -> None:
        """``read_the_repression_ledger``'s own extra Then-check, ported: a
        real, numeric-shaped ``repression_faced`` row."""
        frame = arc_run.frames[arc_run.frame_index["read_the_repression_ledger"]]
        assert _REPRESSION_FACED_ROW_PATTERN.search(frame)

    def test_aid_reached_the_write_path_with_the_honest_target(self, arc_run: _ArcRun) -> None:
        """``issue_aid_on_the_proletariat``'s own extra Then-check, ported:
        the status line confirms a real queue (never a refusal) AND the
        in-memory store's own recorded call carries the honest target —
        ``VerbIssued``/``was_verb_issued`` alone prove only that dispatch
        happened, never WHICH target actually reached the write path."""
        frame = arc_run.frames[arc_run.frame_index["issue_aid_on_the_proletariat"]]
        assert "aid queued" in frame
        assert arc_run.store.submitted_turns, "no turn was ever submitted"
        submitted = arc_run.store.submitted_turns[-1]
        assert submitted["verb"] == "aid"
        assert submitted["target_id"] == "C001"

    def test_peek_reported_no_wikilinks_to_peek(self, arc_run: _ArcRun) -> None:
        """``peek_a_wikilink_with_the_keyboard``'s own extra Then-check,
        ported: the honest "no wikilinks yet" refusal (contract §4's own
        pinned Rust string, ``"status: no wikilinks to peek on this
        page"``), never a fabricated preview."""
        frame = arc_run.frames[arc_run.frame_index["peek_a_wikilink_with_the_keyboard"]]
        assert "no wikilinks to peek" in frame

    def test_run_until_autopause_is_the_honest_gap_no_op_refusal(self, arc_run: _ArcRun) -> None:
        """The M2 honest-gap refusal string (module docstring): Wayne's own
        material state means ``advance_a_tick`` already left the driver
        ``awaiting_ack``, so ``run_until_autopause``'s own ``r`` press is
        observably a no-op refusal, never a genuine multi-tick auto-run."""
        frame = arc_run.frames[arc_run.frame_index["run_until_autopause"]]
        assert "autopause pending" in frame
        assert "press 'a' to acknowledge" in frame

    def test_the_hud_survives_the_tutorial_strip(self, arc_run: _ArcRun) -> None:
        """Verify-panel blocker regression pin: the strip RESERVES rows
        (Textual dock semantics) and must never occlude the HUD — the arc's
        tick/pacing beats teach exactly what the HUD shows. ``T+`` is the
        HUD tick counter's own prefix; ``PACING`` is its third line."""
        frame = arc_run.frames[arc_run.frame_index["advance_a_tick"]]
        assert "T+" in frame, "the HUD tick counter is occluded by the tutorial strip"
        assert "PACING" in frame, "the HUD pacing line is occluded by the tutorial strip"

    @pytest.mark.parametrize(
        ("step_id", "fence"),
        [
            # M4 (contract §8, declared drift): the topology pane renders
            # REAL content now — its case moved to
            # test_topology_pane_renders_real_content_under_the_strip.
            # M5 (maps contract §5, same drift): the map pane followed —
            # its case moved to
            # test_map_pane_renders_real_content_under_the_strip.
            ("learn_the_dashboard_pane", "dashboard pane — not yet ported"),
        ],
    )
    def test_pane_fences_render_under_the_strip(
        self, arc_run: _ArcRun, step_id: str, fence: str
    ) -> None:
        """Verify-panel blocker regression pin: each unported pane's honest
        absence fence must actually be visible at its own teaching beat
        (the strip used to overlay the center region and blank it)."""
        frame = arc_run.frames[arc_run.frame_index[step_id]]
        assert fence in frame, f"{step_id}: the pane fence is not visible"

    def test_map_pane_renders_real_content_under_the_strip(self, arc_run: _ArcRun) -> None:
        """M5 (maps contract §3/§5): the map pane is REAL now — at its
        teaching beat the center region shows the pane's own titled
        surface, never the retired 'not yet ported' fence. CONTENT pin:
        WAYNE's graph carries no county-bearing territories, so the live
        truth is the pane's own honest tier-absence line — THE DAY a
        county producer stamps the WAYNE arc, this goes red and flips to
        asserting real band-colored cells (the M4 topology precedent)."""
        frame = arc_run.frames[arc_run.frame_index["learn_the_map_pane"]]
        assert "map pane — not yet ported" not in frame, (
            "the retired map fence is back — the real pane regressed"
        )
        assert "map — county/value" in frame, (
            "the map pane's own titled surface is not visible under the strip"
        )
        assert "no county map" in frame, (
            "the map pane must render the honest tier-absence line (or, once "
            "WAYNE carries county territories, real band-colored cells) — a "
            "blank interior is the certified-blank-golden class, never acceptable"
        )

    def test_topology_pane_renders_real_content_under_the_strip(self, arc_run: _ArcRun) -> None:
        """M4 (contract §3/§8): the topology pane is REAL now — at its
        teaching beat the center region shows the pane's own titled
        surface (the 3D lane's title bar), never the retired
        'not yet ported' fence."""
        frame = arc_run.frames[arc_run.frame_index["learn_the_topology_pane"]]
        assert "topology pane — not yet ported" not in frame, (
            "the retired topology fence is back — the real pane regressed"
        )
        assert "topology — " in frame, (
            "the topology pane's own titled surface is not visible under the strip"
        )
        # CONTENT pin (verify-panel BLOCKER remediation): the live truth
        # today is the honest-absence line — the engine has no
        # community_memberships producer, so the hypergraph is honestly
        # empty. THE DAY a membership producer lands, this assertion goes
        # red: that is the feature-went-live announcement, and the pin
        # then flips to asserting real braille content.
        assert "no community hyperedges attributed" in frame, (
            "the topology pane must render the honest-absence line (or, once "
            "a membership producer exists, real hypergraph content) — a blank "
            "interior is the certified-blank-golden class, never acceptable"
        )


class TestRotateSmoke:
    """Task 36's live rotate smoke, made durable (contract §9.9 adjustment:
    the HYPERGRAPH is honestly starved, so the rotating subject is the
    contradiction FIELD SURFACE — the one 3D lane with real data today).

    Drives the real engine through its own short scripted flow: mint →
    bind → topology pane → surface mode → two camera steps. Pins that the
    surface renders REAL braille content and that a camera step actually
    changes the projection — a rotation that renders identical frames
    would mean the camera or the surface died silently.
    """

    def test_field_surface_rotates_under_camera_keys(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        host, _store = _build_harness(tmp_path_factory.mktemp("rotate_smoke_vault"))
        config = json.dumps(
            {
                "campaign_id": "",
                "campaign_name": "Lobby",
                "render_tier": "glyph",
                "tutorial_enabled": False,
                "narrator_enabled": False,
                "headless": True,
                "headless_size": list(_PILOT_SIZE),
                "script": [
                    {"key": "n"},
                    {"key": "enter"},
                    {"key": "enter"},
                    # Tick once first: at T+0 the surface honestly reports
                    # 'no field values recorded for any class yet' (its own
                    # advice is 'advance a tick') — the smoke wants the
                    # populated surface, not the absence arm.
                    {"key": "t"},
                    {"key": "4"},  # topology pane (3D hypergraph default)
                    {"key": "s"},  # hypergraph -> field surface
                    {"key": "right"},  # camera ry +15 deg
                    {"key": "up"},  # camera rx -10 deg
                ],
            }
        )
        with mock.patch("babylon.tui.campaign_menu.uuid4", return_value=_PINNED_CAMPAIGN_ID):
            transcript = json.loads(babylon_tui.run(host, config))
        frames = transcript["frames"]
        surface = frames[-3]  # after 's', before any camera step
        assert "UNREADABLE" not in surface, "field surface rendered a loud failure"
        assert any("⠀" <= ch <= "⣿" for ch in surface), (
            "the field surface must render real braille content — the live "
            "engine HAS contradiction-field data (unlike the starved "
            "hypergraph); an empty surface here is a regression, not absence"
        )
        assert frames[-2] != frames[-3], "ry step did not change the projection"
        assert frames[-1] != frames[-2], "rx step did not change the projection"


# --------------------------------------------------------------------------- #
# Tier 4 (contract §5): the transcript artifact — determinism + the golden. #
# --------------------------------------------------------------------------- #

#: The plan's exact committed-golden path (contract §5 tier 4) — NOT
#: ``tests/baselines/**``, so no ``Baselines: blessed(...)`` ceremony
#: applies (CLAUDE.md §6.5's ceremony gate is scoped to that directory
#: alone).
_TRANSCRIPT_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "transcripts" / "wayne_opening_arc.json"
)
_REGEN_ENV_VAR: Final[str] = "BABYLON_REGEN_TRANSCRIPT"


class TestTranscriptArtifact:
    """The tier-4 transcript artifact: determinism, then the committed golden."""

    def test_two_independent_runs_produce_a_byte_identical_transcript(self, tmp_path: Path) -> None:
        """Deterministic under narrator-OFF, Wayne's fixed seed, and the
        pinned mint id: two INDEPENDENTLY-booted runs (fresh store,
        catalog, and vault each — deliberately NOT the shared ``arc_run``
        fixture) must produce a byte-identical transcript. Transcript
        drift IS behavior drift (the pilot's own doctrine, ported)."""
        run_a = _run_full_arc(tmp_path / "vault-a")
        run_b = _run_full_arc(tmp_path / "vault-b")
        transcript_a = json.dumps(_transcript_payload(run_a), indent=2)
        transcript_b = json.dumps(_transcript_payload(run_b), indent=2)
        assert transcript_a, "the transcript must not be empty"
        assert transcript_a == transcript_b

    def test_transcript_matches_the_committed_golden_or_regenerates(self, arc_run: _ArcRun) -> None:
        """Byte-equality against the committed golden
        (``tests/unit/tui/transcripts/wayne_opening_arc.json``) — a build
        BYPRODUCT, regenerate-freely, no ceremony. Set
        ``BABYLON_REGEN_TRANSCRIPT=1`` to (re)write it instead of asserting
        against it."""
        serialized = json.dumps(_transcript_payload(arc_run), indent=2) + "\n"
        if os.environ.get(_REGEN_ENV_VAR) == "1":
            _TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
            _TRANSCRIPT_PATH.write_text(serialized)
            return
        if not _TRANSCRIPT_PATH.exists():
            pytest.fail(
                f"no committed transcript golden at {_TRANSCRIPT_PATH} — regenerate via "
                f"`{_REGEN_ENV_VAR}=1 mise run test:q -- "
                f"tests/unit/tui/test_tutorial_pilot_rs.py` and commit the result"
            )
        assert serialized == _TRANSCRIPT_PATH.read_text()
