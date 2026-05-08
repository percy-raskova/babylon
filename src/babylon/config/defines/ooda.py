"""OODA loop coefficients (Feature 032 — Observe/Orient/Decide/Act).

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from babylon.config.defines._assembler import GameDefines


class OODADefines(BaseModel):
    """OODA Loop System tunable coefficients (Feature 032).

    Controls cycle time computation, initiative scoring, action costs,
    consciousness effect multipliers, and propagation parameters.

    See Also:
        ``specs/032-ooda-loop-system/data-model.md``: Full specification.
    """

    model_config = ConfigDict(frozen=True)

    # --- Cycle time weights (OODA profile contract) ---
    base_observe_time: float = Field(
        default=1.0,
        gt=0,
        description="Base Observe phase duration.",
    )
    latency_weight: float = Field(
        default=0.5,
        ge=0,
        description="Weight of sensor_latency on Observe phase.",
    )
    base_orient_time: float = Field(
        default=2.0,
        gt=0,
        description="Base Orient phase duration.",
    )
    coherence_weight: float = Field(
        default=0.6,
        ge=0,
        le=1.0,
        description="Weight of ideological_coherence on Orient phase.",
    )
    base_act_time: float = Field(
        default=1.0,
        gt=0,
        description="Base Act phase duration (fixed).",
    )
    coord_weight: float = Field(
        default=0.3,
        ge=0,
        description="Weight of coordination on Act phase (reserved).",
    )
    depth_weight: float = Field(
        default=0.4,
        ge=0,
        description="Weight of bureaucratic_depth on Decide phase.",
    )

    # --- Decision mode base times ---
    decision_mode_base_autocratic: float = Field(
        default=1.0,
        gt=0,
        description="[C] 1 cycle: single decision-maker (COIN operational tempo).",
    )
    decision_mode_base_delegate: float = Field(
        default=2.0,
        gt=0,
        description="[C] 2 cycles: FM 3-24 mission command delegation.",
    )
    decision_mode_base_democratic: float = Field(
        default=3.0,
        gt=0,
        description="[C] 3 cycles: majority vote (ProleWiki democratic centralism).",
    )
    decision_mode_base_consensus: float = Field(
        default=5.0,
        gt=0,
        description="[C] 5 cycles: full agreement, mass line process (ProleWiki).",
    )

    # --- Initiative scoring weights ---
    initiative_weight_speed: float = Field(
        default=2.0,
        ge=0,
        description="[C] Boyd's central insight: tempo is decisive factor (RAND decomposition).",
    )
    initiative_weight_institutional: float = Field(
        default=1.0,
        ge=0,
        description="[C] Baseline: institutional power is important but static (RAND).",
    )
    initiative_weight_counterintel: float = Field(
        default=1.5,
        ge=0,
        description="[C] 1.5× institutional: degrades adversary Observe phase (Sparrow).",
    )
    initiative_weight_embeddedness: float = Field(
        default=1.0,
        ge=0,
        description="[C] = institutional: community roots compensate for state advantage (RAND).",
    )
    initiative_weight_momentum: float = Field(
        default=0.5,
        ge=0,
        description="[C] 0.5× baseline: volatile, decays 20%/tick (RAND).",
    )

    # --- Institutional bonus by jurisdiction ---
    institutional_bonus_federal: float = Field(
        default=5.0,
        ge=0,
        description="[C] 5×: COIN force density ratio, federal apparatus (FM 3-24).",
    )
    institutional_bonus_state: float = Field(
        default=3.0,
        ge=0,
        description="[C] 3×: state police force ratio, 60% federal effectiveness (RAND).",
    )
    institutional_bonus_local: float = Field(
        default=1.5,
        ge=0,
        description="[C] 1.5×: local PD baseline + Galula administrative presence premium.",
    )
    institutional_bonus_nonstate: float = Field(
        default=0.0,
        ge=0,
        description="Initiative bonus for non-state organizations.",
    )

    # --- Momentum ---
    momentum_decay: float = Field(
        default=0.8,
        ge=0,
        lt=1.0,
        description="= 1 - 2λ: momentum twice as volatile as consciousness (mass line analysis).",
    )
    momentum_success_bonus: float = Field(
        default=0.2,
        ge=0,
        description="[A] = struggle.solidarity_gain_per_uprising: organizational analog of solidarity gain.",
    )

    # --- Action cost modifiers ---
    embeddedness_discount: float = Field(
        default=0.5,
        ge=0,
        le=1.0,
        description="[B] = solidarity.scaling_factor: community roots discount action costs at solidarity scale.",
    )
    contradiction_cost_multiplier: float = Field(
        default=2.5,
        gt=1.0,
        description="[C] ≈ √4.2: geometric mean of Black/white incarceration disparity (MIM Prisons).",
    )
    outsider_cost_multiplier: float = Field(
        default=1.5,
        gt=1.0,
        description="[C] = territory.rent_spike_multiplier: Prebisch-Singer terms-of-trade penalty.",
    )
    min_cost_modifier: float = Field(
        default=0.5,
        gt=0,
        le=1.0,
        description="Floor cost modifier for embedded orgs.",
    )

    # --- Consciousness effect limits ---
    max_ci_delta_per_tick: float = Field(
        default=0.05,
        gt=0,
        le=1.0,
        description="[B] = λ/2: half the decay rate prevents single actions from overwhelming the ODE.",
    )

    # --- Action base consciousness multipliers ---
    action_base_educate: float = Field(
        default=1.2,
        ge=0,
        description="[B] = 1 + 2λ: overcomes decay plus net positive effect.",
    )
    action_base_agitate: float = Field(
        default=0.0,
        ge=0,
        description="Consciousness multiplier for AGITATE (zero = no CI effect).",
    )
    action_base_provide_service: float = Field(
        default=0.6,
        ge=0,
        description="[B] = k + routing_scale = 0.5 + 0.1: material sensitivity + routing (BPP survival programs).",
    )
    action_base_recruit: float = Field(
        default=0.3,
        ge=0,
        description="[B] = solidarity.activation_threshold: bring recruits to percolation threshold.",
    )
    action_base_organize: float = Field(
        default=0.5,
        ge=0,
        description="[B] = consciousness.sensitivity: organizing operationalizes material sensitivity k.",
    )
    action_base_propagandize: float = Field(
        default=0.8,
        ge=0,
        description="[B] = 1 - 2λ: symmetric inverse of EDUCATE (less precise than education).",
    )
    action_base_repress: float = Field(
        default=0.8,
        ge=0,
        description="[B] = α (extraction_efficiency): repression backfire proportional to extraction visibility.",
    )
    action_base_surveil: float = Field(
        default=0.2,
        ge=0,
        description="[B] = 1 - α: surveillance backfire is complement of extraction (invisible fraction).",
    )
    action_base_assimilate: float = Field(
        default=1.0,
        ge=0,
        description="Negative CI multiplier for ASSIMILATE.",
    )

    # --- Autonomy tradeoff ---
    autonomy_effectiveness_scale: float = Field(
        default=0.5,
        ge=0,
        le=1.0,
        description="[C] 0.5: democratic centralism tradeoff (ProleWiki). Vanguard = 2× coordinated impact.",
    )

    # --- Agitation -> contestation ---
    agitation_contestation_delta: float = Field(
        default=0.1,
        ge=0,
        le=1.0,
        description="[A] = consciousness.agitation_decay_rate: equilibrium requires continuous agitation.",
    )
    agitation_educate_bonus: float = Field(
        default=1.5,
        ge=1.0,
        description="[B] = territory.rent_spike_multiplier: crisis amplification factor (same as eviction premium).",
    )
    contestation_threshold: float = Field(
        default=0.3,
        ge=0,
        le=1.0,
        description="[B] = solidarity.activation_threshold: same tipping point for political engagement.",
    )

    # --- Lifecycle modifiers ---
    elder_legitimacy_multiplier: float = Field(
        default=1.3,
        ge=1.0,
        description="[C] = 1 + lifecycle.ideology_institutional_weight: elder institutional moral authority.",
    )

    # --- Counter-intelligence ---
    counter_intel_increment: float = Field(
        default=0.1,
        ge=0,
        le=1.0,
        description="[C] = λ: network disruption rate matches consciousness entropy (Sparrow).",
    )

    # --- Base action point costs ---
    base_cost_recruit: int = Field(default=2, ge=1, description="AP cost: RECRUIT")
    base_cost_organize: int = Field(default=2, ge=1, description="AP cost: ORGANIZE")
    base_cost_educate: int = Field(default=1, ge=1, description="AP cost: EDUCATE")
    base_cost_agitate: int = Field(default=1, ge=1, description="AP cost: AGITATE")
    base_cost_propagandize: int = Field(default=2, ge=1, description="AP cost: PROPAGANDIZE")
    base_cost_fundraise: int = Field(default=1, ge=1, description="AP cost: FUNDRAISE")
    base_cost_provide_service: int = Field(default=2, ge=1, description="AP cost: PROVIDE_SERVICE")
    base_cost_employ: int = Field(default=1, ge=1, description="AP cost: EMPLOY")
    base_cost_repress: int = Field(default=2, ge=1, description="AP cost: REPRESS")
    base_cost_protest: int = Field(default=2, ge=1, description="AP cost: PROTEST")
    base_cost_strike: int = Field(default=3, ge=1, description="AP cost: STRIKE")
    base_cost_expropriate: int = Field(default=3, ge=1, description="AP cost: EXPROPRIATE")
    base_cost_surveil: int = Field(default=1, ge=1, description="AP cost: SURVEIL")
    base_cost_infiltrate: int = Field(default=3, ge=1, description="AP cost: INFILTRATE")
    base_cost_counter_intel: int = Field(default=2, ge=1, description="AP cost: COUNTER_INTEL")
    base_cost_map_network: int = Field(default=1, ge=1, description="AP cost: MAP_NETWORK")
    base_cost_propose_alliance: int = Field(
        default=1, ge=1, description="AP cost: PROPOSE_ALLIANCE"
    )
    base_cost_denounce: int = Field(default=1, ge=1, description="AP cost: DENOUNCE")
    base_cost_build_infrastructure: int = Field(
        default=3, ge=1, description="AP cost: BUILD_INFRASTRUCTURE"
    )
    base_cost_attack_infrastructure: int = Field(
        default=2, ge=1, description="AP cost: ATTACK_INFRASTRUCTURE"
    )
    base_cost_assimilate: int = Field(default=2, ge=1, description="AP cost: ASSIMILATE")

    # --- Layer 3 propagation coefficients ---
    repress_heat_delta: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="[A] = territory.high_profile_heat_gain: repression IS high-profile attention.",
    )
    surveil_heat_delta: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="[A] = territory.heat_spillover_rate: passive surveillance = background state attention.",
    )
    build_infrastructure_delta: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Infrastructure increase per BUILD action"
    )
    attack_infrastructure_delta: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Infrastructure decrease per ATTACK action"
    )
    orient_time_floor: float = Field(
        default=0.1, ge=0.0, description="Minimum orient phase duration"
    )

    def validate_derivations(self, game_defines: GameDefines) -> list[str]:
        """Cross-validate OODA coefficients against source primitives.

        Checks that derived coefficients (Categories A and B) still match
        their source primitive formulas. Returns a list of drift warnings
        for any mismatches exceeding tolerance (0.001).

        Args:
            game_defines: Parent GameDefines providing source primitives.

        Returns:
            List of warning messages for any detected drift. Empty if clean.
        """
        c = game_defines.consciousness
        t = game_defines.territory
        e = game_defines.economy
        s = game_defines.solidarity
        st = game_defines.struggle
        lc = game_defines.lifecycle
        tol = 0.001
        drifts: list[str] = []

        checks: list[tuple[str, float, float]] = [
            # Category A: direct substitutions
            ("repress_heat_delta", self.repress_heat_delta, t.high_profile_heat_gain),
            ("surveil_heat_delta", self.surveil_heat_delta, t.heat_spillover_rate),
            (
                "momentum_success_bonus",
                self.momentum_success_bonus,
                st.solidarity_gain_per_uprising,
            ),
            (
                "agitation_contestation_delta",
                self.agitation_contestation_delta,
                c.agitation_decay_rate,
            ),
            # Category B: formula derivations
            ("momentum_decay", self.momentum_decay, 1 - 2 * c.agitation_decay_rate),
            ("max_ci_delta_per_tick", self.max_ci_delta_per_tick, c.decay_lambda / 2),
            ("action_base_educate", self.action_base_educate, 1 + 2 * c.decay_lambda),
            ("action_base_propagandize", self.action_base_propagandize, 1 - 2 * c.decay_lambda),
            ("action_base_repress", self.action_base_repress, e.extraction_efficiency),
            ("action_base_surveil", self.action_base_surveil, 1 - e.extraction_efficiency),
            (
                "action_base_provide_service",
                self.action_base_provide_service,
                c.sensitivity + c.routing_scale,
            ),
            ("action_base_organize", self.action_base_organize, c.sensitivity),
            ("action_base_recruit", self.action_base_recruit, s.activation_threshold),
            ("contestation_threshold", self.contestation_threshold, s.activation_threshold),
            ("agitation_educate_bonus", self.agitation_educate_bonus, t.rent_spike_multiplier),
            ("embeddedness_discount", self.embeddedness_discount, s.scaling_factor),
            # Category C: empirically grounded cross-references
            (
                "elder_legitimacy_multiplier",
                self.elder_legitimacy_multiplier,
                1 + lc.ideology_institutional_weight,
            ),
            ("counter_intel_increment", self.counter_intel_increment, c.decay_lambda),
            ("outsider_cost_multiplier", self.outsider_cost_multiplier, t.rent_spike_multiplier),
        ]

        for name, actual, expected in checks:
            if abs(actual - expected) > tol:
                msg = f"OODADefines.{name} drifted: actual={actual}, expected={expected}"
                drifts.append(msg)
                warnings.warn(msg, UserWarning, stacklevel=2)

        return drifts

    def get_base_cost(self, action_type: str) -> int:
        """Look up base AP cost for an action type.

        Args:
            action_type: ActionType value string.

        Returns:
            Base AP cost for the action.

        Raises:
            KeyError: If action_type is not recognized.
        """
        cost_map: dict[str, int] = {
            "recruit": self.base_cost_recruit,
            "organize": self.base_cost_organize,
            "educate": self.base_cost_educate,
            "agitate": self.base_cost_agitate,
            "propagandize": self.base_cost_propagandize,
            "fundraise": self.base_cost_fundraise,
            "provide_service": self.base_cost_provide_service,
            "employ": self.base_cost_employ,
            "repress": self.base_cost_repress,
            "protest": self.base_cost_protest,
            "strike": self.base_cost_strike,
            "expropriate": self.base_cost_expropriate,
            "surveil": self.base_cost_surveil,
            "infiltrate": self.base_cost_infiltrate,
            "counter_intel": self.base_cost_counter_intel,
            "map_network": self.base_cost_map_network,
            "propose_alliance": self.base_cost_propose_alliance,
            "denounce": self.base_cost_denounce,
            "build_infrastructure": self.base_cost_build_infrastructure,
            "attack_infrastructure": self.base_cost_attack_infrastructure,
            "assimilate": self.base_cost_assimilate,
        }
        if action_type not in cost_map:
            msg = f"Unknown action type: {action_type}"
            raise KeyError(msg)
        return cost_map[action_type]

    def get_action_base(self, action_type: str) -> float:
        """Look up consciousness base multiplier for an action type.

        Args:
            action_type: ActionType value string.

        Returns:
            Consciousness base multiplier (0.0 means no CI effect).
        """
        base_map: dict[str, float] = {
            "educate": self.action_base_educate,
            "agitate": self.action_base_agitate,
            "provide_service": self.action_base_provide_service,
            "recruit": self.action_base_recruit,
            "organize": self.action_base_organize,
            "propagandize": self.action_base_propagandize,
            "repress": self.action_base_repress,
            "surveil": self.action_base_surveil,
            "assimilate": self.action_base_assimilate,
        }
        return base_map.get(action_type, 0.0)


__all__ = [
    "OODADefines",
]
