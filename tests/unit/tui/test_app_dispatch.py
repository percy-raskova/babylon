"""Contract tests for WO-45: the kind-dispatch statblock registry.

The single serial integrator's seam: every Lane P kind's provider composes
into one subject-routed :data:`~babylon.tui.directives.StatblockProvider`,
the demo known-set covers every committed fixture subject, every shipped
directive has a live ``BabylonFence`` handler, and the app accepts the
WO-43 epistemic known-set (``reach ∪ intel``) as its resolver input.
"""

from __future__ import annotations

import pytest

from babylon.models.enums.topology import NodeType
from babylon.projection.epistemic_search import known_entity_ids
from babylon.projection.fog.ledger import IntelLedger
from babylon.topology import BabylonGraph
from babylon.tui.app import KNOWN_ENTITIES, ArchiveApp, BabylonMarkdown
from babylon.tui.directives import BabylonFence
from babylon.tui.dispatch import (
    fixture_known_entities,
    fixture_statblock_providers,
    fixture_subject_views,
    kind_dispatch_statblocks,
)
from babylon.tui.wikilinks import known_target_resolver

FIXTURE_SUBJECTS = sorted(fixture_known_entities())


@pytest.fixture(scope="module")
def dispatch():  # type: ignore[no-untyped-def]
    return kind_dispatch_statblocks(fixture_statblock_providers())


class TestKindDispatch:
    @pytest.mark.parametrize("subject", FIXTURE_SUBJECTS)
    def test_every_fixture_kind_resolves_a_provider(self, dispatch, subject: str) -> None:  # type: ignore[no-untyped-def]
        rows = dispatch(subject)
        assert rows is not None, f"{subject} must resolve through the kind dispatch"

    def test_key_figure_resolves_honest_empty_rows(self, dispatch) -> None:  # type: ignore[no-untyped-def]
        """A kind with no live producer answers with empty rows — present,
        not absent (the page's absence blocks carry the remedy copy)."""
        assert dispatch("key_figure/kf-001") == []

    def test_unknown_kind_is_absence(self, dispatch) -> None:  # type: ignore[no-untyped-def]
        assert dispatch("galaxy/andromeda") is None

    def test_known_kind_unknown_id_is_absence(self, dispatch) -> None:  # type: ignore[no-untyped-def]
        assert dispatch("county/99999") is None

    def test_subject_without_kind_prefix_is_absence(self, dispatch) -> None:  # type: ignore[no-untyped-def]
        assert dispatch("26163") is None

    def test_county_rows_carry_real_fixture_values(self, dispatch) -> None:  # type: ignore[no-untyped-def]
        """Rows come from the COMMITTED harvest (single_county scenario:
        two seeded entities), not the hand-shaped Wayne demo numbers the
        keel's sample provider used to hardcode."""
        rows = dict(dispatch("county/26163"))
        assert rows["population"] == "2"
        assert rows["median_wage"] == "21.000000"


class TestKnownSet:
    def test_demo_known_set_covers_every_fixture_subject(self) -> None:
        assert fixture_known_entities() <= KNOWN_ENTITIES

    def test_app_accepts_the_epistemic_known_set(self) -> None:
        """The resolver seam takes WO-43's reach∪intel output directly —
        an entity outside the epistemic set stays a redlink even though a
        fixture provider exists for it (no global oracle)."""
        graph = BabylonGraph()
        graph.add_node("ORG1", NodeType.ORGANIZATION, name="Player Org")
        graph.add_node("T1", NodeType.TERRITORY, name="Home")
        graph.add_edge("ORG1", "T1", "presence")
        known = known_entity_ids(graph, "ORG1", ledger=IntelLedger(), radius=1)

        app = ArchiveApp(resolver=known_target_resolver(known))
        assert app._resolver("T1") is True
        assert app._resolver("county/26163") is False


class TestFixtureSubjectViews:
    """Contract tests for Program 24 P6's :func:`fixture_subject_views` —
    the watchlist rail's default peek-plate source (``ArchiveApp._subject_views``)."""

    def test_keys_match_the_fixture_known_set_exactly(self) -> None:
        assert set(fixture_subject_views()) == fixture_known_entities()

    @pytest.mark.parametrize("subject", FIXTURE_SUBJECTS)
    def test_every_fixture_subject_resolves_to_a_view_model_of_its_own_kind(
        self, subject: str
    ) -> None:
        kind = subject.split("/", 1)[0]
        view = fixture_subject_views()[subject]
        assert view.kind == kind

    def test_county_view_carries_the_same_committed_values_the_statblock_dispatch_uses(
        self,
        dispatch,  # type: ignore[no-untyped-def]
    ) -> None:
        """The row form (``dispatch``) and the model form (this function) must
        agree — same fixture file, same loader, never a second drifted copy."""
        view = fixture_subject_views()["county/26163"]
        rows = dict(dispatch("county/26163"))
        assert str(view.population) == rows["population"]


class TestDirectiveCoverage:
    @pytest.mark.parametrize(
        "name",
        ["statblock", "absence", "narrative", "paoh", "maproom", "egotree", "matrix"],
    )
    def test_every_shipped_directive_has_a_fence_handler(self, name: str) -> None:
        assert callable(getattr(BabylonFence, f"_directive_{name}", None))

    def test_markdown_blocks_cover_the_wikilink_dialect(self) -> None:
        for token in ("fence", "code_block", "paragraph_open", "h1", "th_open", "td_open"):
            assert token in BabylonMarkdown.BLOCKS
