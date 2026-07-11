"""Consciousness-weighted solidarity analysis (US1, Feature 033).

Applies a nonlinear sigmoid transform to collective_identity (CI) so that
solidarity edges in assimilated communities (CI < midpoint) are weighted
near-zero, while oppositional communities (CI > midpoint) receive near-full
weight. This creates the "breakage cliff" that distinguishes revolutionary
from fascist solidarity patterns.

See Also:
    :mod:`babylon.domain.bifurcation.analysis`: Orchestrator that calls these functions.
    :func:`babylon.formulas.survival_calculus.calculate_acquiescence_probability`:
        Established sigmoid pattern (overflow clamp +/-500).
    ``specs/033-bifurcation-topology/spec.md``: Feature specification.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonGraph
import xgi  # type: ignore[import-untyped, unused-ignore]

from babylon.config.defines import BifurcationDefines
from babylon.domain.bifurcation.types import WeightedSolidarityResult
from babylon.models.entities.community import (
    MARGINALIZED_COMMUNITIES,
    CommunityState,
)
from babylon.models.entities.consciousness import TernaryConsciousness
from babylon.models.enums import CommunityType
from babylon.models.types import Probability

# Overflow clamp bound (matches survival_calculus.py line 40)
_EXPONENT_CLAMP = 500


def consciousness_sigmoid(
    collective_identity: float,
    midpoint: float,
    steepness: float,
) -> float:
    """Nonlinear transform with breakage cliff for consciousness weighting.

    Logistic sigmoid: ``1 / (1 + exp(-steepness * (ci - midpoint)))``.
    Exponent is clamped to [-500, +500] to prevent overflow.

    Args:
        collective_identity: Raw CI value [0, 1].
        midpoint: Sigmoid inflection point (from BifurcationDefines).
        steepness: Slope at inflection (from BifurcationDefines).

    Returns:
        Transformed value [0, 1]. Near-zero below midpoint, near-one above.

    Examples:
        >>> consciousness_sigmoid(0.4, 0.4, 10.0)
        0.5
        >>> consciousness_sigmoid(0.0, 0.4, 10.0) < 0.05
        True
    """
    exponent = -steepness * (collective_identity - midpoint)
    exponent = max(-_EXPONENT_CLAMP, min(_EXPONENT_CLAMP, exponent))
    return 1.0 / (1.0 + math.exp(exponent))


def _agent_mean_marginalized_ci(
    agent_id: str,
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
) -> float:
    """Compute mean CI across an agent's marginalized community memberships.

    Args:
        agent_id: The agent node ID.
        H: XGI hypergraph where hyperedge IDs are CommunityType.value strings.
        community_states: Current community consciousness data.

    Returns:
        Mean collective_identity across the agent's marginalized communities.
        Returns 0.0 if the agent has no marginalized community memberships.
    """
    if agent_id not in H.nodes:
        return 0.0

    # H.nodes.memberships() returns the set of hyperedge IDs the agent belongs to
    agent_edge_ids: set[Any] = H.nodes.memberships(agent_id)

    marginalized_cis: list[float] = []
    for edge_id in agent_edge_ids:
        # Convert hyperedge ID back to CommunityType
        try:
            comm_type = CommunityType(edge_id)
        except ValueError:
            continue

        if comm_type not in MARGINALIZED_COMMUNITIES:
            continue

        state = community_states.get(comm_type)
        if state is not None:
            marginalized_cis.append(float(state.consciousness.collective_identity))

    if not marginalized_cis:
        return 0.0

    return sum(marginalized_cis) / len(marginalized_cis)


def consciousness_weighted_solidarity(
    source_id: str,
    target_id: str,
    graph: BabylonGraph,
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
    defines: BifurcationDefines,
) -> WeightedSolidarityResult:
    """Weight a solidarity edge by consciousness of connected agents' communities.

    For each agent, finds their marginalized community memberships via the
    hypergraph, computes mean CI, then weights the edge's solidarity_strength
    by sigmoid(min(source_ci, target_ci)).

    Edges where the effective CI (min of both endpoints) falls below the
    crisis-fragile threshold (0.3) are marked as crisis-fragile — these
    represent assimilated solidarity that collapses under crisis (FR-008).

    Args:
        source_id: Source agent node ID.
        target_id: Target agent node ID.
        graph: The simulation DiGraph (for edge attribute access).
        H: XGI hypergraph (for community membership lookup).
        community_states: Current community consciousness data.
        defines: Configurable parameters (sigmoid midpoint/steepness).

    Returns:
        WeightedSolidarityResult with weight and crisis_fragile flag.
    """
    # Crisis-fragile threshold: r < 0.3 maps to the sigmoid midpoint region
    _CRISIS_FRAGILE_THRESHOLD = 0.3

    # Get solidarity_strength from the edge
    edge_data = graph.edges.get((source_id, target_id), {})
    solidarity_strength: float = edge_data.get("solidarity_strength", 0.0)

    # Compute mean CI for each agent's marginalized communities
    source_ci = _agent_mean_marginalized_ci(source_id, H, community_states)
    target_ci = _agent_mean_marginalized_ci(target_id, H, community_states)

    # Use the minimum CI (weakest link in the solidarity chain)
    effective_ci = min(source_ci, target_ci)

    # Apply consciousness sigmoid
    sigmoid_weight = consciousness_sigmoid(
        collective_identity=effective_ci,
        midpoint=defines.consciousness_sigmoid_midpoint,
        steepness=defines.consciousness_sigmoid_steepness,
    )

    weight = solidarity_strength * sigmoid_weight
    crisis_fragile = effective_ci < _CRISIS_FRAGILE_THRESHOLD

    return WeightedSolidarityResult(weight=weight, crisis_fragile=crisis_fragile)


# ─── Anisotropic Observation Error (FR-009) ──────────────────────────

# Noise standard deviations for state intelligence estimates.
# r has ~3x higher observation error than l/f ratio.
_R_NOISE_STDDEV = 0.06
_LF_NOISE_STDDEV = 0.02


def anisotropic_observation_error(
    true_consciousness: TernaryConsciousness,
    *,
    rng_seed: int | None = None,
    r_noise_stddev: float = _R_NOISE_STDDEV,
    lf_noise_stddev: float = _LF_NOISE_STDDEV,
) -> TernaryConsciousness:
    """Apply anisotropic noise to a consciousness position (FR-009).

    The state observes the l/f split (voting, discourse, media) more
    accurately than the r component (revolutionary consciousness is
    hidden from surveillance). This produces a noisy estimate where
    r has ~3x higher observation error than the l/f ratio.

    Args:
        true_consciousness: Actual community consciousness position.
        rng_seed: Seed for reproducible noise (None = system entropy).
        r_noise_stddev: Gaussian noise std for r component.
        lf_noise_stddev: Gaussian noise std for l/f ratio.

    Returns:
        Observed TernaryConsciousness with anisotropic noise applied,
        clamped to valid simplex point.
    """
    rng = random.Random(rng_seed)

    true_r = float(true_consciousness.r)
    true_l = float(true_consciousness.l)
    true_f = float(true_consciousness.f)

    # 1. Perturb r with higher noise
    observed_r = true_r + rng.gauss(0.0, r_noise_stddev)
    observed_r = max(0.0, min(1.0, observed_r))

    # 2. Perturb l/f ratio with lower noise
    lf_sum = true_l + true_f
    true_lf_ratio = 0.5 if lf_sum < 1e-6 else true_f / lf_sum

    observed_lf_ratio = true_lf_ratio + rng.gauss(0.0, lf_noise_stddev)
    observed_lf_ratio = max(0.0, min(1.0, observed_lf_ratio))

    # 3. Reconstruct observed l, f from remaining budget and perturbed ratio
    remaining = max(0.0, 1.0 - observed_r)
    observed_f = remaining * observed_lf_ratio
    observed_l = remaining * (1.0 - observed_lf_ratio)

    return TernaryConsciousness(
        r=Probability(observed_r),
        l=Probability(observed_l),
        f=Probability(observed_f),
    )


__all__ = [
    "anisotropic_observation_error",
    "consciousness_sigmoid",
    "consciousness_weighted_solidarity",
]
