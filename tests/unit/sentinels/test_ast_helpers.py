"""Tests for the shared AST helpers added for the U7 sentinel family.

These helpers let a layer-0.5 sensor prove facts about ``domain``/``engine``/
``tools`` source WITHOUT importing it (the import-linter contract in
``pyproject.toml`` forbids the import; the sensors must stay cheap and static).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from babylon.sentinels._ast import (
    coupling_edges,
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
