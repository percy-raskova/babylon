"""Vocabulary-sentinel tests: the gate is live, and its eye is not blind.

Two tiers, because a static gate can fail in two directions:

- **Liveness** — the two rules are clean against the real tree right now.
- **Efficacy** — the AST extractor actually SEES each syntactic form it claims
  to cover. This tier is the load-bearing one: a scanner that silently returns
  nothing passes every liveness assertion while enforcing nothing, which is the
  same "green over dead" shape the sentinel exists to prevent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.models.enums import NodeType
from babylon.sentinels._ast import node_type_uses
from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.vocabulary import (
    invented_node_types,
    unstamped_queried_node_types,
)

pytestmark = pytest.mark.unit


def _uses(tmp_path: Path, source: str) -> set[tuple[str, str]]:
    """Parse ``source`` and return its ``(literal, role)`` pairs."""
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    return {(literal, role) for _lineno, literal, role in node_type_uses(path)}


# ---------------------------------------------------------------------------
# Liveness: the gate is clean against the real tree.
# ---------------------------------------------------------------------------


def test_no_invented_node_types_in_repo() -> None:
    """Rule (a): every node-type literal in src/, web/ and tests/ is declared."""
    assert invented_node_types() == []


def test_every_production_queried_node_type_is_production_stamped() -> None:
    """Rule (b): production queries close against production stamps."""
    assert unstamped_queried_node_types() == []


# ---------------------------------------------------------------------------
# Efficacy: the extractor sees each form it claims to cover.
# ---------------------------------------------------------------------------


def test_extractor_sees_protocol_form_stamp(tmp_path: Path) -> None:
    """``add_node(id, "social_class")`` — 2nd-positional protocol form."""
    assert ("social_class", "stamp") in _uses(tmp_path, 'g.add_node("C1", "social_class")')


def test_extractor_sees_authoring_form_stamp(tmp_path: Path) -> None:
    """``add_node(id, _node_type="territory")`` — keyword authoring form."""
    assert ("territory", "stamp") in _uses(tmp_path, 'g.add_node("T1", _node_type="territory")')


def test_extractor_sees_assignment_stamp(tmp_path: Path) -> None:
    """``nodes[id]["_node_type"] = "community"`` — the test-harness form."""
    assert ("community", "stamp") in _uses(tmp_path, 'g.nodes[n]["_node_type"] = "community"')


def test_extractor_sees_dict_literal_stamp(tmp_path: Path) -> None:
    """``{"_node_type": "person"}`` — the conftest payload form."""
    assert ("person", "stamp") in _uses(tmp_path, 'PAYLOAD = {"_node_type": "person", "x": 1}')


def test_extractor_sees_query_nodes_call(tmp_path: Path) -> None:
    """``query_nodes(node_type="faction")`` — the canonical query form."""
    assert ("faction", "query") in _uses(tmp_path, 'g.query_nodes(node_type="faction")')


def test_extractor_sees_equality_comparison(tmp_path: Path) -> None:
    """``data.get("_node_type") == "organization"`` — the bridge's form."""
    assert ("organization", "query") in _uses(
        tmp_path, 'if data.get("_node_type") == "organization": pass'
    )


def test_extractor_sees_membership_comparison(tmp_path: Path) -> None:
    """``.get("_node_type") in (...)`` contributes every member of the tuple."""
    found = _uses(tmp_path, 'if d.get("_node_type") in ("social_class", "organization"): pass')
    assert {("social_class", "query"), ("organization", "query")} <= found


def test_extractor_resolves_nodetype_members_not_just_literals(tmp_path: Path) -> None:
    """``NodeType.TERRITORY`` resolves to ``"territory"``.

    Regression guard for a blind spot found while building this sentinel: with
    literal-only extraction, adopting the enum at the stamp sites emptied the
    observed stamp set, and rule (b) then reported every queried type as
    unstamped. Enum adoption must make the gate stronger, never blind.
    """
    found = _uses(
        tmp_path,
        "g.add_node('T1', _node_type=NodeType.TERRITORY)\n"
        "g.query_nodes(node_type=NodeType.SOCIAL_CLASS)\n",
    )
    assert ("territory", "stamp") in found
    assert ("social_class", "query") in found


def test_extractor_ignores_docstrings_and_comments(tmp_path: Path) -> None:
    """Prose mentioning a node type is not a use — only real code counts."""
    source = '"""Example: add_node(id, "made_up_type").\n\nSee _node_type."""\n# "another_fake"\n'
    assert _uses(tmp_path, source) == set()


def test_extractor_raises_on_unparseable_source(tmp_path: Path) -> None:
    """A broken file is an infrastructure failure, never a silent empty pass."""
    path = tmp_path / "broken.py"
    path.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        node_type_uses(path)


def test_founding_bug_would_be_caught(tmp_path: Path) -> None:
    """The 2026-07-18 defect, reconstructed: the sentinel must reject it.

    A fixture stamping ``"balkanization_faction"`` is not a ``NodeType``
    member, so rule (a) rejects the literal wherever it appears.
    """
    found = _uses(tmp_path, 'g.add_node("FAC_A", "balkanization_faction")')
    assert ("balkanization_faction", "stamp") in found
    assert "balkanization_faction" not in {member.value for member in NodeType}


@pytest.mark.parametrize(
    ("offender", "expected"),
    [
        ("balkanization_faction", NodeType.FACTION),
        ("SocialClass", NodeType.SOCIAL_CLASS),
        ("social_klass", NodeType.SOCIAL_CLASS),
        ("hex_cell", NodeType.HEX),
    ],
)
def test_suggestion_points_at_the_right_member(offender: str, expected: NodeType) -> None:
    """The hint must name the member a reader would actually want.

    Edit distance alone sends ``balkanization_faction`` to ``organization``,
    which actively misleads. The suggestion is the agent-facing half of the
    failure message, so a wrong hint is worse than none.
    """
    from babylon.sentinels.vocabulary.checks import _suggest

    assert f"NodeType.{expected.name}" in _suggest(offender)


def test_cli_entry_point_is_clean() -> None:
    """``sentinel_check.py vocabulary --check`` exits 0 against the real tree."""
    from babylon.sentinels.vocabulary.checks import main

    assert main(["--check"]) == 0
