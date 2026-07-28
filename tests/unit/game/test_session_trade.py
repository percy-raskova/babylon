"""P26 U2 — interactive trade parity: the session-side W-C wiring motions.

Contract: ``specs/101-trade-activation/u2-interactive-parity-contracts.md``
(pinned at ``c0f17798`` before any implementation code). These tests were
written RED first (TDD): they pin the seams by which the playable game gains
the same trade wiring the headless batch path has had since spec-101 —
the four Φ-distribution context keys, ``simulated_year``, the ``vol2_step``
gate input, the economics-overrides thread-through, and the Wayne
imperial-circuit TRIBUTE seeding.

The ``trade=None`` back-compat pin matters as much as the wired paths: every
pre-U2 campaign construction must stay byte-identical (no context key
stamped, both ``economic.py`` sub-stages gated exactly as before).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import pytest

from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegister
from babylon.engine.scenarios import WayneCountyScenario
from babylon.engine.scenarios._legacy_wayne import create_wayne_county_scenario
from babylon.game.session import create_new_campaign
from babylon.game.trade import (
    TradeDataUnavailableError,
    TradeWiring,
    build_interactive_trade_wiring,
)
from babylon.models.enums.topology import EdgeType
from tests.unit.game.test_session import _FakeStore

if TYPE_CHECKING:
    from pathlib import Path

    from babylon.engine.systems.vol2_circulation import Vol2CirculationStep


# --------------------------------------------------------------------------- #
# Test doubles                                                                #
# --------------------------------------------------------------------------- #


class _RecordingEngine:
    """Engine double that captures the per-tick context instead of running
    the 33 systems — the observable seam for the context-stamping contracts.

    ``run_tick`` snapshots the trade-relevant keys via ``context.get`` (the
    exact read pattern ``economic.py``'s gates use), so what these tests
    assert is literally what the gates would see.
    """

    def __init__(self) -> None:
        self.captured: list[dict[str, Any]] = []

    def run_tick(self, graph: Any, services: Any, context: Any) -> None:  # noqa: ARG002
        self.captured.append(
            {
                key: context.get(key)
                for key in (
                    "session_id",
                    "boundary_flow_register",
                    "external_nodes_phi",
                    "county_exposure_by_external",
                    "simulated_year",
                    "vol2_step",
                )
            }
        )


def _wiring(
    *,
    register: BoundaryFlowRegister | None = None,
    vol2_step: Vol2CirculationStep | None = None,
    start_year: int = 2010,
    weeks_per_year: int = 52,
) -> TradeWiring:
    return TradeWiring(
        boundary_register=register if register is not None else BoundaryFlowRegister(),
        external_nodes_phi={"canada": 100_000_000.0},
        county_exposure_by_external={"canada": {"26163": 1.0}},
        start_year=start_year,
        weeks_per_year=weeks_per_year,
        vol2_step=vol2_step,
    )


# --------------------------------------------------------------------------- #
# TradeWiring — derivations                                                   #
# --------------------------------------------------------------------------- #


def test_trade_wiring_simulated_year_is_start_year_plus_whole_years() -> None:
    """``simulated_year`` derives as ``start_year + tick // weeks_per_year``
    (int) — the vol2 gate casts with ``int(simulated_year)`` and the trace
    emitter's float form is a display concern, not a gate input."""
    wiring = _wiring(start_year=2010, weeks_per_year=52)

    assert wiring.simulated_year(0) == 2010
    assert wiring.simulated_year(51) == 2010
    assert wiring.simulated_year(52) == 2011
    assert wiring.simulated_year(520) == 2020


# --------------------------------------------------------------------------- #
# advance_tick — context stamping (W-C motions #1 and #2)                     #
# --------------------------------------------------------------------------- #


def test_advance_tick_without_trade_stamps_no_trade_keys() -> None:
    """The ``trade=None`` default is the byte-identical pre-U2 path: none of
    the five gate inputs appears in context, so both ``economic.py``
    sub-stages stay silently gated exactly as before this unit."""
    store = _FakeStore()
    session = create_new_campaign(store, scenario=WayneCountyScenario())
    recorder = _RecordingEngine()
    session.engine = cast("Any", recorder)

    session.advance_tick()

    (captured,) = recorder.captured
    assert captured == {
        "session_id": None,
        "boundary_flow_register": None,
        "external_nodes_phi": None,
        "county_exposure_by_external": None,
        "simulated_year": None,
        "vol2_step": None,
    }


def test_advance_tick_with_trade_stamps_the_four_phi_keys_and_simulated_year() -> None:
    """W-C motion #1: with ``trade`` wired, ``advance_tick`` supplies exactly
    the inputs ``_invoke_phi_distribution_if_wired`` gates on, mirroring the
    headless runner's ``runner.py:440-447`` — plus ``simulated_year``."""
    store = _FakeStore()
    register = BoundaryFlowRegister()
    trade = _wiring(register=register)
    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)
    recorder = _RecordingEngine()
    session.engine = cast("Any", recorder)

    session.advance_tick()

    (captured,) = recorder.captured
    assert captured["session_id"] == session.session_id
    assert captured["boundary_flow_register"] is register
    assert captured["external_nodes_phi"] == {"canada": 100_000_000.0}
    assert captured["county_exposure_by_external"] == {"canada": {"26163": 1.0}}
    assert captured["simulated_year"] == 2010
    assert captured["vol2_step"] is None


def test_advance_tick_with_vol2_step_stamps_it_into_context() -> None:
    """W-C motion #2 (seam row ``vol2_circulation_vol2_step``): a wired
    ``vol2_step`` reaches context so ``_invoke_vol2_circulation_if_wired``
    finally has a production supplier."""
    store = _FakeStore()
    step_stub = cast("Vol2CirculationStep", object())
    trade = _wiring(vol2_step=step_stub)
    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)
    recorder = _RecordingEngine()
    session.engine = cast("Any", recorder)

    session.advance_tick()

    (captured,) = recorder.captured
    assert captured["vol2_step"] is step_stub


# --------------------------------------------------------------------------- #
# create_new_campaign — services wiring                                       #
# --------------------------------------------------------------------------- #


def test_create_new_campaign_threads_economics_overrides_into_services() -> None:
    """The overrides dict reaches ``ServiceContainer.create`` — the same
    ``**``-unpack contract ``_build_economics_overrides`` documents — so an
    interactive campaign can run the real gamma/melt/Leontief stack instead
    of the zero-stub default."""

    class _GammaSentinel:
        pass

    gamma = _GammaSentinel()
    store = _FakeStore()

    session = create_new_campaign(
        store,
        scenario=WayneCountyScenario(),
        economics_overrides={"gamma_calculator": gamma},
    )

    assert session.services.gamma_calculator is gamma


def test_create_new_campaign_assigns_boundary_register_onto_services() -> None:
    """Runner-twin assignment (``runner.py:1330``): the session's register is
    exposed as ``services.boundary_register`` so engine systems that publish
    boundary flows see the same buffer ``advance_tick`` stamps into context."""
    store = _FakeStore()
    register = BoundaryFlowRegister()
    trade = _wiring(register=register)

    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)

    assert session.services.boundary_register is register


# --------------------------------------------------------------------------- #
# End-to-end: Φ actually flows in an interactive tick                         #
# --------------------------------------------------------------------------- #


def test_phi_flows_into_the_envelope_during_a_real_interactive_tick() -> None:
    """The program's central defect, pinned from the fix side: a REAL engine
    tick on an interactive campaign distributes Canada's weekly Φ slice into
    DRAIN_EDGE register rows (spec-101 semantics: ``phi_year_inflow / 52``
    at exposure weight 1.0), and ``advance_tick`` folds them into the
    atomic envelope (the register's once-per-tick flush contract,
    ``bridge.py:505`` twin) — so the buffer never accumulates across ticks.
    Before this unit, the interactive path structurally produced zero
    boundary rows ever."""
    store = _FakeStore()
    register = BoundaryFlowRegister()
    trade = _wiring(register=register)
    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)

    session.advance_tick()

    assert register.buffered_count() == 0, "advance_tick must flush the buffer into the envelope"
    envelope = store.persist_tick_atomic_calls[-1]
    assert envelope.tick == 1
    rows = [r for r in envelope.boundary_register_rows if r.source_node_id == "canada"]
    assert rows, "expected DRAIN_EDGE rows sourced from the canada external node"
    weekly_slice = 100_000_000.0 / 52.0
    total = sum(row.magnitude for row in rows)
    assert total == pytest.approx(weekly_slice)


# --------------------------------------------------------------------------- #
# Wayne imperial circuit — TRIBUTE seeding (additive, default-off)            #
# --------------------------------------------------------------------------- #


def test_wayne_default_build_seeds_no_tribute_and_is_unchanged() -> None:
    """SC-007 guard from the trade side: the default build stays TRIBUTE-free
    with exactly the four legacy classes — the M3 lane's snapshots and the
    byte-equality pin both stand on this shape."""
    world0, _config, _defines = create_wayne_county_scenario()

    tribute = [r for r in world0.relationships if r.edge_type == EdgeType.TRIBUTE]
    assert tribute == []
    assert sorted(world0.entities.keys()) == ["C001", "C002", "C003", "C004"]


def test_wayne_imperial_circuit_flag_seeds_the_canonical_tribute_circuit() -> None:
    """``include_imperial_circuit=True`` adds the canonical circuit mirrored
    from the imperial-circuit scenario: periphery proletariat (C005)
    →EXPLOITATION→ comprador (C006) →TRIBUTE→ Wayne core bourgeoisie (C003),
    plus the CLIENT_STATE return edge C003→C006 — so
    ``_process_tribute_phase`` finally has an edge to walk interactively."""
    world0, _config, _defines = create_wayne_county_scenario(include_imperial_circuit=True)

    assert "C005" in world0.entities
    assert "C006" in world0.entities

    def _has(source: str, target: str, edge_type: EdgeType) -> bool:
        return any(
            r.source_id == source and r.target_id == target and r.edge_type == edge_type
            for r in world0.relationships
        )

    assert _has("C005", "C006", EdgeType.EXPLOITATION)
    assert _has("C006", "C003", EdgeType.TRIBUTE)
    assert _has("C003", "C006", EdgeType.CLIENT_STATE)


def test_tribute_changes_core_bourgeoisie_wealth_in_a_real_tick() -> None:
    """Same seed, same scenario, one tick — the ONLY delta is the circuit
    flag, and the core bourgeoisie's post-tick wealth must differ (tribute
    received). Pins that the seeded edge is genuinely walked by
    ``_process_tribute_phase``, not just present in the graph."""
    plain = create_new_campaign(_FakeStore(), scenario=WayneCountyScenario())
    plain.advance_tick()
    plain_node = plain.graph.get_node("C003")
    assert plain_node is not None

    bundle = create_wayne_county_scenario(include_imperial_circuit=True)

    class _FrozenBuildScenario:
        """Structural (non-registered) scenario double — subclassing
        ``WayneCountyScenario`` is impossible here because ``Scenario.
        __init_subclass__`` rejects the duplicate ``name`` registration."""

        name = "wayne_county"
        description = "circuit-flagged Wayne build, frozen"

        def build(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
            return bundle

    wired = create_new_campaign(_FakeStore(), scenario=cast("Any", _FrozenBuildScenario()))
    wired.advance_tick()
    wired_node = wired.graph.get_node("C003")
    assert wired_node is not None

    assert wired_node.attributes["wealth"] != plain_node.attributes["wealth"]


# --------------------------------------------------------------------------- #
# subject_view — the trade kind (P26 U6 phase 1)                              #
# --------------------------------------------------------------------------- #


def test_subject_view_trade_kind_projects_bloc_and_overview() -> None:
    """``trade/<node>`` and ``trade/overview`` resolve from the session's own
    wiring + the last tick's flushed DRAIN_EDGE rows (contract:
    specs/103-trade-surfaces/u6-archive-trade-surfaces-contracts.md)."""
    store = _FakeStore()
    trade = _wiring()
    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)
    session.advance_tick()

    bloc = session.subject_view("trade/canada")
    assert bloc is not None
    assert bloc.kind == "trade"
    assert bloc.node_id == "canada"
    assert bloc.verified_tick == 1
    assert bloc.phi_year_inflow == 100_000_000.0
    # The tick's flushed flow reappears on the dossier (weekly slice at
    # exposure weight 1.0 — the same number the envelope test pins).
    assert bloc.last_tick_flow == pytest.approx(100_000_000.0 / 52.0)

    overview = session.subject_view("trade/overview")
    assert overview is not None
    assert overview.node_id == "overview"
    assert overview.breakdown is not None


def test_subject_view_trade_kind_is_honest_absence_when_trade_unwired() -> None:
    """A campaign with no trade wiring resolves ``trade/*`` to ``None`` —
    the existing watchlist 'no longer resolvable' row, never a crash."""
    session = create_new_campaign(_FakeStore(), scenario=WayneCountyScenario())
    session.advance_tick()

    assert session.subject_view("trade/canada") is None
    assert session.subject_view("trade/overview") is None


# --------------------------------------------------------------------------- #
# build_interactive_trade_wiring — loud failure (Constitution III.11)         #
# --------------------------------------------------------------------------- #


def test_build_interactive_trade_wiring_raises_loud_when_reference_db_absent(
    tmp_path: Path,
) -> None:
    """No silent stub: an absent reference DB raises the typed error before
    any Postgres work — the composition root turns this into ONE loud
    degradation warning, never a quiet no-trade campaign."""
    missing = tmp_path / "definitely-not-here.sqlite"

    with pytest.raises(TradeDataUnavailableError, match="reference"):
        build_interactive_trade_wiring(
            session_id=uuid4(),
            runtime=cast("Any", object()),
            defines=None,
            sqlite_path=missing,
            start_year=2010,
            counties=["26163"],
        )


# --------------------------------------------------------------------------- #
# read_page / known_subjects — the trade kind (P26 U6 phase 2, live pages)    #
# --------------------------------------------------------------------------- #


def test_read_page_renders_a_live_trade_overview_page() -> None:
    """``read_page("trade/overview")`` renders live markdown (never a vault
    lookup) — a ``{statblock}`` fence with the national Φ numbers, plus the
    per-bloc breakdown table (contract: specs/103-trade-surfaces/
    u6-archive-trade-surfaces-contracts.md, phase 2)."""
    store = _FakeStore()
    trade = _wiring()
    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)
    session.advance_tick()

    page = session.read_page("trade/overview")

    assert page is not None
    assert "trade/overview" in page
    assert "phi_year_inflow: 100000000.000000" in page
    assert "[[trade/canada]]" in page


def test_read_page_renders_a_live_trade_bloc_page() -> None:
    """``read_page("trade/canada")`` renders the bloc dossier: Φ year/week,
    top county exposure, and a back-link to the overview."""
    store = _FakeStore()
    trade = _wiring()
    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)
    session.advance_tick()

    page = session.read_page("trade/canada")

    assert page is not None
    assert "trade/canada" in page
    assert "26163" in page
    assert "[[trade/overview]]" in page


def test_read_page_trade_is_honest_absence_when_trade_unwired() -> None:
    """No trade wiring: ``read_page`` returns ``None`` for every ``trade/*``
    id — the client's existing "ABSENT" page, never fabricated content."""
    session = create_new_campaign(_FakeStore(), scenario=WayneCountyScenario())
    session.advance_tick()

    assert session.read_page("trade/overview") is None
    assert session.read_page("trade/canada") is None


def test_read_page_trade_is_honest_absence_for_an_unknown_bloc() -> None:
    """A wired campaign still returns ``None`` for a bloc id it never
    attributed — the same unknown-entity contract every sibling ``project_
    <kind>`` honors."""
    store = _FakeStore()
    trade = _wiring()
    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)
    session.advance_tick()

    assert session.read_page("trade/atlantis") is None


def test_known_subjects_includes_live_trade_ids_when_wired() -> None:
    """``known_subjects()`` unions the baked vault set with the live trade
    ids — so the command palette and wikilink resolver both learn about
    ``trade/overview``/``trade/canada`` the instant trade is wired, with no
    vault bake required."""
    store = _FakeStore()
    trade = _wiring()
    session = create_new_campaign(store, scenario=WayneCountyScenario(), trade=trade)

    subjects = session.known_subjects()

    assert "trade/overview" in subjects
    assert "trade/canada" in subjects


def test_known_subjects_excludes_trade_ids_when_unwired() -> None:
    """No trade wiring: ``known_subjects()`` contributes no ``trade/*`` id —
    honest absence, never a fabricated demo entry."""
    session = create_new_campaign(_FakeStore(), scenario=WayneCountyScenario())

    subjects = session.known_subjects()

    assert not any(subject.startswith("trade/") for subject in subjects)
