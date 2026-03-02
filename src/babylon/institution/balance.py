"""Internal balance of forces update function (Feature 040).

Implements alpha-smoothed factional balance shifts driven by crisis
intensity, legitimacy erosion, and external threat conditions.

See Also:
    ``specs/040-institution-base-model/spec.md``: FR-005.
"""

from __future__ import annotations

from babylon.models.entities.institution import (
    BonapartistModeEvent,
    FactionShiftEvent,
    InternalBalanceOfForces,
)


def update_internal_balance(
    balance: InternalBalanceOfForces,
    crisis_intensity: float,
    legitimacy: float,
    external_threat: float,
    alpha: float = 0.05,
    bonapartist_threshold: float = 0.4,
    bonapartist_exclusion_threshold: float = 0.35,
) -> tuple[InternalBalanceOfForces, list[FactionShiftEvent | BonapartistModeEvent]]:
    """Update factional balance under crisis conditions.

    Alpha-smoothed shift mechanics:
    - Rising crisis_intensity drives REVANCHIST weight up
    - Falling legitimacy weakens LIBERAL weight
    - External threat drives BONAPARTIST weight up

    Args:
        balance: Current factional weight distribution.
        crisis_intensity: Crisis severity [0, 1].
        legitimacy: Institutional legitimacy [0, 1].
        external_threat: External threat level [0, 1].
        alpha: Smoothing rate (from InstitutionDefines).
        bonapartist_threshold: BONAPARTIST weight for mode trigger.
        bonapartist_exclusion_threshold: Other fractions must be below this.

    Returns:
        Tuple of (new_balance, events_list). Events may include
        FactionShiftEvent (hegemonic fraction changed) and/or
        BonapartistModeEvent (threshold crossed).
    """
    events: list[FactionShiftEvent | BonapartistModeEvent] = []

    # Compute deltas
    # Crisis drives revanchist up (repression impulse)
    revanchist_delta = alpha * crisis_intensity
    # Low legitimacy weakens liberal (consent breaks down)
    liberal_delta = -alpha * (1.0 - legitimacy)
    # External threat drives bonapartist up (self-preservation)
    bonapartist_delta = alpha * external_threat

    # Apply deltas
    new_liberal = balance.liberal_technocratic + liberal_delta
    new_revanchist = balance.revanchist_fascist + revanchist_delta
    new_bonapartist = balance.institutionalist_bonapartist + bonapartist_delta

    # Clamp to [0, 1]
    new_liberal = max(0.0, min(1.0, new_liberal))
    new_revanchist = max(0.0, min(1.0, new_revanchist))
    new_bonapartist = max(0.0, min(1.0, new_bonapartist))

    # Normalize to sum=1.0
    total = new_liberal + new_revanchist + new_bonapartist
    if total > 0:
        new_liberal /= total
        new_revanchist /= total
        new_bonapartist /= total
    else:
        # Fallback: equal distribution
        new_liberal = new_revanchist = new_bonapartist = 1.0 / 3.0

    # Update contestation: higher when weights are close
    max_weight = max(new_liberal, new_revanchist, new_bonapartist)
    new_contestation = min(1.0, 1.0 - max_weight + 0.1)

    new_balance = InternalBalanceOfForces(
        liberal_technocratic=round(new_liberal, 6),
        revanchist_fascist=round(new_revanchist, 6),
        institutionalist_bonapartist=round(new_bonapartist, 6),
        internal_contestation=round(new_contestation, 6),
    )

    # Check for hegemonic fraction change
    old_fraction = balance.hegemonic_fraction
    new_fraction = new_balance.hegemonic_fraction
    if old_fraction != new_fraction:
        events.append(
            FactionShiftEvent(
                institution_id="",  # Caller sets this
                old_fraction=old_fraction,
                new_fraction=new_fraction,
                weights={
                    "liberal_technocratic": new_balance.liberal_technocratic,
                    "revanchist_fascist": new_balance.revanchist_fascist,
                    "institutionalist_bonapartist": new_balance.institutionalist_bonapartist,
                },
            )
        )

    # Check for Bonapartist mode
    if (
        new_balance.institutionalist_bonapartist > bonapartist_threshold
        and new_balance.liberal_technocratic < bonapartist_exclusion_threshold
        and new_balance.revanchist_fascist < bonapartist_exclusion_threshold
    ):
        events.append(
            BonapartistModeEvent(
                institution_id="",  # Caller sets this
                bonapartist_weight=new_balance.institutionalist_bonapartist,
            )
        )

    return new_balance, events
