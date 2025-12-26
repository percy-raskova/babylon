"""Economic systems for the Babylon simulation - The Base.

Sprint 3.4.1: Imperial Circuit - 4-node value flow model.
Sprint 3.4.4: Dynamic Balance - Pool tracking and decision heuristics.

The Imperial Circuit has five phases:
1. EXPLOITATION: P_w -> P_c (imperial rent extraction)
2. TRIBUTE: P_c -> C_b (comprador keeps 15% cut) -> FEEDS POOL
3. WAGES: C_b -> C_w (dynamic rate super-wages to labor aristocracy) -> DRAINS POOL
4. CLIENT_STATE: C_b -> P_c (subsidy when unstable, converts to repression) -> DRAINS POOL
5. DECISION: Bourgeoisie heuristics update wage_rate/repression based on pool/tension
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.enums import EdgeType, EventType, SocialRole
from babylon.systems.formulas import BourgeoisieDecision

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType


def _get_class_consciousness_from_node(node_data: dict[str, Any]) -> float:
    """Extract class_consciousness from graph node data.

    Args:
        node_data: Graph node data dictionary

    Returns:
        Class consciousness value in [0, 1]
    """
    ideology = node_data.get("ideology")

    if ideology is None:
        return 0.0

    if isinstance(ideology, dict):
        # IdeologicalProfile format
        return float(ideology.get("class_consciousness", 0.0))

    return 0.0


class ImperialRentSystem:
    """Imperial Circuit Economic System - 5-phase value extraction with pool tracking.

    Sprint 3.4.4: Dynamic Balance - The Gas Tank and Driver.

    Implements the MLM-TW model of value flow with finite resources:
    - Phase 1: Extraction (P_w -> P_c via EXPLOITATION)
    - Phase 2: Tribute (P_c -> C_b via TRIBUTE, minus comprador cut) -> FEEDS POOL
    - Phase 3: Wages (C_b -> C_w via WAGES, dynamic rate) -> DRAINS POOL
    - Phase 4: Subsidy (C_b -> P_c via CLIENT_STATE, stabilization) -> DRAINS POOL
    - Phase 5: Decision (Bourgeoisie heuristics adjust wage_rate/repression)

    The imperial_rent_pool in GlobalEconomy tracks available resources:
    - Inflow: Tribute received by Core Bourgeoisie (post-comprador cut)
    - Outflow: Wages paid + Subsidies paid
    - When pool depletes, bourgeoisie must choose between austerity or repression
    """

    name = "Imperial Rent"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Apply the 5-phase Imperial Circuit to the graph.

        Phases execute in sequence, as each depends on the previous:
        1. Extraction must happen before tribute (P_c needs wealth to send)
        2. Tribute must happen before wages (C_b needs wealth to pay) - FEEDS POOL
        3. Wages capped at available pool - DRAINS POOL
        4. Subsidy capped at available pool after wages - DRAINS POOL
        5. Decision phase: Bourgeoisie heuristics update economy for next tick

        The economy state is read from graph.graph["economy"] and written back
        after all phases complete.
        """
        # Load economy from graph metadata (or create default)
        economy = self._load_economy(graph, services)
        initial_pool = services.defines.economy.initial_rent_pool

        # Track inflow/outflow for this tick
        tick_context = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": economy.imperial_rent_pool,
            "wage_rate": economy.current_super_wage_rate,
            "repression_level": economy.current_repression_level,
        }

        # Execute phases with pool tracking
        self._process_extraction_phase(graph, services, context, tick_context)
        self._process_tribute_phase(graph, services, context, tick_context)
        self._process_wages_phase(graph, services, context, tick_context)
        self._process_subsidy_phase(graph, services, context, tick_context)
        self._process_decision_phase(graph, services, context, tick_context, initial_pool)

        # Save updated economy back to graph
        self._save_economy(graph, tick_context)

    def _process_extraction_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
        tick_context: dict[str, Any],
    ) -> None:
        """Phase 1: Imperial rent extraction via EXPLOITATION edges.

        When extraction targets CORE_BOURGEOISIE directly (2-node scenario
        without comprador intermediary), the extracted rent is tracked as
        tribute_inflow to enable wage calculations.
        """
        calculate_imperial_rent = services.formulas.get("imperial_rent")
        extraction_efficiency = services.defines.economy.extraction_efficiency

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.EXPLOITATION:
                continue

            # Get source (worker) data
            worker_data = graph.nodes[source_id]
            worker_wealth = worker_data.get("wealth", 0.0)

            # Extract class consciousness (handles both IdeologicalProfile and legacy)
            consciousness = _get_class_consciousness_from_node(worker_data)

            # Calculate imperial rent
            rent = calculate_imperial_rent(
                alpha=extraction_efficiency,
                periphery_wages=worker_wealth,
                periphery_consciousness=consciousness,
            )

            # Cap rent at available wealth
            rent = min(rent, worker_wealth)

            # Transfer wealth
            graph.nodes[source_id]["wealth"] = max(0.0, worker_wealth - rent)
            graph.nodes[target_id]["wealth"] = graph.nodes[target_id].get("wealth", 0.0) + rent

            # Record value flow
            graph.edges[source_id, target_id]["value_flow"] = rent

            # Track direct extraction to CORE_BOURGEOISIE as tribute_inflow
            # This handles 2-node scenarios where extraction skips comprador
            target_role = graph.nodes[target_id].get("role")
            if isinstance(target_role, str):
                target_role = SocialRole(target_role)
            if target_role == SocialRole.CORE_BOURGEOISIE:
                tick_context["tribute_inflow"] += rent
                tick_context["current_pool"] += rent

            # Emit event for AI narrative layer (ignore floating point noise)
            if rent > services.defines.economy.negligible_rent:
                tick = context.get("tick", 0)
                services.event_bus.publish(
                    Event(
                        type=EventType.SURPLUS_EXTRACTION,
                        tick=tick,
                        payload={
                            "source_id": source_id,
                            "target_id": target_id,
                            "amount": rent,
                            "mechanism": "imperial_rent",
                        },
                    )
                )

    def _process_tribute_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,  # noqa: ARG002 - Used for config.comprador_cut
        context: ContextType,  # noqa: ARG002 - API consistency with other phases
        tick_context: dict[str, Any],  # noqa: ARG002 - Used for pool tracking
    ) -> None:
        """Phase 2: Comprador tribute via TRIBUTE edges -> FEEDS POOL.

        The comprador class keeps a cut (default 15%) and sends the rest
        as tribute to the core bourgeoisie.

        Sprint 3.4.4: Tribute to Core Bourgeoisie feeds the imperial_rent_pool.
        Only tribute reaching CORE_BOURGEOISIE nodes contributes to the pool.
        """
        _ = context  # Unused but kept for API consistency
        comprador_cut = services.defines.economy.comprador_cut

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.TRIBUTE:
                continue

            # Get comprador wealth
            comprador_wealth = graph.nodes[source_id].get("wealth", 0.0)

            if comprador_wealth <= 0:
                continue

            # Comprador keeps their cut
            cut_amount = comprador_wealth * comprador_cut
            tribute_amount = comprador_wealth - cut_amount

            # Transfer tribute (comprador keeps only the cut)
            graph.nodes[source_id]["wealth"] = cut_amount
            graph.nodes[target_id]["wealth"] = (
                graph.nodes[target_id].get("wealth", 0.0) + tribute_amount
            )

            # Record value flow
            graph.edges[source_id, target_id]["value_flow"] = tribute_amount

            # Sprint 3.4.4: Track tribute to Core Bourgeoisie as pool inflow
            target_role = graph.nodes[target_id].get("role")
            if isinstance(target_role, str):
                target_role = SocialRole(target_role)
            if target_role == SocialRole.CORE_BOURGEOISIE:
                tick_context["tribute_inflow"] += tribute_amount
                tick_context["current_pool"] += tribute_amount

    def _process_wages_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,  # noqa: ARG002 - API consistency with other phases
        tick_context: dict[str, Any],
    ) -> None:
        """Phase 3: Super-wages via WAGES edges -> DRAINS POOL.

        The core bourgeoisie pays a fraction of their INCOMING TRIBUTE as super-wages
        to the labor aristocracy (core workers). This is the bribe that
        prevents revolution in the core.

        BUG FIX: Wages are calculated from tribute_inflow (income flow), not
        from bourgeoisie_wealth (accumulated capital). This ensures C_b
        accumulates wealth over time, matching MLM-TW theory.

        PPP Model (Purchasing Power Parity):
        Super-wages don't manifest as direct cash transfers. Instead, the
        labor aristocracy receives nominal wages but enjoys enhanced purchasing
        power due to cheap commodities from the periphery.

        Formula:
            PPP Multiplier = 1 + (extraction_efficiency * superwage_multiplier * ppp_impact)
            Effective Wealth = Nominal Wealth + (Nominal Wage * (PPP Multiplier - 1))
            Unearned Increment = Effective Wealth - Nominal Wealth

        The "unearned increment" is the material basis of labor aristocracy loyalty.

        Sprint 3.4.4: Uses dynamic wage_rate from economy, not static config.
        Wages are capped at available pool to enforce scarcity.
        """
        _ = context  # Unused but kept for API consistency
        # Use dynamic wage rate from economy, not static config
        super_wage_rate = tick_context["wage_rate"]

        # PPP Model parameters
        superwage_multiplier = services.defines.economy.superwage_multiplier
        superwage_ppp_impact = services.defines.economy.superwage_ppp_impact
        extraction_efficiency = services.defines.economy.extraction_efficiency

        # Calculate PPP multiplier: how much purchasing power boost workers get
        # PPP_mult = 1 + (extraction_efficiency * superwage_multiplier * ppp_impact)
        ppp_multiplier = 1.0 + (extraction_efficiency * superwage_multiplier * superwage_ppp_impact)

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.WAGES:
                continue

            # Get bourgeoisie wealth
            bourgeoisie_wealth = graph.nodes[source_id].get("wealth", 0.0)

            if bourgeoisie_wealth <= 0:
                continue

            # Calculate super-wages from INCOME FLOW (tribute), not accumulated capital
            # BUG FIX: This ensures C_b accumulates wealth over time
            tribute_inflow = tick_context.get("tribute_inflow", 0.0)
            desired_wages = tribute_inflow * super_wage_rate
            # Also cap at what bourgeoisie can actually afford to pay
            desired_wages = min(desired_wages, bourgeoisie_wealth)

            # Sprint 3.4.4: Cap wages at available pool
            available_pool = tick_context["current_pool"]
            nominal_wages = min(desired_wages, available_pool)

            if nominal_wages <= 0:
                continue

            # Transfer nominal wages (actual cash transfer)
            graph.nodes[source_id]["wealth"] = bourgeoisie_wealth - nominal_wages
            current_wealth = graph.nodes[target_id].get("wealth", 0.0)
            new_nominal_wealth = current_wealth + nominal_wages
            graph.nodes[target_id]["wealth"] = new_nominal_wealth

            # PPP Model: Calculate effective wealth (what the wages can actually buy)
            # The PPP bonus represents cheap commodities from periphery exploitation
            ppp_bonus = nominal_wages * (ppp_multiplier - 1.0)
            effective_wealth = new_nominal_wealth + ppp_bonus
            unearned_increment = ppp_bonus

            # Store PPP values on the worker node
            graph.nodes[target_id]["effective_wealth"] = effective_wealth
            graph.nodes[target_id]["unearned_increment"] = unearned_increment
            graph.nodes[target_id]["ppp_multiplier"] = ppp_multiplier

            # Record value flow (nominal)
            graph.edges[source_id, target_id]["value_flow"] = nominal_wages

            # Sprint 3.4.4: Track wages as pool outflow
            tick_context["wages_outflow"] += nominal_wages
            tick_context["current_pool"] -= nominal_wages

    def _process_subsidy_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
        tick_context: dict[str, Any],
    ) -> None:
        """Phase 4: Imperial subsidy via CLIENT_STATE edges (The Iron Lung) -> DRAINS POOL.

        When a client state becomes unstable (P(S|R) >= threshold * P(S|A)),
        the core provides a subsidy that converts to repression capacity.

        This is the mechanism by which imperial wealth is used to suppress
        revolution in the periphery. Wealth is NOT conserved - it converts
        to suppression (military aid, police training, etc.).

        Sprint 3.4.4: Subsidy is capped at available pool after wages.
        """
        subsidy_trigger_threshold = services.defines.economy.subsidy_trigger_threshold
        subsidy_conversion_rate = services.defines.economy.subsidy_conversion_rate

        # Get survival probability formulas
        calculate_acquiescence = services.formulas.get("acquiescence_probability")
        calculate_revolution = services.formulas.get("revolution_probability")

        for source_id, target_id, data in graph.edges(data=True):
            edge_type = data.get("edge_type")
            if isinstance(edge_type, str):
                edge_type = EdgeType(edge_type)

            if edge_type != EdgeType.CLIENT_STATE:
                continue

            # Get target (client state) data
            target_data = graph.nodes[target_id]
            target_wealth = target_data.get("wealth", 0.0)
            target_organization = target_data.get(
                "organization", services.defines.DEFAULT_ORGANIZATION
            )
            target_repression = target_data.get(
                "repression_faced", services.defines.DEFAULT_REPRESSION_FACED
            )
            target_subsistence = target_data.get(
                "subsistence_threshold", services.defines.DEFAULT_SUBSISTENCE
            )

            # Get source (core bourgeoisie) wealth
            source_wealth = graph.nodes[source_id].get("wealth", 0.0)

            # Get subsidy cap from edge data
            subsidy_cap = data.get("subsidy_cap", 0.0)

            # Calculate survival probabilities for target
            p_acquiescence = calculate_acquiescence(
                wealth=target_wealth,
                subsistence_threshold=target_subsistence,
                steepness_k=services.defines.survival.steepness_k,
            )
            p_revolution = calculate_revolution(
                cohesion=target_organization,
                repression=target_repression,
            )

            # Check if subsidy is triggered (client state becoming unstable)
            # Subsidy triggers when P(S|R) >= threshold * P(S|A)
            # This means revolution is becoming a rational survival strategy
            if p_acquiescence > 0:
                stability_ratio = p_revolution / p_acquiescence
            else:
                # If P(S|A) = 0, the client state is in crisis
                stability_ratio = 1.0 if p_revolution > 0 else 0.0

            if stability_ratio < subsidy_trigger_threshold:
                # Client state is stable, no subsidy needed
                continue

            # Calculate subsidy amount from POOL INCOME, not accumulated wealth
            # BUG FIX: Like wages, subsidies should come from extracted surplus
            tribute_inflow = tick_context.get("tribute_inflow", 0.0)
            max_subsidy = min(subsidy_cap, tribute_inflow * subsidy_conversion_rate)
            # Also cap at what bourgeoisie can actually afford
            max_subsidy = min(max_subsidy, source_wealth)

            # Sprint 3.4.4: Also cap at available pool
            available_pool = tick_context["current_pool"]
            max_subsidy = min(max_subsidy, available_pool)

            if max_subsidy <= services.defines.economy.negligible_subsidy:
                # Negligible subsidy
                continue

            # Apply subsidy: wealth converts to repression capacity
            # Source loses wealth
            graph.nodes[source_id]["wealth"] = source_wealth - max_subsidy

            # Target gains repression capacity (NOT wealth)
            # Wealth converts at the subsidy_conversion_rate
            repression_boost = max_subsidy * subsidy_conversion_rate
            new_repression = min(1.0, target_repression + repression_boost)
            graph.nodes[target_id]["repression_faced"] = new_repression

            # Record subsidy in edge
            graph.edges[source_id, target_id]["value_flow"] = max_subsidy

            # Sprint 3.4.4: Track subsidy as pool outflow
            tick_context["subsidy_outflow"] += max_subsidy
            tick_context["current_pool"] -= max_subsidy

            # Emit event for AI narrative layer
            tick = context.get("tick", 0)
            services.event_bus.publish(
                Event(
                    type=EventType.IMPERIAL_SUBSIDY,
                    tick=tick,
                    payload={
                        "source_id": source_id,
                        "target_id": target_id,
                        "amount": max_subsidy,
                        "repression_boost": repression_boost,
                        "mechanism": "client_state_subsidy",
                        "stability_ratio": stability_ratio,
                    },
                )
            )

    def _process_decision_phase(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
        tick_context: dict[str, Any],
        initial_pool: float,
    ) -> None:
        """Phase 5: Bourgeoisie decision heuristics (Sprint 3.4.4).

        Based on pool_ratio and aggregate_tension, the bourgeoisie chooses:
        - BRIBERY: Increase wages (when prosperous and tension low)
        - AUSTERITY: Decrease wages (when pool low and tension manageable)
        - IRON_FIST: Increase repression (when pool low and tension high)
        - CRISIS: Both wage cuts and repression spike (when pool critical)
        - NO_CHANGE: Maintain status quo (neutral zone)

        This phase updates tick_context with new wage_rate and repression_level
        for the NEXT tick. It also emits ECONOMIC_CRISIS event if triggered.
        """
        # Get decision formula
        calculate_decision = services.formulas.get("bourgeoisie_decision")

        # Calculate pool ratio
        current_pool = tick_context["current_pool"]
        pool_ratio = current_pool / initial_pool if initial_pool > 0 else 0.0

        # Calculate aggregate tension from class relationships
        aggregate_tension = self._calculate_aggregate_tension(graph)

        # Get thresholds from defines
        high_threshold = services.defines.economy.pool_high_threshold
        low_threshold = services.defines.economy.pool_low_threshold
        critical_threshold = services.defines.economy.pool_critical_threshold

        # Call decision formula
        decision, wage_delta, repression_delta = calculate_decision(
            pool_ratio=pool_ratio,
            aggregate_tension=aggregate_tension,
            high_threshold=high_threshold,
            low_threshold=low_threshold,
            critical_threshold=critical_threshold,
        )

        # Apply deltas to tick_context (will be saved to economy)
        current_wage_rate = tick_context["wage_rate"]
        current_repression = tick_context["repression_level"]

        # Clamp new values within bounds
        min_wage = services.defines.economy.min_wage_rate
        max_wage = services.defines.economy.max_wage_rate
        new_wage_rate = max(min_wage, min(max_wage, current_wage_rate + wage_delta))
        new_repression = max(0.0, min(1.0, current_repression + repression_delta))

        tick_context["wage_rate"] = new_wage_rate
        tick_context["repression_level"] = new_repression

        # Emit ECONOMIC_CRISIS event if decision is CRISIS
        if decision == BourgeoisieDecision.CRISIS:
            tick = context.get("tick", 0)
            services.event_bus.publish(
                Event(
                    type=EventType.ECONOMIC_CRISIS,
                    tick=tick,
                    payload={
                        "pool_ratio": pool_ratio,
                        "aggregate_tension": aggregate_tension,
                        "decision": decision,
                        "wage_delta": wage_delta,
                        "repression_delta": repression_delta,
                        "new_wage_rate": new_wage_rate,
                        "new_repression_level": new_repression,
                        "current_pool": current_pool,
                    },
                )
            )

    def _calculate_aggregate_tension(self, graph: nx.DiGraph[str]) -> float:
        """Calculate aggregate tension across class relationships.

        Returns the average tension value across all edges in the graph.
        Tension ranges from 0 (peaceful) to 1 (revolutionary).

        Args:
            graph: The simulation graph

        Returns:
            Average tension, or 0.0 if no edges have tension values
        """
        tensions = []
        for _, _, data in graph.edges(data=True):
            tension = data.get("tension", 0.0)
            if isinstance(tension, int | float):
                tensions.append(float(tension))

        if not tensions:
            return 0.0

        return sum(tensions) / len(tensions)

    def _load_economy(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
    ) -> GlobalEconomy:
        """Load GlobalEconomy from graph metadata, or create default.

        Args:
            graph: The simulation graph
            services: ServiceContainer for config access

        Returns:
            GlobalEconomy instance
        """
        economy_data = graph.graph.get("economy")
        if economy_data is not None:
            return GlobalEconomy.model_validate(economy_data)

        # Create default economy from defines
        return GlobalEconomy(
            imperial_rent_pool=services.defines.economy.initial_rent_pool,
            current_super_wage_rate=services.defines.economy.super_wage_rate,
            current_repression_level=services.defines.survival.default_repression,
        )

    def _save_economy(
        self,
        graph: nx.DiGraph[str],
        tick_context: dict[str, Any],
    ) -> None:
        """Save updated GlobalEconomy back to graph metadata.

        Args:
            graph: The simulation graph
            tick_context: Dictionary with current_pool, wage_rate, repression_level
        """
        economy = GlobalEconomy(
            imperial_rent_pool=max(0.0, tick_context["current_pool"]),
            current_super_wage_rate=tick_context["wage_rate"],
            current_repression_level=tick_context["repression_level"],
        )
        graph.graph["economy"] = economy.model_dump()
