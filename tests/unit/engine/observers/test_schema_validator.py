"""Tests for NarrativeFrame JSON Schema validation (Sprint 3.2).

Validates that the schema_validator module correctly validates
NarrativeFrame structures against the JSON Schema.
"""

from __future__ import annotations

import pytest

from babylon.engine.observers.schema_validator import (
    is_valid_narrative_frame,
    validate_narrative_frame,
)


class TestValidNarrativeFrames:
    """Test validation of valid NarrativeFrame structures."""

    def test_minimal_valid_frame(self) -> None:
        """Minimal valid frame with one node and no edges."""
        frame = {
            "pattern": "TEST_PATTERN",
            "causal_graph": {
                "nodes": [{"id": "node_1", "type": "ECONOMIC_SHOCK", "tick": 0}],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_shock_doctrine_frame(self) -> None:
        """Full Shock Doctrine pattern with 3 nodes and 2 edges."""
        frame = {
            "pattern": "SHOCK_DOCTRINE",
            "detected_at_tick": 12,
            "causal_graph": {
                "nodes": [
                    {
                        "id": "shock_t10",
                        "type": "ECONOMIC_SHOCK",
                        "tick": 10,
                        "data": {"pool_before": 100.0, "pool_after": 70.0},
                    },
                    {
                        "id": "austerity_t11",
                        "type": "AUSTERITY_RESPONSE",
                        "tick": 11,
                        "data": {"wage_before": 0.20, "wage_after": 0.15},
                    },
                    {
                        "id": "radical_t12",
                        "type": "RADICALIZATION",
                        "tick": 12,
                        "data": {"p_rev_before": 0.30, "p_rev_after": 0.45},
                    },
                ],
                "edges": [
                    {
                        "source": "shock_t10",
                        "target": "austerity_t11",
                        "relation": "TRIGGERS_REACTION",
                    },
                    {
                        "source": "austerity_t11",
                        "target": "radical_t12",
                        "relation": "CAUSES_RADICALIZATION",
                    },
                ],
            },
        }
        errors = validate_narrative_frame(frame)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_is_valid_returns_true_for_valid_frame(self) -> None:
        """is_valid_narrative_frame returns True for valid frame."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [{"id": "n1", "type": "RUPTURE", "tick": 0}],
                "edges": [],
            },
        }
        assert is_valid_narrative_frame(frame) is True


class TestInvalidNarrativeFrames:
    """Test validation catches invalid NarrativeFrame structures."""

    def test_missing_pattern(self) -> None:
        """Missing required 'pattern' field."""
        frame = {
            "causal_graph": {
                "nodes": [{"id": "n1", "type": "ECONOMIC_SHOCK", "tick": 0}],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0
        assert any("pattern" in e.lower() for e in errors)

    def test_missing_causal_graph(self) -> None:
        """Missing required 'causal_graph' field."""
        frame = {"pattern": "TEST"}
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0
        assert any("causal_graph" in e.lower() for e in errors)

    def test_empty_nodes_array(self) -> None:
        """Empty nodes array violates minItems: 1."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0
        assert any("nodes" in e.lower() or "minitems" in e.lower() for e in errors)

    def test_invalid_node_type(self) -> None:
        """Invalid node type not in enum."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [{"id": "n1", "type": "INVALID_TYPE", "tick": 0}],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0

    def test_invalid_edge_relation(self) -> None:
        """Invalid edge relation not in enum."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [
                    {"id": "n1", "type": "ECONOMIC_SHOCK", "tick": 0},
                    {"id": "n2", "type": "RADICALIZATION", "tick": 1},
                ],
                "edges": [{"source": "n1", "target": "n2", "relation": "INVALID_RELATION"}],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0

    def test_node_missing_required_id(self) -> None:
        """Node missing required 'id' field."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [{"type": "ECONOMIC_SHOCK", "tick": 0}],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0
        assert any("id" in e.lower() for e in errors)

    def test_node_missing_required_type(self) -> None:
        """Node missing required 'type' field."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [{"id": "n1", "tick": 0}],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0
        assert any("type" in e.lower() for e in errors)

    def test_node_missing_required_tick(self) -> None:
        """Node missing required 'tick' field."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [{"id": "n1", "type": "ECONOMIC_SHOCK"}],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0
        assert any("tick" in e.lower() for e in errors)

    def test_negative_tick_value(self) -> None:
        """Negative tick value violates minimum: 0."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [{"id": "n1", "type": "ECONOMIC_SHOCK", "tick": -1}],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0

    def test_edge_missing_source(self) -> None:
        """Edge missing required 'source' field."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [
                    {"id": "n1", "type": "ECONOMIC_SHOCK", "tick": 0},
                    {"id": "n2", "type": "RADICALIZATION", "tick": 1},
                ],
                "edges": [{"target": "n2", "relation": "TRIGGERS_REACTION"}],
            },
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0
        assert any("source" in e.lower() for e in errors)

    def test_additional_properties_rejected_at_root(self) -> None:
        """Additional properties at root level are rejected."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [{"id": "n1", "type": "ECONOMIC_SHOCK", "tick": 0}],
                "edges": [],
            },
            "extra_field": "should_fail",
        }
        errors = validate_narrative_frame(frame)
        assert len(errors) > 0

    def test_is_valid_returns_false_for_invalid_frame(self) -> None:
        """is_valid_narrative_frame returns False for invalid frame."""
        frame = {"pattern": "TEST"}  # Missing causal_graph
        assert is_valid_narrative_frame(frame) is False


class TestAllNodeTypes:
    """Test all defined node types are accepted."""

    @pytest.mark.parametrize(
        "node_type",
        [
            "ECONOMIC_SHOCK",
            "AUSTERITY_RESPONSE",
            "RADICALIZATION",
            "REPRESSION",
            "SOLIDARITY_SURGE",
            "RUPTURE",
        ],
    )
    def test_valid_node_type(self, node_type: str) -> None:
        """All defined node types are accepted."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [{"id": "n1", "type": node_type, "tick": 0}],
                "edges": [],
            },
        }
        errors = validate_narrative_frame(frame)
        assert errors == [], f"Node type {node_type} rejected: {errors}"


class TestAllEdgeRelations:
    """Test all defined edge relations are accepted."""

    @pytest.mark.parametrize(
        "relation",
        [
            "TRIGGERS_REACTION",
            "CAUSES_RADICALIZATION",
            "PROVOKES_RESPONSE",
            "LEADS_TO",
            "ENABLES",
        ],
    )
    def test_valid_edge_relation(self, relation: str) -> None:
        """All defined edge relations are accepted."""
        frame = {
            "pattern": "TEST",
            "causal_graph": {
                "nodes": [
                    {"id": "n1", "type": "ECONOMIC_SHOCK", "tick": 0},
                    {"id": "n2", "type": "RADICALIZATION", "tick": 1},
                ],
                "edges": [{"source": "n1", "target": "n2", "relation": relation}],
            },
        }
        errors = validate_narrative_frame(frame)
        assert errors == [], f"Relation {relation} rejected: {errors}"
