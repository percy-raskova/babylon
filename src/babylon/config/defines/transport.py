"""Transport Substrate coefficients (spec-108, Constitution II.13/Amendment O).

Slice 1 (Program 26 U5e, ADR165 director rulings): corridor condition
decay/repair, the conductivity EMA, and the uniform territory-splash
magnitudes consumed by
:class:`~babylon.engine.systems.transport.TransportSystem` (position 9.5)
and :func:`babylon.ooda.layer3._propagate_infrastructure`'s uniform-splash
reconciliation (ADR165 Director ruling 4). ``enabled`` is the master gate --
program-11's own constraint: "defines-gated... default OFF -> baselines
byte-identical."

The damped realization-crisis coupling coefficient (spec-108 D4, ADR165
Director ruling 3) is homed in ``CapitalVolumeIIDefines`` instead, per the
Director's explicit ruling ("damped via a declared coefficient in
CapitalVolumeIIDefines -- commodity_overhang is a Vol II quantity") -- NOT
duplicated here.

The slime-mold ``INFORMAL``-edge minting threshold (tasks.md T5's original
``conductivity_informal_mint_threshold``/``conductivity_prune_threshold``
proposal) is deliberately absent: ADR165 item 2 rules "no autonomous
INFORMAL minting in slice 1" -- conductivity instead feeds
``demand_signal_threshold``, a DEMAND SIGNAL for the sovereign's OODA budget
evaluation (BUILD_INFRASTRUCTURE is the only mint/repair path).

Terrain traversal-cost fields (tasks.md T5's ``terrain_traversal_cost``/
``terrain_impassable_classes``) are also absent: they exist to feed the
min-cost-flow routing solver (T8), which this slice does not implement (no
solver exists in this codebase yet, and building one is a substantial,
separate unit of work per spec-108 research.md §4) -- adding unconsumed
routing coefficients now would be dead configuration.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TransportDefines(BaseModel):
    """Transport Substrate: corridor decay/repair and demand-signal coefficients.

    See Also:
        :mod:`babylon.domain.geography.corridor_mesh`: decay/splash/aggregation.
        :class:`babylon.engine.systems.transport.TransportSystem`: consumer.
        ``specs/108-transport-substrate/spec.md``: FR-108-3, FR-108-4, FR-108-5.
        ``ai/decisions/ADR165_p26_director_rulings_trade_slate.yaml``: items 1-5.
    """

    model_config = ConfigDict(frozen=True)

    enabled: bool = Field(
        default=False,
        description=(
            "SYNTHETIC: master gate for the transport substrate. False (the "
            "default) makes TransportSystem a full no-op -- byte-identical "
            "to pre-U5e ticks. Program-11's own constraint: "
            "'defines-gated... default OFF -> baselines byte-identical.'"
        ),
    )
    condition_decay_rate_per_tick: float = Field(
        default=0.01,
        gt=0.0,
        lt=1.0,
        description=(
            "SYNTHETIC: base per-tick condition decay applied to every "
            "corridor edge (neglect), calibrated (slice 2) against the HPMS "
            "pavement-condition distribution (US3). Passed to "
            "corridor_mesh.decay_all_links(). Bounded < 1.0: a rate >= 1.0 "
            "would zero condition in a single tick regardless of flux."
        ),
    )
    condition_decay_flux_coefficient: float = Field(
        default=0.02,
        gt=0.0,
        description=(
            "SYNTHETIC: additional per-tick decay proportional to a link's "
            "conductivity (flow volume proxy) -- 'degrades with use,' not "
            "just neglect (FR-108-4). Passed to corridor_mesh.decay_all_links()."
        ),
    )
    maintenance_condition_restore_rate: float = Field(
        default=0.15,
        gt=0.0,
        description=(
            "SYNTHETIC: condition restored per BUILD_INFRASTRUCTURE repair "
            "action (engine.actions.build.resolve_build's downstream "
            "layer-3 effect on the community-scoped `infrastructure` "
            "float, ooda/layer3.py's existing BUILD branch)."
        ),
    )
    construction_base_condition: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: starting condition for a newly BUILD_INFRASTRUCTURE- "
            "constructed corridor link (pristine)."
        ),
    )
    state_maintenance_budget_share: float = Field(
        default=0.05,
        gt=0.0,
        lt=1.0,
        description=(
            "SYNTHETIC: fraction of state budget spent as ambient 'faux "
            "frais of circulation' maintenance (US3), offsetting decay "
            "without a player action. Not yet consumed by a production "
            "call site in slice 1 (StateBudget wiring is a follow-up)."
        ),
    )
    conductivity_ema_alpha: float = Field(
        default=0.2,
        gt=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: alpha in the slime-mold conductivity EMA, "
            "D(t+1) = (1-alpha)*D + alpha*|Q| (FR-108-3 second bullet). "
            "Not yet consumed by a production flow-magnitude source in "
            "slice 1 (no min-cost-flow solver exists yet, T8) -- declared "
            "for the future per-tick |Q| update this coefficient governs."
        ),
    )
    demand_signal_threshold: float = Field(
        default=0.3,
        ge=0.0,
        description=(
            "SYNTHETIC: sustained-conductivity level above which "
            "TransportSystem raises `transport_demand_signal` on a "
            "territory -- feeding the sovereign's OODA budget evaluation "
            "(ADR165 item 2's design reframe). Deliberately NOT an "
            "INFORMAL-edge minting trigger: ADR165 item 2 rules out "
            "autonomous INFORMAL minting in slice 1 -- "
            "BUILD_INFRASTRUCTURE is the only mint/repair path."
        ),
    )
    attack_splash_condition_damage: float = Field(
        default=0.2,
        gt=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: uniform condition damage applied to EVERY corridor "
            "edge touching a territory when ATTACK_INFRASTRUCTURE resolves "
            "against it (ADR165 Director ruling 4 -- uniform territory "
            "splash, not edge-targeted). Consumed by "
            "ooda.layer3._propagate_infrastructure via "
            "corridor_mesh.apply_uniform_territory_splash()."
        ),
    )
    build_splash_condition_repair: float = Field(
        default=0.15,
        gt=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: uniform condition repair applied to EVERY corridor "
            "edge touching a territory when BUILD_INFRASTRUCTURE resolves "
            "against it -- the repair-direction counterpart of "
            "attack_splash_condition_damage, same uniform-splash seam."
        ),
    )


__all__ = ["TransportDefines"]
