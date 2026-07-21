"""Contract tests for :func:`babylon.projection.institution.project_institution`.

The institution read-model's behavioral contract: one producer per field
(the institution's own graph node), honest ``None`` for a nonexistent
institution, deterministic output. Fixture-fed — no engine tick, no
database — per the keel's fixture-first discipline. The full-dossier and
loud-failure paths below construct a :class:`~babylon.topology.BabylonGraph`
directly (mirroring ``test_county.py``'s own in-test fixtures) because no
current scenario seeds an ``Institution`` node — see
``src/babylon/projection/institution.py``'s module docstring for the full
disclosure, and ``tests/unit/institution/conftest.py`` for the "Department
of Justice" test-fixture convention this module borrows values from.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.models.enums.topology import NodeType
from babylon.projection.fixtures.recorder import (
    load_institution_fixture,
    record_institution_fixture,
)
from babylon.projection.institution import institution_statblocks, project_institution
from babylon.projection.view_models import (
    FactionalComposition,
    InstitutionView,
    hydrate_record,
)
from babylon.topology import BabylonGraph

DOJ = "doj"

_BALANCE = {
    "liberal_technocratic": 0.5,
    "revanchist_fascist": 0.3,
    "institutionalist_bonapartist": 0.2,
    # Production dumps also carry these two — neither is a
    # FactionalComposition field, and both must be silently ignored (not
    # trip extra="forbid") by the explicit three-key extraction.
    "internal_contestation": 0.3,
    "hegemonic_fraction": "liberal_technocratic",
}


def _doj_graph() -> BabylonGraph:
    """A graph with one fully-attributed Department-of-Justice institution."""
    graph = BabylonGraph()
    graph.add_node(
        DOJ,
        NodeType.INSTITUTION,
        name="Department of Justice",
        apparatus_type="rsa_judicial",
        social_function="adjudication",
        class_inscription="bourgeois",
        legitimacy=0.7,
        budget=1_000_000.0,
        housed_org_ids=["fbi"],
        territory_ids=["us_national"],
        internal_balance=dict(_BALANCE),
    )
    return graph


class TestFullDossier:
    """Every field populated when the institution node carries every attribute."""

    def test_projects_every_field(self) -> None:
        """A fully-attributed institution yields a dossier with no absences."""
        view = project_institution(DOJ, graph=_doj_graph(), tick=847)

        assert view.institution_id == DOJ
        assert view.verified_tick == 847
        assert view.name == "Department of Justice"
        assert view.apparatus_type == "rsa_judicial"
        assert view.social_function == "adjudication"
        assert view.class_inscription == "bourgeois"
        assert view.legitimacy == pytest.approx(0.7)
        assert view.budget == pytest.approx(1_000_000.0)
        assert view.housed_org_ids == ("fbi",)
        assert view.territory_ids == ("us_national",)
        assert view.factional_composition is not None
        assert view.factional_composition.liberal_technocratic == pytest.approx(0.5)
        assert view.factional_composition.revanchist_fascist == pytest.approx(0.3)
        assert view.factional_composition.institutionalist_bonapartist == pytest.approx(0.2)

    def test_factional_composition_ignores_non_serializer_keys(self) -> None:
        """``internal_contestation``/``hegemonic_fraction`` never leak through."""
        view = project_institution(DOJ, graph=_doj_graph(), tick=1)
        assert view.factional_composition is not None
        # FactionalComposition is extra="forbid" — construction above would
        # already have raised had the extra keys leaked in; assert the
        # exact declared field set as a belt-and-braces check.
        assert set(FactionalComposition.model_fields) == {
            "liberal_technocratic",
            "revanchist_fascist",
            "institutionalist_bonapartist",
        }

    def test_empty_housed_org_ids_is_a_real_value_not_absence(self) -> None:
        """Zero housed orgs projects an empty tuple, never ``None``."""
        graph = _doj_graph()
        graph.update_node(DOJ, housed_org_ids=[])
        view = project_institution(DOJ, graph=graph, tick=1)
        assert view.housed_org_ids == ()


class TestHonestAbsence:
    """No institution node with this id -> every field None (III.11)."""

    def test_unknown_institution_id_yields_all_none_fields(self) -> None:
        """An id no institution node carries projects an honest-absence dossier."""
        view = project_institution("does-not-exist", graph=_doj_graph(), tick=5)

        assert view.institution_id == "does-not-exist"
        assert view.verified_tick == 5
        assert view.name is None
        assert view.apparatus_type is None
        assert view.social_function is None
        assert view.class_inscription is None
        assert view.legitimacy is None
        assert view.budget is None
        assert view.housed_org_ids is None
        assert view.territory_ids is None
        assert view.factional_composition is None

    def test_empty_graph_yields_all_none_fields(self) -> None:
        """A graph with no institution node at all is the same honest absence."""
        view = project_institution(DOJ, graph=BabylonGraph(), tick=0)
        assert view.name is None
        assert view.factional_composition is None

    def test_wrong_typed_node_at_the_same_id_is_still_absence(self) -> None:
        """A node sharing the id but not typed ``institution`` never masquerades."""
        graph = BabylonGraph()
        graph.add_node(DOJ, NodeType.TERRITORY, county_fips="26163")
        view = project_institution(DOJ, graph=graph, tick=1)
        assert view.name is None


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_malformed_internal_balance_raises(self) -> None:
        """An internal_balance missing a named weight fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(
            DOJ,
            NodeType.INSTITUTION,
            internal_balance={"liberal_technocratic": 1.0},
        )
        with pytest.raises(ValidationError):
            project_institution(DOJ, graph=graph, tick=1)

    def test_internal_balance_not_summing_to_one_raises(self) -> None:
        """Three weights that don't sum to one (outside engine tolerance) fail loudly."""
        graph = BabylonGraph()
        graph.add_node(
            DOJ,
            NodeType.INSTITUTION,
            internal_balance={
                "liberal_technocratic": 0.9,
                "revanchist_fascist": 0.9,
                "institutionalist_bonapartist": 0.9,
            },
        )
        with pytest.raises(ValidationError):
            project_institution(DOJ, graph=graph, tick=1)

    def test_out_of_range_legitimacy_raises(self) -> None:
        """A legitimacy value outside [0, 1] fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(DOJ, NodeType.INSTITUTION, legitimacy=1.5)
        with pytest.raises(ValidationError):
            project_institution(DOJ, graph=graph, tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        graph = _doj_graph()

        first = project_institution(DOJ, graph=graph, tick=847)
        second = project_institution(DOJ, graph=graph, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()


class TestStatblockProvider:
    """``institution_statblocks`` — the per-kind live StatblockProvider."""

    def test_known_subject_resolves_statblock_rows(self) -> None:
        """A subject present in the views mapping resolves formatted rows."""
        view = project_institution(DOJ, graph=_doj_graph(), tick=1)
        provider = institution_statblocks({"institution/doj": view})

        rows = provider("institution/doj")
        assert rows is not None
        assert ("name", "Department of Justice") in rows

    def test_unknown_subject_resolves_none(self) -> None:
        """A subject absent from the views mapping resolves ``None``."""
        provider = institution_statblocks({})
        assert provider("institution/nonexistent") is None

    def test_all_absent_view_resolves_empty_rows_not_none(self) -> None:
        """A known-but-honestly-absent subject resolves zero rows, not None.

        The subject *is* known (a projection exists for it); it simply has
        no populated fields — distinct from a subject the provider has never
        heard of.
        """
        view = project_institution("ghost", graph=BabylonGraph(), tick=1)
        provider = institution_statblocks({"institution/ghost": view})
        assert provider("institution/ghost") == ()


class TestFixtureRoundTrip:
    """Recording then loading a view yields an equal, byte-identical artifact."""

    def test_round_trips_to_an_equal_view(self, tmp_path: Path) -> None:
        view = project_institution(DOJ, graph=_doj_graph(), tick=847)
        path = tmp_path / "view.json"

        record_institution_fixture(view, path)
        loaded = load_institution_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        view = project_institution(DOJ, graph=_doj_graph(), tick=847)
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_institution_fixture(view, first_path)
        record_institution_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_institution_fixture(tmp_path / "does_not_exist.json")

    def test_recorded_file_hydrates_through_hydrate_record(self, tmp_path: Path) -> None:
        """``hydrate_record`` (keyed on ``kind``) accepts a recorded fixture."""
        view = project_institution(DOJ, graph=_doj_graph(), tick=847)
        path = tmp_path / "view.json"
        record_institution_fixture(view, path)

        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        rehydrated = hydrate_record(data)

        assert rehydrated == view
        assert isinstance(rehydrated, InstitutionView)


class TestCommittedFixture:
    """The WO-19 harvester's committed fixture stays present and well-shaped.

    Deliberately NOT a skip: if ``tests/fixtures/projection/institution_doj.json``
    goes missing or drifts out of ``InstitutionView``'s schema, this test
    must fail loud (Constitution III.11).
    """

    _COMMITTED_FIXTURE: Path = (
        Path(__file__).parent.parent.parent / "fixtures" / "projection" / "institution_doj.json"
    )

    def test_committed_fixture_is_present_and_well_shaped(self) -> None:
        """The shipped fixture loads, names the right id, and has a valid tick."""
        assert self._COMMITTED_FIXTURE.is_file(), (
            f"committed projection fixture missing: {self._COMMITTED_FIXTURE} — "
            "regenerate via `uv run python tools/record_institution_fixture.py`"
        )

        view = load_institution_fixture(self._COMMITTED_FIXTURE)

        assert view.institution_id == "doj"
        assert view.verified_tick >= 0

    def test_committed_fixture_is_honestly_all_absent(self) -> None:
        """No scenario seeds an institution — the fixture proves it, not asserts it.

        See ``src/babylon/projection/institution.py``'s module docstring for
        the disclosure this test pins.
        """
        view = load_institution_fixture(self._COMMITTED_FIXTURE)
        assert view.name is None
        assert view.factional_composition is None
        assert view.housed_org_ids is None
