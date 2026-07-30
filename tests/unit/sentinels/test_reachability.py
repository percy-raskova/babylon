"""Unit tests for the reachability sentinel (Game Design Standard §9 W.3.2).

Mechanism tests run against synthetic trees under ``tmp_path`` so they pin the
scanner/check contracts, not repo facts; one conformance test proves the
shipped registry is truthful against the real tree (the sentinel's own CI
posture). The sentinel's law: every gate operand the EndgameDetector reads has
a *runtime* production writer, or a ledgered disposition citing its charter —
and a ledgered row whose operand gains a writer goes stale loudly.
"""

from __future__ import annotations

from pathlib import Path

from babylon.sentinels.reachability.checks import (
    gate_operand_violations,
    main,
    production_attribute_writes,
    unregistered_gate_reads,
)
from babylon.sentinels.reachability.registry import (
    GATE_OPERAND_ROWS,
    TYPE_KEYS,
    GateOperandRow,
    Governance,
)


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


class TestProductionAttributeWrites:
    """The writer scanner: subscript assigns, update_node/add_node stamps."""

    def test_subscript_assignment_is_a_write(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "sys_a.py", 'payload["colonial_stance"] = stance\n')
        writes = production_attribute_writes([path])
        assert "colonial_stance" in writes
        assert writes["colonial_stance"] == [f"{path}:1"]

    def test_augmented_subscript_assignment_is_a_write(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "sys_b.py", 'node["state_violence_index"] += delta\n')
        assert "state_violence_index" in production_attribute_writes([path])

    def test_update_node_keyword_is_a_write(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "sys_c.py", "graph.update_node(nid, habitability=0.4)\n")
        assert "habitability" in production_attribute_writes([path])

    def test_update_node_dict_literal_is_a_write(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path, "sys_d.py", 'graph.update_node(nid, {"extraction_policy": "halt"})\n'
        )
        assert "extraction_policy" in production_attribute_writes([path])

    def test_add_node_keyword_is_a_write(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "sys_e.py", 'graph.add_node(nid, sovereignty_type="insurgent")\n')
        assert "sovereignty_type" in production_attribute_writes([path])

    def test_reads_are_not_writes(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            "sys_f.py",
            'stance = node.get("colonial_stance", None)\n'
            'if node["ruling_faction_id"] == x:\n    pass\n',
        )
        writes = production_attribute_writes([path])
        assert "colonial_stance" not in writes
        assert "ruling_faction_id" not in writes

    def test_call_keyword_outside_graph_api_is_not_a_write(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "sys_g.py", "score = formula(colonial_stance=stance)\n")
        assert "colonial_stance" not in production_attribute_writes([path])


class TestGateOperandViolations:
    """Per-governance enforcement plus the stale-ledger ratchet."""

    def _detected_row(self, operand: str) -> GateOperandRow:
        return GateOperandRow(
            operand=operand,
            reader="endgame_detector.py (test)",
            governance=Governance.DETECTED,
            citation="",
        )

    def _charter_row(self, operand: str) -> GateOperandRow:
        return GateOperandRow(
            operand=operand,
            reader="endgame_detector.py (test)",
            governance=Governance.CHARTER,
            citation="Game Design Standard §10 Phase 3 (test)",
        )

    def test_detected_row_with_writer_is_clean(self) -> None:
        rows = (self._detected_row("habitability"),)
        violations = gate_operand_violations(rows, {"habitability": ["a.py:1"]})
        assert violations == []

    def test_detected_row_without_writer_is_a_violation(self) -> None:
        rows = (self._detected_row("habitability"),)
        violations = gate_operand_violations(rows, {})
        assert len(violations) == 1
        assert "habitability" in violations[0]

    def test_charter_row_without_writer_is_clean(self) -> None:
        rows = (self._charter_row("colonial_stance"),)
        assert gate_operand_violations(rows, {}) == []

    def test_charter_row_with_writer_is_stale(self) -> None:
        rows = (self._charter_row("colonial_stance"),)
        violations = gate_operand_violations(rows, {"colonial_stance": ["b.py:9"]})
        assert len(violations) == 1
        assert "stale" in violations[0].lower()

    def test_charter_row_requires_a_citation(self) -> None:
        row = GateOperandRow(
            operand="x",
            reader="r",
            governance=Governance.CHARTER,
            citation="",
        )
        violations = gate_operand_violations((row,), {})
        assert len(violations) == 1
        assert "citation" in violations[0].lower()


class TestUnregisteredGateReads:
    """Completeness: a new ``.get("attr")`` in the detector must be registered."""

    def test_new_gate_read_is_a_violation(self, tmp_path: Path) -> None:
        detector = _write(
            tmp_path,
            "endgame_detector.py",
            'a = node.get("colonial_stance", None)\nb = node.get("brand_new_operand", 0.0)\n',
        )
        violations = unregistered_gate_reads(detector, frozenset({"colonial_stance"}))
        assert len(violations) == 1
        assert "brand_new_operand" in violations[0]

    def test_type_keys_are_vocabulary_business(self, tmp_path: Path) -> None:
        detector = _write(tmp_path, "endgame_detector.py", 'k = node.get("_node_type")\n')
        assert unregistered_gate_reads(detector, frozenset()) == []
        assert "_node_type" in TYPE_KEYS


class TestShippedRegistryConformance:
    """The registry rows must be truthful against the real tree, today."""

    def test_registry_covers_every_detector_read(self) -> None:
        operands = {row.operand for row in GATE_OPERAND_ROWS}
        assert operands, "registry must not be empty"

    def test_sentinel_is_green_on_the_real_tree(self) -> None:
        assert main(["--check"]) == 0
