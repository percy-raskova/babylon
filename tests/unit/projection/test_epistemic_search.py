"""Contract tests for WO-43: epistemic search — the org knows what it knows.

The known-entity set is ``organizing_reach() ∪ intel-observed node ids`` —
spatial presence plus INVESTIGATE history — and search executes ONLY over
that set. There is no global oracle: an entity that exists in the graph
but sits outside reach∪intel is not a search result, full stop (charter
P0 batch: FTS-over-known-only). The in-process filter honors the
registry's ``fts_columns`` declarations as the searchable surface.
"""

from __future__ import annotations

from babylon.models.enums.topology import NodeType
from babylon.projection.epistemic_search import (
    SearchHit,
    known_entity_ids,
    search_known,
    searchable_text_for_row,
)
from babylon.projection.fog.ledger import IntelEntry, IntelLedger
from babylon.projection.registry import declared_view
from babylon.topology import BabylonGraph


def _graph() -> BabylonGraph:
    """The reach fixture topology plus one INVESTIGATE-only node.

    ``ORG1 --presence--> T1 <--tenancy-- C1 --solidarity--> C2``;
    ``ORG2``/``T2`` are a rival's world (never reachable); ``T9`` exists
    only through intel history.
    """
    graph = BabylonGraph()
    graph.add_node("ORG1", NodeType.ORGANIZATION, name="Player Org")
    graph.add_node("ORG2", NodeType.ORGANIZATION, name="Rival Org")
    graph.add_node("T1", NodeType.TERRITORY, name="Home Territory")
    graph.add_node("T2", NodeType.TERRITORY, name="Far Territory")
    graph.add_node("T9", NodeType.TERRITORY, name="Investigated Territory")
    graph.add_node("C1", NodeType.SOCIAL_CLASS, name="Detroit Proletariat")
    graph.add_node("C2", NodeType.SOCIAL_CLASS, name="Dearborn Workers")
    graph.add_edge("ORG1", "T1", "presence")
    graph.add_edge("ORG2", "T2", "presence")
    graph.add_edge("C1", "T1", "tenancy")
    graph.add_edge("C1", "C2", "solidarity")
    return graph


def _ledger_with_t9() -> IntelLedger:
    return IntelLedger().append(IntelEntry(node_id="T9", field_group="political", tick_observed=5))


class TestKnownEntityIds:
    def test_union_of_reach_and_intel(self) -> None:
        known = known_entity_ids(_graph(), "ORG1", ledger=_ledger_with_t9(), radius=1)
        assert known == frozenset({"ORG1", "T1", "C1", "C2", "T9"})

    def test_no_global_oracle_rival_world_stays_unknown(self) -> None:
        known = known_entity_ids(_graph(), "ORG1", ledger=_ledger_with_t9(), radius=5)
        assert "ORG2" not in known
        assert "T2" not in known

    def test_no_player_org_knows_only_its_intel(self) -> None:
        known = known_entity_ids(_graph(), None, ledger=_ledger_with_t9(), radius=1)
        assert known == frozenset({"T9"})

    def test_empty_ledger_and_no_org_knows_nothing(self) -> None:
        assert known_entity_ids(_graph(), None, ledger=IntelLedger(), radius=1) == frozenset()


class TestSearchKnown:
    _CORPUS = {
        "C1": "Detroit Proletariat",
        "C2": "Dearborn Workers",
        "T2": "Far Territory",  # present in the corpus, NOT in the known set
    }
    _KNOWN = frozenset({"C1", "C2", "T1"})

    def test_matches_only_known_entities(self) -> None:
        hits = search_known("workers", self._CORPUS, self._KNOWN)
        assert [hit.entity_id for hit in hits] == ["C2"]

    def test_fogged_entity_is_never_surfaced_even_when_its_text_matches(self) -> None:
        hits = search_known("far territory", self._CORPUS, self._KNOWN)
        assert hits == ()

    def test_entity_id_itself_is_searchable(self) -> None:
        hits = search_known("T1", self._CORPUS, self._KNOWN)
        assert [hit.entity_id for hit in hits] == ["T1"]

    def test_case_insensitive_and_deterministically_ordered(self) -> None:
        hits = search_known("DE", self._CORPUS, self._KNOWN)
        assert [hit.entity_id for hit in hits] == ["C1", "C2"]
        assert all(isinstance(hit, SearchHit) for hit in hits)

    def test_blank_query_returns_nothing(self) -> None:
        assert search_known("   ", self._CORPUS, self._KNOWN) == ()


class TestSearchableTextForRow:
    def test_joins_only_the_declared_fts_columns(self) -> None:
        view = declared_view("v_county_value_aggregate")
        row = dict.fromkeys(view.columns, "IGNORED")
        row["county_fips"] = "26163"
        text = searchable_text_for_row(view, row)
        assert text == "26163"

    def test_absent_and_none_values_are_skipped(self) -> None:
        view = declared_view("v_county_value_aggregate")
        assert searchable_text_for_row(view, {"county_fips": None}) == ""
        assert searchable_text_for_row(view, {}) == ""
