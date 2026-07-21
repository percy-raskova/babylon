"""The briefing dossier — the Cadre Council's operation briefing (WO-35).

Port of the legacy web bridge's two pure read-side helpers into the
projection layer: :func:`operation_codename` (``web/game/codenames.py``,
spec-116 FR-116-3) and :func:`journal_objectives`, a port of
``EngineBridge.get_journal_objectives`` (spec-095 FR-095-03 + spec-116 Task
4). Together they build the page a fresh campaign lands on before the first
tick — the operation's name, the five recognized patterns the century can
settle into, and the fixed campaign horizon (owner ruling 2026-07-17,
spec-116).

**NET-NEW page** (Program 24 P2 WO-35): no design-brief S-item covers a
briefing dossier — the design canon's own governance list (§9's item 4)
flags a DESIGN_BIBLE "wiki-page anatomy" section as not yet written. Per the
WO-35 ruling this module is built from the ratified county page anatomy
(:mod:`babylon.projection.county`'s field-producer-table + honest-absence
discipline) plus DESIGN_BIBLE §9b's chrome vocabulary cited for a *later*
fidelity pass — a Jinja markdown scaffold has no CSS layer to carry §9b's
crimson/gold plate treatment itself; that lands when the TUI widget renders
this page.

**One producer per field:**

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``codename``
     - :func:`operation_codename` — a pure function of the session UUID
       (spec-116 FR-116-3; ``web/game/codenames.py``'s 32x32 curated word
       lists, ported verbatim). Deliberately NOT derived from ``rng_seed``
       (see that module's docstring: the seed column defaults to 0 for
       every pre-existing session, which would collide every game).
   * - ``objectives``
     - :func:`journal_objectives` — port of
       ``EngineBridge.get_journal_objectives``'s 5-axis fold; each
       objective's ``progress`` is honestly ``0.0`` when no
       ``endgame_progress`` snapshot exists yet — not a fabricated default,
       the ported helper's own documented ruling that zero progress is the
       genuine tick-0 reading.
   * - ``horizon_years`` / ``horizon_ticks``
     - :func:`~babylon.projection.endgame.campaign_horizon_tick` (WO-39;
       reused verbatim rather than recomputed) over
       ``GameDefines.endgame.campaign_horizon_years`` /
       ``GameDefines.timescale.weeks_per_year``.

Absence discipline (Constitution III.11): unlike
:class:`~babylon.projection.view_models.CountyView`, no field on
:class:`BriefingView` is an honestly-*absent* quantity. The codename is a
pure function of an identity that always exists; the horizon is a
coefficient that is always configured; and a pattern's progress is
honestly zero rather than unknown before any tick has run (see
``journal_objectives``'s docstring). There is accordingly no ``None``
anywhere in this model, and the vault template
(``vault/templates/briefing.md.j2``) carries no ``{absence}`` block.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.config.defines import GameDefines
from babylon.models.enums.events import GameOutcome
from babylon.models.types import Probability
from babylon.projection.endgame import campaign_horizon_tick

__all__ = [
    "WIN_OBJECTIVE_ID",
    "BriefingObjective",
    "BriefingView",
    "journal_objectives",
    "operation_codename",
    "project_briefing",
]

#: Left word — evocative modifier (indexed by UUID bytes 0-1). Verbatim port
#: of ``web/game/codenames.py`` (spec-116 FR-116-3): a curated word list is
#: the deterministic contract itself — do not reorder or re-author entries,
#: doing so would silently rename every already-created campaign.
_LEFT: Final[tuple[str, ...]] = (
    "CRIMSON",
    "IRON",
    "EMBER",
    "GRANITE",
    "SCARLET",
    "HOLLOW",
    "SILENT",
    "NORTHERN",
    "RUSTED",
    "VELVET",
    "COPPER",
    "MIDNIGHT",
    "BURNING",
    "FALLOW",
    "WINTER",
    "SALT",
    "ASH",
    "LONG",
    "BROKEN",
    "PATIENT",
    "RED",
    "STONE",
    "HUNGRY",
    "DISTANT",
    "EARLY",
    "LAST",
    "SOVEREIGN",
    "UNION",
    "HARBOR",
    "SIGNAL",
    "QUIET",
    "FERAL",
)

#: Right word — concrete noun (indexed by UUID bytes 2-3). See :data:`_LEFT`.
_RIGHT: Final[tuple[str, ...]] = (
    "HARVEST",
    "DAWN",
    "FURNACE",
    "ANVIL",
    "RIVER",
    "LANTERN",
    "THRESHOLD",
    "SPINDLE",
    "GRANARY",
    "PICKET",
    "TELEGRAPH",
    "FOUNDRY",
    "ORCHARD",
    "CROSSING",
    "EMBANKMENT",
    "TURBINE",
    "QUARRY",
    "SICKLE",
    "BALLAST",
    "MERIDIAN",
    "WATCHTOWER",
    "CAUSEWAY",
    "DYNAMO",
    "ARCHIVE",
    "BULWARK",
    "TRELLIS",
    "COMPASS",
    "VIADUCT",
    "SEMAPHORE",
    "TANNERY",
    "MILLSTONE",
    "ACCORD",
)


def operation_codename(session_id: UUID) -> str:
    """Derive a stable two-word operation codename from a session UUID.

    Verbatim port of ``web/game/codenames.py::operation_codename`` — the
    same session UUID always renders the same name, with byte-stable
    indices (big-endian, two bytes per list) so the mapping never drifts
    across processes or platforms.

    :param session_id: The game session's primary key.
    :returns: ``"LEFT RIGHT"`` in uppercase, e.g. ``"CRIMSON HARVEST"`` —
        matches ``lobby-briefing.spec.ts``'s
        ``/^OPERATION [A-Z]+ [A-Z]+$/`` acceptance once prefixed with
        ``"OPERATION "`` (the vault template's job, not this function's).
    """
    left_index = int.from_bytes(session_id.bytes[0:2], "big") % len(_LEFT)
    right_index = int.from_bytes(session_id.bytes[2:4], "big") % len(_RIGHT)
    return f"{_LEFT[left_index]} {_RIGHT[right_index]}"


#: The win condition among the five recognized patterns (frontend parity:
#: ``BriefingRoute.tsx``'s ``WIN_OBJECTIVE_ID`` constant).
WIN_OBJECTIVE_ID: Final[str] = "revolution"

#: ``(id, title, description, category, axis_key)`` — verbatim copy of the
#: five dicts ``EngineBridge.get_journal_objectives`` builds (spec-095
#: FR-095-03 + spec-116 Task 4). Order is the win-condition-first canonical
#: order both the frontend and ``first-session.spec.ts`` pin; ``category``
#: differs from ``id`` for three rows (matches the source verbatim — e.g.
#: ``ecological_collapse`` reports under the shorter ``"collapse"``
#: category for :func:`_objective_status`).
_OBJECTIVE_DESCRIPTORS: Final[tuple[tuple[str, str, str, str, str], ...]] = (
    (
        "revolution",
        "Revolutionary Victory",
        "Build mass class consciousness and solidarity edges to overthrow the empire.",
        "revolution",
        "revolutionary_victory",
    ),
    (
        "ecological_collapse",
        "Ecological Collapse",
        "Biocapacity depletion forces a terminal retreat from extraction.",
        "collapse",
        "ecological_collapse",
    ),
    (
        "fascist_consolidation",
        "Fascist Consolidation",
        "False-consciousness bloc achieves a sovereign grip on the state.",
        "fascist",
        "fascist_consolidation",
    ),
    (
        "red_ogv",
        "Red OGV Trap",
        "Settler-socialist formation captures the movement without abolishing empire.",
        "red_ogv",
        "red_ogv",
    ),
    (
        "fragmented_collapse",
        "Fragmented Collapse",
        "Balkanization — sovereign fragmentation outpaces solidarity.",
        "fragmented",
        "fragmented_collapse",
    ),
)

#: ``category`` -> the :class:`GameOutcome` whose recognition completes it.
#: Verbatim port of ``EngineBridge._objective_status``'s per-category match.
_STATUS_OUTCOME_BY_CATEGORY: Final[dict[str, GameOutcome]] = {
    "revolution": GameOutcome.REVOLUTIONARY_VICTORY,
    "collapse": GameOutcome.ECOLOGICAL_COLLAPSE,
    "fascist": GameOutcome.FASCIST_CONSOLIDATION,
    "red_ogv": GameOutcome.RED_OGV,
    "fragmented": GameOutcome.FRAGMENTED_COLLAPSE,
}

ObjectiveStatus = Literal["active", "complete", "failed"]


def _axis_progress(axes: Mapping[str, Any], axis_key: str) -> float:
    """Read one axis's progress, honestly ``0.0`` when unset.

    Verbatim port of ``EngineBridge.get_journal_objectives``'s local
    ``_axis_progress`` helper: a missing or non-numeric axis value reads as
    ``0.0`` — the genuine "no progress accumulated yet" reading, not a
    fabricated placeholder for a quantity the engine withheld.

    :param axes: The persisted ``endgame_progress["axes"]`` block (or an
        empty mapping before any tick has run).
    :param axis_key: The ``EndgameDetector`` axis name to read.
    :returns: The axis's progress as a float, ``0.0`` if absent/non-numeric.
    """
    value = axes.get(axis_key, 0.0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _objective_status(category: str, outcome: GameOutcome | None) -> ObjectiveStatus:
    """Derive one objective's status from the currently-held terminal outcome.

    Verbatim port of ``EngineBridge._objective_status``: the objective whose
    category matches the held outcome is ``"complete"``; every other
    endgame-aligned objective is ``"failed"`` (its path lost); with no
    outcome held yet, every objective is ``"active"``.

    :param category: The objective's :data:`_STATUS_OUTCOME_BY_CATEGORY` key.
    :param outcome: The currently-held terminal outcome, or ``None``.
    :returns: One of ``"active"``, ``"complete"``, ``"failed"``.
    """
    if outcome is None:
        return "active"
    if _STATUS_OUTCOME_BY_CATEGORY.get(category) == outcome:
        return "complete"
    return "failed"


class BriefingObjective(BaseModel):
    """One of the five recognized patterns the century can settle into.

    :param id: Stable objective identifier (matches
        ``EngineBridge.get_journal_objectives``'s dict key exactly — the
        frontend's ``data-testid="briefing-pattern-{id}"`` depends on it).
    :param title: Player-facing pattern name.
    :param description: Player-facing one-sentence stakes description.
    :param progress: The axis's current reading in ``[0, 1]`` — honestly
        ``0.0`` before any tick has run (see :func:`_axis_progress`).
    :param status: ``"active"`` (no outcome held yet), ``"complete"`` (this
        pattern is the held outcome), or ``"failed"`` (a different pattern
        is held).
    :param category: The :data:`_STATUS_OUTCOME_BY_CATEGORY` key this
        objective reports its status under (equal to ``id`` for two of the
        five; the ported source's own naming, not renamed here).
    :param is_win_condition: ``True`` iff ``id == WIN_OBJECTIVE_ID`` —
        precomputed here so the template never repeats that string
        comparison (frontend parity: ``BriefingRoute.tsx``'s win badge).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    progress: Probability
    status: ObjectiveStatus
    category: str = Field(min_length=1)
    is_win_condition: bool


def journal_objectives(
    *,
    axes: Mapping[str, Any] | None = None,
    outcome: GameOutcome | None = None,
) -> tuple[BriefingObjective, ...]:
    """Build the five recognized-pattern rows.

    Port of ``EngineBridge.get_journal_objectives``'s objective list —
    everything except the graph/DB read that helper does to obtain
    ``axes``/``outcome`` in the first place, which the caller supplies
    (transport-neutral by construction, matching :func:`project_county`).

    :param axes: The persisted ``endgame_progress["axes"]`` block, or
        ``None`` before any tick has run — every axis then reads honestly
        ``0.0`` (see :func:`_axis_progress`).
    :param outcome: The currently-held terminal outcome, or ``None`` before
        one is recognized/locked.
    :returns: Exactly five :class:`BriefingObjective` rows, in the
        canonical win-condition-first order of :data:`_OBJECTIVE_DESCRIPTORS`.
    """
    resolved_axes: Mapping[str, Any] = axes if axes is not None else {}
    return tuple(
        BriefingObjective(
            id=objective_id,
            title=title,
            description=description,
            progress=_axis_progress(resolved_axes, axis_key),
            status=_objective_status(category, outcome),
            category=category,
            is_win_condition=(objective_id == WIN_OBJECTIVE_ID),
        )
        for objective_id, title, description, category, axis_key in _OBJECTIVE_DESCRIPTORS
    )


class BriefingView(BaseModel):
    """The Scenario Briefing dossier — the page a fresh campaign lands on.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly, not
    to swallow.

    :param kind: The discriminator literal ``"briefing"``.
    :param session_id: The campaign session UUID — the briefing's identity
        (spec-116 FR-116-3; briefing is not a graph node, the same
        not-a-node discipline :class:`~babylon.projection.view_models.CountyView`
        applies to county).
    :param verified_tick: The committed tick this dossier was projected
        from — ``0`` for a fresh campaign (before "Begin Operation"),
        matching ``lobby-briefing.spec.ts``'s post-create ``tick-value``
        assertion.
    :param codename: The two-word uppercase operation name (see
        :func:`operation_codename`); combined with the ``"OPERATION "``
        prefix at render time to match
        ``/^OPERATION [A-Z]+ [A-Z]+$/``.
    :param objectives: Exactly five :class:`BriefingObjective` rows (see
        :func:`journal_objectives`).
    :param win_objective_id: The id among :attr:`objectives` naming the win
        condition (equal to :data:`WIN_OBJECTIVE_ID`).
    :param horizon_years: The fixed campaign horizon in in-game years
        (``GameDefines.endgame.campaign_horizon_years``, default ``100``).
    :param horizon_ticks: The same horizon in weekly ticks
        (``horizon_years * weeks_per_year``, default ``5200``; see
        :func:`~babylon.projection.endgame.campaign_horizon_tick`).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["briefing"] = "briefing"
    session_id: UUID
    verified_tick: int = Field(ge=0)
    codename: str = Field(pattern=r"^[A-Z]+ [A-Z]+$")
    objectives: tuple[BriefingObjective, ...]
    win_objective_id: str = WIN_OBJECTIVE_ID
    horizon_years: int = Field(gt=0)
    horizon_ticks: int = Field(gt=0)

    @model_validator(mode="after")
    def _validate_five_objectives(self) -> BriefingView:
        """Require exactly five objectives — the fixed EndgameDetector axis count.

        :raises ValueError: if :attr:`objectives` does not have exactly 5
            entries — a malformed briefing is a bug, not a page that quietly
            renders fewer patterns than the century actually recognizes.
        :returns: The validated model (unchanged).
        """
        if len(self.objectives) != 5:
            msg = f"briefing must carry exactly 5 objectives (got {len(self.objectives)})"
            raise ValueError(msg)
        return self


def project_briefing(
    session_id: UUID,
    *,
    tick: int,
    defines: GameDefines,
    axes: Mapping[str, Any] | None = None,
    outcome: GameOutcome | None = None,
) -> BriefingView:
    """Project a campaign's Scenario Briefing dossier.

    :param session_id: The campaign session UUID.
    :param tick: The committed tick this dossier is projected from — ``0``
        for a fresh campaign, before "Begin Operation" starts play.
    :param defines: Coefficient source for the campaign horizon.
    :param axes: The persisted ``endgame_progress["axes"]`` block, or
        ``None`` before any tick has run (a fresh campaign's honest state).
    :param outcome: The currently-held terminal outcome, or ``None``.
    :returns: The frozen, validated briefing dossier.
    :raises pydantic.ValidationError: if ``session_id``/``tick`` produce a
        shape the model rejects — a present-but-wrong input fails loud
        (Constitution III.11's Loud Failure half of the absence contract).
    """
    return BriefingView(
        session_id=session_id,
        verified_tick=tick,
        codename=operation_codename(session_id),
        objectives=journal_objectives(axes=axes, outcome=outcome),
        horizon_years=defines.endgame.campaign_horizon_years,
        horizon_ticks=campaign_horizon_tick(defines),
    )
