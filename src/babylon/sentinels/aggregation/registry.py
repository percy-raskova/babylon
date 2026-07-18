"""Declared invariants of the ``aggregation`` sentinel — partial-coverage symmetry.

Two aggregations in ``web/game/engine_bridge.py`` roll up a per-member
fog-masked field into a single group-level number: ``_aggregate_hex_features``
(``heat`` over hexes rolled into a county/state/MSA/BEA group) and
``_build_state_apparatus_dashboard`` (``heat`` over a session's
state-apparatus organizations). Both are required to treat "every member
masked" identically: the aggregate must be an honest ``None`` (Constitution
III.11), never a fabricated ``0.0`` that would misread as "the police/the
region are under no repression pressure" when the truth is simply
"unknown, out of the player's organizing reach".

Founding grounding (Track 1 audit, 2026-07-18): both functions ALREADY
implement this correctly — ``_aggregate_hex_features`` tracks a dedicated
``heat_pop`` partial-coverage denominator (mirroring ``habitability_pop`` et
al.) instead of reusing ``population_sum``, and
``_build_state_apparatus_dashboard`` sums only ``visible_heats`` and returns
``None`` when that list is empty. This sentinel PINS that symmetry
dynamically (calling the real functions with synthetic all-masked input) so
a third aggregation added later — or a regression in either of these two —
cannot silently diverge to a fabricated ``0.0``.

Why dynamic, not static: the "all-masked -> None" contract is a runtime
behavior (what the function RETURNS for a given input), not a syntactic
shape a source-only AST scan can verify without re-implementing the
aggregation math. The harness that imports ``web.game.engine_bridge`` (a
Django app, layers ABOVE ``babylon.*``) therefore lives in
``tools/aggregation_symmetry_probe.py`` — never inside this package, which
must stay importable below the engine (mirrors
:mod:`babylon.sentinels.partition`'s own package/harness split: the
*declared contract* here, the *engine/Django-touching harness* in
``tools/``).

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "AGGREGATION_EXEMPTIONS",
    "DECLARED_AGGREGATES",
    "AggregationExemption",
    "DeclaredPartialCoverageAggregate",
]


class DeclaredPartialCoverageAggregate(BaseModel):
    """One declared aggregation whose all-masked output must be ``None``.

    :ivar name: Stable identity for the row, and the key the harness in
        ``tools/aggregation_symmetry_probe.py`` uses to look up its
        synthetic-input builder + assertion function (a small, closed,
        hand-written dispatch — see that module — rather than generic
        reflection over arbitrary signatures).
    :ivar def_file: Repo-relative ``.py`` path defining ``function_name``.
    :ivar function_name: The aggregation function/method checked.
    :ivar field: The at-risk field name (e.g. ``"heat"``).
    :ivar denominator_note: One-line description of the partial-coverage
        bookkeeping this aggregate uses (e.g. a dedicated ``heat_pop``
        counter, or a visible-values list).
    :ivar consequence_if_regressed: What a regression would misread as.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    function_name: str
    field: str
    denominator_note: str
    consequence_if_regressed: str

    @model_validator(mode="after")
    def _validate_shape(self) -> DeclaredPartialCoverageAggregate:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any identity field is blank, or ``def_file``
            is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("DeclaredPartialCoverageAggregate.name must be non-empty")
        if not self.function_name.strip():
            raise ValueError(f"{self.name!r}: function_name must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        if not self.field.strip():
            raise ValueError(f"{self.name!r}: field must be non-empty")
        return self


class AggregationExemption(BaseModel):
    """A declared aggregate known to currently violate the symmetry, on record.

    Never a silent shrug: every row names the owner and the dated
    reasoning, exactly as
    :class:`babylon.sentinels.inert.registry.InertExemption` does.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    reason: str
    owner: str
    date: str

    @model_validator(mode="after")
    def _validate_shape(self) -> AggregationExemption:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any field is blank.
        """
        for field_name in ("name", "reason", "owner", "date"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"AggregationExemption.{field_name} must be non-empty")
        return self


#: The two grounded rows (Track 1 Task 10). Both verified clean against the
#: current tree by ``tools/aggregation_symmetry_probe.py``.
DECLARED_AGGREGATES: Final[tuple[DeclaredPartialCoverageAggregate, ...]] = (
    DeclaredPartialCoverageAggregate(
        name="hex_features_heat",
        def_file="web/game/engine_bridge.py",
        function_name="EngineBridge._aggregate_hex_features",
        field="heat",
        denominator_note=(
            "Dedicated heat_pop partial-coverage denominator (mirrors "
            "habitability_pop/solidarity_index_pop/etc) -- population_sum is NOT "
            "reused for heat, so a masked hex's population still counts toward the "
            "group's population total but not toward heat's own coverage."
        ),
        consequence_if_regressed=(
            "A group where every hex's heat is fog-masked would read as heat=0.0 "
            "('the region is fully pacified') instead of None ('unknown to this "
            "player'), a legitimation-index-shaped lie."
        ),
    ),
    DeclaredPartialCoverageAggregate(
        name="state_apparatus_dashboard_heat",
        def_file="web/game/engine_bridge.py",
        function_name="_build_state_apparatus_dashboard",
        field="heat",
        denominator_note=(
            "visible_heats list comprehension excludes masked orgs entirely; "
            "total_heat sums ONLY that list and is None when it is empty."
        ),
        consequence_if_regressed=(
            "A session where every state-apparatus org is fog-masked would read as "
            "total_heat=0.0 ('the police are under no repression pressure') instead "
            "of None ('unknown to this player') -- the exact legitimation-index trap "
            "this dashboard's own docstring names."
        ),
    ),
)

#: Deliberately EMPTY: both declared rows are currently symmetric (verified
#: dynamically). A future row here must name an owner and a dated reason,
#: same as babylon.sentinels.inert.registry.INERT_EXEMPTIONS.
AGGREGATION_EXEMPTIONS: Final[tuple[AggregationExemption, ...]] = ()
