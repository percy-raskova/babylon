"""Tests for SocialClass entity model.

TDD Red Phase: These tests define the contract for SocialClass.
SocialClass is the fundamental node type in Phase 1 - it represents
a social class in the world system.

The tests verify:
1. Creation with required and default fields
2. Validation of ID patterns and field constraints
3. Integration with Sprint 1 types (Currency, Ideology, Probability)
4. Serialization for Ledger (SQLite) storage

Sprint 3.4.3 (George Jackson Refactor): ideology is now an IdeologicalProfile
with class_consciousness, national_identity, and agitation fields.
Tests updated to work with the multi-dimensional consciousness model.
"""

import pytest
from pydantic import ValidationError

# These imports should fail until the model is implemented
from babylon.models import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.math
class TestSocialClassCreation:
    """Test SocialClass instantiation with required and default fields."""

    def test_minimal_creation(self) -> None:
        """Can create SocialClass with just required fields."""
        worker = SocialClass(
            id="C001",
            name="Periphery Proletariat",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.id == "C001"
        assert worker.name == "Periphery Proletariat"
        assert worker.role == SocialRole.PERIPHERY_PROLETARIAT
        # Check defaults are applied
        assert worker.wealth == 10.0
        # ideology is now IdeologicalProfile (Sprint 3.4.3)
        assert isinstance(worker.ideology, IdeologicalProfile)
        assert worker.ideology.class_consciousness == 0.0

    def test_phase1_blueprint_worker(self) -> None:
        """Create the Phase 1 Worker node from the blueprint."""
        worker = SocialClass(
            id="C001",
            name="Periphery Mine Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=20.0,
            ideology=-0.3,  # Leaning revolutionary (legacy conversion)
        )
        assert worker.role == SocialRole.PERIPHERY_PROLETARIAT
        assert worker.wealth == 20.0
        # Legacy ideology=-0.3 converts to class_consciousness=0.65
        assert isinstance(worker.ideology, IdeologicalProfile)
        assert worker.ideology.to_legacy_ideology() == pytest.approx(-0.3, abs=0.01)

    def test_phase1_blueprint_owner(self) -> None:
        """Create the Phase 1 Owner node from the blueprint."""
        owner = SocialClass(
            id="C002",
            name="Core Factory Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=1000.0,
            ideology=0.7,  # Leaning reactionary (legacy conversion)
        )
        assert owner.role == SocialRole.CORE_BOURGEOISIE
        assert owner.wealth == 1000.0
        # Legacy ideology=0.7 converts to class_consciousness=0.15
        assert isinstance(owner.ideology, IdeologicalProfile)
        assert owner.ideology.to_legacy_ideology() == pytest.approx(0.7, abs=0.01)

    def test_all_social_roles_valid(self) -> None:
        """All SocialRole enum values are valid for creating a SocialClass."""
        for i, role in enumerate(SocialRole):
            class_instance = SocialClass(
                id=f"C{i:03d}",
                name=f"Test {role.value}",
                role=role,
            )
            assert class_instance.role == role

    def test_with_survival_probabilities(self) -> None:
        """Can create with explicit survival probabilities."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            p_acquiescence=0.7,
            p_revolution=0.2,
        )
        assert worker.p_acquiescence == 0.7
        assert worker.p_revolution == 0.2

    def test_with_material_conditions(self) -> None:
        """Can create with material conditions for survival calculus."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            subsistence_threshold=5.0,
            organization=0.3,
            repression_faced=0.6,
        )
        assert worker.subsistence_threshold == 5.0
        assert worker.organization == 0.3
        assert worker.repression_faced == 0.6

    def test_with_description(self) -> None:
        """Can create with optional description."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            description="Mine workers in the Global South",
        )
        assert worker.description == "Mine workers in the Global South"


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.math
class TestSocialClassValidation:
    """Test field constraints and validation rules."""

    def test_id_pattern_valid(self) -> None:
        """ID must match ^C[0-9]{3}$ pattern."""
        # Valid IDs
        for valid_id in ["C001", "C002", "C999", "C000"]:
            worker = SocialClass(
                id=valid_id,
                name="Test",
                role=SocialRole.PERIPHERY_PROLETARIAT,
            )
            assert worker.id == valid_id

    def test_id_pattern_rejects_invalid(self) -> None:
        """Invalid ID patterns are rejected."""
        invalid_ids = [
            "c001",  # lowercase
            "C01",  # too short
            "C0001",  # too long
            "X001",  # wrong prefix
            "001",  # missing prefix
            "CABC",  # letters instead of digits
            "",  # empty
        ]
        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError):
                SocialClass(
                    id=invalid_id,
                    name="Test",
                    role=SocialRole.PERIPHERY_PROLETARIAT,
                )

    def test_rejects_negative_wealth(self) -> None:
        """Wealth cannot be negative (Currency constraint)."""
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                name="Test",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                wealth=-10.0,
            )

    def test_rejects_ideology_out_of_range(self) -> None:
        """Legacy ideology must be [-1.0, 1.0] for conversion to work correctly.

        Note: Sprint 3.4.3 changed ideology to IdeologicalProfile. Legacy floats
        outside [-1, 1] are now clamped by the from_legacy_ideology() converter,
        so no ValidationError is raised. We test that clamping works correctly.
        """
        # Extreme negative value gets clamped to -1.0
        worker = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=-1.5,  # Clamped to -1.0 by from_legacy_ideology
        )
        assert worker.ideology.class_consciousness == 1.0  # -1.0 -> 1.0
        assert worker.ideology.national_identity == 0.0  # -1.0 -> 0.0

        # Extreme positive value gets clamped to +1.0
        worker2 = SocialClass(
            id="C002",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=1.5,  # Clamped to +1.0 by from_legacy_ideology
        )
        assert worker2.ideology.class_consciousness == 0.0  # +1.0 -> 0.0
        assert worker2.ideology.national_identity == 1.0  # +1.0 -> 1.0

    def test_rejects_invalid_probability(self) -> None:
        """Probabilities must be [0.0, 1.0]."""
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                name="Test",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                p_acquiescence=-0.1,
            )
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                name="Test",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                p_revolution=1.5,
            )

    def test_rejects_invalid_role_string(self) -> None:
        """Role must be a valid SocialRole enum value."""
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                name="Test",
                role="middle_class",  # type: ignore[arg-type]
            )

    def test_accepts_role_string_values(self) -> None:
        """Role accepts string values that match enum values."""
        worker = SocialClass(
            id="C001",
            name="Test",
            role="periphery_proletariat",  # type: ignore[arg-type]
        )
        assert worker.role == SocialRole.PERIPHERY_PROLETARIAT

    def test_name_required(self) -> None:
        """Name is a required field."""
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                role=SocialRole.PERIPHERY_PROLETARIAT,
            )  # type: ignore[call-arg]

    def test_role_required(self) -> None:
        """Role is a required field."""
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                name="Test",
            )  # type: ignore[call-arg]

    def test_extra_fields_forbidden(self) -> None:
        """Unknown fields are rejected."""
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                name="Test",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                unknown_field="value",  # type: ignore[call-arg]
            )


# =============================================================================
# DEFAULT VALUE TESTS
# =============================================================================


@pytest.mark.math
class TestSocialClassDefaults:
    """Test default values for optional fields."""

    def test_default_wealth(self) -> None:
        """Default wealth is 10.0 (baseline)."""
        worker = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.wealth == 10.0

    def test_default_ideology(self) -> None:
        """Default ideology is IdeologicalProfile with neutral defaults."""
        worker = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        # Sprint 3.4.3: ideology is now IdeologicalProfile
        assert isinstance(worker.ideology, IdeologicalProfile)
        assert worker.ideology.class_consciousness == 0.0
        assert worker.ideology.national_identity == 0.5
        assert worker.ideology.agitation == 0.0

    def test_default_probabilities(self) -> None:
        """Default survival probabilities are 0.0 (not yet calculated)."""
        worker = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.p_acquiescence == 0.0
        assert worker.p_revolution == 0.0

    def test_default_subsistence_threshold(self) -> None:
        """Default subsistence threshold is 5.0."""
        worker = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.subsistence_threshold == 5.0

    def test_default_organization(self) -> None:
        """Default organization is 0.1 (10% cohesion)."""
        worker = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.organization == 0.1

    def test_default_repression(self) -> None:
        """Default repression_faced is 0.5 (moderate)."""
        worker = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.repression_faced == 0.5

    def test_default_description(self) -> None:
        """Default description is empty string."""
        worker = SocialClass(
            id="C001",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.description == ""


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSocialClassSerialization:
    """Test JSON serialization for Ledger (SQLite) storage."""

    def test_serialize_to_json(self) -> None:
        """SocialClass serializes to valid JSON."""
        worker = SocialClass(
            id="C001",
            name="Mine Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
            ideology=-0.5,
        )
        json_str = worker.model_dump_json()
        assert '"id":"C001"' in json_str or '"id": "C001"' in json_str
        assert "Mine Worker" in json_str
        assert "periphery_proletariat" in json_str

    def test_deserialize_from_json(self) -> None:
        """SocialClass can be restored from JSON with legacy ideology."""
        json_str = """
        {
            "id": "C001",
            "name": "Mine Worker",
            "role": "periphery_proletariat",
            "wealth": 50.0,
            "ideology": -0.5,
            "description": "",
            "p_acquiescence": 0.0,
            "p_revolution": 0.0,
            "subsistence_threshold": 5.0,
            "organization": 0.1,
            "repression_faced": 0.5
        }
        """
        worker = SocialClass.model_validate_json(json_str)
        assert worker.id == "C001"
        assert worker.name == "Mine Worker"
        assert worker.role == SocialRole.PERIPHERY_PROLETARIAT
        assert worker.wealth == 50.0
        # Legacy ideology=-0.5 converts to IdeologicalProfile
        assert isinstance(worker.ideology, IdeologicalProfile)
        assert worker.ideology.to_legacy_ideology() == pytest.approx(-0.5, abs=0.01)

    def test_round_trip_preserves_values(self) -> None:
        """JSON round-trip preserves all field values."""
        original = SocialClass(
            id="C001",
            name="Test Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            description="A test class",
            wealth=100.0,
            ideology=-0.7,  # Legacy conversion
            p_acquiescence=0.6,
            p_revolution=0.3,
            subsistence_threshold=8.0,
            organization=0.4,
            repression_faced=0.7,
        )
        json_str = original.model_dump_json()
        restored = SocialClass.model_validate_json(json_str)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.role == original.role
        assert restored.description == original.description
        assert restored.wealth == pytest.approx(original.wealth)
        # ideology is now IdeologicalProfile - compare class_consciousness
        assert restored.ideology.class_consciousness == pytest.approx(
            original.ideology.class_consciousness
        )
        assert restored.p_acquiescence == pytest.approx(original.p_acquiescence)
        assert restored.p_revolution == pytest.approx(original.p_revolution)
        assert restored.subsistence_threshold == pytest.approx(original.subsistence_threshold)
        assert restored.organization == pytest.approx(original.organization)
        assert restored.repression_faced == pytest.approx(original.repression_faced)

    def test_dict_conversion(self) -> None:
        """SocialClass converts to dict for database storage."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
        )
        data = worker.model_dump()

        assert data["id"] == "C001"
        assert data["name"] == "Worker"
        assert data["role"] == "periphery_proletariat"
        assert data["wealth"] == 50.0


# =============================================================================
# NETWORKX INTEGRATION TESTS
# =============================================================================


@pytest.mark.topology
class TestSocialClassNetworkX:
    """Test integration with NetworkX graph storage."""

    def test_can_be_used_as_node_data(self) -> None:
        """SocialClass data can be stored as NetworkX node attributes."""
        import networkx as nx

        worker = SocialClass(
            id="C001",
            name="Mine Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
        )

        G = nx.DiGraph()
        G.add_node(worker.id, **worker.model_dump())

        assert G.has_node("C001")
        assert G.nodes["C001"]["name"] == "Mine Worker"
        assert G.nodes["C001"]["role"] == "periphery_proletariat"
        assert G.nodes["C001"]["wealth"] == 50.0

    def test_can_restore_from_node_data(self) -> None:
        """SocialClass can be restored from NetworkX node attributes."""
        import networkx as nx

        G = nx.DiGraph()
        G.add_node(
            "C001",
            id="C001",
            name="Mine Worker",
            role="periphery_proletariat",
            description="",
            wealth=50.0,
            ideology=-0.3,
            p_acquiescence=0.0,
            p_revolution=0.0,
            subsistence_threshold=5.0,
            organization=0.1,
            repression_faced=0.5,
        )

        node_data = dict(G.nodes["C001"])
        restored = SocialClass.model_validate(node_data)

        assert restored.id == "C001"
        assert restored.name == "Mine Worker"
        assert restored.role == SocialRole.PERIPHERY_PROLETARIAT
        assert restored.wealth == 50.0

    def test_two_nodes_can_coexist(self) -> None:
        """Phase 1 blueprint: two nodes can exist in the same graph."""
        import networkx as nx

        worker = SocialClass(
            id="C001",
            name="Periphery Mine Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        owner = SocialClass(
            id="C002",
            name="Core Factory Owner",
            role=SocialRole.CORE_BOURGEOISIE,
        )

        G = nx.DiGraph()
        G.add_node(worker.id, **worker.model_dump())
        G.add_node(owner.id, **owner.model_dump())

        assert G.number_of_nodes() == 2
        assert G.nodes["C001"]["role"] == "periphery_proletariat"
        assert G.nodes["C002"]["role"] == "core_bourgeoisie"


# =============================================================================
# COMPONENT MODEL TESTS
# =============================================================================


@pytest.mark.math
class TestComponentModels:
    """Test component model creation and validation."""

    def test_economic_component_creation(self) -> None:
        """Can create EconomicComponent with valid data."""
        from babylon.models.entities.social_class import EconomicComponent

        econ = EconomicComponent(wealth=50.0, subsistence_threshold=10.0)
        assert econ.wealth == 50.0
        assert econ.subsistence_threshold == 10.0

    def test_ideological_component_creation(self) -> None:
        """Can create IdeologicalComponent with valid data."""
        from babylon.models.entities.social_class import IdeologicalComponent

        # Sprint 3.4.3: ideology in IdeologicalComponent is now IdeologicalProfile
        profile = IdeologicalProfile(class_consciousness=0.75, national_identity=0.3)
        ideo = IdeologicalComponent(ideology=profile, organization=0.3)
        assert ideo.ideology.class_consciousness == 0.75
        assert ideo.organization == 0.3

    def test_survival_component_creation(self) -> None:
        """Can create SurvivalComponent with valid data."""
        from babylon.models.entities.social_class import SurvivalComponent

        surv = SurvivalComponent(p_acquiescence=0.6, p_revolution=0.4)
        assert surv.p_acquiescence == 0.6
        assert surv.p_revolution == 0.4

    def test_material_conditions_component_creation(self) -> None:
        """Can create MaterialConditionsComponent with valid data."""
        from babylon.models.entities.social_class import MaterialConditionsComponent

        mat = MaterialConditionsComponent(repression_faced=0.7)
        assert mat.repression_faced == 0.7

    def test_component_is_frozen(self) -> None:
        """Components are immutable."""
        from babylon.models.entities.social_class import EconomicComponent

        econ = EconomicComponent(wealth=50.0)
        with pytest.raises(ValidationError):
            econ.wealth = 100.0  # type: ignore[misc]


@pytest.mark.math
class TestSocialClassComponentConstruction:
    """Test component-based SocialClass construction."""

    def test_create_with_economic_component(self) -> None:
        """Can create SocialClass using EconomicComponent."""
        from babylon.models.entities.social_class import EconomicComponent

        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            economic=EconomicComponent(wealth=50.0, subsistence_threshold=10.0),
        )
        assert worker.wealth == 50.0
        assert worker.subsistence_threshold == 10.0

    def test_create_with_all_components(self) -> None:
        """Can create SocialClass using all components."""
        from babylon.models.entities.social_class import (
            EconomicComponent,
            IdeologicalComponent,
            MaterialConditionsComponent,
            SurvivalComponent,
        )

        # Sprint 3.4.3: ideology in IdeologicalComponent is now IdeologicalProfile
        profile = IdeologicalProfile(class_consciousness=0.75, national_identity=0.25)
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            economic=EconomicComponent(wealth=50.0),
            ideological=IdeologicalComponent(ideology=profile, organization=0.3),
            survival=SurvivalComponent(p_acquiescence=0.6, p_revolution=0.4),
            material_conditions=MaterialConditionsComponent(repression_faced=0.7),
        )
        assert worker.wealth == 50.0
        assert worker.ideology.class_consciousness == 0.75
        assert worker.organization == 0.3
        assert worker.p_acquiescence == 0.6
        assert worker.p_revolution == 0.4
        assert worker.repression_faced == 0.7

    def test_flat_construction_still_works(self) -> None:
        """Flat field construction with legacy ideology is unchanged."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
            ideology=-0.3,  # Legacy float converted to IdeologicalProfile
        )
        assert worker.wealth == 50.0
        # Legacy ideology=-0.3 converts to class_consciousness=0.65
        assert isinstance(worker.ideology, IdeologicalProfile)
        assert worker.ideology.to_legacy_ideology() == pytest.approx(-0.3, abs=0.01)

    def test_serialization_remains_flat(self) -> None:
        """model_dump() produces flat output."""
        from babylon.models.entities.social_class import EconomicComponent

        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            economic=EconomicComponent(wealth=50.0),
        )
        data = worker.model_dump()

        assert "wealth" in data
        assert data["wealth"] == 50.0
        assert "economic" not in data


@pytest.mark.math
class TestSocialClassComponentAccess:
    """Test accessing entity data via component properties."""

    def test_access_economic_component(self) -> None:
        """Can access economic data via component property."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
            subsistence_threshold=10.0,
        )
        assert worker.economic.wealth == 50.0
        assert worker.economic.subsistence_threshold == 10.0

    def test_access_ideological_component(self) -> None:
        """Can access ideological data via component property."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            ideology=-0.5,  # Legacy conversion to IdeologicalProfile
            organization=0.3,
        )
        # Sprint 3.4.3: ideology is now IdeologicalProfile
        assert isinstance(worker.ideological.ideology, IdeologicalProfile)
        assert worker.ideological.ideology.to_legacy_ideology() == pytest.approx(-0.5, abs=0.01)
        assert worker.ideological.organization == 0.3

    def test_access_survival_component(self) -> None:
        """Can access survival data via component property."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            p_acquiescence=0.6,
            p_revolution=0.4,
        )
        assert worker.survival.p_acquiescence == 0.6
        assert worker.survival.p_revolution == 0.4

    def test_access_material_conditions_component(self) -> None:
        """Can access material conditions via component property."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            repression_faced=0.7,
        )
        assert worker.material_conditions.repression_faced == 0.7

    def test_component_returns_correct_type(self) -> None:
        """Component properties return correct types."""
        from babylon.models.entities.social_class import (
            EconomicComponent,
            IdeologicalComponent,
            MaterialConditionsComponent,
            SurvivalComponent,
        )

        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert isinstance(worker.economic, EconomicComponent)
        assert isinstance(worker.ideological, IdeologicalComponent)
        assert isinstance(worker.survival, SurvivalComponent)
        assert isinstance(worker.material_conditions, MaterialConditionsComponent)


# =============================================================================
# METABOLIC CONSUMPTION TESTS (Slice 1.4)
# =============================================================================


@pytest.mark.math
class TestSocialClassMetabolicDefaults:
    """SocialClass metabolic fields should have sensible defaults."""

    def test_s_bio_defaults_to_0_01(self) -> None:
        """Biological minimum defaults to 0.01 (1% of baseline)."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.s_bio == 0.01

    def test_s_class_defaults_to_0(self) -> None:
        """Social reproduction defaults to 0 (no lifestyle overhead)."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        assert worker.s_class == 0.0


@pytest.mark.math
class TestSocialClassMetabolicConstraints:
    """SocialClass metabolic fields should be properly constrained."""

    def test_s_bio_accepts_zero(self) -> None:
        """Zero biological minimum is valid (edge case)."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.0,
        )
        assert worker.s_bio == 0.0

    def test_s_bio_rejects_negative(self) -> None:
        """Negative biological minimum is invalid."""
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                name="Worker",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                s_bio=-0.01,
            )

    def test_s_class_accepts_zero(self) -> None:
        """Zero social reproduction is valid (subsistence living)."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_class=0.0,
        )
        assert worker.s_class == 0.0

    def test_s_class_rejects_negative(self) -> None:
        """Negative social reproduction is invalid."""
        with pytest.raises(ValidationError):
            SocialClass(
                id="C001",
                name="Worker",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                s_class=-0.5,
            )

    def test_s_class_accepts_high_value(self) -> None:
        """High social reproduction is valid (labor aristocracy lifestyle)."""
        bourgeois = SocialClass(
            id="C001",
            name="Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            s_class=10.0,
        )
        assert bourgeois.s_class == 10.0


@pytest.mark.math
class TestSocialClassConsumptionNeeds:
    """SocialClass consumption_needs computed property."""

    def test_consumption_needs_sums_s_bio_and_s_class(self) -> None:
        """Consumption needs = s_bio + s_class."""
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.05,
            s_class=0.15,
        )
        assert worker.consumption_needs == pytest.approx(0.20, abs=0.001)

    def test_consumption_needs_zero_when_both_zero(self) -> None:
        """Zero consumption when both components are zero."""
        minimal = SocialClass(
            id="C001",
            name="Minimal",
            role=SocialRole.LUMPENPROLETARIAT,
            s_bio=0.0,
            s_class=0.0,
        )
        assert minimal.consumption_needs == 0.0

    def test_consumption_needs_bio_only(self) -> None:
        """Consumption equals s_bio when s_class is zero."""
        subsistence = SocialClass(
            id="C001",
            name="Subsistence",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.03,
            s_class=0.0,
        )
        assert subsistence.consumption_needs == pytest.approx(0.03, abs=0.001)

    def test_consumption_needs_class_difference(self) -> None:
        """Different classes have different consumption needs."""
        proletariat = SocialClass(
            id="C001",
            name="Proletariat",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            s_bio=0.02,
            s_class=0.01,
        )
        labor_aristocracy = SocialClass(
            id="C002",
            name="Labor Aristocracy",
            role=SocialRole.LABOR_ARISTOCRACY,
            s_bio=0.02,
            s_class=0.10,  # Higher lifestyle expectations
        )

        assert proletariat.consumption_needs < labor_aristocracy.consumption_needs
        assert proletariat.consumption_needs == pytest.approx(0.03, abs=0.001)
        assert labor_aristocracy.consumption_needs == pytest.approx(0.12, abs=0.001)
