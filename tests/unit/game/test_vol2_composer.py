"""P26 U5g — the Vol2CirculationStep composer (contract:
``specs/101-trade-activation/u5-engine-train-contracts.md`` §U5g).

Written RED first (TDD). Closes ADR162's disclosed inert half: U2 wired the
``vol2_step`` seam through ``GameSession.advance_tick`` but no production
code constructed a :class:`~babylon.engine.systems.vol2_circulation.
Vol2CirculationStep` anywhere. The composer builds one from its two live
production suppliers — the checked-in LODES tri-county artifact
(:func:`resolve_lodes_hydration_kwargs`) and the session's real hex→county
adjunction (:func:`read_hex_county_adjunction`) — and degrades to honest
``None`` (one loud warning) whenever either supplier has nothing real to
give (Constitution III.8/III.11): never a vacuous step walking an empty
adjunction.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest

from babylon.domain.dialectics.instances.scale import ScaleAdjunction
from babylon.engine.systems.vol2_circulation import Vol2CirculationStep
from babylon.game.vol2 import build_vol2_circulation_step

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from babylon.persistence.protocols import RuntimePersistence

_DETROIT_TRI_COUNTY = frozenset({"26163", "26125", "26099"})
_RUNTIME_SENTINEL = cast("RuntimePersistence", object())


def _reader_returning(
    adjunction: ScaleAdjunction,
) -> Callable[[RuntimePersistence, UUID], ScaleAdjunction]:
    def _read(runtime: RuntimePersistence, session_id: UUID) -> ScaleAdjunction:
        _ = runtime, session_id
        return adjunction

    return _read


def test_out_of_scope_counties_compose_to_none_with_loud_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A scope outside the Detroit tri-county artifact coverage returns
    ``None`` (the artifact reader's own honest-absence contract) — and says
    so out loud."""
    with caplog.at_level(logging.WARNING):
        step = build_vol2_circulation_step(
            runtime=_RUNTIME_SENTINEL,
            session_id=uuid4(),
            counties=frozenset({"06037"}),  # Los Angeles — not in the artifact
            adjunction_reader=_reader_returning(ScaleAdjunction.uniform({"hex-a": "06037"})),
        )
    assert step is None
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert "vol2" in joined.lower()


def test_empty_adjunction_composes_to_none_with_loud_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Hex hydration that never ran (empty ``hex_spatial_map``) yields an
    EMPTY adjunction — the composer must refuse to build a vacuous step."""
    with caplog.at_level(logging.WARNING):
        step = build_vol2_circulation_step(
            runtime=_RUNTIME_SENTINEL,
            session_id=uuid4(),
            counties=_DETROIT_TRI_COUNTY,
            adjunction_reader=_reader_returning(ScaleAdjunction.uniform({})),
        )
    assert step is None
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert "hex" in joined.lower()


def test_tri_county_scope_with_real_adjunction_composes_a_live_step() -> None:
    """The production path: tri-county scope + a populated adjunction →
    a real ``Vol2CirculationStep`` whose loader reads the CHECKED-IN LODES
    artifact (no drive access, no fabricated paths)."""
    adjunction = ScaleAdjunction.uniform({"872a9a409ffffff": "26163", "872a9a40affffff": "26125"})
    step = build_vol2_circulation_step(
        runtime=_RUNTIME_SENTINEL,
        session_id=uuid4(),
        counties=_DETROIT_TRI_COUNTY,
        adjunction_reader=_reader_returning(adjunction),
    )
    assert isinstance(step, Vol2CirculationStep)


def test_composer_builds_fresh_steps_per_call() -> None:
    """Two composes over identical inputs yield distinct live steps (the
    loader's year cache is per-instance by design), both bound to the same
    adjunction inputs."""
    adjunction = ScaleAdjunction.uniform({"872a9a409ffffff": "26163"})
    reader = _reader_returning(adjunction)
    session = uuid4()
    first = build_vol2_circulation_step(
        runtime=_RUNTIME_SENTINEL,
        session_id=session,
        counties=_DETROIT_TRI_COUNTY,
        adjunction_reader=reader,
    )
    second = build_vol2_circulation_step(
        runtime=_RUNTIME_SENTINEL,
        session_id=session,
        counties=_DETROIT_TRI_COUNTY,
        adjunction_reader=reader,
    )
    assert first is not None
    assert second is not None
    assert first is not second
