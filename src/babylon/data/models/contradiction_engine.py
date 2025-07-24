"""Contradiction engine for managing dialectical contradictions in the game.

This engine is responsible for:
- Evolving contradictions over time
- Managing contradiction networks and relationships
- Triggering events based on contradiction states
- Calculating systemic effects of contradictions
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .contradictions import (
    Contradiction, ContradictionHistory, ContradictionEffect, 
    ContradictionNetwork, ContradictionResolution,
    ContradictionType, ContradictionIntensity, ContradictionState, ContradictionAntagonism
)


class ContradictionEngine:
    """Engine for managing the evolution and effects of contradictions."""
    
    def __init__(self, game_id: int):
        """Initialize the contradiction engine for a specific game.
        
        Args:
            game_id: ID of the game this engine manages
        """
        self.game_id = game_id
        self.contradictions: Dict[int, Contradiction] = {}
        self.networks: List[ContradictionNetwork] = []
        self.current_turn = 1
        
    def add_contradiction(self, contradiction: Contradiction) -> None:
        """Add a contradiction to the engine.
        
        Args:
            contradiction: Contradiction to add
        """
        self.contradictions[contradiction.id] = contradiction
        
    def evolve_all_contradictions(self, turn: int, game_state: dict) -> Dict[int, bool]:
        """Evolve all contradictions for the current turn.
        
        Args:
            turn: Current game turn
            game_state: Current state of the game (economic, political, etc.)
            
        Returns:
            Dict[int, bool]: Map of contradiction IDs to whether they changed
        """
        self.current_turn = turn
        evolution_results = {}
        
        # Extract external factors from game state
        external_factors = self._extract_external_factors(game_state)
        
        # Evolve each contradiction
        for contradiction_id, contradiction in self.contradictions.items():
            # Apply network effects before evolution
            network_effects = self._calculate_network_effects(contradiction_id, external_factors)
            external_factors.update(network_effects)
            
            # Evolve the contradiction
            changed = contradiction.evolve_contradiction(turn, external_factors)
            evolution_results[contradiction_id] = changed
            
            # Generate new effects if contradiction changed significantly
            if changed and contradiction.intensity == ContradictionIntensity.CRITICAL:
                self._generate_crisis_effects(contradiction)
        
        return evolution_results
        
    def _extract_external_factors(self, game_state: dict) -> dict:
        """Extract external factors affecting contradictions from game state.
        
        Args:
            game_state: Current game state
            
        Returns:
            dict: External factors for contradiction evolution
        """
        factors = {}
        
        # Economic factors
        economy = game_state.get("economy", {})
        if economy:
            # Economic crisis conditions
            gdp_growth = economy.get("gdp_growth", 0.0)
            unemployment = economy.get("unemployment_rate", 0.0)
            inflation = economy.get("inflation_rate", 0.0)
            
            factors["economic_crisis"] = (gdp_growth < -0.02 or unemployment > 0.08 or inflation > 0.05)
            factors["economic_instability"] = abs(gdp_growth) > 0.03 or unemployment > 0.06
            
            # Rate of profit factors
            rate_of_profit = economy.get("rate_of_profit", 0.2)
            factors["profit_pressure"] = rate_of_profit < 0.1
            
        # Political factors
        politics = game_state.get("politics", {})
        if politics:
            stability = politics.get("stability", 0.5)
            factors["political_instability"] = stability
            factors["revolutionary_situation"] = stability < 0.3
            
        # Social factors
        social = game_state.get("social", {})
        if social:
            class_consciousness = social.get("class_consciousness", 0.3)
            factors["class_consciousness"] = class_consciousness
            factors["mass_mobilization"] = class_consciousness > 0.7
            
        return factors
        
    def _calculate_network_effects(self, contradiction_id: int, conditions: dict) -> dict:
        """Calculate effects from contradiction networks.
        
        Args:
            contradiction_id: ID of contradiction being affected
            conditions: Current game conditions
            
        Returns:
            dict: Network effects to apply
        """
        effects = {}
        
        # Find networks where this contradiction is the target
        for network in self.networks:
            if (network.target_contradiction_id == contradiction_id and 
                network.is_relationship_active(conditions)):
                
                source_contradiction = self.contradictions.get(network.source_contradiction_id)
                if source_contradiction:
                    influence = network.calculate_influence_strength(source_contradiction.intensity_value)
                    
                    # Apply influence based on relationship type
                    if network.relationship_type == "amplifies":
                        effects["network_amplification"] = effects.get("network_amplification", 0.0) + influence
                    elif network.relationship_type == "suppresses":
                        effects["network_suppression"] = effects.get("network_suppression", 0.0) + abs(influence)
                    elif network.relationship_type == "generates":
                        effects["network_generation"] = effects.get("network_generation", 0.0) + influence
                        
        return effects
        
    def _generate_crisis_effects(self, contradiction: Contradiction) -> List[ContradictionEffect]:
        """Generate crisis effects when contradiction reaches critical state.
        
        Args:
            contradiction: Contradiction in critical state
            
        Returns:
            List[ContradictionEffect]: Generated effects
        """
        effects = []
        
        if contradiction.contradiction_type == ContradictionType.ECONOMIC:
            # Economic crisis effects
            effect = ContradictionEffect(
                contradiction_id=contradiction.id,
                effect_type="economic_crisis",
                effect_name="Economic Crisis Manifestation",
                description="Critical economic contradiction triggering crisis conditions",
                target_system="economic",
                effect_magnitude=0.8,
                effect_direction="negative",
                activation_turn=self.current_turn,
                is_active=True
            )
            effects.append(effect)
            
        elif contradiction.contradiction_type == ContradictionType.CLASS:
            # Class struggle intensification
            effect = ContradictionEffect(
                contradiction_id=contradiction.id,
                effect_type="class_struggle",
                effect_name="Class Struggle Intensification",
                description="Critical class contradiction heightening social tensions",
                target_system="social",
                effect_magnitude=0.9,
                effect_direction="negative",
                activation_turn=self.current_turn,
                is_active=True,
                effect_parameters={"consciousness_boost": 0.2}
            )
            effects.append(effect)
            
        return effects
        
    def identify_principal_contradiction(self) -> Optional[Contradiction]:
        """Identify the principal contradiction in the current system.
        
        Returns:
            Optional[Contradiction]: The principal contradiction, if any
        """
        if not self.contradictions:
            return None
            
        # Calculate transformation pressure for each contradiction
        candidates = []
        for contradiction in self.contradictions.values():
            if contradiction.state in [ContradictionState.ACTIVE, ContradictionState.ESCALATING]:
                pressure = contradiction.calculate_transformation_pressure()
                candidates.append((pressure, contradiction))
                
        if not candidates:
            return None
            
        # Sort by transformation pressure and return highest
        candidates.sort(key=lambda x: x[0], reverse=True)
        principal = candidates[0][1]
        
        # Mark as principal if not already
        if not principal.is_principal_contradiction:
            principal.is_principal_contradiction = True
            
        return principal
        
    def suggest_resolution_strategies(self, contradiction_id: int) -> List[dict]:
        """Suggest resolution strategies for a specific contradiction.
        
        Args:
            contradiction_id: ID of contradiction to resolve
            
        Returns:
            List[dict]: Suggested resolution strategies with analysis
        """
        contradiction = self.contradictions.get(contradiction_id)
        if not contradiction:
            return []
            
        base_options = contradiction.get_resolution_options()
        
        # Enhance options with current context
        enhanced_options = []
        for option in base_options:
            enhanced = option.copy()
            
            # Adjust success probability based on current conditions
            enhanced["current_success_probability"] = self._calculate_contextual_success_probability(
                contradiction, option
            )
            
            # Add resource requirements
            enhanced["estimated_cost"] = self._estimate_resolution_cost(contradiction, option)
            
            # Add risk assessment
            enhanced["risks"] = self._assess_resolution_risks(contradiction, option)
            
            enhanced_options.append(enhanced)
            
        return sorted(enhanced_options, key=lambda x: x["current_success_probability"], reverse=True)
        
    def _calculate_contextual_success_probability(self, contradiction: Contradiction, option: dict) -> float:
        """Calculate success probability adjusted for current context.
        
        Args:
            contradiction: Contradiction being resolved
            option: Resolution option
            
        Returns:
            float: Adjusted success probability
        """
        base_probability = option["success_probability"]
        
        # Adjust based on contradiction intensity
        if contradiction.intensity == ContradictionIntensity.CRITICAL:
            base_probability *= 0.7  # Harder to resolve critical contradictions
        elif contradiction.intensity == ContradictionIntensity.LOW:
            base_probability *= 1.2  # Easier to resolve low-intensity contradictions
            
        # Adjust based on method and contradiction type
        if (option["method"] == "revolutionary_transformation" and 
            contradiction.antagonism == ContradictionAntagonism.ANTAGONISTIC):
            base_probability *= 1.3  # Revolutionary methods work better for antagonistic contradictions
            
        return min(base_probability, 1.0)
        
    def _estimate_resolution_cost(self, contradiction: Contradiction, option: dict) -> dict:
        """Estimate the cost of a resolution attempt.
        
        Args:
            contradiction: Contradiction being resolved
            option: Resolution option
            
        Returns:
            dict: Estimated costs by resource type
        """
        base_cost = contradiction.intensity_value * 100
        
        costs = {
            "political_capital": base_cost,
            "economic_resources": base_cost * 0.8,
            "time_turns": int(base_cost / 20),
            "social_disruption": base_cost * 0.6
        }
        
        # Adjust based on method
        if option["method"] == "revolutionary_transformation":
            costs["social_disruption"] *= 2.0
            costs["time_turns"] *= 1.5
        elif option["method"] == "reform":
            costs["political_capital"] *= 1.5
            costs["time_turns"] *= 0.8
            
        return costs
        
    def _assess_resolution_risks(self, contradiction: Contradiction, option: dict) -> List[str]:
        """Assess risks of a resolution attempt.
        
        Args:
            contradiction: Contradiction being resolved
            option: Resolution option
            
        Returns:
            List[str]: List of potential risks
        """
        risks = []
        
        if option["method"] == "revolutionary_transformation":
            risks.extend([
                "Potential counter-revolution",
                "Social instability during transition",
                "Economic disruption",
                "International intervention"
            ])
        elif option["method"] == "reform":
            risks.extend([
                "Inadequate change leading to escalation",
                "Elite resistance",
                "Partial implementation"
            ])
        elif option["method"] == "suppression":
            risks.extend([
                "Temporary solution only",
                "Underground resistance",
                "Legitimacy crisis",
                "Future explosive manifestation"
            ])
            
        # Add intensity-specific risks
        if contradiction.intensity == ContradictionIntensity.CRITICAL:
            risks.append("Resolution failure could trigger systemic crisis")
            
        return risks
        
    def get_system_stability_assessment(self) -> dict:
        """Assess overall system stability based on current contradictions.
        
        Returns:
            dict: Stability assessment with metrics and warnings
        """
        if not self.contradictions:
            return {"stability": 1.0, "status": "stable", "warnings": []}
            
        # Calculate overall instability
        total_pressure = 0.0
        critical_count = 0
        antagonistic_count = 0
        
        for contradiction in self.contradictions.values():
            if contradiction.state in [ContradictionState.ACTIVE, ContradictionState.ESCALATING]:
                pressure = contradiction.calculate_transformation_pressure()
                total_pressure += pressure
                
                if contradiction.intensity == ContradictionIntensity.CRITICAL:
                    critical_count += 1
                    
                if contradiction.antagonism == ContradictionAntagonism.ANTAGONISTIC:
                    antagonistic_count += 1
                    
        # Calculate stability score (0.0 = highly unstable, 1.0 = stable)
        stability = max(0.0, 1.0 - (total_pressure / len(self.contradictions)))
        
        # Determine status
        if stability > 0.8:
            status = "stable"
        elif stability > 0.6:
            status = "somewhat_unstable"
        elif stability > 0.4:
            status = "unstable"
        elif stability > 0.2:
            status = "highly_unstable"
        else:
            status = "crisis"
            
        # Generate warnings
        warnings = []
        if critical_count > 0:
            warnings.append(f"{critical_count} critical contradiction(s) detected")
        if antagonistic_count > 2:
            warnings.append(f"{antagonistic_count} antagonistic contradictions present")
        if total_pressure > 3.0:
            warnings.append("High systemic transformation pressure")
        if stability < 0.3:
            warnings.append("Revolutionary situation may be developing")
            
        return {
            "stability": stability,
            "status": status,
            "warnings": warnings,
            "total_pressure": total_pressure,
            "critical_contradictions": critical_count,
            "antagonistic_contradictions": antagonistic_count,
            "principal_contradiction": self.identify_principal_contradiction()
        }