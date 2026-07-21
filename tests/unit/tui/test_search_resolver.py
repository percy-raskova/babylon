"""Contract tests for WO-43's TUI leg: wikilinks resolve epistemically.

The resolver the shell wires is built from the org's ``reach ∪ intel``
known-set — a link to an entity the org has never reached or investigated
renders as a redlink even though the entity exists in the graph (no
global oracle; the redlink IS the honest "you don't know this yet").
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token

from babylon.models.enums.topology import NodeType
from babylon.projection.epistemic_search import known_entity_ids
from babylon.projection.fog.ledger import IntelEntry, IntelLedger
from babylon.topology import BabylonGraph
from babylon.tui.wikilinks import known_target_resolver, wikilink_plugin


def _graph() -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node("ORG1", NodeType.ORGANIZATION, name="Player Org")
    graph.add_node("ORG2", NodeType.ORGANIZATION, name="Rival Org")
    graph.add_node("T1", NodeType.TERRITORY, name="Home Territory")
    graph.add_node("C1", NodeType.SOCIAL_CLASS, name="Detroit Proletariat")
    graph.add_edge("ORG1", "T1", "presence")
    graph.add_edge("C1", "T1", "tenancy")
    return graph


def _inline_children(markdown: str, known: frozenset[str]) -> list[Token]:
    parser = MarkdownIt()
    wikilink_plugin(parser, known_target_resolver(known))
    tokens = parser.parse(markdown)
    inline = next(token for token in tokens if token.type == "inline")
    assert inline.children is not None
    return inline.children


class TestEpistemicResolver:
    def test_reached_entity_resolves_as_wikilink(self) -> None:
        known = known_entity_ids(_graph(), "ORG1", ledger=IntelLedger(), radius=1)
        children = _inline_children("[[C1]]", known)
        assert children[0].type == "wikilink_open"

    def test_existing_but_unknown_entity_renders_as_redlink(self) -> None:
        """ORG2 exists in the graph — the resolver still redlinks it."""
        known = known_entity_ids(_graph(), "ORG1", ledger=IntelLedger(), radius=1)
        children = _inline_children("[[ORG2]]", known)
        assert children[0].type == "redlink_open"
        assert children[0].attrs["href"] == "babylon://redlink/ORG2"

    def test_intel_history_promotes_a_redlink_to_a_wikilink(self) -> None:
        """INVESTIGATE history is the second way of knowing: the same
        target flips from redlink to wikilink once it enters the ledger."""
        before = known_entity_ids(_graph(), "ORG1", ledger=IntelLedger(), radius=1)
        assert _inline_children("[[T9]]", before)[0].type == "redlink_open"

        ledger = IntelLedger().append(
            IntelEntry(node_id="T9", field_group="political", tick_observed=5)
        )
        after = known_entity_ids(_graph(), "ORG1", ledger=ledger, radius=1)
        assert _inline_children("[[T9]]", after)[0].type == "wikilink_open"
