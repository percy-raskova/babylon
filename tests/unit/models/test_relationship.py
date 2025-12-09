"""Tests for Relationship entity model.

TDD Red Phase: These tests define the contract for Relationship.
Relationship is the fundamental edge type in Phase 1 - it represents
a directed relationship between two entities (typically SocialClasses).

The tests verify:
1. Creation with required and default fields
2. Validation of edge constraints (no self-loops)
3. Integration with Sprint 1 types (Currency, Intensity)
4. Serialization for Ledger (SQLite) storage
5. NetworkX graph integration
"""

import pytest
from pydantic import ValidationError

# These imports should fail until the model is implemented
from babylon.models import Relationship
from babylon.models.enums import EdgeType

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.math
class TestRelationshipCreation:
    """Test Relationship instantiation with required and default fields."""

    def test_minimal_creation(self) -> None:
        """Can create Relationship with just required fields."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
        )
        assert edge.source_id == "C001"
        assert edge.target_id == "C002"
        assert edge.edge_type == EdgeType.EXPLOITATION
        # Check defaults
        assert edge.value_flow == 0.0
        assert edge.tension == 0.0

    def test_phase1_exploitation_edge(self) -> None:
        """Create the Phase 1 exploitation edge from the blueprint."""
        # Worker (C001) is exploited by Owner (C002)
        # Value flows from worker to owner
        edge = Relationship(
            source_id="C001",  # Worker produces value
            target_id="C002",  # Owner extracts value
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,  # Φ = labor_value - wage = 100 - 20
        )
        assert edge.source_id == "C001"
        assert edge.target_id == "C002"
        assert edge.edge_type == EdgeType.EXPLOITATION
        assert edge.value_flow == 80.0

    def test_all_edge_types_valid(self) -> None:
        """All EdgeType enum values are valid for creating a Relationship."""
        for i, edge_type in enumerate(EdgeType):
            edge = Relationship(
                source_id=f"C{i:03d}",
                target_id=f"C{(i + 1):03d}",
                edge_type=edge_type,
            )
            assert edge.edge_type == edge_type

    def test_with_tension(self) -> None:
        """Can create with explicit tension level."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.7,  # High tension due to exploitation
        )
        assert edge.tension == 0.7

    def test_with_description(self) -> None:
        """Can create with optional description."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            description="Imperial rent extraction from periphery to core",
        )
        assert edge.description == "Imperial rent extraction from periphery to core"

    def test_solidarity_edge(self) -> None:
        """Can create solidarity relationship."""
        edge = Relationship(
            source_id="C001",
            target_id="C003",
            edge_type=EdgeType.SOLIDARITY,
            tension=0.0,  # Solidarity reduces tension
        )
        assert edge.edge_type == EdgeType.SOLIDARITY
        assert edge.tension == 0.0

    def test_repression_edge(self) -> None:
        """Can create repression relationship."""
        edge = Relationship(
            source_id="C002",  # Bourgeoisie
            target_id="C001",  # Proletariat
            edge_type=EdgeType.REPRESSION,
            tension=0.9,  # High tension from repression
        )
        assert edge.edge_type == EdgeType.REPRESSION
        assert edge.tension == 0.9


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.math
class TestRelationshipValidation:
    """Test field constraints and validation rules."""

    def test_rejects_self_loop(self) -> None:
        """Entities cannot have a relationship with themselves."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C001",  # Same as source
                edge_type=EdgeType.EXPLOITATION,
            )

    def test_rejects_negative_value_flow(self) -> None:
        """Value flow cannot be negative (Currency constraint)."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C002",
                edge_type=EdgeType.EXPLOITATION,
                value_flow=-10.0,
            )

    def test_rejects_tension_out_of_range(self) -> None:
        """Tension must be [0.0, 1.0] (Intensity constraint)."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C002",
                edge_type=EdgeType.EXPLOITATION,
                tension=-0.1,
            )
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C002",
                edge_type=EdgeType.EXPLOITATION,
                tension=1.5,
            )

    def test_rejects_invalid_edge_type_string(self) -> None:
        """Edge type must be a valid EdgeType enum value."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C002",
                edge_type="friendship",  # type: ignore[arg-type]
            )

    def test_accepts_edge_type_string_values(self) -> None:
        """Edge type accepts string values that match enum values."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type="exploitation",  # type: ignore[arg-type]
        )
        assert edge.edge_type == EdgeType.EXPLOITATION

    def test_source_id_required(self) -> None:
        """Source ID is a required field."""
        with pytest.raises(ValidationError):
            Relationship(
                target_id="C002",
                edge_type=EdgeType.EXPLOITATION,
            )  # type: ignore[call-arg]

    def test_target_id_required(self) -> None:
        """Target ID is a required field."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                edge_type=EdgeType.EXPLOITATION,
            )  # type: ignore[call-arg]

    def test_edge_type_required(self) -> None:
        """Edge type is a required field."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C002",
            )  # type: ignore[call-arg]

    def test_extra_fields_forbidden(self) -> None:
        """Unknown fields are rejected."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C002",
                edge_type=EdgeType.EXPLOITATION,
                unknown_field="value",  # type: ignore[call-arg]
            )


# =============================================================================
# DEFAULT VALUE TESTS
# =============================================================================


@pytest.mark.math
class TestRelationshipDefaults:
    """Test default values for optional fields."""

    def test_default_value_flow(self) -> None:
        """Default value_flow is 0.0 (no value transfer)."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
        )
        assert edge.value_flow == 0.0

    def test_default_tension(self) -> None:
        """Default tension is 0.0 (dormant)."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
        )
        assert edge.tension == 0.0

    def test_default_description(self) -> None:
        """Default description is empty string."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
        )
        assert edge.description == ""


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestRelationshipSerialization:
    """Test JSON serialization for Ledger (SQLite) storage."""

    def test_serialize_to_json(self) -> None:
        """Relationship serializes to valid JSON."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
            tension=0.5,
        )
        json_str = edge.model_dump_json()
        assert "C001" in json_str
        assert "C002" in json_str
        assert "exploitation" in json_str

    def test_deserialize_from_json(self) -> None:
        """Relationship can be restored from JSON."""
        json_str = """
        {
            "source_id": "C001",
            "target_id": "C002",
            "edge_type": "exploitation",
            "value_flow": 80.0,
            "tension": 0.5,
            "description": ""
        }
        """
        edge = Relationship.model_validate_json(json_str)
        assert edge.source_id == "C001"
        assert edge.target_id == "C002"
        assert edge.edge_type == EdgeType.EXPLOITATION
        assert edge.value_flow == 80.0
        assert edge.tension == 0.5

    def test_round_trip_preserves_values(self) -> None:
        """JSON round-trip preserves all field values."""
        original = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
            tension=0.7,
            description="Imperial rent extraction",
        )
        json_str = original.model_dump_json()
        restored = Relationship.model_validate_json(json_str)

        assert restored.source_id == original.source_id
        assert restored.target_id == original.target_id
        assert restored.edge_type == original.edge_type
        assert restored.value_flow == pytest.approx(original.value_flow)
        assert restored.tension == pytest.approx(original.tension)
        assert restored.description == original.description

    def test_dict_conversion(self) -> None:
        """Relationship converts to dict for database storage."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
        )
        data = edge.model_dump()

        assert data["source_id"] == "C001"
        assert data["target_id"] == "C002"
        assert data["edge_type"] == "exploitation"
        assert data["value_flow"] == 80.0


# =============================================================================
# NETWORKX INTEGRATION TESTS
# =============================================================================


@pytest.mark.topology
class TestRelationshipNetworkX:
    """Test integration with NetworkX graph storage."""

    def test_can_add_to_graph(self) -> None:
        """Relationship can become a NetworkX edge."""
        import networkx as nx

        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
        )

        G = nx.DiGraph()
        G.add_edge(
            edge.source_id,
            edge.target_id,
            **edge.model_dump(exclude={"source_id", "target_id"}),
        )

        assert G.has_edge("C001", "C002")
        assert G["C001"]["C002"]["value_flow"] == 80.0
        assert G["C001"]["C002"]["edge_type"] == "exploitation"

    def test_can_restore_from_edge_data(self) -> None:
        """Relationship can be restored from NetworkX edge attributes."""
        import networkx as nx

        G = nx.DiGraph()
        G.add_edge(
            "C001",
            "C002",
            edge_type="exploitation",
            value_flow=80.0,
            tension=0.5,
            description="",
        )

        u, v, edge_data = list(G.edges(data=True))[0]
        restored = Relationship(
            source_id=u,
            target_id=v,
            **edge_data,
        )

        assert restored.source_id == "C001"
        assert restored.target_id == "C002"
        assert restored.edge_type == EdgeType.EXPLOITATION
        assert restored.value_flow == 80.0

    def test_phase1_complete_graph(self) -> None:
        """Phase 1 blueprint: two nodes + one edge complete graph."""
        import networkx as nx

        from babylon.models import SocialClass
        from babylon.models.enums import SocialRole

        # Create the two Phase 1 nodes
        worker = SocialClass(
            id="C001",
            name="Periphery Mine Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=20.0,
        )
        owner = SocialClass(
            id="C002",
            name="Core Factory Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=1000.0,
        )

        # Create the exploitation edge
        exploitation = Relationship(
            source_id=worker.id,
            target_id=owner.id,
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,  # Φ = 100 - 20
        )

        # Build the graph
        G = nx.DiGraph()
        G.add_node(worker.id, **worker.model_dump())
        G.add_node(owner.id, **owner.model_dump())
        G.add_edge(
            exploitation.source_id,
            exploitation.target_id,
            **exploitation.model_dump(exclude={"source_id", "target_id"}),
        )

        # Verify Phase 1 structure
        assert G.number_of_nodes() == 2
        assert G.number_of_edges() == 1
        assert G.nodes["C001"]["role"] == "periphery_proletariat"
        assert G.nodes["C002"]["role"] == "core_bourgeoisie"
        assert G["C001"]["C002"]["value_flow"] == 80.0
        assert G["C001"]["C002"]["edge_type"] == "exploitation"

    def test_bidirectional_relationships(self) -> None:
        """Can have edges in both directions between nodes."""
        import networkx as nx

        exploitation = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
        )
        repression = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.REPRESSION,
            tension=0.8,
        )

        G = nx.DiGraph()
        G.add_edge(
            exploitation.source_id,
            exploitation.target_id,
            **exploitation.model_dump(exclude={"source_id", "target_id"}),
        )
        G.add_edge(
            repression.source_id,
            repression.target_id,
            **repression.model_dump(exclude={"source_id", "target_id"}),
        )

        assert G.has_edge("C001", "C002")
        assert G.has_edge("C002", "C001")
        assert G["C001"]["C002"]["edge_type"] == "exploitation"
        assert G["C002"]["C001"]["edge_type"] == "repression"


# =============================================================================
# EDGE TUPLE HELPER TESTS
# =============================================================================


@pytest.mark.topology
class TestRelationshipEdgeTuple:
    """Test edge_tuple property for NetworkX integration."""

    def test_edge_tuple_returns_source_target(self) -> None:
        """edge_tuple returns (source_id, target_id) for NetworkX."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
        )
        assert edge.edge_tuple == ("C001", "C002")

    def test_edge_data_excludes_ids(self) -> None:
        """edge_data returns attributes without source/target IDs."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
            tension=0.5,
        )
        data = edge.edge_data
        assert "source_id" not in data
        assert "target_id" not in data
        assert data["edge_type"] == "exploitation"
        assert data["value_flow"] == 80.0
        assert data["tension"] == 0.5


# =============================================================================
# FLOW COMPONENT TESTS
# =============================================================================


@pytest.mark.math
class TestFlowComponent:
    """Test FlowComponent model."""

    def test_flow_component_creation(self) -> None:
        """Can create FlowComponent with valid data."""
        from babylon.models.entities.relationship import FlowComponent

        flow = FlowComponent(value_flow=80.0, tension=0.5)
        assert flow.value_flow == 80.0
        assert flow.tension == 0.5

    def test_flow_component_is_frozen(self) -> None:
        """FlowComponent is immutable."""
        from babylon.models.entities.relationship import FlowComponent

        flow = FlowComponent(value_flow=80.0)
        with pytest.raises(ValidationError):
            flow.value_flow = 100.0  # type: ignore[misc]


@pytest.mark.math
class TestRelationshipComponentConstruction:
    """Test component-based Relationship construction."""

    def test_create_with_flow_component(self) -> None:
        """Can create Relationship using FlowComponent."""
        from babylon.models.entities.relationship import FlowComponent

        rel = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            flow=FlowComponent(value_flow=80.0, tension=0.5),
        )
        assert rel.value_flow == 80.0
        assert rel.tension == 0.5

    def test_flat_construction_still_works(self) -> None:
        """Flat field construction is unchanged."""
        rel = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
            tension=0.5,
        )
        assert rel.value_flow == 80.0
        assert rel.tension == 0.5


@pytest.mark.math
class TestRelationshipComponentAccess:
    """Test accessing relationship data via flow property."""

    def test_access_flow_component(self) -> None:
        """Can access flow data via component property."""
        rel = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=80.0,
            tension=0.5,
        )
        assert rel.flow.value_flow == 80.0
        assert rel.flow.tension == 0.5

    def test_flow_returns_correct_type(self) -> None:
        """Flow property returns correct type."""
        from babylon.models.entities.relationship import FlowComponent

        rel = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
        )
        assert isinstance(rel.flow, FlowComponent)


# =============================================================================
# SOLIDARITY STRENGTH TESTS (Sprint 3.4.2)
# =============================================================================


@pytest.mark.math
class TestSolidarityStrength:
    """Test solidarity_strength field for SOLIDARITY edges.

    Sprint 3.4.2: Proletarian Internationalism - The Counterforce.

    CRITICAL DESIGN DECISION: solidarity_strength is a PERSISTENT ATTRIBUTE
    ON THE EDGE, not auto-calculated from source organization.

    This enables the Fascist Bifurcation scenario:
    - Periphery revolts BUT solidarity_strength=0 -> NO transmission -> Fascist turn
    - Periphery revolts AND solidarity_strength>0 -> Transmission -> Revolutionary turn
    """

    def test_solidarity_strength_default_zero(self) -> None:
        """solidarity_strength defaults to 0.0 (no built infrastructure)."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
        )
        assert edge.solidarity_strength == 0.0

    def test_solidarity_strength_can_be_set(self) -> None:
        """solidarity_strength can be set explicitly."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )
        assert edge.solidarity_strength == 0.8

    def test_solidarity_strength_accepts_zero(self) -> None:
        """Zero solidarity_strength is valid (Fascist scenario)."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.0,
        )
        assert edge.solidarity_strength == 0.0

    def test_solidarity_strength_accepts_one(self) -> None:
        """Maximum solidarity_strength (1.0) is valid."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=1.0,
        )
        assert edge.solidarity_strength == 1.0

    def test_solidarity_strength_rejects_negative(self) -> None:
        """Negative solidarity_strength is invalid."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C002",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=-0.1,
            )

    def test_solidarity_strength_rejects_greater_than_one(self) -> None:
        """solidarity_strength > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            Relationship(
                source_id="C001",
                target_id="C002",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=1.5,
            )

    def test_solidarity_strength_in_edge_data(self) -> None:
        """solidarity_strength is included in edge_data for NetworkX."""
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.7,
        )
        data = edge.edge_data
        assert "solidarity_strength" in data
        assert data["solidarity_strength"] == 0.7

    def test_solidarity_strength_on_non_solidarity_edge(self) -> None:
        """solidarity_strength can be set on any edge type for flexibility."""
        # While typically used on SOLIDARITY edges, we allow it on any edge
        # for modeling flexibility (e.g., potential solidarity in exploitation)
        edge = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            solidarity_strength=0.3,
        )
        assert edge.solidarity_strength == 0.3

    def test_solidarity_strength_json_round_trip(self) -> None:
        """solidarity_strength survives JSON round-trip."""
        original = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.65,
        )
        json_str = original.model_dump_json()
        restored = Relationship.model_validate_json(json_str)
        assert restored.solidarity_strength == pytest.approx(0.65)
