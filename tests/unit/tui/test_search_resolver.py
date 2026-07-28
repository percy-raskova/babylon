"""Contract tests for WO-43's client leg: wikilinks resolve epistemically.

The resolver the client wires is built from the org's ``reach ∪ intel``
known-set — a link to an entity the org has never reached or investigated
is UNKNOWN even though the entity exists in the graph (no global oracle;
the redlink IS the honest "you don't know this yet"). Since the M7 cutover
the render half lives in the Rust client (babylon-md's native wikilinks);
the durable Python-side contract is the RESOLVER VERDICT itself —
:func:`babylon.tui.wikilink_grammar.known_target_resolver` over
:func:`babylon.projection.epistemic_search.known_entity_ids` — which is
exactly what crosses the host seam as ``known_subjects_json``.
"""

from __future__ import annotations

from babylon.models.enums.topology import NodeType
from babylon.projection.epistemic_search import known_entity_ids
from babylon.projection.fog.ledger import IntelEntry, IntelLedger
from babylon.topology import BabylonGraph
from babylon.tui.wikilink_grammar import known_target_resolver


def _graph() -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node("ORG1", NodeType.ORGANIZATION, name="Player Org")
    graph.add_node("ORG2", NodeType.ORGANIZATION, name="Rival Org")
    graph.add_node("T1", NodeType.TERRITORY, name="Home Territory")
    graph.add_node("C1", NodeType.SOCIAL_CLASS, name="Detroit Proletariat")
    graph.add_edge("ORG1", "T1", "presence")
    graph.add_edge("C1", "T1", "tenancy")
    return graph


class TestEpistemicResolver:
    def test_reached_entity_resolves_as_known(self) -> None:
        known = known_entity_ids(_graph(), "ORG1", ledger=IntelLedger(), radius=1)
        assert known_target_resolver(known)("C1") is True

    def test_existing_but_unknown_entity_resolves_as_unknown(self) -> None:
        """ORG2 exists in the graph — the resolver still refuses it (the
        redlink verdict; no global oracle)."""
        known = known_entity_ids(_graph(), "ORG1", ledger=IntelLedger(), radius=1)
        assert known_target_resolver(known)("ORG2") is False

    def test_intel_history_promotes_an_unknown_target_to_known(self) -> None:
        """INVESTIGATE history is the second way of knowing: the same
        target flips from unknown to known once it enters the ledger."""
        before = known_entity_ids(_graph(), "ORG1", ledger=IntelLedger(), radius=1)
        assert known_target_resolver(before)("T9") is False

        ledger = IntelLedger().append(
            IntelEntry(node_id="T9", field_group="political", tick_observed=5)
        )
        after = known_entity_ids(_graph(), "ORG1", ledger=ledger, radius=1)
        assert known_target_resolver(after)("T9") is True
