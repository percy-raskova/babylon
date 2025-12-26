"""Tests for helper functions in the survival systems.

Task 4: Unit tests for _calculate_solidarity_multiplier (26.9% -> 85%)

This tests the internal helper function that calculates the solidarity
multiplier from incoming SOLIDARITY edges in the graph.
"""

import networkx as nx
import pytest

from babylon.engine.systems.survival import _calculate_solidarity_multiplier
from babylon.models.enums import EdgeType


@pytest.mark.unit
class TestCalculateSolidarityMultiplier:
    """Test the _calculate_solidarity_multiplier helper function.

    This function calculates the organization multiplier from incoming
    SOLIDARITY edges:
    - No edges: returns 1.0 (base multiplier)
    - SOLIDARITY edges: returns 1.0 + sum(solidarity_strength)
    - Non-SOLIDARITY edges: ignored
    """

    def test_no_incoming_edges_returns_one(self) -> None:
        """Isolated node with no edges returns base multiplier of 1.0.

        A worker without solidarity infrastructure has no bonus.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("C_w")  # Isolated node

        result = _calculate_solidarity_multiplier(graph, "C_w")

        assert result == pytest.approx(1.0, abs=0.001)

    def test_non_solidarity_edge_ignored(self) -> None:
        """Non-SOLIDARITY edges (like EXPLOITATION) do not affect multiplier.

        Only SOLIDARITY edges contribute to organization.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("P_c")  # Periphery comprador
        graph.add_node("C_w")  # Core worker

        # EXPLOITATION edge - should NOT count toward solidarity
        graph.add_edge(
            "P_c",
            "C_w",
            edge_type=EdgeType.EXPLOITATION,
            solidarity_strength=0.5,  # This should be ignored
        )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        assert result == pytest.approx(1.0, abs=0.001)

    def test_single_solidarity_edge(self) -> None:
        """Single SOLIDARITY edge with strength=0.3 returns 1.3 multiplier."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("P_w")  # Periphery worker
        graph.add_node("C_w")  # Core worker

        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.3,
        )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        assert result == pytest.approx(1.3, abs=0.001)

    def test_multiple_edges_accumulate(self) -> None:
        """Multiple SOLIDARITY edges accumulate their strengths.

        Two edges with strengths 0.2 + 0.3 = 0.5, multiplier = 1.5
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("P_w1")  # Periphery worker 1
        graph.add_node("P_w2")  # Periphery worker 2
        graph.add_node("C_w")  # Core worker

        graph.add_edge(
            "P_w1",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.2,
        )
        graph.add_edge(
            "P_w2",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.3,
        )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        # 1.0 + 0.2 + 0.3 = 1.5
        assert result == pytest.approx(1.5, abs=0.001)

    def test_missing_solidarity_strength_defaults_zero(self) -> None:
        """SOLIDARITY edge without solidarity_strength attribute defaults to 0.

        Missing attribute should not break the calculation.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("P_w")
        graph.add_node("C_w")

        # SOLIDARITY edge WITHOUT solidarity_strength attribute
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            # Note: no solidarity_strength key
        )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        # Missing strength defaults to 0.0, so multiplier = 1.0 + 0.0 = 1.0
        assert result == pytest.approx(1.0, abs=0.001)

    def test_string_edge_type_converted(self) -> None:
        """Edge type stored as string "solidarity" is correctly handled.

        Graph edges may store edge_type as string or enum.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("P_w")
        graph.add_node("C_w")

        # Edge type as STRING (not enum) - must match enum value
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type="solidarity",  # String value, not EdgeType.SOLIDARITY
            solidarity_strength=0.4,
        )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        # Should correctly convert string to enum and match
        assert result == pytest.approx(1.4, abs=0.001)

    def test_mixed_edge_types(self) -> None:
        """Only SOLIDARITY edges are counted, not other types.

        A node may have multiple edge types pointing to it.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("P_w")  # Periphery worker
        graph.add_node("C_b")  # Core bourgeoisie
        graph.add_node("C_w")  # Core worker

        # SOLIDARITY edge from periphery
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.3,
        )

        # WAGES edge from bourgeoisie (should be ignored)
        graph.add_edge(
            "C_b",
            "C_w",
            edge_type=EdgeType.WAGES,
            solidarity_strength=0.5,  # Should NOT count
        )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        # Only SOLIDARITY edge counts: 1.0 + 0.3 = 1.3
        assert result == pytest.approx(1.3, abs=0.001)

    def test_outgoing_edges_not_counted(self) -> None:
        """Only INCOMING edges are counted, not outgoing.

        Solidarity is received, not given, for the multiplier.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("C_w")  # Core worker
        graph.add_node("Other")  # Another node

        # OUTGOING edge from C_w (should not count)
        graph.add_edge(
            "C_w",
            "Other",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        # No incoming edges, so multiplier = 1.0
        assert result == pytest.approx(1.0, abs=0.001)

    def test_zero_solidarity_strength(self) -> None:
        """SOLIDARITY edge with strength=0.0 contributes nothing.

        This is the fascist scenario: edge exists but no infrastructure.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("P_w")
        graph.add_node("C_w")

        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.0,  # No infrastructure
        )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        assert result == pytest.approx(1.0, abs=0.001)

    def test_high_solidarity_multiple_edges(self) -> None:
        """High solidarity from multiple sources can exceed 2.0 multiplier.

        Multiple strong solidarity connections compound.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("P_w1")
        graph.add_node("P_w2")
        graph.add_node("P_w3")
        graph.add_node("C_w")

        # Three strong solidarity connections
        for source in ["P_w1", "P_w2", "P_w3"]:
            graph.add_edge(
                source,
                "C_w",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=0.5,
            )

        result = _calculate_solidarity_multiplier(graph, "C_w")

        # 1.0 + 0.5 + 0.5 + 0.5 = 2.5
        assert result == pytest.approx(2.5, abs=0.001)

    def test_none_edge_type_ignored(self) -> None:
        """Edge with edge_type=None is ignored (not a SOLIDARITY edge)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("A")
        graph.add_node("B")

        # Edge with no edge_type set
        graph.add_edge(
            "A",
            "B",
            solidarity_strength=0.5,
            # Note: no edge_type attribute
        )

        result = _calculate_solidarity_multiplier(graph, "B")

        assert result == pytest.approx(1.0, abs=0.001)
