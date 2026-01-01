"""VitalitySystem - The Drain, The Attrition, and The Reaper.

ADR032: Materialist Causality System Order
Mass Line Refactor: Agent-as-Block Population Dynamics

This system runs FIRST in the materialist causality chain, implementing:
1. Phase 1 - The Drain: Linear subsistence burn (cost = base_subsistence * multiplier)
2. Phase 2 - Grinding Attrition: Probabilistic mortality from inequality
3. Phase 3 - The Reaper: Full extinction check (population=0 → active=False)

Historical Materialist Principle:
    Life requires material sustenance. Living costs wealth. No wealth = no life.
    Elites with higher subsistence multipliers burn faster when cut off from
    imperial rent flows - modeling the "Principal Contradiction" where
    bourgeoisie depends on extraction to maintain their standard of living.

Mass Line Principle:
    One agent = one demographic block. High inequality within a block means
    marginal workers (bottom 40%) starve even when average wealth is sufficient.
    The Grinding Attrition Formula models this probabilistic mortality:
        marginal_wealth = per_capita_wealth × (1 - inequality)
        mortality_rate = max(0, (consumption_needs - marginal_wealth) / consumption_needs)
        deaths = floor(population × mortality_rate × base_mortality_factor)

Malthusian Correction:
    When deaths occur, population decreases → per-capita wealth increases →
    future mortality decreases → equilibrium. This creates natural carrying
    capacity dynamics based on available wealth.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EventType

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType


class VitalitySystem:
    """Phase 1: The Drain + Grinding Attrition + The Reaper (Mass Line Refactor).

    Three-phase vitality check for all active entities:

    Phase 1 - The Drain (Subsistence Burn):
        cost = base_subsistence × subsistence_multiplier
        wealth = max(0, wealth - cost)

    Phase 2 - Grinding Attrition (Probabilistic Mortality):
        For blocks with population > 1 or any inequality:
        - Calculate per-capita and marginal wealth
        - Apply mortality formula based on inequality
        - Reduce population, emit POPULATION_DEATH event

    Phase 3 - The Reaper (Extinction Check):
        If population = 0 OR (population = 1 AND wealth < consumption_needs):
        - Mark entity as inactive
        - Emit ENTITY_DEATH event

    Events:
        POPULATION_DEATH: Probabilistic deaths from inequality.
            payload: {entity_id, deaths, remaining_population, mortality_rate}
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

        Phase 1 - The Drain: Burn wealth based on subsistence cost.
        Phase 2 - Grinding Attrition: Calculate probabilistic deaths.
        Phase 3 - The Reaper: Mark extinct entities as inactive.
        """
        tick: int = context.get("tick", 0)
        base_subsistence = services.defines.economy.base_subsistence
        mortality_factor = services.defines.vitality.base_mortality_factor
        inequality_impact = services.defines.vitality.inequality_impact

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

            # Phase 1: The Drain (Subsistence Burn)
            if base_subsistence > 0:
                wealth = data.get("wealth", 0.0)
                multiplier = data.get("subsistence_multiplier", 1.0)
                cost = base_subsistence * multiplier
                graph.nodes[node_id]["wealth"] = max(0.0, wealth - cost)

            # Phase 2: Grinding Attrition (Probabilistic Mortality)
            deaths = self._calculate_deaths(
                graph.nodes[node_id],
                mortality_factor,
                inequality_impact,
            )

            if deaths > 0:
                new_population = max(0, population - deaths)
                graph.nodes[node_id]["population"] = new_population
                mortality_rate = deaths / population if population > 0 else 0.0

                # Emit POPULATION_DEATH event
                services.event_bus.publish(
                    Event(
                        type=EventType.POPULATION_DEATH,
                        tick=tick,
                        payload={
                            "entity_id": node_id,
                            "deaths": deaths,
                            "remaining_population": new_population,
                            "mortality_rate": mortality_rate,
                        },
                    )
                )

            # Phase 3: The Reaper (Extinction Check)
            current_population = graph.nodes[node_id].get("population", 1)
            wealth = graph.nodes[node_id].get("wealth", 0.0)
            s_bio = data.get("s_bio", 0.0)
            s_class = data.get("s_class", 0.0)
            consumption_needs = s_bio + s_class

            # Full extinction: population=0 OR (population=1 AND starving)
            is_extinct = current_population <= 0
            is_starving = current_population == 1 and wealth < consumption_needs

            if is_extinct or is_starving:
                graph.nodes[node_id]["active"] = False
                if is_starving and current_population == 1:
                    graph.nodes[node_id]["population"] = 0

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
                            "cause": "extinction" if is_extinct else "starvation",
                        },
                    )
                )

    def _calculate_deaths(
        self,
        data: dict[str, Any],
        mortality_factor: float,
        inequality_impact: float,
    ) -> int:
        """Calculate probabilistic deaths using the Grinding Attrition Formula.

        The Grinding Attrition Formula:
        1. effective_wealth_per_capita = wealth / population
        2. marginal_wealth = effective_wealth_per_capita * (1 - inequality * inequality_impact)
           - At inequality=0: marginal_wealth = average (everyone gets same)
           - At inequality=1: marginal_wealth = 0 (bottom has nothing)
        3. consumption_needs = s_bio + s_class
        4. mortality_rate = max(0, (consumption_needs - marginal_wealth) / consumption_needs)
           - At marginal_wealth >= consumption_needs: mortality_rate = 0
           - At marginal_wealth = 0: mortality_rate = 1.0 (100% at risk)
        5. deaths = floor(population * mortality_rate * mortality_factor)

        The Malthusian Correction:
        When population decreases, per-capita wealth increases, reducing future mortality.
        This creates equilibrium dynamics - population stabilizes at carrying capacity.

        Args:
            data: Node data dictionary with wealth, population, inequality, etc.
            mortality_factor: Base fraction of at-risk population that dies per tick.
            inequality_impact: How strongly inequality affects marginal wealth.

        Returns:
            Number of deaths (integer, >= 0).
        """
        wealth = data.get("wealth", 0.0)
        population = data.get("population", 1)
        inequality = data.get("inequality", 0.0)
        s_bio = data.get("s_bio", 0.0)
        s_class = data.get("s_class", 0.0)
        consumption_needs = s_bio + s_class

        # Edge case: no consumption needs = no deaths from grinding attrition
        if consumption_needs <= 0:
            return 0

        # Edge case: zero or negative population
        if population <= 0:
            return 0

        # Step 1: Calculate effective wealth per capita
        effective_wealth_per_capita = wealth / population

        # Step 2: Calculate marginal wealth (what the poorest get)
        # At inequality=0: marginal = average
        # At inequality=1: marginal = 0 (all wealth concentrated at top)
        marginal_wealth = effective_wealth_per_capita * (1 - inequality * inequality_impact)

        # Step 3: Calculate mortality rate
        # If marginal workers can afford consumption, no grinding deaths
        if marginal_wealth >= consumption_needs:
            return 0

        mortality_rate = (consumption_needs - marginal_wealth) / consumption_needs

        # Step 4: Calculate deaths
        deaths = int(population * mortality_rate * mortality_factor)

        return deaths
