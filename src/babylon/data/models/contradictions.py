"""Contradiction system database models.

These models capture the dialectical contradictions that drive
systemic change in the Marxist framework. Contradictions are
the core engine of transformation in the game.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ContradictionType(PyEnum):
    """Types of contradictions in dialectical analysis."""
    
    ECONOMIC = "economic"
    POLITICAL = "political" 
    SOCIAL = "social"
    CULTURAL = "cultural"
    ENVIRONMENTAL = "environmental"
    CLASS = "class"


class ContradictionUniversality(PyEnum):
    """Universality level of contradictions."""
    
    UNIVERSAL = "universal"  # Present in all similar systems
    PARTICULAR = "particular"  # Specific to certain conditions
    SINGULAR = "singular"  # Unique to specific instance


class ContradictionAntagonism(PyEnum):
    """Antagonism level of contradictions."""
    
    ANTAGONISTIC = "antagonistic"  # Irreconcilable, requires systemic change
    NON_ANTAGONISTIC = "non_antagonistic"  # Can be resolved within system


class ContradictionIntensity(PyEnum):
    """Intensity levels of contradictions."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictionState(PyEnum):
    """Current state of contradictions."""
    
    LATENT = "latent"  # Present but not yet manifesting
    ACTIVE = "active"  # Currently manifesting effects
    ESCALATING = "escalating"  # Increasing in intensity
    RESOLVING = "resolving"  # In process of resolution
    RESOLVED = "resolved"  # Resolved (temporarily or permanently)
    TRANSFORMED = "transformed"  # Led to systemic transformation


class Contradiction(Base):
    """Represents a dialectical contradiction in the system.
    
    Contradictions are the driving force of change in dialectical
    materialist analysis. They exist between opposing forces or
    aspects within the same phenomenon.
    """
    
    __tablename__ = "contradictions"
    __table_args__ = (
        Index("idx_contradiction_game_type", "game_id", "contradiction_type"),
        Index("idx_contradiction_intensity_state", "intensity", "state"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False)
    
    # Contradiction identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contradiction_type: Mapped[ContradictionType] = mapped_column(
        Enum(ContradictionType), nullable=False
    )
    
    # Dialectical properties
    universality: Mapped[ContradictionUniversality] = mapped_column(
        Enum(ContradictionUniversality), default=ContradictionUniversality.PARTICULAR
    )
    antagonism: Mapped[ContradictionAntagonism] = mapped_column(
        Enum(ContradictionAntagonism), nullable=False
    )
    
    # Current state
    intensity: Mapped[ContradictionIntensity] = mapped_column(
        Enum(ContradictionIntensity), default=ContradictionIntensity.LOW
    )
    state: Mapped[ContradictionState] = mapped_column(
        Enum(ContradictionState), default=ContradictionState.LATENT
    )
    
    # Quantitative measures
    intensity_value: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    stability_impact: Mapped[float] = mapped_column(Float, default=0.0)  # Impact on system stability
    transformation_potential: Mapped[float] = mapped_column(Float, default=0.0)  # Potential for systemic change
    
    # Aspects of the contradiction
    principal_aspect: Mapped[Optional[str]] = mapped_column(String(200))
    secondary_aspect: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Related entities and systems
    affected_entities: Mapped[Optional[List[int]]] = mapped_column(JSON)  # Entity IDs
    related_systems: Mapped[Optional[List[str]]] = mapped_column(JSON)  # e.g., ["economic", "political"]
    
    # Resolution information
    resolution_methods: Mapped[Optional[dict]] = mapped_column(JSON)
    conditions_for_transformation: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Historical tracking
    first_observed_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    last_escalation_turn: Mapped[Optional[int]] = mapped_column(Integer)
    resolution_turn: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Relationships to other contradictions
    parent_contradiction_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("contradictions.id")
    )
    is_principal_contradiction: Mapped[bool] = mapped_column(default=False)
    
    # Additional data
    contradiction_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="contradictions")
    history: Mapped[List["ContradictionHistory"]] = relationship(
        "ContradictionHistory", back_populates="contradiction", cascade="all, delete-orphan"
    )
    child_contradictions: Mapped[List["Contradiction"]] = relationship(
        "Contradiction", remote_side=[id]
    )
    effects: Mapped[List["ContradictionEffect"]] = relationship(
        "ContradictionEffect", back_populates="contradiction", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of the contradiction."""
        return (
            f"<Contradiction(id={self.id}, name='{self.name}', "
            f"type={self.contradiction_type.value}, intensity={self.intensity.value}, "
            f"state={self.state.value})>"
        )

    def calculate_transformation_pressure(self) -> float:
        """Calculate the pressure for systemic transformation.
        
        Returns:
            float: Transformation pressure (0.0 to 1.0)
        """
        # Base pressure from intensity and antagonism
        base_pressure = self.intensity_value
        
        # Amplify for antagonistic contradictions
        if self.antagonism == ContradictionAntagonism.ANTAGONISTIC:
            base_pressure *= 1.5
        
        # Universal contradictions create more pressure
        if self.universality == ContradictionUniversality.UNIVERSAL:
            base_pressure *= 1.2
        
        # Escalating state increases pressure
        if self.state == ContradictionState.ESCALATING:
            base_pressure *= 1.3
        
        return min(base_pressure, 1.0)

    def is_ready_for_resolution(self) -> bool:
        """Check if contradiction is ready for resolution attempt.
        
        Returns:
            bool: True if conditions are met for resolution
        """
        # Must be active or escalating
        if self.state not in [ContradictionState.ACTIVE, ContradictionState.ESCALATING]:
            return False
        
        # Must have sufficient intensity
        if self.intensity in [ContradictionIntensity.LOW]:
            return False
        
        # Check if resolution methods are available
        if not self.resolution_methods:
            return False
        
        return True

    def evolve_contradiction(self, game_turn: int, external_factors: Optional[dict] = None) -> bool:
        """Evolve the contradiction based on game dynamics.
        
        Args:
            game_turn: Current game turn
            external_factors: Dict of external factors affecting evolution
            
        Returns:
            bool: True if contradiction changed state/intensity
        """
        external_factors = external_factors or {}
        changed = False
        
        # Store previous state for history
        prev_intensity = self.intensity
        prev_state = self.state
        
        # Calculate intensity change based on various factors
        intensity_delta = 0.0
        
        # Economic crisis amplifies contradictions
        if external_factors.get("economic_crisis", False):
            intensity_delta += 0.1
        
        # Political instability affects contradictions
        if external_factors.get("political_instability", 0.0) > 0.5:
            intensity_delta += 0.05
        
        # Natural evolution - some contradictions intensify over time
        if self.contradiction_type == ContradictionType.ECONOMIC:
            intensity_delta += 0.02  # Tendency of rate of profit to fall
        
        # Update intensity value
        self.intensity_value = min(max(self.intensity_value + intensity_delta, 0.0), 1.0)
        
        # Update categorical intensity
        new_intensity = self._calculate_intensity_category()
        if new_intensity != self.intensity:
            self.intensity = new_intensity
            changed = True
        
        # Update state based on intensity and conditions
        new_state = self._calculate_state_transition(external_factors)
        if new_state != self.state:
            self.state = new_state
            changed = True
        
        # Record history if changed
        if changed:
            self._record_evolution(game_turn, prev_intensity, prev_state, external_factors)
        
        return changed

    def _calculate_intensity_category(self) -> ContradictionIntensity:
        """Calculate categorical intensity from numeric value."""
        if self.intensity_value <= 0.25:
            return ContradictionIntensity.LOW
        elif self.intensity_value <= 0.5:
            return ContradictionIntensity.MEDIUM
        elif self.intensity_value <= 0.75:
            return ContradictionIntensity.HIGH
        else:
            return ContradictionIntensity.CRITICAL

    def _calculate_state_transition(self, external_factors: dict) -> ContradictionState:
        """Calculate state transition based on current conditions."""
        current_state = self.state
        
        if current_state == ContradictionState.LATENT:
            # Become active if intensity rises
            if self.intensity_value > 0.3:
                return ContradictionState.ACTIVE
        
        elif current_state == ContradictionState.ACTIVE:
            # Escalate if intensity continues rising
            if self.intensity_value > 0.6:
                return ContradictionState.ESCALATING
            # Begin resolving if resolution attempts are made
            elif external_factors.get("resolution_attempt", False):
                return ContradictionState.RESOLVING
        
        elif current_state == ContradictionState.ESCALATING:
            # Critical state leads to transformation pressure
            if self.intensity_value > 0.8:
                # Could trigger transformation or forced resolution
                if self.antagonism == ContradictionAntagonism.ANTAGONISTIC:
                    return ContradictionState.ESCALATING  # Remains escalating until transformed
                else:
                    return ContradictionState.RESOLVING
            elif external_factors.get("resolution_attempt", False):
                return ContradictionState.RESOLVING
        
        elif current_state == ContradictionState.RESOLVING:
            # Resolution success depends on approach and conditions
            if external_factors.get("resolution_success", False):
                if self.antagonism == ContradictionAntagonism.ANTAGONISTIC:
                    return ContradictionState.TRANSFORMED
                else:
                    return ContradictionState.RESOLVED
            # Failed resolution might escalate
            elif external_factors.get("resolution_failure", False):
                return ContradictionState.ESCALATING
        
        return current_state

    def _record_evolution(self, turn: int, prev_intensity: ContradictionIntensity, 
                         prev_state: ContradictionState, factors: dict) -> None:
        """Record contradiction evolution in history."""
        from .contradictions import ContradictionHistory  # Avoid circular import
        
        # This would be handled by the session in actual usage
        # For now, just update the tracking fields
        self.last_escalation_turn = turn
        self.updated_at = datetime.utcnow()

    def apply_effects(self, target_systems: Optional[List[str]] = None) -> List[dict]:
        """Apply contradiction effects to target systems.
        
        Args:
            target_systems: List of systems to affect (if None, affects all related)
            
        Returns:
            List[dict]: Effects applied with their parameters
        """
        target_systems = target_systems or self.related_systems or []
        applied_effects = []
        
        for system in target_systems:
            effect_magnitude = self.intensity_value * self.transformation_potential
            
            if system == "economic":
                # Economic effects
                effects = self._generate_economic_effects(effect_magnitude)
                applied_effects.extend(effects)
            
            elif system == "political":
                # Political effects
                effects = self._generate_political_effects(effect_magnitude)
                applied_effects.extend(effects)
            
            elif system == "social":
                # Social effects
                effects = self._generate_social_effects(effect_magnitude)
                applied_effects.extend(effects)
        
        return applied_effects

    def _generate_economic_effects(self, magnitude: float) -> List[dict]:
        """Generate economic system effects."""
        effects = []
        
        if self.contradiction_type == ContradictionType.ECONOMIC:
            if self.name.lower().find("profit") != -1:  # Rate of profit related
                effects.append({
                    "type": "rate_of_profit_pressure",
                    "magnitude": -magnitude,  # Negative pressure on profit rate
                    "description": "Tendency of rate of profit to fall manifesting"
                })
            
            if self.intensity == ContradictionIntensity.CRITICAL:
                effects.append({
                    "type": "economic_crisis_risk",
                    "magnitude": magnitude,
                    "description": "Economic contradiction creating crisis conditions"
                })
        
        return effects

    def _generate_political_effects(self, magnitude: float) -> List[dict]:
        """Generate political system effects."""
        effects = []
        
        if self.intensity in [ContradictionIntensity.HIGH, ContradictionIntensity.CRITICAL]:
            effects.append({
                "type": "political_instability",
                "magnitude": magnitude,
                "description": f"{self.name} creating political tensions"
            })
        
        if self.antagonism == ContradictionAntagonism.ANTAGONISTIC:
            effects.append({
                "type": "revolutionary_pressure",
                "magnitude": magnitude,
                "description": "Antagonistic contradiction building revolutionary potential"
            })
        
        return effects

    def _generate_social_effects(self, magnitude: float) -> List[dict]:
        """Generate social system effects."""
        effects = []
        
        if self.contradiction_type == ContradictionType.CLASS:
            effects.append({
                "type": "class_consciousness",
                "magnitude": magnitude,
                "description": "Class contradictions raising awareness"
            })
        
        if self.intensity == ContradictionIntensity.CRITICAL:
            effects.append({
                "type": "social_unrest",
                "magnitude": magnitude,
                "description": "Critical contradictions manifesting as social tension"
            })
        
        return effects

    def get_resolution_options(self) -> List[dict]:
        """Get available resolution options based on contradiction properties.
        
        Returns:
            List[dict]: Available resolution approaches with metadata
        """
        options = []
        
        if self.antagonism == ContradictionAntagonism.NON_ANTAGONISTIC:
            options.extend([
                {
                    "method": "reform",
                    "success_probability": 0.7,
                    "description": "Reform existing structures to reduce contradiction",
                    "requirements": ["political_will", "resources"]
                },
                {
                    "method": "compromise",
                    "success_probability": 0.6,
                    "description": "Negotiate compromise between opposing forces",
                    "requirements": ["dialogue", "mutual_interest"]
                }
            ])
        
        if self.antagonism == ContradictionAntagonism.ANTAGONISTIC:
            options.extend([
                {
                    "method": "revolutionary_transformation",
                    "success_probability": 0.4,
                    "description": "Transform the system fundamentally",
                    "requirements": ["mass_support", "organization", "critical_consciousness"]
                },
                {
                    "method": "suppression",
                    "success_probability": 0.3,
                    "description": "Forcibly suppress contradiction (temporary)",
                    "requirements": ["state_power", "coercive_capacity"],
                    "temporary": True
                }
            ])
        
        # Universal options
        options.append({
            "method": "ignore",
            "success_probability": 0.1,
            "description": "Attempt to ignore the contradiction",
            "requirements": [],
            "consequences": "Likely escalation"
        })
        
        return options

    @classmethod
    def create_economic_contradiction(cls, game_id: int, name: str, description: str,
                                    intensity: float = 0.3, turn: int = 1) -> "Contradiction":
        """Factory method for creating economic contradictions.
        
        Args:
            game_id: Game ID
            name: Contradiction name
            description: Description
            intensity: Initial intensity (0.0-1.0)
            turn: Turn when first observed
            
        Returns:
            Contradiction: New economic contradiction instance
        """
        return cls(
            game_id=game_id,
            name=name,
            description=description,
            contradiction_type=ContradictionType.ECONOMIC,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,  # Most economic contradictions are antagonistic
            intensity=cls._intensity_from_value(intensity),
            intensity_value=intensity,
            transformation_potential=min(intensity * 1.2, 1.0),
            first_observed_turn=turn,
            related_systems=["economic", "political"],
            conditions_for_transformation=["economic_crisis", "mass_consciousness", "organization"]
        )

    @classmethod
    def create_class_contradiction(cls, game_id: int, name: str, description: str,
                                 intensity: float = 0.4, turn: int = 1) -> "Contradiction":
        """Factory method for creating class contradictions.
        
        Args:
            game_id: Game ID
            name: Contradiction name  
            description: Description
            intensity: Initial intensity (0.0-1.0)
            turn: Turn when first observed
            
        Returns:
            Contradiction: New class contradiction instance
        """
        return cls(
            game_id=game_id,
            name=name,
            description=description,
            contradiction_type=ContradictionType.CLASS,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            universality=ContradictionUniversality.UNIVERSAL,  # Class struggle is universal
            intensity=cls._intensity_from_value(intensity),
            intensity_value=intensity,
            transformation_potential=min(intensity * 1.5, 1.0),  # High transformation potential
            first_observed_turn=turn,
            related_systems=["economic", "political", "social"],
            conditions_for_transformation=["class_consciousness", "organization", "revolutionary_situation"]
        )

    @staticmethod
    def _intensity_from_value(value: float) -> ContradictionIntensity:
        """Convert numeric intensity to categorical."""
        if value <= 0.25:
            return ContradictionIntensity.LOW
        elif value <= 0.5:
            return ContradictionIntensity.MEDIUM
        elif value <= 0.75:
            return ContradictionIntensity.HIGH
        else:
            return ContradictionIntensity.CRITICAL


class ContradictionHistory(Base):
    """Tracks the historical evolution of contradictions.
    
    This captures how contradictions develop, intensify, and resolve
    over time, providing insight into dialectical processes.
    """
    
    __tablename__ = "contradiction_history"
    __table_args__ = (
        Index("idx_contradiction_hist_turn", "contradiction_id", "turn_number"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    
    # Historical state
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_intensity: Mapped[Optional[ContradictionIntensity]] = mapped_column(
        Enum(ContradictionIntensity)
    )
    new_intensity: Mapped[ContradictionIntensity] = mapped_column(
        Enum(ContradictionIntensity), nullable=False
    )
    previous_state: Mapped[Optional[ContradictionState]] = mapped_column(
        Enum(ContradictionState)
    )
    new_state: Mapped[ContradictionState] = mapped_column(
        Enum(ContradictionState), nullable=False
    )
    
    # Quantitative changes
    intensity_change: Mapped[float] = mapped_column(Float, default=0.0)
    stability_impact_change: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Change triggers
    triggering_event_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("events.id")
    )
    change_factors: Mapped[Optional[dict]] = mapped_column(JSON)
    change_description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    contradiction: Mapped["Contradiction"] = relationship("Contradiction", back_populates="history")

    def __repr__(self) -> str:
        """String representation of contradiction history entry."""
        return (
            f"<ContradictionHistory(id={self.id}, contradiction_id={self.contradiction_id}, "
            f"turn={self.turn_number}, {self.previous_intensity} -> {self.new_intensity})>"
        )

    def calculate_intensity_trend(self) -> str:
        """Calculate the trend direction of intensity change.
        
        Returns:
            str: 'increasing', 'decreasing', or 'stable'
        """
        if self.intensity_change > 0.01:
            return "increasing"
        elif self.intensity_change < -0.01:
            return "decreasing"
        else:
            return "stable"

    def is_significant_change(self) -> bool:
        """Check if this represents a significant change in contradiction.
        
        Returns:
            bool: True if the change is significant
        """
        # State changes are always significant
        if self.previous_state != self.new_state:
            return True
        
        # Large intensity changes are significant
        if abs(self.intensity_change) > 0.1:
            return True
        
        # Intensity category changes are significant
        if self.previous_intensity != self.new_intensity:
            return True
        
        return False

    def get_change_summary(self) -> str:
        """Get a human-readable summary of the change.
        
        Returns:
            str: Summary of what changed
        """
        changes = []
        
        if self.previous_state != self.new_state:
            changes.append(f"state: {self.previous_state.value} → {self.new_state.value}")
        
        if self.previous_intensity != self.new_intensity:
            changes.append(f"intensity: {self.previous_intensity.value} → {self.new_intensity.value}")
        
        if abs(self.intensity_change) > 0.01:
            direction = "increased" if self.intensity_change > 0 else "decreased"
            changes.append(f"intensity {direction} by {abs(self.intensity_change):.2f}")
        
        return "; ".join(changes) if changes else "no significant change"


class ContradictionEffect(Base):
    """Represents the effects that contradictions have on the system.
    
    This models how contradictions manifest their influence on
    various aspects of the game world.
    """
    
    __tablename__ = "contradiction_effects"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    
    # Effect identification
    effect_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "economic", "political"
    effect_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Effect parameters
    target_system: Mapped[Optional[str]] = mapped_column(String(100))  # System affected
    target_entity_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("entities.id")
    )
    
    # Effect magnitude and direction
    effect_magnitude: Mapped[float] = mapped_column(Float, default=0.0)
    effect_direction: Mapped[str] = mapped_column(String(20))  # "positive", "negative", "neutral"
    
    # Conditions and triggers
    trigger_conditions: Mapped[Optional[dict]] = mapped_column(JSON)
    effect_duration: Mapped[Optional[int]] = mapped_column(Integer)  # In turns, if limited
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    activation_turn: Mapped[Optional[int]] = mapped_column(Integer)
    deactivation_turn: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Additional effect data
    effect_parameters: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    contradiction: Mapped["Contradiction"] = relationship("Contradiction", back_populates="effects")

    def __repr__(self) -> str:
        """String representation of contradiction effect."""
        return (
            f"<ContradictionEffect(id={self.id}, contradiction_id={self.contradiction_id}, "
            f"type='{self.effect_type}', magnitude={self.effect_magnitude})>"
        )

    def is_currently_active(self, current_turn: int) -> bool:
        """Check if effect is currently active.
        
        Args:
            current_turn: Current game turn
            
        Returns:
            bool: True if effect is active
        """
        if not self.is_active:
            return False
        
        # Check if effect has started
        if self.activation_turn and current_turn < self.activation_turn:
            return False
        
        # Check if effect has ended
        if self.deactivation_turn and current_turn > self.deactivation_turn:
            return False
        
        # Check duration limit
        if (self.effect_duration and self.activation_turn and 
            current_turn > self.activation_turn + self.effect_duration):
            return False
        
        return True

    def calculate_current_magnitude(self, current_turn: int) -> float:
        """Calculate current effect magnitude, potentially modified by time.
        
        Args:
            current_turn: Current game turn
            
        Returns:
            float: Current effective magnitude
        """
        if not self.is_currently_active(current_turn):
            return 0.0
        
        base_magnitude = self.effect_magnitude
        
        # Apply time-based modifications if configured
        if self.effect_parameters:
            decay_rate = self.effect_parameters.get("decay_rate", 0.0)
            if decay_rate > 0 and self.activation_turn:
                turns_active = current_turn - self.activation_turn
                decay_factor = max(0.0, 1.0 - (decay_rate * turns_active))
                base_magnitude *= decay_factor
        
        return base_magnitude

    def activate(self, turn: int) -> None:
        """Activate the effect at a specific turn.
        
        Args:
            turn: Turn when effect activates
        """
        self.is_active = True
        self.activation_turn = turn

    def deactivate(self, turn: int) -> None:
        """Deactivate the effect at a specific turn.
        
        Args:
            turn: Turn when effect deactivates
        """
        self.is_active = False
        self.deactivation_turn = turn

    def get_effect_description(self) -> str:
        """Get a detailed description of the effect.
        
        Returns:
            str: Detailed effect description
        """
        direction_text = {
            "positive": "beneficial",
            "negative": "detrimental", 
            "neutral": "neutral"
        }.get(self.effect_direction, self.effect_direction)
        
        magnitude_text = "minor"
        if self.effect_magnitude > 0.7:
            magnitude_text = "major"
        elif self.effect_magnitude > 0.4:
            magnitude_text = "moderate"
        
        return (f"{magnitude_text.capitalize()} {direction_text} effect on "
                f"{self.target_system or 'system'}: {self.description}")


class ContradictionNetwork(Base):
    """Represents relationships between contradictions.
    
    Models how contradictions interact with and influence each other,
    creating complex networks of dialectical relationships.
    """
    
    __tablename__ = "contradiction_networks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    target_contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    
    # Relationship details
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "amplifies", "suppresses", "generates"
    relationship_strength: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Description and context
    description: Mapped[Optional[str]] = mapped_column(Text)
    conditions: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    discovered_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Additional relationship data
    network_data: Mapped[Optional[dict]] = mapped_column(JSON)

    def __repr__(self) -> str:
        """String representation of contradiction network relationship."""
        return (
            f"<ContradictionNetwork(id={self.id}, "
            f"{self.source_contradiction_id} --{self.relationship_type}--> "
            f"{self.target_contradiction_id}, strength={self.relationship_strength})>"
        )

    def calculate_influence_strength(self, source_intensity: float) -> float:
        """Calculate how much influence this relationship transmits.
        
        Args:
            source_intensity: Current intensity of source contradiction
            
        Returns:
            float: Influence strength to apply to target
        """
        if not self.is_active:
            return 0.0
        
        base_influence = source_intensity * self.relationship_strength
        
        # Apply relationship type modifiers
        if self.relationship_type == "amplifies":
            return base_influence * 1.2
        elif self.relationship_type == "suppresses":
            return -base_influence * 0.8
        elif self.relationship_type == "generates":
            return base_influence * 1.5
        elif self.relationship_type == "transforms":
            return base_influence * 2.0
        else:
            return base_influence

    def is_relationship_active(self, current_conditions: dict) -> bool:
        """Check if relationship is currently active based on conditions.
        
        Args:
            current_conditions: Dictionary of current game conditions
            
        Returns:
            bool: True if relationship should be active
        """
        if not self.is_active:
            return False
        
        # Check conditions if they exist
        if self.conditions:
            for condition, required_value in self.conditions.items():
                if current_conditions.get(condition) != required_value:
                    return False
        
        return True

    def get_relationship_description(self) -> str:
        """Get human-readable description of the relationship.
        
        Returns:
            str: Description of how source affects target
        """
        strength_desc = "weakly"
        if self.relationship_strength > 0.7:
            strength_desc = "strongly"
        elif self.relationship_strength > 0.4:
            strength_desc = "moderately"
        
        return f"Source contradiction {strength_desc} {self.relationship_type} target contradiction"


class ContradictionResolution(Base):
    """Records attempts to resolve contradictions and their outcomes.
    
    This tracks both successful and failed attempts to resolve
    contradictions, providing insight into what works and what doesn't.
    """
    
    __tablename__ = "contradiction_resolutions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contradiction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contradictions.id"), nullable=False
    )
    
    # Resolution attempt details
    resolution_method: Mapped[str] = mapped_column(String(200), nullable=False)
    attempted_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted_by: Mapped[Optional[str]] = mapped_column(String(100))  # Player, system, event
    
    # Resolution approach
    approach_description: Mapped[str] = mapped_column(Text, nullable=False)
    resources_invested: Mapped[Optional[dict]] = mapped_column(JSON)
    policies_implemented: Mapped[Optional[List[int]]] = mapped_column(JSON)  # Policy IDs
    
    # Outcome
    success_level: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    actual_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    unintended_consequences: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Impact assessment
    intensity_reduction: Mapped[float] = mapped_column(Float, default=0.0)
    new_contradictions_created: Mapped[Optional[List[int]]] = mapped_column(JSON)  # IDs of new contradictions
    systemic_changes: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        """String representation of contradiction resolution attempt."""
        return (
            f"<ContradictionResolution(id={self.id}, contradiction_id={self.contradiction_id}, "
            f"method='{self.resolution_method}', success={self.success_level:.2f})>"
        )

    def was_successful(self, threshold: float = 0.5) -> bool:
        """Check if resolution attempt was successful.
        
        Args:
            threshold: Success threshold (0.0 to 1.0)
            
        Returns:
            bool: True if success level meets threshold
        """
        return self.success_level >= threshold

    def had_unintended_consequences(self) -> bool:
        """Check if resolution had significant unintended consequences.
        
        Returns:
            bool: True if there were notable unintended consequences
        """
        if not self.unintended_consequences:
            return False
        
        # Check for severity markers in consequences
        consequences_str = str(self.unintended_consequences).lower()
        severity_markers = ["severe", "major", "significant", "crisis", "escalation"]
        
        return any(marker in consequences_str for marker in severity_markers)

    def created_new_contradictions(self) -> bool:
        """Check if resolution created new contradictions.
        
        Returns:
            bool: True if new contradictions were generated
        """
        return bool(self.new_contradictions_created)

    def get_effectiveness_rating(self) -> str:
        """Get a qualitative rating of resolution effectiveness.
        
        Returns:
            str: Rating from 'failed' to 'excellent'
        """
        if self.success_level < 0.2:
            return "failed"
        elif self.success_level < 0.4:
            return "poor"
        elif self.success_level < 0.6:
            return "fair"
        elif self.success_level < 0.8:
            return "good"
        else:
            return "excellent"

    def calculate_net_benefit(self) -> float:
        """Calculate net benefit considering success and consequences.
        
        Returns:
            float: Net benefit score (-1.0 to 1.0)
        """
        base_benefit = self.success_level
        
        # Subtract for unintended consequences
        if self.had_unintended_consequences():
            base_benefit -= 0.3
        
        # Subtract for creating new contradictions
        if self.created_new_contradictions():
            num_new = len(self.new_contradictions_created or [])
            base_benefit -= (num_new * 0.1)
        
        # Add for positive systemic changes
        if self.systemic_changes:
            positive_changes = sum(1 for change in self.systemic_changes.values() 
                                 if isinstance(change, (int, float)) and change > 0)
            base_benefit += (positive_changes * 0.05)
        
        return max(-1.0, min(1.0, base_benefit))

    def get_resolution_summary(self) -> dict:
        """Get comprehensive summary of resolution attempt.
        
        Returns:
            dict: Summary with key metrics and outcomes
        """
        return {
            "method": self.resolution_method,
            "success_level": self.success_level,
            "effectiveness": self.get_effectiveness_rating(),
            "net_benefit": self.calculate_net_benefit(),
            "intensity_reduction": self.intensity_reduction,
            "had_consequences": self.had_unintended_consequences(),
            "created_contradictions": self.created_new_contradictions(),
            "attempted_by": self.attempted_by,
            "turn": self.attempted_turn
        }