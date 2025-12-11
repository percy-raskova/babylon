"""Babylon - The Fall of America

Entry point for the Babylon simulation engine.
Uses the Phase 2 Engine Facade for simulation execution.
"""

from __future__ import annotations

import logging
import sys

from babylon.config.logging_config import setup_logging
from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation

# Initialize logging using the centralized configuration
# This is the single entry point for all logging setup
setup_logging()

logger = logging.getLogger(__name__)


def get_tension(sim: Simulation) -> float:
    """Get tension from the first relationship (exploitation edge)."""
    relationships = sim.current_state.relationships
    if relationships:
        return relationships[0].tension
    return 0.0


def main() -> None:
    """Run a single simulation step using the Phase 2 Engine Facade."""
    logger.info("Babylon - The Fall of America")
    logger.info("Initializing simulation...")

    # Create the two-node scenario (Worker vs Owner)
    initial_state, config, _defines = create_two_node_scenario()

    # Initialize simulation facade
    sim = Simulation(initial_state=initial_state, config=config)

    logger.info("Initial state: tick=%d", sim.current_state.tick)
    logger.info("Initial tension: %.4f", get_tension(sim))

    # Display initial entity states
    for entity_id, entity in sim.current_state.entities.items():
        logger.info("  %s (%s): wealth=%.2f", entity.name, entity_id, entity.wealth)

    # Run one simulation step
    logger.info("Running simulation step...")
    sim.step()

    logger.info("After step: tick=%d", sim.current_state.tick)
    logger.info("Tension: %.4f", get_tension(sim))

    # Display updated entity states
    for entity_id, entity in sim.current_state.entities.items():
        logger.info("  %s (%s): wealth=%.2f", entity.name, entity_id, entity.wealth)

    logger.info("Simulation step complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Simulation terminated by user")
        sys.exit(0)
    except Exception:
        logger.critical("Unexpected error occurred", exc_info=True)
        sys.exit(1)
