"""The Party Congress — Unit 5 of the DoctrineSystem (ADR073).

Owner slate ruling 5 ("Party Congress → seeded-RNG weighted by tag deltas")
as sharpened by the history-sweep ruling DT-5
(``project/research/history-sweep/addendum-dt-rulings.md``): the purge of an
opposed element routes through a **weighted seeded-RNG draw** —
``P(purge_succeeds) = f(tag_vector_delta)`` — where sustained tag growth
since the last congress biases the odds (Yugoslavia 1948), but the
probability is clamped inside ``[floor, 1-floor]`` so a contingent term
stays live at any delta (Lushan 1959, Gang of Four 1976: the decisive
information was never part of any observable state).

Everything here is PURE: the roll is injected by the caller
(:mod:`babylon.engine.systems.doctrine` draws it from the seed-deterministic
tick RNG, Constitution III.7); same inputs, same congress. Trap escape is
``self_criticism`` at ``trap_escape_tl`` (slate ruling 6) — the theoretical
labor is spent on the ATTEMPT, success or not, because the congress itself
is an opportunity-cost draw on cadre time (program proposal), and a failed
rectification still consumed the struggle.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from babylon.config.defines.doctrine import DoctrineDefines
from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.enums.doctrine import DoctrineTag

__all__ = [
    "CongressResult",
    "held_sprung_traps",
    "purge_probability",
    "run_congress",
    "tag_delta_score",
]


class CongressResult(BaseModel):
    """Outcome of one Party Congress for one organization (pure data)."""

    model_config = ConfigDict(frozen=True)

    acquired: tuple[str, ...] = Field(description="Post-congress acquired node ids.")
    theoretical_labor: float = Field(ge=0.0, description="Post-congress TL balance.")
    doctrine_tags: dict[DoctrineTag, float] = Field(description="Post-congress tag accumulator.")
    snapshot: dict[DoctrineTag, float] = Field(
        description="The new tag snapshot — next congress's delta baseline."
    )
    attempted_trap_id: str | None = Field(
        default=None, description="The trap whose purge was attempted, if any."
    )
    escaped: bool = Field(default=False, description="Whether the purge succeeded.")


def held_sprung_traps(tree: DoctrineTree, acquired: tuple[str, ...]) -> tuple[str, ...]:
    """Trap nodes the organization has fallen into, id-sorted (deterministic)."""
    held = set(acquired)
    return tuple(
        sorted(node.id for node in tree.nodes.values() if node.is_trap and node.id in held)
    )


def tag_delta_score(
    current: Mapping[DoctrineTag, float], snapshot: Mapping[DoctrineTag, float]
) -> float:
    """Net tag-vector movement since the last congress (missing keys = 0)."""
    keys = set(current) | set(snapshot)
    return sum(float(current.get(k, 0.0)) - float(snapshot.get(k, 0.0)) for k in keys)


def purge_probability(delta_score: float, defines: DoctrineDefines) -> float:
    """``P(purge_succeeds)`` per DT-5: linear delta bias, clamped contingency.

    ``0.5 + weight·delta`` clamped to ``[floor, 1-floor]`` — even odds at zero
    delta, never certainty in either direction.
    """
    floor = defines.congress_contingency_floor
    raw = 0.5 + defines.congress_delta_weight * delta_score
    return min(max(raw, floor), 1.0 - floor)


def run_congress(
    *,
    acquired: tuple[str, ...],
    theoretical_labor: float,
    tags: Mapping[DoctrineTag, float],
    snapshot: Mapping[DoctrineTag, float],
    tree: DoctrineTree,
    defines: DoctrineDefines,
    roll: float,
) -> CongressResult:
    """Convene one Party Congress (pure; the roll is injected).

    At most ONE purge is attempted per congress — the first held trap by node
    id (a congress has one principal struggle). The attempt requires
    ``theoretical_labor >= trap_escape_tl`` and spends it win or lose; success
    (``roll < P``) removes the trap and reverses its tag contribution. Every
    congress — attempt or not — re-baselines the tag snapshot: the congress
    sums up the period.
    """
    current_tags = {k: float(v) for k, v in tags.items()}
    traps = held_sprung_traps(tree, acquired)
    affordable = theoretical_labor >= float(defines.trap_escape_tl)

    if not traps or not affordable:
        return CongressResult(
            acquired=acquired,
            theoretical_labor=theoretical_labor,
            doctrine_tags=current_tags,
            snapshot=dict(current_tags),
        )

    trap_id = traps[0]
    trap = tree.nodes[trap_id]
    tl_after = theoretical_labor - float(defines.trap_escape_tl)
    probability = purge_probability(tag_delta_score(current_tags, snapshot), defines)

    if roll < probability:
        new_acquired = tuple(node_id for node_id in acquired if node_id != trap_id)
        new_tags = dict(current_tags)
        for tag, delta in trap.tag_deltas.items():
            new_tags[tag] = new_tags.get(tag, 0.0) - float(delta)
        return CongressResult(
            acquired=new_acquired,
            theoretical_labor=tl_after,
            doctrine_tags=new_tags,
            snapshot=dict(new_tags),
            attempted_trap_id=trap_id,
            escaped=True,
        )

    return CongressResult(
        acquired=acquired,
        theoretical_labor=tl_after,
        doctrine_tags=current_tags,
        snapshot=dict(current_tags),
        attempted_trap_id=trap_id,
        escaped=False,
    )
