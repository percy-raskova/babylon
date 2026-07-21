"""Tests for the shared AST helpers added for the U7 sentinel family.

These helpers let a layer-0.5 sensor prove facts about ``domain``/``engine``/
``tools`` source WITHOUT importing it (the import-linter contract in
``pyproject.toml`` forbids the import; the sensors must stay cheap and static).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from babylon.models.enums.events import EventType
from babylon.sentinels._ast import (
    all_dict_literal_str_items,
    attribute_is_none_guard_lines,
    conditional_literal_returns_by_enum_member,
    coupling_edges,
    dict_get_call_lines,
    frozenset_str_members,
    function_return_annotation_name,
    hasattr_guard_lines,
    literal_keyword_call_lines,
    module_level_function_names,
    optional_dict_literal_str_items,
    parse_module,
    referenced_names,
    returned_dict_keys,
)
from babylon.sentinels.base import SentinelCheckError

pytestmark = pytest.mark.unit

_REPO_ROOT: Path = Path(__file__).resolve().parents[3]


def test_parse_module_returns_a_module(tmp_path: Path) -> None:
    """A well-formed file parses to an ``ast.Module``."""
    target = tmp_path / "ok.py"
    target.write_text("X = 1\n", encoding="utf-8")
    assert isinstance(parse_module(target), ast.Module)


def test_parse_module_raises_on_missing_file(tmp_path: Path) -> None:
    """A missing file is infrastructure failure, never a silent empty result."""
    with pytest.raises(SentinelCheckError, match="cannot read"):
        parse_module(tmp_path / "absent.py")


def test_parse_module_raises_on_syntax_error(tmp_path: Path) -> None:
    """An unparseable file is infrastructure failure (exit 2, not a false pass)."""
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError, match="cannot parse"):
        parse_module(target)


def test_referenced_names_covers_names_attributes_keywords_and_strings(
    tmp_path: Path,
) -> None:
    """Every way a module can mention a symbol counts as a reference."""
    target = tmp_path / "refs.py"
    target.write_text(
        "\n".join(
            [
                "import thing",
                "def f(graph):",
                "    graph.update_node(node_id, price_divergence=1.0)",
                "    return thing.fictitious_log, attrs.get('national_financial')",
            ]
        ),
        encoding="utf-8",
    )
    names = referenced_names(target)
    assert "graph" in names
    assert "update_node" in names
    assert "price_divergence" in names
    assert "fictitious_log" in names
    assert "national_financial" in names


def test_coupling_edges_reads_the_real_catalog() -> None:
    """The production catalog's declared ``Coupling(...)`` literals are extracted."""
    edges = coupling_edges(_REPO_ROOT / "src/babylon/domain/dialectics/instances/catalog.py")
    assert ("surplus_distribution", "debt_spiral", "transforms") in edges
    assert ("credit", "financial", "transforms") in edges
    assert ("capital_labor", "imperial", "antagonizes") in edges


def test_coupling_edges_skips_non_literal_calls(tmp_path: Path) -> None:
    """A computed endpoint yields no row rather than raising."""
    target = tmp_path / "couplings.py"
    target.write_text(
        "E = (\n"
        "    Coupling(source='a', target='b', kind='feeds'),\n"
        "    Coupling(source=key, target='c', kind='feeds'),\n"
        ")\n",
        encoding="utf-8",
    )
    assert coupling_edges(target) == (("a", "b", "feeds"),)


def test_returned_dict_keys_reads_the_real_financial_factory() -> None:
    """The Vol III factory's returned service-key set is extracted statically."""
    keys = returned_dict_keys(
        _REPO_ROOT / "src/babylon/domain/economics/factory.py",
        "create_financial_services",
    )
    assert "distribution_calculator" in keys
    assert "financial_crisis_assessor" in keys
    assert "fictitious_capital_calculator" in keys


def test_returned_dict_keys_raises_on_unknown_function(tmp_path: Path) -> None:
    """Naming a function the file lacks is infrastructure failure, not silence."""
    target = tmp_path / "mod.py"
    target.write_text("def g():\n    return {'a': 1}\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError, match="no function"):
        returned_dict_keys(target, "does_not_exist")


def test_returned_dict_keys_takes_only_the_last_top_level_return(tmp_path: Path) -> None:
    """A dead/superseded early ``return {...}`` branch must not leak its keys in."""
    target = tmp_path / "mod.py"
    target.write_text(
        "\n".join(
            [
                "def make():",
                "    if False:",
                "        return {'dead_key': 1}",
                "    return {'real_key': 2}",
            ]
        ),
        encoding="utf-8",
    )
    assert returned_dict_keys(target, "make") == ("real_key",)


def test_frozenset_str_members_reads_a_frozenset_literal(tmp_path: Path) -> None:
    """U7.11: a module-level ``VAR: frozenset[str] = frozenset({...})`` reads back
    as the set of its string members, statically (no import)."""
    target = tmp_path / "m.py"
    target.write_text(
        "from __future__ import annotations\n"
        "EXPECTED: frozenset[str] = frozenset({'A', 'B', 'C'})\n",
        encoding="utf-8",
    )
    assert set(frozenset_str_members(target, "EXPECTED")) == {"A", "B", "C"}


def test_frozenset_str_members_raises_on_absent_var_name(tmp_path: Path) -> None:
    """A renamed/typo'd baseline variable is infrastructure failure, not an
    empty (and therefore falsely drift-free) baseline — mirrors
    ``literal_str_tuple``'s contract for the same failure mode."""
    target = tmp_path / "m.py"
    target.write_text("OTHER = frozenset({'A'})\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError, match="no module-level assignment"):
        frozenset_str_members(target, "EXPECTED")


def test_frozenset_str_members_raises_on_non_literal_value(tmp_path: Path) -> None:
    """A computed/aliased baseline (not a set/list/tuple literal) must raise,
    not silently read back as an empty baseline."""
    target = tmp_path / "m.py"
    target.write_text(
        "OTHER = frozenset({'A'})\nEXPECTED = OTHER\n",
        encoding="utf-8",
    )
    with pytest.raises(SentinelCheckError, match="not a frozenset/set/list/tuple literal"):
        frozenset_str_members(target, "EXPECTED")


def test_optional_dict_literal_str_items_returns_empty_when_absent(tmp_path: Path) -> None:
    """T1.1 U6: absence of the named var is the CLEAN state (severity is
    single-sourced), never an error — the opposite contract of
    ``literal_dict_keys``."""
    target = tmp_path / "m.py"
    target.write_text("OTHER = {'a': 'b'}\n", encoding="utf-8")
    assert optional_dict_literal_str_items(target, "_EVENT_SEVERITY") == {}


def test_optional_dict_literal_str_items_reads_a_present_dict(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        '_EVENT_SEVERITY = {"economic_crisis": "critical", "surplus_extraction": "informational"}\n',
        encoding="utf-8",
    )
    assert optional_dict_literal_str_items(target, "_EVENT_SEVERITY") == {
        "economic_crisis": "critical",
        "surplus_extraction": "informational",
    }


def test_optional_dict_literal_str_items_skips_non_literal_entries(tmp_path: Path) -> None:
    """A computed key or value (e.g. ``EventType.X.value``) is invisible to a
    static reader — skipped, never misread as a literal."""
    target = tmp_path / "m.py"
    target.write_text(
        "\n".join(
            [
                "_EVENT_SEVERITY = {",
                "    EventType.ECONOMIC_CRISIS.value: 'critical',",
                "    'pogrom': SOME_VARIABLE,",
                "    'lockout': 'warning',",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    assert optional_dict_literal_str_items(target, "_EVENT_SEVERITY") == {"lockout": "warning"}


def test_optional_dict_literal_str_items_raises_on_non_dict_value(tmp_path: Path) -> None:
    """The name IS bound, but not to a dict literal — a genuinely malformed
    reappearance, distinct from clean absence."""
    target = tmp_path / "m.py"
    target.write_text("_EVENT_SEVERITY = some_function()\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError, match="not a dict literal"):
        optional_dict_literal_str_items(target, "_EVENT_SEVERITY")


def test_optional_dict_literal_str_items_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError, match="cannot parse"):
        optional_dict_literal_str_items(target, "_EVENT_SEVERITY")


def test_all_dict_literal_str_items_returns_every_named_dict(tmp_path: Path) -> None:
    """T1.1 U6 post-review hardening: unlike ``optional_dict_literal_str_items``
    (one watched name), this returns EVERY module-level dict literal, keyed by
    its own name -- a re-forked severity table does not stop being a re-fork
    just because it is renamed away from the two retired literal names."""
    target = tmp_path / "m.py"
    target.write_text(
        "\n".join(
            [
                "_FIRST = {'a': 'b'}",
                "_SECOND = {'bifurcation_threshold': 'warning'}",
                "NOT_A_DICT = 'plain string'",
            ]
        ),
        encoding="utf-8",
    )
    assert all_dict_literal_str_items(target) == {
        "_FIRST": {"a": "b"},
        "_SECOND": {"bifurcation_threshold": "warning"},
    }


def test_all_dict_literal_str_items_skips_non_literal_entries(tmp_path: Path) -> None:
    """Mirrors ``optional_dict_literal_str_items``'s own "skip, don't except"
    stance on a computed key/value; a dict left with NO literal entries at all
    contributes nothing."""
    target = tmp_path / "m.py"
    target.write_text(
        "\n".join(
            [
                "_MIXED = {EventType.ECONOMIC_CRISIS.value: 'critical', 'lockout': 'warning'}",
                "_ALL_COMPUTED = {SOME_KEY: SOME_VALUE}",
            ]
        ),
        encoding="utf-8",
    )
    assert all_dict_literal_str_items(target) == {"_MIXED": {"lockout": "warning"}}


def test_all_dict_literal_str_items_returns_empty_for_no_dicts(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("X = 1\n", encoding="utf-8")
    assert all_dict_literal_str_items(target) == {}


def test_all_dict_literal_str_items_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError, match="cannot parse"):
        all_dict_literal_str_items(target)


def test_conditional_literal_returns_finds_a_bare_string_return(tmp_path: Path) -> None:
    """T1.1 U6 post-review hardening: an inline per-member override folded
    straight into a classify function's control flow -- no dict literal at
    all -- is the vector the two dict-literal prongs above cannot see."""
    target = tmp_path / "m.py"
    target.write_text(
        "\n".join(
            [
                "def classify(event_type):",
                "    if event_type == EventType.BIFURCATION_THRESHOLD:",
                "        return 'warning'",
                "    return resolve_severity(event_type).tier",
            ]
        ),
        encoding="utf-8",
    )
    tiers = frozenset({"critical", "warning", "informational"})
    assert conditional_literal_returns_by_enum_member(target, tiers, EventType, "EventType") == {
        "bifurcation_threshold": "warning"
    }


def test_conditional_literal_returns_finds_a_tier_keyword_return(tmp_path: Path) -> None:
    """The Archive Chronicle's real return shape wraps the tier in a
    ``Model(tier=..., ...)`` call, not a bare string -- the keyword form must
    be recognized too."""
    target = tmp_path / "m.py"
    target.write_text(
        "\n".join(
            [
                "def classify(event_type):",
                "    if event_type == EventType.BIFURCATION_THRESHOLD:",
                "        return EventSalience(tier='warning', unclassified=False)",
                "    severity = resolve_severity(event_type)",
                "    return EventSalience(tier=severity.tier, unclassified=severity.unclassified)",
            ]
        ),
        encoding="utf-8",
    )
    tiers = frozenset({"critical", "warning", "informational"})
    assert conditional_literal_returns_by_enum_member(target, tiers, EventType, "EventType") == {
        "bifurcation_threshold": "warning"
    }


def test_conditional_literal_returns_finds_a_membership_fan_in(tmp_path: Path) -> None:
    """``if event_type in {EventType.A, EventType.B}: return "<tier>"`` -- a
    fan-in branch over several members, not just a single ``==``."""
    target = tmp_path / "m.py"
    target.write_text(
        "\n".join(
            [
                "def classify(event_type):",
                "    if event_type in {EventType.POGROM, EventType.LOCKOUT}:",
                "        return 'critical'",
                "    return resolve_severity(event_type).tier",
            ]
        ),
        encoding="utf-8",
    )
    tiers = frozenset({"critical", "warning", "informational"})
    assert conditional_literal_returns_by_enum_member(target, tiers, EventType, "EventType") == {
        "pogrom": "critical",
        "lockout": "critical",
    }


def test_conditional_literal_returns_ignores_an_unrelated_if(tmp_path: Path) -> None:
    """An ``if`` not keyed on the enum at all, or one whose branch does not
    return a tier literal, contributes nothing -- avoids false positives on
    unrelated control flow (e.g. the Archive's own ``compute_autopause_state``,
    which branches on a ``.tier`` VALUE comparison, not an enum-member key)."""
    target = tmp_path / "m.py"
    target.write_text(
        "\n".join(
            [
                "def compute_autopause_state(events):",
                "    for event in events:",
                "        if classify(event).tier == 'critical':",
                "            return AutopauseState(active=True)",
                "    return AutopauseState(active=False)",
            ]
        ),
        encoding="utf-8",
    )
    tiers = frozenset({"critical", "warning", "informational"})
    assert conditional_literal_returns_by_enum_member(target, tiers, EventType, "EventType") == {}


def test_conditional_literal_returns_ignores_an_except_clause(tmp_path: Path) -> None:
    """The Loud-Failure floor's own ``except ValueError: return "warning"`` is
    not keyed on any enum member at all -- must not be mistaken for a
    per-member override."""
    target = tmp_path / "m.py"
    target.write_text(
        "\n".join(
            [
                "def classify(event_type_str):",
                "    try:",
                "        event_type = EventType(event_type_str.lower())",
                "    except ValueError:",
                "        return 'warning'",
                "    return resolve_severity(event_type).tier",
            ]
        ),
        encoding="utf-8",
    )
    tiers = frozenset({"critical", "warning", "informational"})
    assert conditional_literal_returns_by_enum_member(target, tiers, EventType, "EventType") == {}


def test_conditional_literal_returns_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    tiers = frozenset({"critical", "warning", "informational"})
    with pytest.raises(SentinelCheckError, match="cannot parse"):
        conditional_literal_returns_by_enum_member(target, tiers, EventType, "EventType")


def test_returned_dict_keys_excludes_nested_scope_returns(tmp_path: Path) -> None:
    """A dict-returning method on a class/closure declared inside stays out."""
    target = tmp_path / "mod.py"
    target.write_text(
        "\n".join(
            [
                "def make():",
                "    class _Adapter:",
                "        def as_dict(self) -> dict:",
                "            return {'nested_key': 1}",
                "    def inner():",
                "        return {'closure_key': 2}",
                "    _Adapter()",
                "    inner()",
                "    return {'real_key': 3}",
            ]
        ),
        encoding="utf-8",
    )
    assert returned_dict_keys(target, "make") == ("real_key",)


# ---------------------------------------------------------------------------
# attribute_is_none_guard_lines (T1.1 U4 gate-satisfaction) -- efficacy
# ---------------------------------------------------------------------------


def test_attribute_is_none_guard_lines_finds_a_direct_comparison(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        "def f(services):\n    if services.foo is None:\n        return\n",
        encoding="utf-8",
    )
    assert attribute_is_none_guard_lines(target, "foo") == [2]


def test_attribute_is_none_guard_lines_finds_the_reversed_operand_order(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        "def f(services):\n    if None is services.foo:\n        return\n",
        encoding="utf-8",
    )
    assert attribute_is_none_guard_lines(target, "foo") == [2]


def test_attribute_is_none_guard_lines_ignores_a_different_attribute(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        "def f(services):\n    if services.bar is None:\n        return\n",
        encoding="utf-8",
    )
    assert attribute_is_none_guard_lines(target, "foo") == []


def test_attribute_is_none_guard_lines_ignores_a_non_none_comparison(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        "def f(services):\n    if services.foo == 0:\n        return\n",
        encoding="utf-8",
    )
    assert attribute_is_none_guard_lines(target, "foo") == []


def test_attribute_is_none_guard_lines_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        attribute_is_none_guard_lines(target, "foo")


# ---------------------------------------------------------------------------
# dict_get_call_lines (T1.1 U4 gate-satisfaction) -- efficacy
# ---------------------------------------------------------------------------


def test_dict_get_call_lines_finds_the_literal_key(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        'def f(context):\n    return context.get("vol2_step")\n',
        encoding="utf-8",
    )
    assert dict_get_call_lines(target, "vol2_step") == [2]


def test_dict_get_call_lines_ignores_a_different_key(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        'def f(context):\n    return context.get("other_key")\n',
        encoding="utf-8",
    )
    assert dict_get_call_lines(target, "vol2_step") == []


def test_dict_get_call_lines_ignores_a_differently_named_method(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        'def f(context):\n    return context.fetch("vol2_step")\n',
        encoding="utf-8",
    )
    assert dict_get_call_lines(target, "vol2_step") == []


def test_dict_get_call_lines_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        dict_get_call_lines(target, "vol2_step")


# ---------------------------------------------------------------------------
# hasattr_guard_lines (T1.1 U4 gate-satisfaction) -- efficacy
# ---------------------------------------------------------------------------


def test_hasattr_guard_lines_finds_the_literal_attr(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        'def f(context):\n    return context.x if hasattr(context, "session_id") else None\n',
        encoding="utf-8",
    )
    assert hasattr_guard_lines(target, "session_id") == [2]


def test_hasattr_guard_lines_ignores_a_different_attr(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        'def f(context):\n    return hasattr(context, "other_attr")\n',
        encoding="utf-8",
    )
    assert hasattr_guard_lines(target, "session_id") == []


def test_hasattr_guard_lines_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        hasattr_guard_lines(target, "session_id")


# ---------------------------------------------------------------------------
# literal_keyword_call_lines (T1.1 U5 stub-vs-calculator) -- efficacy
# ---------------------------------------------------------------------------


def test_literal_keyword_call_lines_finds_a_bare_constant_keyword(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("value = Thing(condition_met=True, gap=0.0)\n", encoding="utf-8")
    assert literal_keyword_call_lines(target, "Thing", "condition_met") == [1]


def test_literal_keyword_call_lines_matches_the_final_attribute_component(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("value = module.Thing(condition_met=True)\n", encoding="utf-8")
    assert literal_keyword_call_lines(target, "Thing", "condition_met") == [1]


def test_literal_keyword_call_lines_ignores_a_variable_keyword_value(tmp_path: Path) -> None:
    """The anti-false-positive heuristic: a keyword bound to a NAME (a real
    computed value) is never classified as a literal stub."""
    target = tmp_path / "m.py"
    target.write_text(
        "computed = check(a, b)\nvalue = Thing(condition_met=computed)\n", encoding="utf-8"
    )
    assert literal_keyword_call_lines(target, "Thing", "condition_met") == []


def test_literal_keyword_call_lines_ignores_a_different_field(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("value = Thing(other_field=True)\n", encoding="utf-8")
    assert literal_keyword_call_lines(target, "Thing", "condition_met") == []


def test_literal_keyword_call_lines_ignores_a_differently_named_symbol(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("value = OtherThing(condition_met=True)\n", encoding="utf-8")
    assert literal_keyword_call_lines(target, "Thing", "condition_met") == []


def test_literal_keyword_call_lines_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        literal_keyword_call_lines(target, "Thing", "condition_met")


# ---------------------------------------------------------------------------
# module_level_function_names (T1.1 U5 stub-vs-calculator) -- efficacy
# ---------------------------------------------------------------------------


def test_module_level_function_names_finds_top_level_defs(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("def foo():\n    pass\n\ndef bar():\n    pass\n", encoding="utf-8")
    assert module_level_function_names(target) == frozenset({"foo", "bar"})


def test_module_level_function_names_excludes_nested_defs(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text(
        "def foo():\n    def nested():\n        pass\n    return nested\n", encoding="utf-8"
    )
    assert module_level_function_names(target) == frozenset({"foo"})


def test_module_level_function_names_excludes_class_methods(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("class C:\n    def method(self):\n        pass\n", encoding="utf-8")
    assert module_level_function_names(target) == frozenset()


def test_module_level_function_names_includes_async_defs(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("async def foo():\n    pass\n", encoding="utf-8")
    assert module_level_function_names(target) == frozenset({"foo"})


def test_module_level_function_names_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        module_level_function_names(target)


# ---------------------------------------------------------------------------
# function_return_annotation_name (T1.1 U5 stub-vs-calculator) -- efficacy
# ---------------------------------------------------------------------------


def test_function_return_annotation_name_reads_a_plain_name_annotation(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("def f(a, b) -> Thing:\n    return Thing()\n", encoding="utf-8")
    assert function_return_annotation_name(target, "f") == "Thing"


def test_function_return_annotation_name_reads_a_quoted_forward_ref(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text('def f(a, b) -> "Thing":\n    return Thing()\n', encoding="utf-8")
    assert function_return_annotation_name(target, "f") == "Thing"


def test_function_return_annotation_name_returns_none_for_no_annotation(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("def f(a, b):\n    return None\n", encoding="utf-8")
    assert function_return_annotation_name(target, "f") is None


def test_function_return_annotation_name_returns_none_for_unresolvable_annotation(
    tmp_path: Path,
) -> None:
    """A subscripted generic (e.g. ``tuple[int, ...]``) is out of scope --
    honest absence over a guess."""
    target = tmp_path / "m.py"
    target.write_text("def f(a, b) -> tuple[int, ...]:\n    return (a, b)\n", encoding="utf-8")
    assert function_return_annotation_name(target, "f") is None


def test_function_return_annotation_name_returns_none_for_absent_function(tmp_path: Path) -> None:
    target = tmp_path / "m.py"
    target.write_text("def other() -> Thing:\n    return Thing()\n", encoding="utf-8")
    assert function_return_annotation_name(target, "f") is None


def test_function_return_annotation_name_raises_on_unparseable_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SentinelCheckError):
        function_return_annotation_name(target, "f")
