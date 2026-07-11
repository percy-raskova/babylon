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

import logging
from typing import TYPE_CHECKING, ClassVar

from babylon.economics.tensor import NoDataSentinel
from babylon.models.enums import EdgeType, SocialRole

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType

logger = logging.getLogger(__name__)

# Direct producers: receive production directly (self-employed/exploited)
_DIRECT_PRODUCER_ROLES: frozenset[SocialRole] = frozenset({SocialRole.PERIPHERY_PROLETARIAT})

# Employed producers: production routes to employer (Amin/Wallerstein model)
_EMPLOYED_PRODUCER_ROLES: frozenset[SocialRole] = frozenset({SocialRole.LABOR_ARISTOCRACY})

# All producer roles (union for filtering)
_PRODUCER_ROLES: frozenset[SocialRole] = _DIRECT_PRODUCER_ROLES | _EMPLOYED_PRODUCER_ROLES


class ProductionSystem(SystemBase):
    """Phase 1: Value creation - The Soil.

    Workers produce wealth proportional to territory biocapacity.

    Production formula:
        produced_value = base_labor_power * (biocapacity / max_biocapacity)

    Only active workers with TENANCY edges to territories can produce.
    Bourgeoisie classes extract value but do not produce it.
    """

    # Spec 053 INV-001: ProductionSystem observes already-hydrated value-in-hours
    # from capital stocks rather than generating fresh value. Opted in to per-system
    # c+v+s conservation check by default-deny.
    creates_value: ClassVar[bool] = False

    # Spec 040, Discipline 1: Declared invariants preserved by this system
    invariants: list[object] = []  # populated in __init__

    # Spec 040, Discipline 4: Phase this system operates in
    phase: int = 0  # Phase.PRODUCTION

    def __init__(self) -> None:
        """Initialize ProductionSystem with declared invariants and phase."""
        from babylon.engine.invariants import NonNegativeWealth
        from babylon.engine.phase import Phase

        self.invariants = [NonNegativeWealth()]
        self.phase = Phase.PRODUCTION

    name: ClassVar[str] = "production"

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
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

        # Owner item 25 (ProductionSystem staleness bug): the tensor-registry
        # lookup year must climb with tick, not stay pinned at whatever
        # ``base_year`` was hydrated with. Same epoch formula as
        # TickDynamicsSystem._determine_year / babylon.kernel.sim_clock
        # (``base_year + tick // weeks_per_year``) — reconciled here rather
        # than centralized, since those two call sites don't take a
        # ServicesProtocol/weeks_per_year the same way this one does.
        tick: int
        if hasattr(context, "tick"):
            tick = context.tick
        elif isinstance(context, dict):
            tick = context.get("tick", 0)
        else:
            tick = 0

        # Track production per territory for extraction_intensity
        territory_production: dict[str, float] = {}

        # Track LA production for wages phase (Amin/Wallerstein model)
        la_production: dict[str, float] = {}

        for node in graph.query_nodes(node_type="social_class"):
            attrs = node.attributes

            # Skip inactive (dead) workers
            if not attrs.get("active", True):
                continue

            # Skip non-producer roles (bourgeoisie)
            role = attrs.get("role")
            if role not in _PRODUCER_ROLES:
                continue

            # Find territory via TENANCY edge
            territory_id = self._find_tenancy_target(graph, node.id)
            if territory_id is None:
                continue

            # Calculate production based on territory biocapacity
            territory_node = graph.get_node(territory_id)
            territory_attrs = territory_node.attributes if territory_node else {}
            biocapacity = territory_attrs.get("biocapacity", 0.0)
            max_biocapacity = territory_attrs.get("max_biocapacity", 1.0)

            # Calculate biocapacity ratio (avoid division by zero)
            bio_ratio = 0.0 if max_biocapacity <= 0 else biocapacity / max_biocapacity

            # Mass Line: Scale production by population (demographic block size)
            population = attrs.get("population", 1)

            # Determine effective labor power from tensor or fallback (Feature 020)
            effective_labor_power = base_labor_power  # default fallback
            tensor_registry = getattr(services, "tensor_registry", None)
            if tensor_registry is not None:
                fips_code = territory_attrs.get("fips_code")
                if fips_code is not None:
                    hydrated_base_year = graph.get_graph_attr("base_year", 2022)
                    current_year = hydrated_base_year + tick // weeks_per_year
                    tensor = tensor_registry.get(fips_code, current_year)
                    if not isinstance(tensor, NoDataSentinel):
                        # Use variable capital as proxy for productive capacity
                        # Convert annual to weekly (same as base_labor_power)
                        effective_labor_power = tensor.total_v / weeks_per_year

            # Calculate production value
            produced_value = (effective_labor_power * population) * bio_ratio
            current_wealth = attrs.get("wealth", 0.0)

            # Route production based on role type
            if role in _DIRECT_PRODUCER_ROLES:
                # Direct producers: production goes to worker wealth
                graph.update_node(node.id, wealth=current_wealth + produced_value)
            elif role in _EMPLOYED_PRODUCER_ROLES:
                # Employed producers (LA): production routes to employer
                # Wages phase will pay back productivity + super-wage bonus
                employer_id = self._find_employer(graph, node.id)
                if employer_id is not None:
                    # Route production to employer's wealth
                    employer_node = graph.get_node(employer_id)
                    employer_wealth = (
                        employer_node.attributes.get("wealth", 0.0) if employer_node else 0.0
                    )
                    graph.update_node(employer_id, wealth=employer_wealth + produced_value)
                    # Store production for wages phase
                    la_production[node.id] = produced_value
                else:
                    # Fallback: no employer found, LA produces directly
                    # This shouldn't happen in a properly configured scenario
                    graph.update_node(node.id, wealth=current_wealth + produced_value)

            # Accumulate production by territory for extraction_intensity
            if territory_id and produced_value > 0:
                territory_production[territory_id] = (
                    territory_production.get(territory_id, 0.0) + produced_value
                )

        # Store LA production for wages phase (ImperialRentSystem)
        graph.set_graph_attr("la_production", la_production)

        # Set extraction_intensity on all territories
        self._update_extraction_intensities(graph, territory_production)

    def _find_tenancy_target(self, graph: GraphProtocol, worker_id: str) -> str | None:
        """Find the territory a worker occupies via TENANCY edge.

        Args:
            graph: The world graph.
            worker_id: The worker node ID.

        Returns:
            Territory node ID if found, None otherwise.
        """
        for edge in graph.query_edges(edge_type=EdgeType.TENANCY):
            if edge.source_id == worker_id:
                return edge.target_id
        return None

    def _find_employer(self, graph: GraphProtocol, worker_id: str) -> str | None:
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
        for edge in graph.query_edges(edge_type=EdgeType.WAGES):
            if edge.target_id == worker_id:
                return edge.source_id
        return None

    def _update_extraction_intensities(
        self,
        graph: GraphProtocol,
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
        for node in graph.query_nodes(node_type="territory"):
            attrs = node.attributes
            total_production = territory_production.get(node.id, 0.0)
            max_biocapacity = attrs.get("max_biocapacity", 100.0)

            intensity = min(1.0, total_production / max_biocapacity) if max_biocapacity > 0 else 0.0
            graph.update_node(node.id, extraction_intensity=intensity)
