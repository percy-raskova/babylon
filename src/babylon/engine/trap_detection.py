"""Trap detection system for the Wayne County Organizer.

Detects three ideological deviations that represent strategic dead ends
in revolutionary organizing. Each trap is grounded in historical analysis
of movement failure modes:

1. **Liberal Trap**: Over-reliance on electoralism and institutional reform.
   Signs: high budget, low cadre, high "negotiate" and "campaign" usage,
   organizations drift toward ClassCharacter.PETTY_BOURGEOIS.
   Historical examples: DSA electoral focus, co-optation by Democratic Party.

2. **Ultra-Left Trap**: Premature confrontation without mass base.
   Signs: high "attack" usage, low sympathizer labor, high heat,
   territory loss from state repression.
   Historical examples: Weather Underground, Red Army Faction.

3. **Rightist Trap**: Organizational conservatism, avoiding conflict.
   Signs: only "aid" and "educate" actions, no mobilization,
   stagnant consciousness, growing fascist consolidation.
   Historical examples: CPUSA during WWII popular front, NGO-ification.

Each trap triggers warnings at mild/moderate severity, and can trigger
endgame at severe level if uncorrected.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from babylon.models.types import Probability


class TrapType(StrEnum):
    """The three strategic deviation traps."""

    LIBERAL = "liberal"
    ULTRA_LEFT = "ultra_left"
    RIGHTIST = "rightist"


class TrapSeverity(StrEnum):
    """How deep into a trap the player has fallen."""

    NONE = "none"
    MILD = "mild"  # Warning — you're drifting
    MODERATE = "moderate"  # Alarm — course correct now
    SEVERE = "severe"  # Endgame trigger — too late


class TrapStatus(BaseModel):
    """Current trap detection state for a player organization.

    Attributes:
        trap_type: Which deviation is detected.
        severity: How deep the deviation is.
        score: Continuous score [0, 1] for this trap.
        indicators: Human-readable diagnostic strings.
        ticks_at_moderate: Consecutive ticks at MODERATE or above.
    """

    trap_type: TrapType
    severity: TrapSeverity = TrapSeverity.NONE
    score: Probability = Field(default=0.0)
    indicators: list[str] = Field(default_factory=list)
    ticks_at_moderate: int = Field(default=0, ge=0)


class TrapDetectionResult(BaseModel):
    """Full trap detection output for a single tick.

    Attributes:
        liberal: Liberal trap status.
        ultra_left: Ultra-left trap status.
        rightist: Rightist trap status.
        active_trap: The dominant trap (highest score), or None.
        game_over_trap: If any trap has reached SEVERE, this is set.
    """

    liberal: TrapStatus
    ultra_left: TrapStatus
    rightist: TrapStatus
    active_trap: TrapType | None = None
    game_over_trap: TrapType | None = None


# ---------------------------------------------------------------------------
# Trap detection logic
# ---------------------------------------------------------------------------

# Thresholds for severity levels
_MILD_THRESHOLD = 0.3
_MODERATE_THRESHOLD = 0.6
_SEVERE_THRESHOLD = 0.85
_TICKS_TO_SEVERE = 5  # Consecutive ticks at MODERATE before SEVERE


def _score_to_severity(score: float, ticks_at_moderate: int) -> TrapSeverity:
    """Convert a continuous score to a severity level."""
    if score >= _SEVERE_THRESHOLD or ticks_at_moderate >= _TICKS_TO_SEVERE:
        return TrapSeverity.SEVERE
    if score >= _MODERATE_THRESHOLD:
        return TrapSeverity.MODERATE
    if score >= _MILD_THRESHOLD:
        return TrapSeverity.MILD
    return TrapSeverity.NONE


def detect_liberal_trap(
    action_history: list[dict[str, Any]],
    org_budget: float,
    org_cadre: float,
    org_cohesion: float,
    consciousness_avg: float,
) -> TrapStatus:
    """Detect liberal deviation.

    Indicators:
    - High ratio of "negotiate" and "campaign" to total actions
    - High budget but low cadre (buying influence, not building power)
    - Stagnant consciousness despite activity

    Args:
        action_history: Recent action dicts with 'verb' keys.
        org_budget: Player org budget.
        org_cadre: Player org cadre_level.
        org_cohesion: Player org cohesion.
        consciousness_avg: Average consciousness across entities.
    """
    indicators: list[str] = []
    score = 0.0

    # Factor 1: Action mix — too many negotiation/campaign, not enough militant
    if action_history:
        liberal_verbs = {"negotiate", "campaign", "aid"}
        militant_verbs = {"mobilize", "attack", "educate"}
        total = len(action_history)
        liberal_count = sum(1 for a in action_history if a.get("verb") in liberal_verbs)
        militant_count = sum(1 for a in action_history if a.get("verb") in militant_verbs)

        liberal_ratio = liberal_count / total if total > 0 else 0
        if liberal_ratio > 0.7:
            score += 0.3
            indicators.append(
                f"Liberal action ratio: {liberal_ratio:.0%} "
                f"({liberal_count} liberal vs {militant_count} militant)"
            )

    # Factor 2: Budget-cadre imbalance (spending money, not building org)
    if org_budget > 200 and org_cadre < 0.2:
        score += 0.25
        indicators.append(f"Budget-cadre gap: ${org_budget:.0f} budget but {org_cadre:.1%} cadre")

    # Factor 3: Stagnant consciousness (activity without transformation)
    if consciousness_avg < 0.3 and len(action_history) > 10:
        score += 0.2
        indicators.append(
            f"Consciousness stagnant at {consciousness_avg:.1%} despite "
            f"{len(action_history)} actions"
        )

    # Factor 4: Low cohesion (org is loose, more coalition than party)
    if org_cohesion < 0.3:
        score += 0.1
        indicators.append(f"Low cohesion: {org_cohesion:.1%} (coalition, not party)")

    score = min(1.0, score)
    return TrapStatus(
        trap_type=TrapType.LIBERAL,
        score=score,
        severity=_score_to_severity(score, 0),
        indicators=indicators,
    )


def detect_ultra_left_trap(
    action_history: list[dict[str, Any]],
    org_heat: float,
    sympathizer_labor: float,
    territory_count: int,
    territory_losses: int = 0,
) -> TrapStatus:
    """Detect ultra-left deviation.

    Indicators:
    - High ratio of "attack" to total actions
    - High heat (state has identified you as a threat)
    - Low sympathizer labor (no mass base)
    - Territory losses from repression

    Args:
        action_history: Recent action dicts with 'verb' keys.
        org_heat: Player org heat level.
        sympathizer_labor: Current SL availability.
        territory_count: Territories the org operates in.
        territory_losses: Territories lost to repression recently.
    """
    indicators: list[str] = []
    score = 0.0

    # Factor 1: Too many attacks without mass base
    if action_history:
        total = len(action_history)
        attack_count = sum(1 for a in action_history if a.get("verb") == "attack")
        attack_ratio = attack_count / total if total > 0 else 0
        if attack_ratio > 0.4:
            score += 0.3
            indicators.append(f"Attack ratio: {attack_ratio:.0%} ({attack_count}/{total} actions)")

    # Factor 2: High heat (you're a target)
    if org_heat > 0.5:
        score += org_heat * 0.3
        indicators.append(f"Heat: {org_heat:.0%} (state is watching)")

    # Factor 3: No mass base
    if sympathizer_labor < 2.0:
        score += 0.2
        indicators.append(f"SL: {sympathizer_labor:.1f} (no mass base)")

    # Factor 4: Territory losses
    if territory_losses > 0:
        score += min(0.3, territory_losses * 0.1)
        indicators.append(f"Lost {territory_losses} territories to repression")

    # Factor 5: Isolation (operating in very few territories)
    if territory_count <= 1:
        score += 0.15
        indicators.append("Operating in only 1 territory (isolated)")

    score = min(1.0, score)
    return TrapStatus(
        trap_type=TrapType.ULTRA_LEFT,
        score=score,
        severity=_score_to_severity(score, 0),
        indicators=indicators,
    )


def detect_rightist_trap(
    action_history: list[dict[str, Any]],
    org_cadre: float,
    tick: int,
    fascist_entities: int = 0,
    total_entities: int = 1,
) -> TrapStatus:
    """Detect rightist deviation.

    Indicators:
    - Only "aid" and "educate" actions (no mobilization or confrontation)
    - No growth in cadre over time
    - Rising fascism unchecked

    Args:
        action_history: Recent action dicts with 'verb' keys.
        org_cadre: Player org cadre_level.
        tick: Current simulation tick.
        fascist_entities: Entities with dominant national_identity.
        total_entities: Total entity count.
    """
    indicators: list[str] = []
    score = 0.0

    # Factor 1: Only passive actions
    if action_history:
        total = len(action_history)
        passive_verbs = {"aid", "educate", "investigate"}
        active_verbs = {"mobilize", "campaign", "attack", "move"}
        passive_count = sum(1 for a in action_history if a.get("verb") in passive_verbs)
        active_count = sum(1 for a in action_history if a.get("verb") in active_verbs)

        passive_ratio = passive_count / total if total > 0 else 0
        if passive_ratio > 0.8 and total > 5:
            score += 0.3
            indicators.append(
                f"Passive action ratio: {passive_ratio:.0%} "
                f"({passive_count} passive vs {active_count} active)"
            )

    # Factor 2: Stagnant cadre
    if tick > 10 and org_cadre < 0.15:
        score += 0.2
        indicators.append(f"Cadre stagnant at {org_cadre:.1%} after {tick} ticks")

    # Factor 3: Rising fascism unchallenged
    if total_entities > 0:
        fascist_ratio = fascist_entities / total_entities
        if fascist_ratio > 0.3:
            score += fascist_ratio * 0.4
            indicators.append(
                f"Fascism rising: {fascist_entities}/{total_entities} "
                f"entities trending fascist ({fascist_ratio:.0%})"
            )

    # Factor 4: Late-game inaction
    if tick > 26 and score > 0:  # Past half the 52-tick game
        score += 0.1
        indicators.append("Late game — time is running out")

    score = min(1.0, score)
    return TrapStatus(
        trap_type=TrapType.RIGHTIST,
        score=score,
        severity=_score_to_severity(score, 0),
        indicators=indicators,
    )


def detect_traps(
    action_history: list[dict[str, Any]],
    org_budget: float,
    org_cadre: float,
    org_cohesion: float,
    org_heat: float,
    sympathizer_labor: float,
    territory_count: int,
    consciousness_avg: float,
    tick: int,
    fascist_entities: int = 0,
    total_entities: int = 1,
    territory_losses: int = 0,
    previous_result: TrapDetectionResult | None = None,
) -> TrapDetectionResult:
    """Run all three trap detectors and produce a combined result.

    Args:
        action_history: List of recent action dicts (last ~10 ticks).
        org_budget: Player org budget.
        org_cadre: Player org cadre_level.
        org_cohesion: Player org cohesion.
        org_heat: Player org heat.
        sympathizer_labor: Current SL.
        territory_count: Territories the org operates in.
        consciousness_avg: Average consciousness across entities.
        tick: Current simulation tick.
        fascist_entities: Entities with dominant national identity.
        total_entities: Total entity count.
        territory_losses: Territories lost to repression recently.
        previous_result: Previous tick's detection result (for persistence).

    Returns:
        TrapDetectionResult with all three trap statuses.
    """
    liberal = detect_liberal_trap(
        action_history,
        org_budget,
        org_cadre,
        org_cohesion,
        consciousness_avg,
    )
    ultra_left = detect_ultra_left_trap(
        action_history,
        org_heat,
        sympathizer_labor,
        territory_count,
        territory_losses,
    )
    rightist = detect_rightist_trap(
        action_history,
        org_cadre,
        tick,
        fascist_entities,
        total_entities,
    )

    # Carry forward ticks_at_moderate from previous result
    if previous_result is not None:
        for trap, prev in [
            (liberal, previous_result.liberal),
            (ultra_left, previous_result.ultra_left),
            (rightist, previous_result.rightist),
        ]:
            if trap.severity in {TrapSeverity.MODERATE, TrapSeverity.SEVERE}:
                trap.ticks_at_moderate = prev.ticks_at_moderate + 1
            else:
                trap.ticks_at_moderate = 0
            # Re-evaluate severity with updated ticks
            trap.severity = _score_to_severity(trap.score, trap.ticks_at_moderate)

    # Determine dominant trap
    all_traps = [liberal, ultra_left, rightist]
    active = max(all_traps, key=lambda t: t.score)
    active_trap = active.trap_type if active.severity != TrapSeverity.NONE else None

    # Check for game-over trap
    game_over = None
    for trap in all_traps:
        if trap.severity == TrapSeverity.SEVERE:
            game_over = trap.trap_type
            break

    return TrapDetectionResult(
        liberal=liberal,
        ultra_left=ultra_left,
        rightist=rightist,
        active_trap=active_trap,
        game_over_trap=game_over,
    )
