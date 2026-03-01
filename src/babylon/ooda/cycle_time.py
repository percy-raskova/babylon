"""Cycle time computation for OODA profiles (Feature 032).

Implements the four-phase additive model:
cycle_time = observe + orient + decide + act

See Also:
    ``specs/032-ooda-loop-system/contracts/ooda-profile-contract.md``
"""

from __future__ import annotations

from babylon.config.defines import OODADefines
from babylon.models.enums import DecisionMode
from babylon.ooda.types import OODAProfile

_ORIENT_FLOOR = 0.1  # Minimum orient phase duration


def compute_cycle_time(profile: OODAProfile, defines: OODADefines) -> float:
    """Compute total OODA cycle time from a profile and defines.

    Args:
        profile: Organization's OODA profile.
        defines: OODADefines coefficients.

    Returns:
        Total cycle time (always > 0).
    """
    observe_time = defines.base_observe_time + profile.sensor_latency * defines.latency_weight

    orient_raw = defines.base_orient_time * (
        1.0 - profile.ideological_coherence * defines.coherence_weight
    )
    orient_time = max(orient_raw, _ORIENT_FLOOR)

    decision_base = _decision_mode_base(profile.decision_mode, defines)
    decide_time = decision_base * (1.0 + profile.bureaucratic_depth * defines.depth_weight)

    act_time = defines.base_act_time

    return observe_time + orient_time + decide_time + act_time


def _decision_mode_base(mode: DecisionMode, defines: OODADefines) -> float:
    """Look up decision mode base time from defines.

    Args:
        mode: Decision mode enum value.
        defines: OODADefines with decision mode base times.

    Returns:
        Base time for the decision mode.
    """
    mode_map: dict[DecisionMode, float] = {
        DecisionMode.AUTOCRATIC: defines.decision_mode_base_autocratic,
        DecisionMode.DELEGATE: defines.decision_mode_base_delegate,
        DecisionMode.DEMOCRATIC: defines.decision_mode_base_democratic,
        DecisionMode.CONSENSUS: defines.decision_mode_base_consensus,
    }
    return mode_map[mode]


__all__ = ["compute_cycle_time"]
