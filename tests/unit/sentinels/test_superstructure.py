"""Citing + mutation tests for the superstructure-direction sentinel (I-ORD, ADR135).

The sentinel package is layer 0.5 and may not import the engine, so its
MATERIAL_BASE file list is hand-declared — THIS test is the citation that
keeps it in lockstep with ``simulation_engine.MATERIAL_BASE_SYSTEMS`` (the
test layer may import anything). The mutation legs prove each gating rule
actually fires (standing rule: every sentinel is mutation-validated).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from babylon.sentinels.superstructure.checks import (
    check_direction,
    check_ownership,
    check_registry_integrity,
    find_superstructure_writes,
)
from babylon.sentinels.superstructure.registry import (
    MATERIAL_BASE_SYSTEM_FILES,
    SUPERSTRUCTURE_ATTR_OWNERS,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]


class TestCurrentTreeIsClean:
    def test_all_three_gates_are_clean(self) -> None:
        assert check_ownership() == []
        assert check_direction() == []
        assert check_registry_integrity() == []

    def test_every_declared_register_has_a_live_write_site(self) -> None:
        """The dual of ownership: a declared register nobody writes is a
        stale row (the inert-family failure mode)."""
        written = {register for _path, _line, register in find_superstructure_writes()}
        assert written == set(SUPERSTRUCTURE_ATTR_OWNERS)


class TestCitation:
    def test_material_base_files_match_the_engine_partition(self) -> None:
        """The hand-declared base-file list IS simulation_engine's
        MATERIAL_BASE_SYSTEMS, file for file (the layer-0.5 citation)."""
        from babylon.engine.simulation_engine import MATERIAL_BASE_SYSTEMS

        engine_files = {
            Path(inspect.getfile(cls)).resolve().relative_to(_REPO_ROOT).as_posix()
            for cls in MATERIAL_BASE_SYSTEMS
        }
        assert engine_files == set(MATERIAL_BASE_SYSTEM_FILES)

    def test_owners_are_never_base_partition_files(self) -> None:
        for owners in SUPERSTRUCTURE_ATTR_OWNERS.values():
            assert not (owners & MATERIAL_BASE_SYSTEM_FILES)


class TestMutationValidation:
    """Craft violating source under tmp_path and prove each rule fires."""

    def _write(self, root: Path, rel: str, body: str) -> None:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    def test_ownership_gate_fires_on_a_foreign_writer(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "rogue.py",
            'def f(graph):\n    graph.set_graph_attr("policy_overlays", {})\n',
        )
        violations = check_ownership(tmp_path)
        assert len(violations) == 1
        assert "policy_overlays" in violations[0]

    def test_ownership_gate_resolves_declared_constant_aliases(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "aliased.py",
            "POLICY_AGENDA_ATTR = 'policy_agenda'\n"
            "def f(graph):\n    graph.set_graph_attr(POLICY_AGENDA_ATTR, [])\n",
        )
        violations = check_ownership(tmp_path)
        assert len(violations) == 1
        assert "policy_agenda" in violations[0]

    def test_direction_gate_fires_on_a_base_partition_writer(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "src/babylon/engine/systems/metabolism.py",
            'def f(graph):\n    graph.set_graph_attr("sovereign_fiscal", {})\n',
        )
        violations = check_direction(tmp_path)
        assert len(violations) == 1
        assert "I-ORD" in violations[0]

    def test_undeclared_attrs_are_out_of_scope(self, tmp_path: Path) -> None:
        """The sentinel guards ONLY the declared registers — a write to an
        unrelated graph attr never trips it (no false ownership claims)."""
        self._write(
            tmp_path,
            "other.py",
            'def f(graph):\n    graph.set_graph_attr("economy", {})\n',
        )
        assert check_ownership(tmp_path) == []
        assert check_direction(tmp_path) == []
