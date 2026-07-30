"""The client contract — the durable seam every terminal client renders through.

Extracted VERBATIM from ``babylon.tui.app`` (and the tutorial protocols from
``babylon.tui.tutorial_overlay``) at the M7 cutover decoupling
(``docs/superpowers/specs/2026-07-28-m7-cutover-contracts.md`` §4): the
Rust/Ratatui client's host (:mod:`babylon.tui.host`), the composition root
(:mod:`babylon.cli.play`) and the parity harness all speak these Protocols,
so they must survive the Textual estate's deletion — this module is
deliberately textual-free (the ceremony's acceptance check imports
:mod:`babylon.tui.host` and asserts no ``textual`` module loads).

The seam philosophy (unchanged from its ``app.py`` birth): structural
Protocols and ``Callable`` aliases only — :class:`~babylon.game.session.
GameSession` satisfies :class:`CampaignHandle` without either module
importing the other (the WO-37 trick; ``babylon.tui`` never imports
``babylon.game``/``babylon.engine``/``babylon.persistence`` at runtime,
enforced by the import-linter contract).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence  # noqa: TC003
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

from babylon.projection.endgame import EndgameStatus  # noqa: TC001
from babylon.projection.verbs.view_models import VerbPlateView  # noqa: TC001
from babylon.projection.view_models import (  # noqa: TC001
    EconomyView,
    FieldStateView,
    NationalTrendView,
    ProjectionRecord,
)
from babylon.tui.chronicle import ChronicleEvent  # noqa: TC001

if TYPE_CHECKING:
    # Type-only: the tui layer never imports persistence at runtime (the
    # import-linter contract); the aggregate row model appears here solely
    # so CampaignHandle can NAME the shape the composition root hands over.
    from babylon.persistence.postgres_aggregation import NationalValueAggregate

__all__ = [
    "CampaignHandle",
    "CampaignLoader",
    "DriverFactory",
    "PacedDriverHandle",
    "TickOutcome",
    "TutorialProgress",
    "TutorialProgressFactory",
    "TutorialStepView",
]


@runtime_checkable
class TickOutcome(Protocol):
    """Structural shape of one :meth:`CampaignHandle.advance_tick` result.

    :class:`~babylon.game.session.TickAdvanceResult` satisfies this
    structurally (it also carries ``world``/``events``/
    ``replay_identity_hash``, which this seam doesn't need) — the WO-37 trick,
    no import in either direction.
    """

    @property
    def tick(self) -> int:
        """The committed tick just reached."""
        ...

    @property
    def paused(self) -> bool:
        """Whether the pacing driver's pause predicate fired this tick."""
        ...

    @property
    def chronicle(self) -> tuple[ChronicleEvent, ...]:
        """This tick's chronicle events, chronological (Program 24 P3).

        :attr:`~babylon.game.session.TickAdvanceResult.chronicle` satisfies this
        structurally — the same WO-37 trick this Protocol already uses for
        ``tick``/``paused``. :meth:`ArchiveApp._refresh_chronicle` appends this
        ONE tick's events onto its own running history; this seam never carries
        more than one tick's worth at a time.
        """
        ...


@runtime_checkable
class CampaignHandle(Protocol):
    """Structural seam: one booted/resumed live campaign (Program v1.0.0 Unit C2).

    :class:`~babylon.game.session.GameSession` satisfies this without
    either module importing the other: ``babylon.tui`` never imports
    ``babylon.game``/``babylon.engine``/``babylon.persistence`` (the
    import-linter contract); the composition root hands :class:`ArchiveApp`
    a real ``GameSession`` where this seam expects one.
    """

    @property
    def session_id(self) -> UUID:
        """The campaign's identity — the same UUID the lobby chose."""
        ...

    @property
    def tick(self) -> int:
        """The last committed tick."""
        ...

    def read_page(self, subject: str) -> str | None:
        """Read one baked vault page for this campaign (see :data:`PageSource`)."""
        ...

    def known_subjects(self) -> frozenset[str]:
        """Every subject id this campaign's vault has baked so far (Unit U1).

        Replaces the demo :data:`KNOWN_ENTITIES` fixture set once a live
        campaign boots — :meth:`ArchiveApp._on_campaign_chosen` reads this
        to rebuild :attr:`ArchiveApp.known_entities`/``_resolver`` against
        the REAL vault instead of the built-in fixture set, so wikilink
        classification and the command palette speak the live campaign's
        own baked pages.
        """
        ...

    def dashboard_view(self) -> EconomyView | None:
        """This campaign's live economy dashboard projection (Program 24 P2).

        Computed HOST-SIDE by the composition root
        (:func:`~babylon.projection.economy.project_economy`, called from
        :mod:`babylon.game.session` — never from ``babylon.tui``:
        ``project_economy`` needs the live graph/world this Protocol
        deliberately never exposes, and calling it from this module would be
        a projection-purity violation, the same import-linter contract
        :attr:`known_subjects`'s docstring already names). Handed to
        :class:`~babylon.tui.shell.views.dashboard_view.DashboardView` as a
        pure, frozen pydantic view model — the TUI only ever renders it,
        never builds it.

        :returns: the freshly-projected :class:`EconomyView`, or ``None``
            when this composition root chose not to wire a live projection
            (e.g. a test double standing in for a campaign with no vault) —
            :meth:`ArchiveApp._refresh_dashboard` then leaves the pane's
            existing honest-absence fence untouched (Constitution III.11),
            never a blank or fabricated repaint.
        """
        ...

    def subject_view(self, subject_id: str) -> ProjectionRecord | None:
        """One pinnable subject's live dossier view-model (shell-interconnect,
        "live-subject-view").

        Computed HOST-SIDE by the composition root
        (:meth:`~babylon.game.session.GameSession.subject_view`, dispatching
        ``subject_id``'s ``"<kind>/<entity_id>"`` shape onto whichever of the
        ten Lane P ``project_<kind>`` functions the kind names — never from
        ``babylon.tui``: every one of those functions needs the live
        graph/world this Protocol deliberately never exposes, the same
        projection-purity reasoning :attr:`dashboard_view`'s docstring
        already names). Handed to :func:`~babylon.tui.peek.peek` as a pure,
        frozen pydantic view model — the right rail's watchlist only ever
        renders it, never builds it.

        :param subject_id: the vault-relative subject id a pinned watchlist
            row names (e.g. ``"county/26163"``).
        :returns: the freshly-projected :data:`~babylon.projection.
            view_models.ProjectionRecord`, or ``None`` when this composition
            root chose not to wire a live projection (e.g. a test double), OR
            ``subject_id``'s kind names none of the ten pinnable Lane P
            kinds, OR (``community`` only) names no real
            :class:`~babylon.models.enums.CommunityType` member —
            :meth:`ArchiveApp._refresh_watchlist` then renders its own
            already-established "no longer resolvable" row (Constitution
            III.11), never a crash or a silently dropped pin.
        """
        ...

    def endgame_status(self) -> EndgameStatus | None:
        """This campaign's live endgame-progress HUD status (Program 24 P4).

        Computed HOST-SIDE by the composition root
        (:meth:`~babylon.game.session.GameSession.endgame_status`, folding
        its own :class:`~babylon.engine.observers.endgame_detector.
        EndgameDetector` via :func:`~babylon.projection.endgame.
        endgame_status` — never from ``babylon.tui``: the detector needs the
        live world/graph this Protocol deliberately never exposes, the same
        projection-purity reasoning :attr:`dashboard_view`'s docstring
        already names). Handed to
        :class:`~babylon.tui.shell.views.dashboard_view.DashboardView` as a
        pure, frozen pydantic view model — the TUI only ever renders it,
        never computes it.

        :returns: the freshly-folded :class:`~babylon.projection.endgame.
            EndgameStatus`, or ``None`` when this composition root chose not
            to wire a live projection — :meth:`ArchiveApp._refresh_dashboard`
            then leaves the HUD's existing honest-absence fence untouched
            (Constitution III.11), same as :attr:`dashboard_view`.
        """
        ...

    def verb_plate_view(self) -> VerbPlateView | None:
        """This campaign's live verb-plate projection (Program 24 P5).

        Computed HOST-SIDE by the composition root
        (:func:`~babylon.projection.verbs.plate.build_verb_plate`, called from
        :meth:`~babylon.game.session.GameSession.verb_plate_view` — never
        from ``babylon.tui``: ``build_verb_plate`` needs the live graph this
        Protocol deliberately never exposes, the same projection-purity
        reasoning :attr:`dashboard_view`'s docstring already names). Handed
        to :func:`~babylon.tui.verb_plate.render_verb_plate` as a pure,
        frozen pydantic view model — the TUI only ever renders it, never
        builds it.

        :returns: the freshly-built :class:`~babylon.projection.verbs.
            view_models.VerbPlateView`, or ``None`` when this composition
            root chose not to wire a live plate (e.g. a test double, or a
            campaign whose graph carries no player-org pointer) —
            :meth:`ArchiveApp._refresh_action_bar` then leaves the bar's
            existing honest-absence fence untouched (Constitution III.11),
            never a blank or fabricated repaint.
        """
        ...

    def topology_view(self, kind: str, focus: str | None = None) -> dict[str, object] | None:
        """This campaign's live topology surface, as a hand-built envelope dict (Task 30, M4 §1).

        Computed HOST-SIDE by the composition root
        (:meth:`~babylon.game.session.GameSession.topology_view`, fanning
        one ``WorldState.from_graph`` out through :func:`~babylon.projection.
        topology.paoh.paoh_ordering`/:func:`~babylon.projection.topology.
        incidence.incidence_ordering`/:func:`~babylon.projection.topology.
        incidence.adjacency_ordering`/:func:`~babylon.projection.topology.
        levi.levi_ego_tree` plus :func:`~babylon.projection.topology.layout.
        bipartite_shell_layout` — never from ``babylon.tui``: every one of
        those needs the live graph/world this Protocol deliberately never
        exposes, the same projection-purity reasoning :attr:`dashboard_view`'s
        docstring already names). Handed to
        :meth:`~babylon.tui.host.RustClientHost.topology_json` as an already
        JSON-serializable ``dict``, never a shared pydantic model (the
        contract's own "hand-built dicts, deliberately no shared
        discriminated union" ruling — an ``egotree`` envelope is not a
        :data:`~babylon.projection.view_models.ProjectionRecord` member).

        :param kind: one of ``"paoh"``, ``"egotree"``, ``"incidence"``,
            ``"adjacency"``.
        :param focus: the ego-tree root id — REQUIRED for ``kind="egotree"``,
            IGNORED for the other three kinds.
        :returns: the resolved kind's envelope, or ``None`` when this
            composition root chose not to wire a live projection (a test
            double), OR ``kind == "egotree"`` and ``focus`` is ``None``/names
            no resolvable root/resolves to zero bipartite edges — an honest
            absence (Constitution III.11), never a fabricated tree or a
            propagated error for a stale post-tick focus.
        """
        ...

    def choropleth_view(self, tier: str, lens: str) -> dict[str, object] | None:
        """This campaign's live map choropleth surface, as a hand-built envelope dict (Task 37, M5 \u00a71).

        Computed HOST-SIDE by the composition root
        (:meth:`~babylon.game.session.GameSession.choropleth_view`, folding
        the graph's TickDynamics stamps through the M5 tier/lens helpers \u2014
        never from ``babylon.tui``: the fold needs the live graph, the
        epistemic-horizon defines and the county-WKT seam, none of which
        this Protocol exposes; the same projection-purity reasoning every
        sibling member's docstring names). Handed to
        :meth:`~babylon.tui.host.RustClientHost.choropleth_json` as an
        already JSON-serializable ``dict`` (``inf`` pre-encoded as the
        string ``"inf"`` \u2014 JSON has no Infinity).

        :param tier: ``"county"``, ``"state"``, or ``"ea"``.
        :param lens: ``"value"``, ``"tension"``, or ``"fog"``.
        :returns: the envelope, or ``None`` when this composition root
            chose not to wire a live projection (a test double), OR the
            graph carries no county-bearing territory, OR ``tier="ea"``
            (no producer exists) \u2014 honest absence (Constitution III.11).
        """
        ...

    def trend_view(self, last_n: int) -> tuple[NationalTrendView, ...]:
        """This campaign's national trend window, oldest\u2192newest (M6 Task 41).

        Computed HOST-SIDE by the composition root
        (:meth:`~babylon.game.session.GameSession.trend_view`, reading the
        ``v_national_trend`` declared view through the store seam \u2014 never
        from ``babylon.tui``: the read needs a live Postgres session this
        Protocol deliberately does not expose; the same projection-purity
        reasoning every sibling member's docstring names).

        :param last_n: how many most-recent ticks to window.
        :returns: chart-ready rows in ascending tick order; empty before
            the first committed tick, or when this composition root chose
            not to wire a live read at all (a test double) \u2014 honest
            absence either way.
        :raises ValueError: on a non-positive ``last_n`` \u2014 LOUD, never
            laundered into an empty window.
        """
        ...

    def national_value_snapshot(self) -> NationalValueAggregate | None:
        """The latest national c/v/s/k value-composition row (M6 Task 41).

        Computed HOST-SIDE by the composition root
        (:meth:`~babylon.game.session.GameSession.national_value_snapshot`,
        reading ``v_national_value_aggregate`` through the store seam \u2014
        the sums live in the hex ledger, not the graph, spec-089). The
        row's own ``tick`` is the staleness disclosure: the hex ledger is
        written at hydration and never per-tick.

        :returns: the aggregate row, or ``None`` when no hex hydration ran
            (or this composition root wired no live read) \u2014 honest absence.
        """
        ...

    def field_state_view(self) -> FieldStateView | None:
        """This campaign's live field-state dossier (Task 30, M4 §2 — the Weather Layer).

        Computed HOST-SIDE by the composition root
        (:meth:`~babylon.game.session.GameSession.field_state_view`, calling
        :func:`~babylon.projection.field_state.project_field_state` DIRECTLY
        on the live graph — never through ``WorldState.from_graph``, which
        drops the field-stack attrs this dossier needs; never from
        ``babylon.tui``, the same projection-purity reasoning
        :attr:`dashboard_view`'s docstring already names). Handed to
        :meth:`~babylon.tui.host.RustClientHost.field_state_json` as a pure,
        frozen pydantic view model — the host only ever serializes it, never
        builds it.

        :returns: the freshly-projected :class:`~babylon.projection.
            view_models.FieldStateView`, or ``None`` when this composition
            root chose not to wire a live projection (e.g. a test double) —
            :meth:`~babylon.tui.host.RustClientHost.field_state_json` then
            returns the literal ``"null"`` (Constitution III.11).
        """
        ...

    def issue_verb(
        self,
        action_id: str,
        *,
        target_id: str | None = None,
        target_community: str | None = None,
    ) -> int:
        """Issue one player verb through the registry-gated write path (Program 24 P5).

        The action bar's real write-path seam — the FIRST time the player
        can act on the world from this shell. Computed HOST-SIDE (
        :meth:`~babylon.game.session.GameSession.issue_verb`, which composes
        :func:`~babylon.game.actions.player_driver.issue_action`'s
        agent-type/``LIVE``-status gate with :func:`~babylon.projection.
        verbs.submit.submit_verb`'s own affordability gate) — never from
        ``babylon.tui``: only primitives (``str`` in, ``int`` out, or a
        builtin exception) cross this boundary, the same deliberately narrow
        crossing :class:`PacedDriverHandle` already established, so this
        module never needs to import ``ActionNotPermitted``/``ActionNotLive``
        by name.

        Unit "verb-targeting" (shell-interconnect) widens this seam with two
        optional, keyword-only primitives — still only ``str``/``None`` cross
        the boundary. :meth:`ArchiveApp.action_issue_verb` supplies
        ``target_id`` from :attr:`ArchiveApp.nav`'s own current subject
        (:func:`_honest_target_id`) ONLY when it is honestly a member of the
        row's own :attr:`~babylon.projection.verbs.view_models.VerbRow.
        candidate_target_ids` — never invented, never dropped when it IS
        honestly available. ``target_community`` is threaded for parity with
        ``issue_action``'s own signature; no caller supplies a real one yet.

        :param action_id: one of the nine canonical Article V verbs.
        :param target_id: an explicit target node id, or ``None`` to leave
            the untargeted self-target fallback exactly as it was before
            this unit.
        :param target_community: an explicit target community id, or
            ``None`` (no production caller supplies a real one yet).
        :raises RuntimeError: no player org to act as, the organizer may not
            issue ``action_id``, or it is a STUB with no wired effect yet.
        :raises KeyError: ``action_id`` names no registered action at all.
        :raises ValueError: a non-canonical verb, or the org cannot afford it.
        :returns: the queued turn's integer id.
        """
        ...

    def advance_tick(self) -> TickOutcome:
        """Resolve exactly one further tick."""
        ...


CampaignLoader = Callable[[UUID], CampaignHandle]
"""The lobby's boot-or-resume seam: a chosen campaign UUID -> a live
:class:`CampaignHandle`. Fulfilled for real by :mod:`babylon.game.session`'s
composition-root factories (:func:`~babylon.game.session.
create_new_campaign` / :func:`~babylon.game.session.resume_campaign`) in
the ``babylon play`` composition root — ``babylon.tui`` calls only through
this seam, never those factories directly."""


@runtime_checkable
class PacedDriverHandle(Protocol):
    """Structural seam: the paced tick driver (Program v1.0.0 Unit C3).

    :class:`~babylon.game.pacing.PacedTickDriver` satisfies this without
    ``babylon.tui`` importing ``babylon.game``/``babylon.engine`` — the
    same WO-37 trick :class:`CampaignHandle` already uses, one layer up.
    Deliberately narrow: only primitives (``bool``/``str``/``None``) cross
    this boundary, so the UI never needs
    :class:`~babylon.kernel.event_bus.Event` or
    :class:`~babylon.models.enums.events.GameOutcome` to render a status
    line (:attr:`~babylon.game.pacing.PacedTickDriver.pause_summary` /
    ``lock_reason`` already format themselves; a ``GameOutcome`` IS a
    ``str`` — it's a ``StrEnum`` — so it satisfies ``lock_reason: str |
    None`` here with no cast).
    """

    @property
    def locked(self) -> bool:
        """``True`` once the endgame lock has engaged — permanent."""
        ...

    @property
    def lock_reason(self) -> str | None:
        """The recognized terminal outcome's name, or ``None`` while unlocked."""
        ...

    @property
    def awaiting_ack(self) -> bool:
        """``True`` while a tick's autopause is unacknowledged."""
        ...

    @property
    def busy(self) -> bool:
        """``True`` while a previous advance on this SAME driver is still
        in flight — a Textual worker's cancellation cannot actually stop
        an executor thread already running underneath it (see
        :mod:`babylon.game.pacing`'s Re-entrancy note), so the UI must
        check this BEFORE starting a second overlapping advance rather
        than relying on ``@work``'s own ``exclusive`` cancellation."""
        ...

    @property
    def pause_summary(self) -> str | None:
        """The pending autopause's UI-safe one-liner, or ``None``."""
        ...

    def advance_once(self) -> TickOutcome:
        """Resolve exactly one further tick (the Unit C2 binding's seam)."""
        ...

    def run_until_paused(self) -> Sequence[TickOutcome]:
        """Advance repeatedly until an autopause or the endgame lock."""
        ...

    def acknowledge_pause(self) -> None:
        """Clear a pending autopause, permitting the next advance."""
        ...


DriverFactory = Callable[[CampaignHandle], PacedDriverHandle]
"""The booted campaign's pacing-driver seam: a live :class:`CampaignHandle`
-> a :class:`PacedDriverHandle` wrapping it. Fulfilled for real by
:func:`~babylon.game.pacing.paced_driver_for_session` in the ``babylon
play`` composition root (the SAME concrete object satisfies both
``CampaignHandle`` and whatever ``paced_driver_for_session`` actually
needs — the composition root holds the real
:class:`~babylon.game.session.GameSession`, this module only ever sees it
through the narrower seam types)."""


@runtime_checkable
class TutorialStepView(Protocol):
    """Structural shape of one rendered step (:class:`~babylon.game.tutorial.
    TutorialStep` satisfies this without either module importing the other).

    Deliberately narrow: only the two DERIVED rendering properties the
    overlay actually paints, never the raw ``given``/``when``/``then``
    fields directly — rendering through the model's own properties (rather
    than reassembling the fields here) is what keeps this widget's output a
    verbatim, zero-copy-divergence render of U1's own rendering contract.
    """

    @property
    def scenario_name(self) -> str:
        """The step's one-sentence summary (the developer-docs title)."""
        ...

    @property
    def overlay_text(self) -> str:
        """The GIVEN/WHEN/THEN block, the SAME fields as :attr:`scenario_name`."""
        ...


@runtime_checkable
class TutorialProgress(Protocol):
    """The predicate-evaluation seam: is step ``step_index`` complete RIGHT
    NOW against the live campaign?

    Fulfilled for real by :class:`~babylon.game.tutorial_runtime.
    TutorialRuntimeProgress` (the composition root's concrete evaluator,
    reading the live campaign's tick, the paced driver's ``awaiting_ack``,
    and the nav shell's current subject) — never implemented in this
    module, which only ever calls through this seam.
    """

    def is_step_complete(self, step_index: int) -> bool:
        """Whether the step at ``step_index`` currently holds.

        :param step_index: an index into the SAME step sequence the caller
            constructed this evaluator with — the overlay and its evaluator
            must always share one common, identically-ordered step list.
        :returns: ``True`` iff that step's completion predicate is satisfied
            by the live campaign's CURRENT state.
        """
        ...


TutorialProgressFactory = Callable[
    [
        CampaignHandle,
        "PacedDriverHandle | None",
        Callable[[], "str | None"],
        Callable[[], "str | None"],
        Callable[[str], bool],
        Callable[[str], bool],
    ],
    "TutorialProgress | None",
]
"""The booted campaign's tutorial-progress seam (Program v1.0.0 T6, Unit U4;
extended by Program 24 P8, "the tutorial learns the shell"; widened again by
the M3 ``VerbIssued`` defect fix, ``docs/superpowers/specs/
2026-07-27-m3-tutorial-contracts.md`` §0) — one layer up from
:data:`DriverFactory`, same shape. Takes the just-booted
:class:`CampaignHandle`, the just-built :class:`PacedDriverHandle` (or
``None`` when no ``driver_factory`` was wired), a zero-arg callable reading
:attr:`ArchiveApp.nav`'s current subject at call time, a zero-arg callable
reading the hybrid shell's ``ContentSwitcher`` ``.current`` pane at call time
(P8), a one-arg callable reading whether a given subject id currently
holds a watchlist pin at call time (P8), and — the M3 addition — a one-arg
``was_verb_issued`` callable answering whether a named verb/binding action
has been dispatched at least once this session
(:attr:`ArchiveApp._verbs_issued`'s own ``__contains__`` — the dispatch-proof
seam :class:`~babylon.game.tutorial_runtime.TutorialRuntimeProgress` needs to
resolve a :class:`~babylon.game.tutorial.VerbIssued` completion without
instrumenting production dispatch itself); returns ``None`` to mean "the
tutorial should not show for this campaign" — the composition root's own
new-vs-resumed gating decision (see ``babylon.cli.play``'s own docstring for
the honest first-session heuristic it uses), in which case
:meth:`ArchiveApp._on_briefing_dismissed` never mounts a
:class:`~babylon.tui.tutorial_overlay.TutorialOverlay` at all."""
