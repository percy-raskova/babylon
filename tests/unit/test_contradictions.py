"""Unit tests for contradiction models and engine."""

import pytest
from datetime import datetime

from babylon.data.models.contradictions import (
    Contradiction, ContradictionHistory, ContradictionEffect, 
    ContradictionNetwork, ContradictionResolution,
    ContradictionType, ContradictionIntensity, ContradictionState, 
    ContradictionAntagonism, ContradictionUniversality
)
from babylon.data.models.contradiction_engine import ContradictionEngine


class TestContradiction:
    """Test cases for the Contradiction model."""
    
    def test_create_contradiction(self):
        """Test creating a contradiction instance."""
        contradiction = Contradiction(
            game_id=1,
            name="Test Contradiction",
            description="A test contradiction",
            contradiction_type=ContradictionType.ECONOMIC,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            intensity=ContradictionIntensity.MEDIUM,
            first_observed_turn=1
        )
        
        assert contradiction.name == "Test Contradiction"
        assert contradiction.contradiction_type == ContradictionType.ECONOMIC
        assert contradiction.antagonism == ContradictionAntagonism.ANTAGONISTIC
        assert contradiction.intensity == ContradictionIntensity.MEDIUM
        
    def test_calculate_transformation_pressure(self):
        """Test transformation pressure calculation."""
        contradiction = Contradiction(
            game_id=1,
            name="High Pressure Contradiction",
            description="Test",
            contradiction_type=ContradictionType.CLASS,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            universality=ContradictionUniversality.UNIVERSAL,
            state=ContradictionState.ESCALATING,
            intensity_value=0.8,
            first_observed_turn=1
        )
        
        pressure = contradiction.calculate_transformation_pressure()
        
        # Should be amplified by antagonistic + universal + escalating
        # 0.8 * 1.5 * 1.2 * 1.3 = 1.872, capped at 1.0
        assert pressure == 1.0
        
    def test_is_ready_for_resolution(self):
        """Test resolution readiness check."""
        # Not ready - latent state
        contradiction = Contradiction(
            game_id=1,
            name="Test",
            description="Test",
            contradiction_type=ContradictionType.ECONOMIC,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            state=ContradictionState.LATENT,
            intensity=ContradictionIntensity.HIGH,
            first_observed_turn=1,
            resolution_methods={"reform": "possible"}
        )
        
        assert not contradiction.is_ready_for_resolution()
        
        # Ready - active state, high intensity, has resolution methods
        contradiction.state = ContradictionState.ACTIVE
        assert contradiction.is_ready_for_resolution()
        
    def test_factory_methods(self):
        """Test factory methods for creating specific contradiction types."""
        # Economic contradiction
        economic = Contradiction.create_economic_contradiction(
            game_id=1,
            name="Rate of Profit Fall",
            description="Tendency of rate of profit to fall",
            intensity=0.6,
            turn=5
        )
        
        assert economic.contradiction_type == ContradictionType.ECONOMIC
        assert economic.antagonism == ContradictionAntagonism.ANTAGONISTIC
        assert economic.intensity_value == 0.6
        assert economic.first_observed_turn == 5
        assert "economic" in economic.related_systems
        
        # Class contradiction
        class_contradiction = Contradiction.create_class_contradiction(
            game_id=1,
            name="Worker vs Capitalist",
            description="Class struggle",
            intensity=0.7,
            turn=3
        )
        
        assert class_contradiction.contradiction_type == ContradictionType.CLASS
        assert class_contradiction.universality == ContradictionUniversality.UNIVERSAL
        assert class_contradiction.antagonism == ContradictionAntagonism.ANTAGONISTIC
        
    def test_get_resolution_options(self):
        """Test getting resolution options."""
        # Antagonistic contradiction
        antagonistic = Contradiction(
            game_id=1,
            name="Test",
            description="Test",
            contradiction_type=ContradictionType.CLASS,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            first_observed_turn=1
        )
        
        options = antagonistic.get_resolution_options()
        
        # Should include revolutionary transformation for antagonistic
        option_methods = [opt["method"] for opt in options]
        assert "revolutionary_transformation" in option_methods
        assert "suppression" in option_methods
        assert "ignore" in option_methods
        
        # Non-antagonistic contradiction
        non_antagonistic = Contradiction(
            game_id=1,
            name="Test",
            description="Test",
            contradiction_type=ContradictionType.POLITICAL,
            antagonism=ContradictionAntagonism.NON_ANTAGONISTIC,
            first_observed_turn=1
        )
        
        options = non_antagonistic.get_resolution_options()
        option_methods = [opt["method"] for opt in options]
        assert "reform" in option_methods
        assert "compromise" in option_methods
        
    def test_evolve_contradiction(self):
        """Test contradiction evolution."""
        contradiction = Contradiction(
            game_id=1,
            name="Test Contradiction",
            description="Test",
            contradiction_type=ContradictionType.ECONOMIC,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            intensity=ContradictionIntensity.LOW,
            intensity_value=0.2,
            state=ContradictionState.LATENT,
            first_observed_turn=1
        )
        
        # Evolve with economic crisis
        external_factors = {
            "economic_crisis": True,
            "political_instability": 0.6
        }
        
        changed = contradiction.evolve_contradiction(5, external_factors)
        
        # Should have intensified
        assert changed
        assert contradiction.intensity_value > 0.2
        assert contradiction.updated_at is not None


class TestContradictionHistory:
    """Test cases for ContradictionHistory model."""
    
    def test_create_history_entry(self):
        """Test creating a history entry."""
        history = ContradictionHistory(
            contradiction_id=1,
            turn_number=5,
            previous_intensity=ContradictionIntensity.LOW,
            new_intensity=ContradictionIntensity.MEDIUM,
            previous_state=ContradictionState.LATENT,
            new_state=ContradictionState.ACTIVE,
            intensity_change=0.15
        )
        
        assert history.turn_number == 5
        assert history.intensity_change == 0.15
        
    def test_calculate_intensity_trend(self):
        """Test intensity trend calculation."""
        history = ContradictionHistory(
            contradiction_id=1,
            turn_number=1,
            new_intensity=ContradictionIntensity.MEDIUM,
            new_state=ContradictionState.ACTIVE,
            intensity_change=0.15
        )
        
        assert history.calculate_intensity_trend() == "increasing"
        
        history.intensity_change = -0.1
        assert history.calculate_intensity_trend() == "decreasing"
        
        history.intensity_change = 0.005
        assert history.calculate_intensity_trend() == "stable"
        
    def test_is_significant_change(self):
        """Test significant change detection."""
        # State change is significant
        history = ContradictionHistory(
            contradiction_id=1,
            turn_number=1,
            previous_state=ContradictionState.LATENT,
            new_state=ContradictionState.ACTIVE,
            new_intensity=ContradictionIntensity.MEDIUM,
            intensity_change=0.05
        )
        
        assert history.is_significant_change()
        
        # Large intensity change is significant
        history.previous_state = ContradictionState.ACTIVE
        history.new_state = ContradictionState.ACTIVE
        history.intensity_change = 0.15
        
        assert history.is_significant_change()
        
        # Small change is not significant
        history.intensity_change = 0.02
        history.previous_intensity = ContradictionIntensity.MEDIUM
        history.new_intensity = ContradictionIntensity.MEDIUM
        
        assert not history.is_significant_change()


class TestContradictionEffect:
    """Test cases for ContradictionEffect model."""
    
    def test_create_effect(self):
        """Test creating an effect."""
        effect = ContradictionEffect(
            contradiction_id=1,
            effect_type="economic",
            effect_name="Rate of Profit Pressure",
            description="Pressure on profit rates",
            effect_magnitude=0.8,
            effect_direction="negative",
            is_active=True
        )
        
        assert effect.effect_type == "economic"
        assert effect.effect_magnitude == 0.8
        assert effect.effect_direction == "negative"
        
    def test_is_currently_active(self):
        """Test current activity check."""
        effect = ContradictionEffect(
            contradiction_id=1,
            effect_type="test",
            effect_name="Test Effect",
            description="Test",
            is_active=True,
            activation_turn=5,
            effect_duration=3
        )
        
        # Active within duration
        assert effect.is_currently_active(7)
        
        # Inactive after duration
        assert not effect.is_currently_active(10)
        
        # Inactive before activation
        assert not effect.is_currently_active(3)
        
    def test_calculate_current_magnitude(self):
        """Test magnitude calculation with decay."""
        effect = ContradictionEffect(
            contradiction_id=1,
            effect_type="test",
            effect_name="Test Effect",
            description="Test",
            effect_magnitude=1.0,
            is_active=True,
            activation_turn=5,
            effect_parameters={"decay_rate": 0.1}
        )
        
        # No decay at activation
        assert effect.calculate_current_magnitude(5) == 1.0
        
        # Decay after 2 turns
        magnitude = effect.calculate_current_magnitude(7)
        assert magnitude == 0.8  # 1.0 * (1.0 - 0.1 * 2)


class TestContradictionEngine:
    """Test cases for ContradictionEngine."""
    
    def test_create_engine(self):
        """Test creating a contradiction engine."""
        engine = ContradictionEngine(game_id=1)
        
        assert engine.game_id == 1
        assert len(engine.contradictions) == 0
        assert engine.current_turn == 1
        
    def test_add_contradiction(self):
        """Test adding contradictions to engine."""
        engine = ContradictionEngine(game_id=1)
        
        contradiction = Contradiction(
            id=1,
            game_id=1,
            name="Test",
            description="Test",
            contradiction_type=ContradictionType.ECONOMIC,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            first_observed_turn=1
        )
        
        engine.add_contradiction(contradiction)
        
        assert len(engine.contradictions) == 1
        assert engine.contradictions[1] == contradiction
        
    def test_identify_principal_contradiction(self):
        """Test principal contradiction identification."""
        engine = ContradictionEngine(game_id=1)
        
        # Add multiple contradictions
        low_contradiction = Contradiction(
            id=1,
            game_id=1,
            name="Low Impact",
            description="Test",
            contradiction_type=ContradictionType.POLITICAL,
            antagonism=ContradictionAntagonism.NON_ANTAGONISTIC,
            state=ContradictionState.ACTIVE,
            intensity_value=0.3,
            first_observed_turn=1
        )
        
        high_contradiction = Contradiction(
            id=2,
            game_id=1,
            name="High Impact",
            description="Test",
            contradiction_type=ContradictionType.CLASS,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            universality=ContradictionUniversality.UNIVERSAL,
            state=ContradictionState.ESCALATING,
            intensity_value=0.8,
            first_observed_turn=1
        )
        
        engine.add_contradiction(low_contradiction)
        engine.add_contradiction(high_contradiction)
        
        principal = engine.identify_principal_contradiction()
        
        assert principal == high_contradiction
        assert high_contradiction.is_principal_contradiction
        
    def test_get_system_stability_assessment(self):
        """Test system stability assessment."""
        engine = ContradictionEngine(game_id=1)
        
        # Empty system is stable
        assessment = engine.get_system_stability_assessment()
        assert assessment["stability"] == 1.0
        assert assessment["status"] == "stable"
        
        # Add critical contradiction
        critical_contradiction = Contradiction(
            id=1,
            game_id=1,
            name="Critical Issue",
            description="Test",
            contradiction_type=ContradictionType.ECONOMIC,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            state=ContradictionState.ESCALATING,
            intensity=ContradictionIntensity.CRITICAL,
            intensity_value=0.9,
            first_observed_turn=1
        )
        
        engine.add_contradiction(critical_contradiction)
        
        assessment = engine.get_system_stability_assessment()
        
        assert assessment["stability"] < 0.5
        assert assessment["status"] in ["unstable", "highly_unstable", "crisis"]
        assert "critical contradiction" in str(assessment["warnings"]).lower()