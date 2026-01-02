"""VitalitySystem - The Drain, The Attrition, and The Reaper.

ADR032: Materialist Causality System Order
Mass Line Refactor Phase 3: Coverage Ratio Threshold Model

This system runs FIRST in the materialist causality chain, implementing:
1. Phase 1 - The Drain: Population-scaled subsistence burn
   cost = (base_subsistence * population) * subsistence_multiplier
2. Phase 2 - Grinding Attrition: Coverage ratio threshold mortality
3. Phase 3 - The Reaper: Full extinction check (population=0 → active=False)

Historical Materialist Principle:
    Life requires material sustenance. Living costs wealth. No wealth = no life.
    Elites with higher subsistence multipliers burn faster when cut off from
    imperial rent flows - modeling the "Principal Contradiction" where
    bourgeoisie depends on extraction to maintain their standard of living.

Mass Line Principle (Phase 3 Coverage Ratio Formula):
    One agent = one demographic block. High inequality within a block means
    you need MORE coverage to prevent deaths:
        coverage_ratio = wealth_per_capita / subsistence_needs
        threshold = 1.0 + inequality
        deficit = max(0, threshold - coverage_ratio)
        attrition_rate = clamp(deficit × (0.5 + inequality), 0, 1)
        deaths = floor(population × attrition_rate)

Malthusian Correction:
    When deaths occur, population decreases → per-capita wealth increases →
    future mortality decreases → equilibrium. Wealth is NOT reduced when
    people die (the poor die with 0 wealth).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EventType
from babylon.systems.formulas import calculate_mortality_rate

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType


class VitalitySystem:
    """Mass Line Phase 3: The Drain + Grinding Attrition + The Reaper.

    Three-phase vitality check for all active entities:

    Phase 1 - The Drain (Population-Scaled Subsistence Burn):
        cost = (base_subsistence × population) × subsistence_multiplier
        wealth = max(0, wealth - cost)

    Phase 2 - Grinding Attrition (Coverage Ratio Threshold Mortality):
        Uses calculate_mortality_rate() from formulas.vitality:
        - coverage_ratio = wealth_per_capita / subsistence_needs
        - threshold = 1.0 + inequality
        - deficit = max(0, threshold - coverage_ratio)
        - attrition_rate = clamp(deficit × (0.5 + inequality), 0, 1)
        - Reduce population, emit POPULATION_ATTRITION event

    Phase 3 - The Reaper (Extinction Check):
        If population = 0 OR (population = 1 AND wealth < consumption_needs):
        - Mark entity as inactive
        - Emit ENTITY_DEATH event

    Events:
        POPULATION_ATTRITION: Coverage deficit deaths from inequality.
            payload: {entity_id, deaths, remaining_population, attrition_rate}
        ENTITY_DEATH: Full extinction of a demographic block.
            payload: {entity_id, wealth, consumption_needs, cause, tick}
    """

    @property
    def name(self) -> str:
        """System identifier."""
        return "vitality"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Execute three-phase vitality check.

        Phase 1 - The Drain: Burn wealth based on population-scaled subsistence cost.
        Phase 2 - Grinding Attrition: Calculate coverage ratio threshold deaths.
        Phase 3 - The Reaper: Mark extinct entities as inactive.
        """
        tick: int = context.get("tick", 0)
        base_subsistence = services.defines.economy.base_subsistence

        for node_id, data in graph.nodes(data=True):
            # Skip non-entity nodes (territories, etc.)
            if data.get("_node_type") != "social_class":
                continue

            # Skip already-dead entities
            if not data.get("active", True):
                continue

            population = data.get("population", 1)

            # Skip entities with zero population (already extinct)
            if population <= 0:
                continue

            # Phase 1: The Drain (Population-Scaled Subsistence Burn)
            if base_subsistence > 0:
                wealth = data.get("wealth", 0.0)
                multiplier = data.get("subsistence_multiplier", 1.0)
                # Phase 3 change: Scale by population
                cost = (base_subsistence * population) * multiplier
                graph.nodes[node_id]["wealth"] = max(0.0, wealth - cost)

            # Phase 2: Grinding Attrition (Coverage Ratio Threshold Mortality)
            deaths, attrition_rate = self._calculate_deaths(
                graph.nodes[node_id],
            )

            if deaths > 0:
                new_population = max(0, population - deaths)
                graph.nodes[node_id]["population"] = new_population

                # Emit POPULATION_ATTRITION event (Phase 3 change)
                services.event_bus.publish(
                    Event(
                        type=EventType.POPULATION_ATTRITION,
                        tick=tick,
                        payload={
                            "entity_id": node_id,
                            "deaths": deaths,
                            "remaining_population": new_population,
                            "attrition_rate": attrition_rate,
                        },
                    )
                )

            # Phase 3: The Reaper (Extinction Check)
            current_population = graph.nodes[node_id].get("population", 1)
            wealth = graph.nodes[node_id].get("wealth", 0.0)
            s_bio = data.get("s_bio", 0.0)
            s_class = data.get("s_class", 0.0)
            consumption_needs = s_bio + s_class

            # Zombie Prevention Failsafe (Sprint 1.X D2: High-Fidelity State)
            # Only for population=1: prevents asymptotic decay without death.
            # For population>1, attrition naturally reduces to 1 before this triggers.
            death_threshold = services.defines.economy.death_threshold
            is_zombie_trapped = wealth < death_threshold and current_population == 1

            # Full extinction: population=0 OR (population=1 AND starving) OR zombie trap
            is_extinct = current_population <= 0
            is_starving = current_population == 1 and wealth < consumption_needs

            if is_extinct or is_starving or is_zombie_trapped:
                graph.nodes[node_id]["active"] = False
                if is_starving and current_population == 1:
                    graph.nodes[node_id]["population"] = 0
                if is_zombie_trapped:
                    graph.nodes[node_id]["population"] = 0

                # Determine cause of death
                if is_extinct:
                    cause = "extinction"
                elif is_zombie_trapped:
                    cause = "wealth_threshold"
                else:
                    cause = "starvation"

                # Emit ENTITY_DEATH event for full extinction
                services.event_bus.publish(
                    Event(
                        type=EventType.ENTITY_DEATH,
                        tick=tick,
                        payload={
                            "entity_id": node_id,
                            "wealth": wealth,
                            "consumption_needs": consumption_needs,
                            "s_bio": s_bio,
                            "s_class": s_class,
                            "cause": cause,
                        },
                    )
                )

    def _calculate_deaths(
        self,
        data: dict[str, Any],
    ) -> tuple[int, float]:
        """Calculate deaths using the Coverage Ratio Threshold Formula.

        Phase 3 Coverage Ratio Formula (from formulas.vitality):
            coverage_ratio = wealth_per_capita / subsistence_needs
            threshold = 1.0 + inequality
            deficit = max(0, threshold - coverage_ratio)
            attrition_rate = clamp(deficit × (0.5 + inequality), 0, 1)
            deaths = floor(population × attrition_rate)

        The Malthusian Correction:
            When population decreases, per-capita wealth increases, reducing
            future mortality. Wealth is NOT reduced when people die (the poor
            die with 0 wealth).

        Args:
            data: Node data dictionary with wealth, population, inequality, etc.

        Returns:
            Tuple of (deaths: int, attrition_rate: float).
        """
        wealth = data.get("wealth", 0.0)
        population = data.get("population", 1)
        inequality = data.get("inequality", 0.0)
        s_bio = data.get("s_bio", 0.0)
        s_class = data.get("s_class", 0.0)
        subsistence_needs = s_bio + s_class

        # Edge case: no consumption needs = no deaths
        if subsistence_needs <= 0:
            return 0, 0.0

        # Edge case: zero or negative population
        if population <= 0:
            return 0, 0.0

        # Calculate wealth per capita
        wealth_per_capita = wealth / population

        # Use the Phase 3 formula from formulas.vitality
        attrition_rate = calculate_mortality_rate(
            wealth_per_capita=wealth_per_capita,
            subsistence_needs=subsistence_needs,
            inequality=inequality,
        )

        # Calculate deaths
        deaths = int(population * attrition_rate)

        return deaths, attrition_rate
