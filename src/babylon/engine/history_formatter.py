"""History formatter for generating narrative summaries.

This module provides functions to format simulation history
as human-readable narratives describing the class struggle dynamics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.engine.simulation import Simulation


def format_class_struggle_history(simulation: Simulation) -> str:
    """Format simulation history as a narrative of class struggle.

    Generates a human-readable summary of the simulation history,
    highlighting wealth transfers, ideological changes, and
    tension accumulation.

    Args:
        simulation: A Simulation instance with history data

    Returns:
        A formatted string narrative describing the class struggle dynamics.

    Example:
        >>> sim = Simulation(initial_state, config)
        >>> sim.run(100)
        >>> print(format_class_struggle_history(sim))
        # History of Class Struggle
        ...
    """
    history = simulation.get_history()

    if len(history) < 2:
        return "# History of Class Struggle\n\nNo simulation data available."

    initial_state = history[0]
    final_state = history[-1]

    # Build narrative
    lines: list[str] = [
        "# History of Class Struggle",
        "",
        f"## Simulation Summary (Tick 0 to Tick {final_state.tick})",
        "",
    ]

    # Entity summaries
    lines.append("### Economic Dynamics")
    lines.append("")

    for entity_id, initial_entity in initial_state.entities.items():
        if entity_id not in final_state.entities:
            continue

        final_entity = final_state.entities[entity_id]
        wealth_change = final_entity.wealth - initial_entity.wealth

        if wealth_change > 0:
            change_desc = f"gained {wealth_change:.4f}"
            direction = "accumulated wealth through extraction"
        elif wealth_change < 0:
            change_desc = f"lost {abs(wealth_change):.4f}"
            direction = "suffered value extraction"
        else:
            change_desc = "unchanged"
            direction = "maintained economic position"

        lines.append(f"**{final_entity.name}** ({entity_id}):")
        lines.append(
            f"  - Wealth: {initial_entity.wealth:.4f} -> {final_entity.wealth:.4f} ({change_desc})"
        )
        lines.append(f"  - The {final_entity.name} {direction}.")
        lines.append("")

    # Ideological changes (Sprint 3.4.3: Updated for IdeologicalProfile)
    lines.append("### Consciousness Drift")
    lines.append("")

    for entity_id, initial_entity in initial_state.entities.items():
        if entity_id not in final_state.entities:
            continue

        final_entity = final_state.entities[entity_id]

        # Get class_consciousness from IdeologicalProfile
        initial_consciousness = initial_entity.ideology.class_consciousness
        final_consciousness = final_entity.ideology.class_consciousness
        consciousness_change = final_consciousness - initial_consciousness

        if consciousness_change > 0.1:
            direction = "developed revolutionary consciousness"
        elif consciousness_change < -0.1:
            direction = "drifted toward reaction"
        else:
            direction = "maintained ideological position"

        lines.append(f"**{final_entity.name}**:")
        lines.append(
            f"  - Class Consciousness: {initial_consciousness:.4f} -> {final_consciousness:.4f}"
        )
        lines.append(
            f"  - National Identity: {initial_entity.ideology.national_identity:.4f} -> {final_entity.ideology.national_identity:.4f}"
        )
        lines.append(f"  - {final_entity.name} {direction}.")
        lines.append("")

    # Tension on relationships
    if initial_state.relationships and final_state.relationships:
        lines.append("### Contradiction Tension")
        lines.append("")

        for i, (initial_rel, final_rel) in enumerate(
            zip(initial_state.relationships, final_state.relationships, strict=False)
        ):
            if i >= len(final_state.relationships):
                break

            tension_change = final_rel.tension - initial_rel.tension
            if tension_change > 0.1:
                tension_desc = "significant tension accumulation"
            elif tension_change > 0:
                tension_desc = "gradual tension buildup"
            else:
                tension_desc = "stable tension levels"

            lines.append(
                f"**{initial_rel.source_id} -> {initial_rel.target_id}** ({initial_rel.edge_type.value}):"
            )
            lines.append(f"  - Tension: {initial_rel.tension:.4f} -> {final_rel.tension:.4f}")
            lines.append(f"  - {tension_desc.capitalize()}")
            lines.append(f"  - Imperial rent extraction: {final_rel.value_flow:.4f}")
            lines.append("")

    # Summary
    lines.append("### Period Summary")
    lines.append("")
    lines.append(f"Over {final_state.tick} turns, the simulation demonstrated the material basis")
    lines.append("of class struggle through wealth transfer dynamics.")
    lines.append("")

    return "\n".join(lines)
