"""Doctrine Tree mechanic coefficients — the DoctrineSystem tunables.

Source: the six owner-ratified DT rulings (2026-07-15). Program doc:
``project/research/doctrine-tree-program-proposal.md``. The read-only tree data
(3 trunks / 3 tags / 11 MVP nodes) and its DAG validator + ``compute_tags`` live
in :mod:`babylon.domain.doctrine`; this category supplies the coefficients the
*mechanic* layer (acquisition, trap-firing, theoretical-labor economy, Party
Congress) reads — every value overridable via ``defines.yaml`` like all others
(Constitution "never hardcode a coefficient").

Ruling → field:

1. Scope = full, phased — a build-scope decision, not a coefficient.
2. Faction-flip = yes, Phase 2 → :attr:`faction_flip_enabled` (default ``False``:
   the ideology→faction-allegiance pathway stays OFF until Phase 2).
3. Tag decay = 0.55 %/tick → :attr:`tag_decay_rate`.
4. Study allocation = 0.15–0.25 → :attr:`study_allocation_min` /
   :attr:`study_allocation_max` (fraction of an org's material surplus routed to
   theoretical labour each tick; the org's OODA picks within the band).
5. Party Congress = seeded-RNG weighted by tag deltas → :attr:`congress_interval_ticks`
   (cadence; the seeded weighting itself is engine logic, Constitution III.7).
6. Trap-escape = self-criticism @ 300 TL → :attr:`trap_escape_tl`.

Re-exported via :mod:`babylon.config.defines.__init__`; composed into
:class:`babylon.config.defines.GameDefines` in
:mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DoctrineDefines(BaseModel):
    """Tunable coefficients for the DoctrineSystem (owner-ratified 2026-07-15).

    All defaults are the ratified-slate values; ranges are enforced so a mod that
    drives a coefficient out of its meaningful domain fails loudly at load rather
    than silently mis-simulating.
    """

    model_config = ConfigDict(frozen=True)

    tag_decay_rate: float = Field(
        default=0.0055,
        ge=0.0,
        le=1.0,
        description="Ruling 3: per-tick multiplicative decay of accumulated doctrine tag strength (0.55%/tick).",
    )
    study_allocation_min: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Ruling 4: lower bound of the surplus fraction an org may route to theoretical labour each tick.",
    )
    study_allocation_max: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Ruling 4: upper bound of the surplus fraction an org may route to theoretical labour each tick.",
    )
    congress_interval_ticks: int = Field(
        default=52,
        ge=1,
        description="Ruling 5: ticks between Party Congress events (seeded-RNG resolution weighted by tag deltas).",
    )
    trap_escape_tl: int = Field(
        default=300,
        ge=0,
        description="Ruling 6: theoretical-labour cost of self-criticism to escape an ideological trap node.",
    )
    faction_flip_enabled: bool = Field(
        default=False,
        description="Ruling 2: whether acquiring a node may flip a faction's allegiance/behaviour. OFF until Phase 2.",
    )
    congress_delta_weight: float = Field(
        default=0.15,
        ge=0.0,
        description="Ruling 5 / DT-5: linear weight of the tag-vector delta since the last congress on the purge-success probability (Yugoslavia-1948 pattern — sustained material divergence predicts direction).",
    )
    congress_contingency_floor: float = Field(
        default=0.10,
        gt=0.0,
        lt=0.5,
        description="Ruling 5 / DT-5: purge-success probability is clamped to [floor, 1-floor] — a nonzero contingent term stays live at ANY delta (Lushan 1959 / Gang of Four 1976: the decisive information was never in the observable state).",
    )
    theory_bonus_per_class_analysis: float = Field(
        default=0.02,
        ge=0.0,
        description="Unit 6b feedback: per-point CLASS_ANALYSIS multiplier on an org's consciousness-raising delta (corpus: 'High: correct prioritization, theory bonus'); tag capped at 10 => max +20% at default.",
    )
    mass_work_solidarity_gain: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Unit 6b write side (ADR087): base org->class SOLIDARITY solidarity_strength gain per mass-work verb dispatch (EDUCATE/PROPAGANDIZE/PROVIDE_SERVICE targeting a social_class), before MASS_LINK amplification.",
    )
    mass_link_weight: float = Field(
        default=0.1,
        ge=0.0,
        description="Unit 6b write side (ADR087): multiplier on the org's MASS_LINK tag (range [0, 10]) amplifying mass_work_solidarity_gain -- gain = base * (1 + weight * mass_link); at the default weight and MASS_LINK's ceiling (10) the gain doubles.",
    )
    mass_work_solidarity_decay_rate: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Unit 6b write side (ADR087): per-tick multiplicative decay of org-sourced SOLIDARITY edges' solidarity_strength -- a mass link not renewed by work withers (floored at 0). Faster than tag_decay_rate (0.55%/tick): an edge is a concrete organizing relationship, not accumulated theory, and lapses sooner without renewal.",
    )


__all__ = ["DoctrineDefines"]
