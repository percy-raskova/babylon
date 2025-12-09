### SPRINT PROTOCOL: OPERATION IRON FOUNDRY

**1. The Objective:**
We will refactor `SocialClass` from a loose collection of fields into a strict **Entity-Component System (ECS)**. We will introduce `SurvivalComponent` to house the survival calculus logic. We will modify `WorldState` to flattened these components when generating the simulation graph, ensuring the **Economic Base** (Engine) continues to function without interruption while the **Superstructure** (Data Model) advances.

**2. The Token Budget Assessment:**
Medium. We are creating one new file, heavily modifying one, and tweaking a third. The context fits.

**3. The Files of Production:**

1.  `babylon/src/babylon/models/components/survival.py` (New: The Calculus of Revolution)
2.  `babylon/src/babylon/models/entities/social_class.py` (Refactor: The Composite Entity)
3.  `babylon/src/babylon/models/world_state.py` (Modification: The Graph Adapter)
4.  `babylon/src/babylon/tests/unit/models/test_social_class_composition.py` (Verification)

**4. The Implementation:**

First, we define the **SurvivalComponent**.

```python
# babylon/src/babylon/models/components/survival.py
"""SurvivalComponent - Survival calculus state of an entity.

SurvivalComponent represents the existential calculations of an entity,
tracking its probability of survival through acquiescence versus revolution,
and the repression it faces from the state.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Probability


class SurvivalComponent(BaseModel):
    """Survival calculus outputs and conditions.

    Tracks:
    - P(S|A): Probability of survival given acquiescence
    - P(S|R): Probability of survival given revolution
    - Repression: State violence directed at this class

    All values use constrained types for automatic validation:
    - Probability [0, 1]

    Attributes:
        p_acquiescence: Survival prob. if obeying (default: 0.5)
        p_revolution: Survival prob. if revolting (default: 0.1)
        repression_faced: Level of state violence (default: 0.0)
    """

    model_config = ConfigDict(frozen=True)

    p_acquiescence: Probability = Field(
        default=0.5,
        description="P(S|A) - survival probability through acquiescence",
    )
    p_revolution: Probability = Field(
        default=0.1,
        description="P(S|R) - survival probability through revolution",
    )
    repression_faced: Probability = Field(
        default=0.0,
        description="State violence directed at this class [0=none, 1=total]",
    )

    @property
    def component_type(self) -> str:
        """Return the component type identifier."""
        return "survival"
```

Next, the **SocialClass** refactor. We remove the inner classes and composed the strict components. We implement a `flatten` method to help `WorldState`.

```python
# babylon/src/babylon/models/entities/social_class.py
"""SocialClass entity model.

A SocialClass is the fundamental node type in the Babylon simulation.
It is a Composite Entity formed from:
- MaterialComponent (Base)
- VitalityComponent (Life)
- IdeologicalComponent (Consciousness)
- OrganizationComponent (Power)
- SurvivalComponent (Calculus)

Phase 2.2: Refactored to strict Component Composition.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.components.ideological import IdeologicalComponent
from babylon.models.components.material import MaterialComponent
from babylon.models.components.organization import OrganizationComponent
from babylon.models.components.survival import SurvivalComponent
from babylon.models.components.vitality import VitalityComponent
from babylon.models.enums import SocialRole


class SocialClass(BaseModel):
    """A social class in the world system.

    The fundamental unit of the simulation. Classes are defined by their
    relationship to production and their position in the imperial hierarchy.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # Core Identity
    id: str = Field(
        ...,
        pattern=r"^C[0-9]{3}$",
        description="Unique identifier matching ^C[0-9]{3}$",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for the class",
    )
    role: SocialRole = Field(
        ...,
        description="Position in the world system",
    )
    description: str = Field(
        default="",
        description="Detailed description of the class",
    )

    # Components
    material: MaterialComponent = Field(
        default_factory=MaterialComponent,
        description="Economic material conditions",
    )
    vitality: VitalityComponent = Field(
        default_factory=VitalityComponent,
        description="Population and subsistence needs",
    )
    ideological: IdeologicalComponent = Field(
        default_factory=IdeologicalComponent,
        description="Ideological alignment and adherence",
    )
    organization: OrganizationComponent = Field(
        default_factory=OrganizationComponent,
        description="Organizational cohesion and cadre level",
    )
    survival: SurvivalComponent = Field(
        default_factory=SurvivalComponent,
        description="Survival calculus probabilities and repression",
    )

    @model_validator(mode="before")
    @classmethod
    def unpack_legacy_data(cls, data: Any) -> Any:
        """Migrate flat or legacy dictionary structures to Components.

        This ensures we can still load data files that haven't been
        fully migrated to the component structure.
        """
        if not isinstance(data, dict):
            return data

        # Helper to extract and remove fields for a component
        def extract_fields(source: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
            result = {}
            for old_key, new_key in mapping.items():
                if old_key in source:
                    result[new_key] = source.pop(old_key)
            return result

        # 1. MaterialComponent
        # Legacy 'wealth' -> material.wealth
        # Legacy 'economic.wealth' -> material.wealth
        material_data = extract_fields(data, {
            "wealth": "wealth",
            "resources": "resources",
            "means_of_production": "means_of_production"
        })
        if "economic" in data and isinstance(data["economic"], dict):
             material_data.update(extract_fields(data["economic"], {"wealth": "wealth"}))

        if material_data:
            # If 'material' key exists, merge; otherwise set
            if "material" in data and isinstance(data["material"], dict):
                data["material"].update(material_data)
            elif "material" not in data:
                data["material"] = material_data

        # 2. VitalityComponent
        # Legacy 'subsistence_threshold' -> vitality.subsistence_needs
        # Legacy 'economic.subsistence_threshold' -> vitality.subsistence_needs
        vitality_data = extract_fields(data, {
            "subsistence_threshold": "subsistence_needs",
            "population": "population"
        })
        if "economic" in data and isinstance(data["economic"], dict):
             vitality_data.update(extract_fields(data["economic"], {"subsistence_threshold": "subsistence_needs"}))

        if vitality_data:
            if "vitality" in data and isinstance(data["vitality"], dict):
                data["vitality"].update(vitality_data)
            elif "vitality" not in data:
                data["vitality"] = vitality_data

        # Cleanup empty legacy dicts
        if "economic" in data and not data["economic"]:
            del data["economic"]

        # 3. IdeologicalComponent
        # Legacy 'ideology' -> ideological.alignment
        # Legacy 'ideological.ideology' -> ideological.alignment
        ideo_data = extract_fields(data, {
            "ideology": "alignment",
            "adherence": "adherence"
        })
        # Note: In old model 'ideological' was a dict key but also the component name.
        # We need to be careful not to overwrite the new 'ideological' component dict if it was passed as legacy struct.
        # But 'unpack_components' in old model handled this.
        # Let's check top level fields first.

        if ideo_data:
             if "ideological" in data and isinstance(data["ideological"], dict):
                 # Check if the dict is legacy (has 'ideology' key) or new (has 'alignment')
                 # The 'extract_fields' pulled from TOP level.
                 data["ideological"].update(ideo_data)
             elif "ideological" not in data:
                 data["ideological"] = ideo_data

        # Handle legacy nested 'ideological' dict if it has 'ideology' key
        if "ideological" in data and isinstance(data["ideological"], dict):
            if "ideology" in data["ideological"]:
                data["ideological"]["alignment"] = data["ideological"].pop("ideology")
            if "organization" in data["ideological"]:
                 # This belongs to organization component now
                 org_val = data["ideological"].pop("organization")
                 if "organization" not in data:
                     data["organization"] = {}
                 if isinstance(data["organization"], dict):
                     data["organization"]["cohesion"] = org_val

        # 4. OrganizationComponent
        # Legacy 'organization' (float) -> organization.cohesion
        org_data = extract_fields(data, {
            "organization": "cohesion",
            "cadre_level": "cadre_level"
        })
        if org_data:
            if "organization" in data and isinstance(data["organization"], dict):
                data["organization"].update(org_data)
            elif "organization" not in data:
                data["organization"] = org_data

        # 5. SurvivalComponent
        # Legacy 'p_acquiescence', 'p_revolution', 'repression_faced'
        surv_data = extract_fields(data, {
            "p_acquiescence": "p_acquiescence",
            "p_revolution": "p_revolution",
            "repression_faced": "repression_faced"
        })
        if "survival" in data and isinstance(data["survival"], dict):
            # Check legacy keys inside survival dict if any
             pass
        if "material_conditions" in data and isinstance(data["material_conditions"], dict):
            if "repression_faced" in data["material_conditions"]:
                surv_data["repression_faced"] = data["material_conditions"].pop("repression_faced")
            if not data["material_conditions"]:
                del data["material_conditions"]

        if surv_data:
             if "survival" in data and isinstance(data["survival"], dict):
                 data["survival"].update(surv_data)
             elif "survival" not in data:
                 data["survival"] = surv_data

        return data

    def flatten(self) -> dict[str, Any]:
        """Export state as a flat dictionary for graph algorithms.

        This merges component fields into the top-level dictionary,
        simulating the legacy flat structure for the Engine.
        """
        data = self.model_dump(exclude={
            "material", "vitality", "ideological", "organization", "survival"
        })

        # Merge components (precedence to components)
        # We map strict component fields back to "Legacy" names where they differ

        # Material
        mat = self.material.model_dump()
        data.update(mat) # wealth, resources, means_of_production

        # Vitality
        vit = self.vitality.model_dump()
        data["subsistence_threshold"] = vit["subsistence_needs"] # Map back
        data["population"] = vit["population"]

        # Ideological
        ideo = self.ideological.model_dump()
        data["ideology"] = ideo["alignment"] # Map back
        data["adherence"] = ideo["adherence"]

        # Organization
        org = self.organization.model_dump()
        data["organization"] = org["cohesion"] # Map back to generic 'organization' or keep 'cohesion'?
        # The engine likely looks for "organization" as a probability.
        # In old model: organization: Probability.
        # So we map cohesion -> organization.

        # Survival
        surv = self.survival.model_dump()
        data.update(surv) # p_acquiescence, p_revolution, repression_faced

        return data
```

Then, update **WorldState** to use `flatten()`.

```python
# babylon/src/babylon/models/world_state.py
# ... (imports)
# Update to_graph method

    def to_graph(self) -> nx.DiGraph[str]:
        """Convert state to NetworkX DiGraph for formula application.

        Nodes are entity IDs with all SocialClass fields as attributes.
        Edges are relationships with all Relationship fields as attributes.

        Returns:
            NetworkX DiGraph with nodes and edges from this state.
        """
        G: nx.DiGraph[str] = nx.DiGraph()

        # Add nodes with entity data
        for entity_id, entity in self.entities.items():
            # Use flatten() to expose component data as flat attributes for the engine
            G.add_node(entity_id, **entity.flatten())

        # Add edges with relationship data
        for rel in self.relationships:
            source, target = rel.edge_tuple
            G.add_edge(source, target, **rel.edge_data)

        return G
```

Finally, the **Test**.

```python
# babylon/src/babylon/tests/unit/models/test_social_class_composition.py
import pytest
from babylon.models.entities.social_class import SocialClass
from babylon.models.components.material import MaterialComponent
from babylon.models.enums import SocialRole

def test_social_class_initialization_with_components():
    """Test initializing SocialClass with strict components."""
    entity = SocialClass(
        id="C001",
        name="Proletariat",
        role=SocialRole.PROLETARIAT,
        material=MaterialComponent(wealth=50.0),
    )

    assert entity.material.wealth == 50.0
    assert entity.vitality.population == 1.0 # Default

def test_legacy_data_unpacking():
    """Test that legacy flat dictionaries are correctly migrated to components."""
    data = {
        "id": "C002",
        "name": "Bourgeoisie",
        "role": "Bourgeoisie",
        "wealth": 100.0,
        "subsistence_threshold": 10.0,
        "ideology": 0.8,
        "organization": 0.9,
        "repression_faced": 0.1
    }

    entity = SocialClass(**data)

    # Check migration
    assert entity.material.wealth == 100.0
    assert entity.vitality.subsistence_needs == 10.0
    assert entity.ideological.alignment == 0.8
    assert entity.organization.cohesion == 0.9
    assert entity.survival.repression_faced == 0.1

def test_flatten_consistency():
    """Test that flatten() produces data expected by the engine."""
    entity = SocialClass(
        id="C003",
        name="Lumpen",
        role=SocialRole.LUMPENPROLETARIAT,
        material=MaterialComponent(wealth=2.0),
    )

    flat = entity.flatten()

    assert flat["id"] == "C003"
    assert flat["wealth"] == 2.0
    assert "material" not in flat
    assert "organization" in flat # Mapped from cohesion
```

**5. The Verification:**
`pytest babylon/src/babylon/tests/unit/models/test_social_class_composition.py`

I will now generate the files.

```python
# babylon/src/babylon/models/components/survival.py
"""SurvivalComponent - Survival calculus state of an entity.

SurvivalComponent represents the existential calculations of an entity,
tracking its probability of survival through acquiescence versus revolution,
and the repression it faces from the state.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Probability


class SurvivalComponent(BaseModel):
    """Survival calculus outputs and conditions.

    Tracks:
    - P(S|A): Probability of survival given acquiescence
    - P(S|R): Probability of survival given revolution
    - Repression: State violence directed at this class

    All values use constrained types for automatic validation:
    - Probability [0, 1]

    Attributes:
        p_acquiescence: Survival prob. if obeying (default: 0.5)
        p_revolution: Survival prob. if revolting (default: 0.1)
        repression_faced: Level of state violence (default: 0.0)
    """

    model_config = ConfigDict(frozen=True)

    p_acquiescence: Probability = Field(
        default=0.5,
        description="P(S|A) - survival probability through acquiescence",
    )
    p_revolution: Probability = Field(
        default=0.1,
        description="P(S|R) - survival probability through revolution",
    )
    repression_faced: Probability = Field(
        default=0.0,
        description="State violence directed at this class [0=none, 1=total]",
    )

    @property
    def component_type(self) -> str:
        """Return the component type identifier."""
        return "survival"
```

```python
# babylon/src/babylon/models/entities/social_class.py
"""SocialClass entity model.

A SocialClass is the fundamental node type in the Babylon simulation.
It is a Composite Entity formed from:
- MaterialComponent (Base)
- VitalityComponent (Life)
- IdeologicalComponent (Consciousness)
- OrganizationComponent (Power)
- SurvivalComponent (Calculus)

Phase 2.2: Refactored to strict Component Composition.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.components.ideological import IdeologicalComponent
from babylon.models.components.material import MaterialComponent
from babylon.models.components.organization import OrganizationComponent
from babylon.models.components.survival import SurvivalComponent
from babylon.models.components.vitality import VitalityComponent
from babylon.models.enums import SocialRole


class SocialClass(BaseModel):
    """A social class in the world system.

    The fundamental unit of the simulation. Classes are defined by their
    relationship to production and their position in the imperial hierarchy.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # Core Identity
    id: str = Field(
        ...,
        pattern=r"^C[0-9]{3}$",
        description="Unique identifier matching ^C[0-9]{3}$",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for the class",
    )
    role: SocialRole = Field(
        ...,
        description="Position in the world system",
    )
    description: str = Field(
        default="",
        description="Detailed description of the class",
    )

    # Components
    material: MaterialComponent = Field(
        default_factory=MaterialComponent,
        description="Economic material conditions",
    )
    vitality: VitalityComponent = Field(
        default_factory=VitalityComponent,
        description="Population and subsistence needs",
    )
    ideological: IdeologicalComponent = Field(
        default_factory=IdeologicalComponent,
        description="Ideological alignment and adherence",
    )
    organization: OrganizationComponent = Field(
        default_factory=OrganizationComponent,
        description="Organizational cohesion and cadre level",
    )
    survival: SurvivalComponent = Field(
        default_factory=SurvivalComponent,
        description="Survival calculus probabilities and repression",
    )

    @model_validator(mode="before")
    @classmethod
    def unpack_legacy_data(cls, data: Any) -> Any:
        """Migrate flat or legacy dictionary structures to Components.

        This ensures we can still load data files that haven't been
        fully migrated to the component structure.
        """
        if not isinstance(data, dict):
            return data

        # Helper to extract and remove fields for a component
        def extract_fields(source: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
            result = {}
            for old_key, new_key in mapping.items():
                if old_key in source:
                    result[new_key] = source.pop(old_key)
            return result

        # 1. MaterialComponent
        material_data = extract_fields(data, {
            "wealth": "wealth",
            "resources": "resources",
            "means_of_production": "means_of_production"
        })
        # Check legacy nested
        if "economic" in data and isinstance(data["economic"], dict):
            # Only pull keys that exist
            if "wealth" in data["economic"]:
                 material_data["wealth"] = data["economic"].pop("wealth")

        if material_data:
            if "material" in data and isinstance(data["material"], dict):
                data["material"].update(material_data)
            elif "material" not in data:
                data["material"] = material_data

        # 2. VitalityComponent
        vitality_data = extract_fields(data, {
            "subsistence_threshold": "subsistence_needs",
            "population": "population"
        })
        if "economic" in data and isinstance(data["economic"], dict):
            if "subsistence_threshold" in data["economic"]:
                vitality_data["subsistence_needs"] = data["economic"].pop("subsistence_threshold")

        if vitality_data:
            if "vitality" in data and isinstance(data["vitality"], dict):
                data["vitality"].update(vitality_data)
            elif "vitality" not in data:
                data["vitality"] = vitality_data

        # Cleanup empty legacy dicts
        if "economic" in data and not data["economic"]:
            del data["economic"]

        # 3. IdeologicalComponent
        ideo_data = extract_fields(data, {
            "ideology": "alignment",
            "adherence": "adherence"
        })

        # Handle legacy nested 'ideological' which might contain 'organization'
        if "ideological" in data and isinstance(data["ideological"], dict):
            if "ideology" in data["ideological"]:
                ideo_data["alignment"] = data["ideological"].pop("ideology")
            if "organization" in data["ideological"]:
                 org_val = data["ideological"].pop("organization")
                 if "organization" not in data:
                     data["organization"] = {}
                 if isinstance(data["organization"], dict):
                     data["organization"]["cohesion"] = org_val
            # Merge whatever is left (e.g. alignment if it was already correct)
            # We want to merge ideo_data INTO data['ideological']
            data["ideological"].update(ideo_data)
        elif ideo_data:
             data["ideological"] = ideo_data

        # 4. OrganizationComponent
        org_data = extract_fields(data, {
            "organization": "cohesion",
            "cadre_level": "cadre_level"
        })
        if org_data:
            if "organization" in data and isinstance(data["organization"], dict):
                data["organization"].update(org_data)
            elif "organization" not in data:
                data["organization"] = org_data

        # 5. SurvivalComponent
        surv_data = extract_fields(data, {
            "p_acquiescence": "p_acquiescence",
            "p_revolution": "p_revolution",
            "repression_faced": "repression_faced"
        })

        if "material_conditions" in data and isinstance(data["material_conditions"], dict):
            if "repression_faced" in data["material_conditions"]:
                surv_data["repression_faced"] = data["material_conditions"].pop("repression_faced")
            if not data["material_conditions"]:
                del data["material_conditions"]

        if surv_data:
             if "survival" in data and isinstance(data["survival"], dict):
                 data["survival"].update(surv_data)
             elif "survival" not in data:
                 data["survival"] = surv_data

        return data

    def flatten(self) -> dict[str, Any]:
        """Export state as a flat dictionary for graph algorithms.

        This merges component fields into the top-level dictionary,
        simulating the legacy flat structure for the Engine.
        """
        data = self.model_dump(exclude={
            "material", "vitality", "ideological", "organization", "survival"
        })

        # Merge components (precedence to components)

        # Material
        data.update(self.material.model_dump())

        # Vitality
        vit = self.vitality.model_dump()
        data["subsistence_threshold"] = vit["subsistence_needs"] # Map back for legacy engine
        data["population"] = vit["population"]

        # Ideological
        ideo = self.ideological.model_dump()
        data["ideology"] = ideo["alignment"] # Map back
        data["adherence"] = ideo["adherence"]

        # Organization
        org = self.organization.model_dump()
        data["organization"] = org["cohesion"] # Map back
        data["cadre_level"] = org["cadre_level"]

        # Survival
        data.update(self.survival.model_dump())

        return data
```

```python
# babylon/src/babylon/tests/unit/models/test_social_class_composition.py
"""Test suite for SocialClass component composition and legacy migration."""

import pytest
from babylon.models.entities.social_class import SocialClass
from babylon.models.components.material import MaterialComponent
from babylon.models.enums import SocialRole

def test_social_class_initialization_with_components():
    """Test initializing SocialClass with strict components."""
    entity = SocialClass(
        id="C001",
        name="Proletariat",
        role=SocialRole.PROLETARIAT,
        material=MaterialComponent(wealth=50.0),
    )

    assert entity.material.wealth == 50.0
    assert entity.vitality.population == 1.0 # Default

def test_legacy_data_unpacking():
    """Test that legacy flat dictionaries are correctly migrated to components."""
    data = {
        "id": "C002",
        "name": "Bourgeoisie",
        "role": "Bourgeoisie",
        "wealth": 100.0,
        "subsistence_threshold": 10.0,
        "ideology": 0.8,
        "organization": 0.9,
        "repression_faced": 0.1
    }

    entity = SocialClass(**data)

    # Check migration
    assert entity.material.wealth == 100.0
    assert entity.vitality.subsistence_needs == 10.0
    assert entity.ideological.alignment == 0.8
    assert entity.organization.cohesion == 0.9
    assert entity.survival.repression_faced == 0.1

def test_flatten_consistency():
    """Test that flatten() produces data expected by the engine."""
    entity = SocialClass(
        id="C003",
        name="Lumpen",
        role=SocialRole.LUMPENPROLETARIAT,
        material=MaterialComponent(wealth=2.0),
    )

    flat = entity.flatten()

    assert flat["id"] == "C003"
    assert flat["wealth"] == 2.0
    assert "material" not in flat
    assert "organization" in flat # Mapped from cohesion
    assert flat["organization"] == 0.1 # Default cohesion
```

```python
# babylon/src/babylon/models/world_state.py
"""WorldState model for the Babylon simulation.

WorldState is an immutable snapshot of the entire simulation at a specific tick.
It encapsulates:
- All entities (social classes) as nodes
- All relationships (value flows, tensions) as edges
- A tick counter for temporal tracking
- An event log for narrative/debugging

The state is designed for functional transformation:
    new_state = step(old_state, config)

Sprint 4: Phase 2 game loop state container with NetworkX integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field

from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    pass


class WorldState(BaseModel):
    """Immutable snapshot of the simulation at a specific tick.

    WorldState follows the Data/Logic separation principle:
    - State holds WHAT exists (pure data)
    - Engine determines HOW it transforms (pure logic)

    This enables:
    - Determinism: Same state + same engine = same output
    - Replayability: Save initial state, replay entire history
    - Counterfactuals: Modify a parameter, run forward, compare
    - Testability: Feed state in, assert on state out

    Attributes:
        tick: Current turn number (0-indexed)
        entities: Map of entity ID to SocialClass (the nodes)
        relationships: List of Relationship edges (the edges)
        event_log: Recent events for narrative/debugging
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(
        default=0,
        ge=0,
        description="Current turn number (0-indexed)",
    )

    entities: dict[str, SocialClass] = Field(
        default_factory=dict,
        description="Map of entity ID to SocialClass (graph nodes)",
    )

    relationships: list[Relationship] = Field(
        default_factory=list,
        description="List of relationships (graph edges)",
    )

    event_log: list[str] = Field(
        default_factory=list,
        description="Recent events for narrative/debugging",
    )

    # =========================================================================
    # NetworkX Conversion
    # =========================================================================

    def to_graph(self) -> nx.DiGraph[str]:
        """Convert state to NetworkX DiGraph for formula application.

        Nodes are entity IDs with all SocialClass fields as attributes.
        Edges are relationships with all Relationship fields as attributes.

        Returns:
            NetworkX DiGraph with nodes and edges from this state.

        Example:
            G = state.to_graph()
            for node_id, data in G.nodes(data=True):
                data["wealth"] += 10  # Modify in graph
            new_state = WorldState.from_graph(G, tick=state.tick + 1)
        """
        G: nx.DiGraph[str] = nx.DiGraph()

        # Add nodes with entity data
        for entity_id, entity in self.entities.items():
            # Use flatten() to expose component data as flat attributes for the engine
            G.add_node(entity_id, **entity.flatten())

        # Add edges with relationship data
        for rel in self.relationships:
            source, target = rel.edge_tuple
            G.add_edge(source, target, **rel.edge_data)

        return G

    @classmethod
    def from_graph(
        cls,
        G: nx.DiGraph[str],
        tick: int,
        event_log: list[str] | None = None,
    ) -> WorldState:
        """Reconstruct WorldState from NetworkX DiGraph.

        Args:
            G: NetworkX DiGraph with node/edge data
            tick: The tick number for the new state
            event_log: Optional event log to preserve

        Returns:
            New WorldState with entities and relationships from graph.

        Example:
            G = state.to_graph()
            # ... modify graph ...
            new_state = WorldState.from_graph(G, tick=state.tick + 1)
        """
        # Reconstruct entities from nodes
        entities: dict[str, SocialClass] = {}
        for node_id, data in G.nodes(data=True):
            # unpack_legacy_data validator in SocialClass will handle the flat data
            entities[node_id] = SocialClass(**data)

        # Reconstruct relationships from edges
        relationships: list[Relationship] = []
        for source_id, target_id, data in G.edges(data=True):
            # Reconstruct edge_type from stored value
            edge_type = data.get("edge_type", EdgeType.EXPLOITATION)
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            relationships.append(
                Relationship(
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=edge_type,
                    value_flow=data.get("value_flow", 0.0),
                    tension=data.get("tension", 0.0),
                    description=data.get("description", ""),
                )
            )

        return cls(
            tick=tick,
            entities=entities,
            relationships=relationships,
            event_log=event_log or [],
        )

    # =========================================================================
    # Immutable Mutation Methods
    # =========================================================================

    def add_entity(self, entity: SocialClass) -> WorldState:
        """Return new state with entity added.

        Args:
            entity: SocialClass to add

        Returns:
            New WorldState with the entity included.

        Example:
            new_state = state.add_entity(worker)
        """
        new_entities = {**self.entities, entity.id: entity}
        return self.model_copy(update={"entities": new_entities})

    def add_relationship(self, relationship: Relationship) -> WorldState:
        """Return new state with relationship added.

        Args:
            relationship: Relationship edge to add

        Returns:
            New WorldState with the relationship included.

        Example:
            new_state = state.add_relationship(exploitation_edge)
        """
        new_relationships = [*self.relationships, relationship]
        return self.model_copy(update={"relationships": new_relationships})

    def add_event(self, event: str) -> WorldState:
        """Return new state with event appended to log.

        Args:
            event: Event description string

        Returns:
            New WorldState with event in log.

        Example:
            new_state = state.add_event("Worker crossed poverty threshold")
        """
        new_log = [*self.event_log, event]
        return self.model_copy(update={"event_log": new_log})
```
