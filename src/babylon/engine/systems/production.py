"""ProductionSystem - The Soil.

Material Reality Refactor: Workers generate wealth from labor × biocapacity.

This system runs after VitalitySystem and before ImperialRentSystem.
Workers (PERIPHERY_PROLETARIAT, LABOR_ARISTOCRACY) produce value based on:
- Their territory's biocapacity ratio (biocapacity / max_biocapacity)
- The base_labor_power configuration parameter

Amin/Wallerstein Model (Labor Aristocracy):
    The LA produces value, but their wages are HIGHER than productivity due to
    super-profits extracted from the periphery. The difference is the "imperial bribe."

    Production routing:
    - PERIPHERY_PROLETARIAT: Production goes directly to worker wealth
    - LABOR_ARISTOCRACY: Production routes to employer (Core Bourgeoisie),
      then wages phase pays back productivity + super-wage bonus from rent pool

After calculating production, this system sets extraction_intensity on each
territory, enabling MetabolismSystem to calculate biocapacity depletion.

Historical Materialist Principle:
    Value comes from labor applied to nature. Dead land = no production.
    Production depletes nature. The metabolic rift is the ecological cost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

from babylon.models.enums import EdgeType, SocialRole

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType

# Direct producers: receive production directly (self-employed/exploited)
_DIRECT_PRODUCER_ROLES: frozenset[SocialRole] = frozenset({SocialRole.PERIPHERY_PROLETARIAT})

# Employed producers: production routes to employer (Amin/Wallerstein model)
_EMPLOYED_PRODUCER_ROLES: frozenset[SocialRole] = frozenset({SocialRole.LABOR_ARISTOCRACY})

# All producer roles (union for filtering)
_PRODUCER_ROLES: frozenset[SocialRole] = _DIRECT_PRODUCER_ROLES | _EMPLOYED_PRODUCER_ROLES


class ProductionSystem:
    """Phase 1: Value creation - The Soil.

    Workers produce wealth proportional to territory biocapacity.

    Production formula:
        produced_value = base_labor_power * (biocapacity / max_biocapacity)

    Only active workers with TENANCY edges to territories can produce.
    Bourgeoisie classes extract value but do not produce it.
    """

    @property
    def name(self) -> str:
        """System identifier."""
        return "production"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        _context: ContextType,
    ) -> None:
        """Generate wealth for workers and set extraction_intensity.

        Iterates all social_class nodes. For active workers with TENANCY
        edges, calculates production based on territory health.

        Production routing (Amin/Wallerstein model):
        - Direct producers (periphery): Production added to worker wealth
        - Employed producers (LA): Production routed to employer, stored
          in graph metadata for wages phase to pay back with bonus

        NOTE: base_labor_power is an annual rate, converted to weekly here
        to match ImperialRentSystem's timescale conversion.
        """
        # Convert annual production to weekly (same as extraction_efficiency)
        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        base_labor_power = annual_labor_power / weeks_per_year

        # Track production per territory for extraction_intensity
        territory_production: dict[str, float] = {}

        # Track LA production for wages phase (Amin/Wallerstein model)
        la_production: dict[str, float] = {}

        for node_id, data in graph.nodes(data=True):
            # Skip non-entity nodes (territories, etc.)
            if data.get("_node_type") != "social_class":
                continue

            # Skip inactive (dead) workers
            if not data.get("active", True):
                continue

            # Skip non-producer roles (bourgeoisie)
            role = data.get("role")
            if role not in _PRODUCER_ROLES:
                continue

            # Find territory via TENANCY edge
            territory_id = self._find_tenancy_target(graph, node_id)
            if territory_id is None:
                continue

            # Calculate production based on territory biocapacity
            territory_data = graph.nodes[territory_id]
            biocapacity = territory_data.get("biocapacity", 0.0)
            max_biocapacity = territory_data.get("max_biocapacity", 1.0)

            # Calculate biocapacity ratio (avoid division by zero)
            bio_ratio = 0.0 if max_biocapacity <= 0 else biocapacity / max_biocapacity

            # Mass Line: Scale production by population (demographic block size)
            population = data.get("population", 1)

            # Calculate production value
            produced_value = (base_labor_power * population) * bio_ratio
            current_wealth = data.get("wealth", 0.0)

            # Route production based on role type
            if role in _DIRECT_PRODUCER_ROLES:
                # Direct producers: production goes to worker wealth
                graph.nodes[node_id]["wealth"] = current_wealth + produced_value
            elif role in _EMPLOYED_PRODUCER_ROLES:
                # Employed producers (LA): production routes to employer
                # Wages phase will pay back productivity + super-wage bonus
                employer_id = self._find_employer(graph, node_id)
                if employer_id is not None:
                    # Route production to employer's wealth
                    employer_wealth = graph.nodes[employer_id].get("wealth", 0.0)
                    graph.nodes[employer_id]["wealth"] = employer_wealth + produced_value
                    # Store production for wages phase
                    la_production[node_id] = produced_value
                else:
                    # Fallback: no employer found, LA produces directly
                    # This shouldn't happen in a properly configured scenario
                    graph.nodes[node_id]["wealth"] = current_wealth + produced_value

            # Accumulate production by territory for extraction_intensity
            if territory_id and produced_value > 0:
                territory_production[territory_id] = (
                    territory_production.get(territory_id, 0.0) + produced_value
                )

        # Store LA production for wages phase (ImperialRentSystem)
        graph.graph["la_production"] = la_production

        # Set extraction_intensity on all territories
        self._update_extraction_intensities(graph, territory_production)

    def _find_tenancy_target(self, graph: nx.DiGraph[str], worker_id: str) -> str | None:
        """Find the territory a worker occupies via TENANCY edge.

        Args:
            graph: The world graph.
            worker_id: The worker node ID.

        Returns:
            Territory node ID if found, None otherwise.
        """
        for _, target_id, edge_data in graph.out_edges(worker_id, data=True):
            if edge_data.get("edge_type") == EdgeType.TENANCY:
                return target_id
        return None

    def _find_employer(self, graph: nx.DiGraph[str], worker_id: str) -> str | None:
        """Find employer via incoming WAGES edge (employer -> worker).

        In the Amin/Wallerstein model, the Labor Aristocracy works for the
        Core Bourgeoisie. The employer is identified by the source of WAGES
        edges pointing to the worker.

        Args:
            graph: The world graph.
            worker_id: The LA worker node ID.

        Returns:
            Employer node ID if found, None otherwise.
        """
        for source_id, _, edge_data in graph.in_edges(worker_id, data=True):
            if edge_data.get("edge_type") == EdgeType.WAGES:
                return source_id
        return None

    def _update_extraction_intensities(
        self,
        graph: nx.DiGraph[str],
        territory_production: dict[str, float],
    ) -> None:
        """Update extraction_intensity on territory nodes.

        Sets extraction_intensity based on total production on each territory.
        Territories with no production this tick get intensity = 0.0.

        Formula: intensity = min(1.0, total_production / max_biocapacity)

        Args:
            graph: The world graph with territory nodes.
            territory_production: Map of territory_id -> total production this tick.
        """
        for node_id, data in graph.nodes(data=True):
            if data.get("_node_type") != "territory":
                continue

            total_production = territory_production.get(node_id, 0.0)
            max_biocapacity = data.get("max_biocapacity", 100.0)

            intensity = min(1.0, total_production / max_biocapacity) if max_biocapacity > 0 else 0.0
            graph.nodes[node_id]["extraction_intensity"] = intensity
