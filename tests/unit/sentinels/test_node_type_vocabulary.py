"""Vocabulary-sentinel tests: the gate is live, and its eye is not blind.

Two tiers, because a static gate can fail in two directions:

- **Liveness** — the five rules are clean against the real tree right now.
- **Efficacy** — the AST extractor actually SEES each syntactic form it claims
  to cover. This tier is the load-bearing one: a scanner that silently returns
  nothing passes every liveness assertion while enforcing nothing, which is the
  same "green over dead" shape the sentinel exists to prevent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.models.enums import EdgeType, NodeType
from babylon.sentinels._ast import (
    add_node_attribute_stamps,
    edge_source_type_uses,
    graph_node_attribute_reads,
    node_type_uses,
)
from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.exemptions import SentinelExemption
from babylon.sentinels.vocabulary import (
    fabricated_edge_sources,
    fabricated_node_attributes,
    invented_node_types,
    phantom_attribute_uses,
    unstamped_queried_node_types,
)
from babylon.sentinels.vocabulary.registry import MODEL_FIELDS_BY_NODE_TYPE

pytestmark = pytest.mark.unit


def _uses(tmp_path: Path, source: str) -> set[tuple[str, str]]:
    """Parse ``source`` and return its ``(literal, role)`` pairs."""
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    return {(literal, role) for _lineno, literal, role in node_type_uses(path)}


def _stamps(tmp_path: Path, source: str) -> set[tuple[str, str]]:
    """Parse ``source`` and return its ``(node_type, attribute)`` pairs."""
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    return {(node_type, attr) for _lineno, node_type, attr in add_node_attribute_stamps(path)}


# ---------------------------------------------------------------------------
# Liveness: the gate is clean against the real tree.
# ---------------------------------------------------------------------------


def test_no_invented_node_types_in_repo() -> None:
    """Rule (a): every node-type literal in src/, web/ and tests/ is declared."""
    assert invented_node_types() == []


def test_every_production_queried_node_type_is_production_stamped() -> None:
    """Rule (b): production queries close against production stamps."""
    assert unstamped_queried_node_types() == []


def test_no_fabricated_node_attributes_in_repo() -> None:
    """Rule (c): every stamped attribute on a known node type is real shape."""
    assert fabricated_node_attributes() == []


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


# ---------------------------------------------------------------------------
# Rule (c) — shape closure: the extractor sees each form it claims to cover.
# ---------------------------------------------------------------------------


def test_shape_extractor_sees_two_positional_form_with_kwargs(tmp_path: Path) -> None:
    """``add_node(id, "social_class", wealth=1.0, territory_ids=[...])``."""
    found = _stamps(
        tmp_path,
        'g.add_node("C1", "social_class", wealth=1.0, territory_ids=["T1"])',
    )
    assert found == {("social_class", "wealth"), ("social_class", "territory_ids")}


def test_shape_extractor_sees_node_type_keyword_form_with_kwargs(tmp_path: Path) -> None:
    """``add_node(id, _node_type="territory", heat=0.1)`` -- authoring form."""
    found = _stamps(tmp_path, 'g.add_node("T1", _node_type="territory", heat=0.1)')
    assert found == {("territory", "heat")}


def test_shape_extractor_sees_nodetype_member_form(tmp_path: Path) -> None:
    """``_node_type=NodeType.SOCIAL_CLASS`` resolves the same as the literal."""
    found = _stamps(tmp_path, 'g.add_node("C1", _node_type=NodeType.SOCIAL_CLASS, wealth=1.0)')
    assert found == {("social_class", "wealth")}


def test_shape_extractor_sees_dict_literal_kwargs(tmp_path: Path) -> None:
    """``add_node(id, **{"_node_type": "territory", "heat": 0.1})``."""
    found = _stamps(tmp_path, 'g.add_node("T1", **{"_node_type": "territory", "heat": 0.1})')
    assert found == {("territory", "heat")}


def test_shape_extractor_ignores_unresolved_node_type(tmp_path: Path) -> None:
    """A variable node type is unresolvable statically -- honest absence, not a guess."""
    assert _stamps(tmp_path, 'g.add_node("C1", node_type_var, wealth=1.0)') == set()


def test_shape_extractor_ignores_update_node_calls(tmp_path: Path) -> None:
    """``update_node`` carries no co-located node type -- out of scope by design."""
    assert _stamps(tmp_path, 'g.update_node("C1", wealth=1.0)') == set()


def test_shape_extractor_ignores_variable_payload_unpacking(tmp_path: Path) -> None:
    """``add_node(id, "social_class", **payload)`` -- a variable payload
    contributes nothing (only dict LITERALS are inspected)."""
    assert _stamps(tmp_path, 'g.add_node("C1", "social_class", **payload)') == set()


def test_shape_founding_bug_would_be_caught() -> None:
    """The 2026-07-18 defect, reconstructed: ``territory_ids`` on a
    ``social_class`` node is not real shape -- ``SocialClass`` has no such
    field, so rule (c) would reject a fixture stamping it."""
    assert "territory_ids" not in MODEL_FIELDS_BY_NODE_TYPE["social_class"]
    assert "territory_ids" in MODEL_FIELDS_BY_NODE_TYPE["organization"]


# ---------------------------------------------------------------------------
# Mutation-validation: SentinelExemption teeth, exercised through the real
# rule (c) check (gate-governance ruling, 2026-07-18).
# ---------------------------------------------------------------------------


def test_attribute_exemption_does_not_absorb_a_different_symbol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exemption exact-keyed to one ``(file, node_type, attribute)``
    triple must NOT clear a genuinely different fabricated attribute in the
    SAME file on the SAME node type -- same shape, different symbol."""
    from babylon.sentinels.exemptions import SentinelExemption

    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "sample.py").write_text(
        'g.add_node("C1", "social_class", exempted_fake_attr=1.0, other_fake_attr=2.0)\n',
        encoding="utf-8",
    )
    exemption = SentinelExemption(
        key=("node_attribute", "src/sample.py", "social_class", "exempted_fake_attr"),
        reason="test exemption",
        owner="test",
        date="2026-07-18",
        tracking_task="#1",
    )
    monkeypatch.setattr("babylon.sentinels.vocabulary.checks._REPO_ROOT", tmp_path)
    monkeypatch.setattr("babylon.sentinels.vocabulary.checks.ATTRIBUTE_EXEMPTIONS", (exemption,))
    violations = fabricated_node_attributes()
    assert len(violations) == 1
    assert "other_fake_attr" in violations[0]
    assert "exempted_fake_attr" not in violations[0]


# ---------------------------------------------------------------------------
# Rule (d) — edge-shape closure (ADR087): every fixture-stamped
# (edge_type, source_node_type) combination must have a production producer,
# or a cited EDGE_SOURCE_ALLOWLIST entry.
# ---------------------------------------------------------------------------


def _edge_uses(tmp_path: Path, source: str) -> set[tuple[str, str]]:
    """Parse ``source`` and return its ``(edge_type, source_node_type)`` pairs."""
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    return {
        (edge_type, source_type) for _lineno, edge_type, source_type in edge_source_type_uses(path)
    }


def test_no_fabricated_edge_sources_in_repo() -> None:
    """Rule (d): every fixture-stamped edge-source combination has a
    production producer or a cited allowlist entry."""
    assert fabricated_edge_sources() == []


def test_edge_extractor_sees_add_edge_keyword_form(tmp_path: Path) -> None:
    """``add_node(id, TYPE)`` + ``add_edge(id, tgt, edge_type=EdgeType.X)``."""
    found = _edge_uses(
        tmp_path,
        "g.add_node('ORG1', NodeType.ORGANIZATION)\n"
        "g.add_edge('ORG1', 'C001', edge_type=EdgeType.SOLIDARITY)\n",
    )
    assert ("solidarity", "organization") in found


def test_edge_extractor_sees_add_edge_positional_form(tmp_path: Path) -> None:
    """``add_edge(source, target, "TYPE", ...)`` — the 3rd-positional protocol form."""
    found = _edge_uses(
        tmp_path,
        'g.add_node("C001", "social_class")\ng.add_edge("C001", "C002", "solidarity")\n',
    )
    assert ("solidarity", "social_class") in found


def test_edge_extractor_sees_relationship_constructor_form(tmp_path: Path) -> None:
    """``SocialClass(id=X, ...)`` + ``Relationship(source_id=X, edge_type=EdgeType.Y)``
    — the scenario-genesis pattern (``scenarios/_legacy.py``)."""
    found = _edge_uses(
        tmp_path,
        "worker = SocialClass(id=PERIPHERY_WORKER_ID, name='W')\n"
        "solidarity = Relationship(source_id=PERIPHERY_WORKER_ID, target_id=OTHER_ID, "
        "edge_type=EdgeType.SOLIDARITY)\n",
    )
    assert ("solidarity", "social_class") in found


def test_edge_extractor_resolves_dot_value_suffixed_edge_type(tmp_path: Path) -> None:
    """``edge_type=EdgeType.TRANSACTIONAL.value`` resolves the same as the
    bare member (a common real-code idiom, e.g. ``negotiate.py``)."""
    found = _edge_uses(
        tmp_path,
        "g.add_node('ORG1', NodeType.ORGANIZATION)\n"
        "g.add_edge('ORG1', 'ORG2', edge_type=EdgeType.TRANSACTIONAL.value)\n",
    )
    assert ("transactional", "organization") in found


def test_edge_extractor_ignores_an_unresolvable_variable_source(tmp_path: Path) -> None:
    """A runtime-parameter source (``org_id``, never bound in this file) is
    honest absence, not a guess -- mirrors real verb-resolver producers
    (``engine/actions/negotiate.py``, ``_mass_work.py``), which are
    deliberately invisible to this rule (see the allowlist docstring)."""
    found = _edge_uses(
        tmp_path, "graph.add_edge(org_id, target_id, edge_type=EdgeType.SOLIDARITY)\n"
    )
    assert found == set()


def test_edge_extractor_raises_on_unparseable_source(tmp_path: Path) -> None:
    """A broken file is an infrastructure failure, never a silent empty pass."""
    path = tmp_path / "broken.py"
    path.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        edge_source_type_uses(path)


def test_edge_founding_bug_would_be_caught(tmp_path: Path) -> None:
    """The ADR085 defect, reconstructed: a fabricated 'vanguard' organization
    node feeding a fabricated org-sourced SOLIDARITY edge -- the exact shape
    the salvage test's original fixture used, and rule (d) exists to reject."""
    found = _edge_uses(
        tmp_path,
        "graph.add_node(_ORG_ID, NodeType.ORGANIZATION, cadre_level=cadre_level)\n"
        "graph.add_edge(_ORG_ID, _CLASS_ID, edge_type=EdgeType.SOLIDARITY, "
        "solidarity_strength=_SOLIDARITY_STRENGTH)\n",
    )
    assert (EdgeType.SOLIDARITY.value, "organization") in found


def test_edge_source_allowlist_does_not_absorb_a_different_combination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An allowlist entry for one (edge_type, source_type) pair must NOT
    clear a genuinely different fabricated combination in the same tree —
    mirrors ``test_attribute_exemption_does_not_absorb_a_different_symbol``'s
    exact discipline for rule (c), applied to rule (d)'s type-level list."""
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "sample.py").write_text(
        "graph.add_node('ORG1', NodeType.ORGANIZATION)\n"
        "graph.add_node('C001', NodeType.SOCIAL_CLASS)\n"
        "graph.add_edge('ORG1', 'C001', edge_type=EdgeType.SOLIDARITY)\n"
        "graph.add_edge('ORG1', 'C001', edge_type=EdgeType.MEMBERSHIP)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("babylon.sentinels.vocabulary.checks._REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        "babylon.sentinels.vocabulary.checks.EDGE_SOURCE_ALLOWLIST",
        frozenset({("membership", "organization")}),
    )
    violations = fabricated_edge_sources()
    assert len(violations) == 1
    assert "solidarity" in violations[0]
    assert "membership" not in violations[0]


def test_edge_source_allowlist_clears_a_genuinely_allowlisted_combination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reverse of the above: the SAME combination, once allowlisted,
    produces zero violations (red -> green round-trip)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "sample.py").write_text(
        "graph.add_node('ORG1', NodeType.ORGANIZATION)\n"
        "graph.add_node('C001', NodeType.SOCIAL_CLASS)\n"
        "graph.add_edge('ORG1', 'C001', edge_type=EdgeType.SOLIDARITY)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("babylon.sentinels.vocabulary.checks._REPO_ROOT", tmp_path)

    # RED: not yet allowlisted.
    monkeypatch.setattr("babylon.sentinels.vocabulary.checks.EDGE_SOURCE_ALLOWLIST", frozenset())
    assert fabricated_edge_sources() != []

    # GREEN: allowlisted.
    monkeypatch.setattr(
        "babylon.sentinels.vocabulary.checks.EDGE_SOURCE_ALLOWLIST",
        frozenset({("solidarity", "organization")}),
    )
    assert fabricated_edge_sources() == []


# ---------------------------------------------------------------------------
# Rule (e) — phantom-attribute closure (task #40): no banned attribute is
# read off, or stamped onto, a graph node.
# ---------------------------------------------------------------------------


def test_no_phantom_attribute_uses_in_repo() -> None:
    """Rule (e): no banned attribute is read off or stamped onto a graph
    node anywhere in src/, web/ or tests/ (beyond the two owner-gated,
    out-of-scope exemptions this module's own registry cites)."""
    assert phantom_attribute_uses() == []


def test_read_extractor_sees_get_call_on_bound_node_payload(tmp_path: Path) -> None:
    """``member_data = graph.nodes.get(x, {})`` then
    ``member_data.get("community_type")`` -- the two-step bind-then-read
    idiom every real violation in this codebase uses."""
    path = tmp_path / "sample.py"
    path.write_text(
        'member_data = graph.nodes.get(x, {})\nmember_data.get("community_type", "")\n',
        encoding="utf-8",
    )
    assert (2, "community_type") in graph_node_attribute_reads(path, frozenset({"community_type"}))


def test_read_extractor_sees_pop_call_on_bound_node_payload(tmp_path: Path) -> None:
    """``.pop("attr")`` is also a read (mirrors ``_is_type_key_read``'s own
    ``get``/``pop`` pair)."""
    path = tmp_path / "sample.py"
    path.write_text(
        'row = graph.nodes.get(x, {})\nrow.pop("community_type")\n',
        encoding="utf-8",
    )
    assert (2, "community_type") in graph_node_attribute_reads(path, frozenset({"community_type"}))


def test_read_extractor_sees_subscript_on_bound_node_payload(tmp_path: Path) -> None:
    """``target_data["community_type"]`` -- the subscript read form."""
    path = tmp_path / "sample.py"
    path.write_text(
        'target_data = graph.nodes[x]\nv = target_data["community_type"]\n',
        encoding="utf-8",
    )
    assert (2, "community_type") in graph_node_attribute_reads(path, frozenset({"community_type"}))


def test_read_extractor_sees_direct_chained_form(tmp_path: Path) -> None:
    """``graph.nodes.get(x, {}).get("community_type")`` -- no intermediate
    variable needed."""
    path = tmp_path / "sample.py"
    path.write_text('graph.nodes.get(x, {}).get("community_type")\n', encoding="utf-8")
    assert (1, "community_type") in graph_node_attribute_reads(path, frozenset({"community_type"}))


def test_read_extractor_ignores_unrelated_dict_reads(tmp_path: Path) -> None:
    """A ``.get("community_type")`` read on a name NEVER bound from
    ``graph.nodes`` (a DB row, an arbitrary list item) is a different
    namespace entirely -- invisible to this rule by construction."""
    path = tmp_path / "sample.py"
    path.write_text('row = cursor.fetchone()\nrow.get("community_type")\n', encoding="utf-8")
    assert graph_node_attribute_reads(path, frozenset({"community_type"})) == []


def test_stamp_extractor_reuses_add_node_attribute_stamps(tmp_path: Path) -> None:
    """The STAMP side reuses the existing rule-(c) extractor unmodified --
    any node type, since the point is no production code stamps this
    attribute onto ANY graph node."""
    path = tmp_path / "sample.py"
    path.write_text(
        'g.add_node("P1", _node_type="person", community_type="new_afrikan")\n',
        encoding="utf-8",
    )
    stamps = add_node_attribute_stamps(path)
    assert (1, "person", "community_type") in stamps


def test_founding_bug_would_be_caught_by_phantom_read_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The task #40 defect, reconstructed: a ``.get("community_type")`` read
    off a real graph-node payload is rejected by rule (e)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "sample.py").write_text(
        'node_data = graph.nodes.get(org_id, {})\nnode_data.get("community_type")\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("babylon.sentinels.vocabulary.checks._REPO_ROOT", tmp_path)
    monkeypatch.setattr("babylon.sentinels.vocabulary.checks.PHANTOM_ATTRIBUTE_EXEMPTIONS", ())
    violations = phantom_attribute_uses()
    assert len(violations) == 1
    assert "community_type" in violations[0]


def test_phantom_exemption_does_not_absorb_a_different_symbol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exemption exact-keyed to one ``(kind, file, attribute)`` triple
    must NOT clear a genuinely different banned attribute in the SAME file
    -- mirrors ``test_attribute_exemption_does_not_absorb_a_different_symbol``'s
    exact discipline for rule (c), applied to rule (e). Uses synthetic
    attribute names (not ``community_type``) so the assertion cannot be
    fooled by ``_WHY_PHANTOM``'s own boilerplate example text."""
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "sample.py").write_text(
        "node_data = graph.nodes.get(org_id, {})\n"
        'node_data.get("exempted_fake_attr")\n'
        'node_data.get("other_fake_attr")\n',
        encoding="utf-8",
    )
    exemption = SentinelExemption(
        key=("phantom_attribute_read", "src/sample.py", "exempted_fake_attr"),
        reason="test exemption",
        owner="test",
        date="2026-07-19",
        tracking_task="#1",
    )
    monkeypatch.setattr("babylon.sentinels.vocabulary.checks._REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        "babylon.sentinels.vocabulary.checks.PHANTOM_ATTRIBUTE_READS",
        frozenset({"exempted_fake_attr", "other_fake_attr"}),
    )
    monkeypatch.setattr(
        "babylon.sentinels.vocabulary.checks.PHANTOM_ATTRIBUTE_EXEMPTIONS", (exemption,)
    )
    violations = phantom_attribute_uses()
    assert len(violations) == 1
    assert "other_fake_attr" in violations[0]
    assert "exempted_fake_attr" not in violations[0]


def test_phantom_read_extractor_raises_on_unparseable_source(tmp_path: Path) -> None:
    """A broken file is an infrastructure failure, never a silent empty pass."""
    path = tmp_path / "broken.py"
    path.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        graph_node_attribute_reads(path, frozenset({"community_type"}))
