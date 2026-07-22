"""Pure politics kernel — the ambient electoral machine's formulas (P25 U7, ADR133).

The load-bearing arithmetic of ``the-electoral-question.md`` §2, free of any
engine or graph type: the valve law (§2.5), the electoral hope field H(c)
(§2.5), the funding identity / reform ceiling (§2.4, O'Connor's fiscal crisis
as arithmetic), and the derived platform vector with the Przeworski–Sprague
breadth⟷alignment trade-off (§2.1, L-PRZ). Property laws pinned in
``tests/unit/formulas/test_politics.py``; systems consume these from U8–U10.

Theory notes live with each function; heavier exposition belongs in
``docs/reference`` when the systems land.
"""

from __future__ import annotations

import math

from babylon.formulas.survival_calculus import calculate_acquiescence_probability


def valve_multiplier(hope: float, valve_strength: float) -> float:
    """The valve law: conversion efficiency multiplier ``1 − v·H`` (§2.5).

    While hope is high, organizing is hard — not by decree but because the
    promised gradient of ``P(S|A)`` outcompetes ``P(S|R)``'s risk in every
    rational survival ledger. Clamped to ``[0, 1]``: hope SUPPRESSES and
    never amplifies conversion (L-VALVE's sign law).

    :param hope: The class's hope field ``H(c)`` in ``[0, 1]``.
    :param valve_strength: Θ_feel ``politics.valve_strength`` in ``[0, 1]``.
    :returns: Multiplier applied to Agitation→Organization conversion.
    """
    return min(1.0, max(0.0, 1.0 - valve_strength * hope))


def hope_field(terms: tuple[tuple[float, float, float], ...]) -> float:
    """The electoral hope field ``H(c) = Σ_p allegiance·viability·max(0, ΔP(S|A))`` (§2.5).

    Hope is not a mood primitive: it is the believed arithmetic of the
    acquiescence branch — the allegiance-weighted, viability-discounted
    promised improvement in survival-by-acquiescence (Aleksandrov chain,
    III.8). A platform that promises no improvement contributes exactly
    zero (L-HOPE-MATERIAL: no hope without a promise trace).

    :param terms: Per-party ``(allegiance, viability, delta_p_s_a)`` rows for
        one class; ``delta_p_s_a`` is the counterfactual sigmoid improvement
        (see :func:`counterfactual_hope_gain`).
    :returns: ``H(c) >= 0``.
    """
    return sum(allegiance * viability * max(0.0, delta) for allegiance, viability, delta in terms)


def counterfactual_hope_gain(
    wealth: float,
    subsistence: float,
    promised_transfer: float,
    steepness_k: float,
) -> float:
    """One platform's promised improvement in ``P(S|A)`` for one class (§2.5, T-5).

    Previews are evaluations, not estimates: the gain is the SAME sigmoid the
    engine adjudicates, evaluated under the promised overlay minus the status
    quo — never a parallel feed.

    :returns: ``max(0, P(S|A | wealth+transfer) − P(S|A | wealth))``.
    """
    promised = calculate_acquiescence_probability(
        wealth + promised_transfer, subsistence, steepness_k
    )
    status_quo = calculate_acquiescence_probability(wealth, subsistence, steepness_k)
    return max(0.0, promised - status_quo)


def sw_deliverable(
    promised: float,
    t_claim: float,
    phi_slice: float,
    debt_service: float,
) -> float:
    """The funding identity: ``min(SW_promised, t + Φ_slice − debt_service)`` (§2.4).

    The social wage is a claim on measured surplus, never minted value
    (L-CEILING; the four-source license is untouched). As Φ falls, delivery
    detaches from promise with no one lying — the platform is sincere, the
    arithmetic is fatal.

    :returns: Deliverable social wage, ``>= 0`` and ``<= promised``.
    """
    funded = max(0.0, t_claim + phi_slice - debt_service)
    return min(max(0.0, promised), funded)


def delivery_ratio(delivered: float, promised: float) -> float:
    """``SW_deliverable / SW_promised`` in ``[0, 1]``; an empty promise delivers fully.

    :returns: 1.0 when nothing was promised (no gap can accrue from silence).
    """
    if promised <= 0.0:
        return 1.0
    return min(1.0, max(0.0, delivered / promised))


def delivery_gap(promised: float, delivered: float) -> float:
    """``promised − delivered``, the single most load-bearing new quantity (§2.4).

    Drives allegiance drift, betrayal-agitation, and legitimation decay;
    accumulated per class per incumbent as the betrayal integral ``b(c)``.

    :returns: ``>= 0`` (over-delivery does not mint negative betrayal).
    """
    return max(0.0, promised - delivered)


def platform_vector(
    base_terms: tuple[tuple[float, tuple[float, ...]], ...],
    donor_terms: tuple[tuple[float, tuple[float, ...]], ...],
    donor_weight: float,
) -> tuple[float, ...]:
    """The derived platform: ``normalize(Σ w_c·interest_c + θ_donor·Σ f_d·interest_d)`` (§2.1).

    Computed fresh each tick (II.2 — never stored); party positions drift
    with the material composition of their coalition, which is what makes
    the Przeworski–Sprague dilemma a LAW rather than a script (L-PRZ:
    broadening reach dilutes the platform away from any single class's
    interest vector).

    :param base_terms: ``(membership_weight, interest_vector)`` per class.
    :param donor_terms: ``(funding_share, interest_vector)`` per donor.
    :param donor_weight: Θ_feel ``politics.donor_platform_weight``.
    :returns: Unit-normalized platform vector; ``()`` for an empty coalition.
    """
    dims = 0
    for _, vec in (*base_terms, *donor_terms):
        dims = max(dims, len(vec))
    if dims == 0:
        return ()
    acc = [0.0] * dims
    for weight, vec in base_terms:
        for i, component in enumerate(vec):
            acc[i] += weight * component
    for share, vec in donor_terms:
        for i, component in enumerate(vec):
            acc[i] += donor_weight * share * component
    norm = math.sqrt(sum(x * x for x in acc))
    if norm == 0.0:
        return tuple(acc)
    return tuple(x / norm for x in acc)


def allegiance_drift(
    fit: float,
    contact: float,
    align_rate: float,
    contact_rate: float,
    media_influence: float = 0.0,
    media_rate: float = 0.0,
    delivery_gap_term: float = 0.0,
    betrayal_rate: float = 0.0,
) -> float:
    """Per-tick allegiance drift toward one party for one class (§2.2).

    The four-term law, all Θ-projections, deterministic::

        Δallegiance(c, p) = θ.align · fit  +  θ.media · media_influence
                          + θ.contact · contact  −  θ.betrayal · delivery_gap

    The media (ISA_COMM apparatus) and betrayal (U9 delivery-gap) terms
    default to exact zeros until their producers exist — honest absence,
    never a fabricated weight (U8/ADR134).

    :param fit: :func:`interest_fit` of the class's interest vector against
        the party's derived platform.
    :param contact: Organizing-contact signal (MEMBERSHIP-edge base reach).
    :param align_rate: Θ_feel ``politics.allegiance_align_rate``.
    :param contact_rate: Θ_feel ``politics.allegiance_contact_rate``.
    :param media_influence: Σ ISA_COMM influence·line (producer pending).
    :param media_rate: θ.media (0.0 until the media apparatus lands).
    :param delivery_gap_term: Incumbent promise − delivery (U9's producer).
    :param betrayal_rate: θ.betrayal (0.0 until U9).
    :returns: Signed drift delta for this (class, party) pair.
    """
    return (
        align_rate * fit
        + media_rate * media_influence
        + contact_rate * contact
        - betrayal_rate * delivery_gap_term
    )


def apply_allegiance_drift(
    allegiance: tuple[float, ...],
    deltas: tuple[float, ...],
) -> tuple[tuple[float, ...], float]:
    """Apply drift deltas under mass discipline (§2.2 node-attribute ruling).

    The allegiance distribution over (parties ∪ abstention) is a partition
    of the class's political existence: deltas MOVE mass between parties
    and the abstention pool, they never mint or destroy it. Per-party
    masses clamp at zero; if the party total exceeds unit mass it rescales
    proportionally (abstention exhausted); otherwise abstention absorbs
    the residual.

    :param allegiance: Current per-party masses (abstention excluded).
    :param deltas: Per-party drift deltas (same order/length).
    :returns: ``(new_party_masses, abstention)`` summing to exactly 1.0.
    """
    updated = [max(0.0, mass + delta) for mass, delta in zip(allegiance, deltas, strict=True)]
    total = sum(updated)
    if total > 1.0:
        return tuple(mass / total for mass in updated), 0.0
    return tuple(updated), 1.0 - total


def interest_fit(interest: tuple[float, ...], platform: tuple[float, ...]) -> float:
    """Cosine-style alignment between a class interest vector and a platform (§2.2).

    Feeds the allegiance drift's material-interest term; symmetric inputs
    give 1.0, orthogonal give 0.0.

    :returns: Fit in ``[-1, 1]``; 0.0 when either vector is empty or zero.
    """
    if not interest or not platform:
        return 0.0
    dims = min(len(interest), len(platform))
    dot = sum(interest[i] * platform[i] for i in range(dims))
    norm_i = math.sqrt(sum(x * x for x in interest[:dims]))
    norm_p = math.sqrt(sum(x * x for x in platform[:dims]))
    if norm_i == 0.0 or norm_p == 0.0:
        return 0.0
    return dot / (norm_i * norm_p)
