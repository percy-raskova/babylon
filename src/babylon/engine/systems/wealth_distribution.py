"""Wealth-distribution system — Phase 1 SHADOW ONLY (Program 21, Data Constitution).

Wires the formerly-orphaned ``babylon.formulas.class_dynamics`` ODE (FRED-DFA
fitted, Feature 016) into the tick as the **runtime wealth-share axis**: a
single national 4-bracket vector ``(w1..w4)`` = wealth held by top-1% /
p90-99 / p50-90 / bottom-50, relaxing toward the ``GameDefines.class_dynamics``
equilibria that ``tests/unit/config/test_wealth_distribution_invariants.py``
pins against 111 years of WID/Piketty data.

This is the axis the population partition was conflated with (the census
found four sites hardcoding *headcount* shares mislabelled as wealth); it is
**additive** — the per-county 5-class population substrate is untouched.

PHASE 1 SCOPE (binding, per the design brief): observe-only shadow.

- State home: ``G.graph["wealth_distribution"]`` metadata (the
  ``economy``/``state_finances`` round-trip pattern), plus a per-node
  ``wealth_share`` projection onto ``social_class`` nodes (a **declared**
  ``SocialClass`` field — the ``extra="forbid"`` landmine).
- Nothing reads these outputs yet: no feedback into wealth, consciousness, or
  bifurcation (Phase 2, owner-gated), so the sampled qa:regression
  checkpoints stay byte-identical.
- Deterministic by construction: seeded from defines, iterated in sorted node
  order, no RNG (Constitution III.7).

Bracket mapping RATIFIED (owner ruling 2026-07-16, ADR075): the 8
``SocialRole`` members fold onto the 4 wealth brackets by the Fed-DFA
``dim_wealth_class.babylon_class`` correspondence. Two clarifications from
the ruling: CARCERAL_ENFORCER is a *distinctive subclass of the labor
aristocracy* (same w3 bracket, kept as its own role for the decomposition
mechanics); INTERNAL_PROLETARIAT and PERIPHERY_PROLETARIAT read as ONE
singular proletariat in w4 (migrant farm workers, the $7.25 stratum — the
periphery-internal distinction is an extraction-channel fact, not a wealth-
bracket fact). A possible future enum-level merge of the two proletariat
roles is NOTED, not executed (the LA-decomposition mechanic references
INTERNAL_PROLETARIAT specifically).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.formulas.class_dynamics import (
    ClassDynamicsParams,
    SecondOrderParams,
    calculate_full_dynamics,
)
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.models.enums import SocialRole

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

#: RATIFIED 8-role → 4-bracket fold (0=w1 top-1%, 1=w2 p90-99,
#: 2=w3 p50-90, 3=w4 bottom-50). Owner ruling 2026-07-16; see module docstring.
_BRACKET_BY_ROLE: dict[SocialRole, int] = {
    SocialRole.CORE_BOURGEOISIE: 0,
    SocialRole.COMPRADOR_BOURGEOISIE: 0,
    SocialRole.PETTY_BOURGEOISIE: 1,
    SocialRole.LABOR_ARISTOCRACY: 2,
    SocialRole.CARCERAL_ENFORCER: 2,
    SocialRole.PERIPHERY_PROLETARIAT: 3,
    SocialRole.INTERNAL_PROLETARIAT: 3,
    SocialRole.LUMPENPROLETARIAT: 3,
}

_Vector = tuple[float, float, float, float]


def bracket_of_role(role: SocialRole) -> int:
    """Return the wealth-bracket index (0..3) a social role folds into.

    :param role: Any :class:`SocialRole` member.
    :returns: The bracket index under the PROVISIONAL mapping.
    """
    return _BRACKET_BY_ROLE[role]


def _coerce_role(raw: object) -> SocialRole | None:
    """Coerce a graph-node ``role`` attr to :class:`SocialRole` (or ``None``)."""
    if isinstance(raw, SocialRole):
        return raw
    if isinstance(raw, str):
        try:
            return SocialRole(raw)
        except ValueError:
            return None
    return None


def _seed_vector(defines: Any) -> _Vector:
    """Seed the national vector from the calibration equilibria, normalized.

    :param defines: This session's ``ClassDynamicsDefines``.
    :returns: The equilibrium shares scaled to sum exactly to 1.
    """
    raw = (
        defines.equilibrium_w1,
        defines.equilibrium_w2,
        defines.equilibrium_w3,
        defines.equilibrium_w4,
    )
    total = sum(raw)
    return (raw[0] / total, raw[1] / total, raw[2] / total, raw[3] / total)


def _ode_params(defines: Any) -> tuple[ClassDynamicsParams, SecondOrderParams]:
    """Build the ODE parameter sets from the SESSION defines (not import-time).

    ``ClassDynamicsParams``' dataclass defaults are frozen at import from the
    default ``GameDefines`` — a modded session would silently ignore its own
    coefficients if we relied on them.

    :param defines: This session's ``ClassDynamicsDefines``.
    :returns: ``(first_order, second_order)`` parameter sets.
    """
    first = ClassDynamicsParams(
        alpha_41=defines.alpha_41,
        alpha_31=defines.alpha_31,
        alpha_21=defines.alpha_21,
        alpha_32=defines.alpha_32,
        alpha_42=defines.alpha_42,
        alpha_43=defines.alpha_43,
        delta_1=defines.delta_1,
        delta_2=defines.delta_2,
        delta_3=defines.delta_3,
        gamma_3=defines.gamma_3,
    )
    second = SecondOrderParams(
        beta=(defines.beta_1, defines.beta_2, defines.beta_3, defines.beta_4),
        omega=(defines.omega_1, defines.omega_2, defines.omega_3, defines.omega_4),
        equilibrium=_seed_vector(defines),
    )
    return first, second


def _bracket_resistances(graph: GraphProtocol) -> _Vector:
    """Mean ``class_consciousness`` per bracket — the ODE's resistance input.

    Deterministic: nodes visited in sorted-id order; brackets with no nodes
    contribute zero resistance (honest absence, not a fabricated default).

    :param graph: The live tick graph.
    :returns: Per-bracket mean consciousness ``(r1..r4)``.
    """
    sums = [0.0, 0.0, 0.0, 0.0]
    counts = [0, 0, 0, 0]
    nodes = sorted(graph.query_nodes(node_type="social_class"), key=lambda n: n.id)
    for node in nodes:
        role = _coerce_role(node.attributes.get("role"))
        if role is None:
            continue
        bracket = _BRACKET_BY_ROLE[role]
        sums[bracket] += float(node.attributes.get("class_consciousness", 0.0))
        counts[bracket] += 1
    return tuple(s / c if c else 0.0 for s, c in zip(sums, counts, strict=True))  # type: ignore[return-value]


def _advance(
    shares: _Vector,
    velocities: _Vector,
    resistances: _Vector,
    defines: Any,
) -> tuple[_Vector, _Vector]:
    """One deterministic Euler step of the class-dynamics ODE.

    The ODE's rates are quarterly (Feature 016 FRED-DFA fit); one tick is
    ``1 / ticks_per_quarter`` quarters. Velocity integrates the second-order
    acceleration; shares integrate the first-order flow plus velocity, then
    clamp to ``[0, 1]`` and renormalize so Σ == 1 exactly (conservation of
    the whole — float drift never accumulates across ticks).

    :param shares: Current ``(w1..w4)``.
    :param velocities: Current ODE momentum state.
    :param resistances: Per-bracket class-consciousness resistances.
    :param defines: This session's ``ClassDynamicsDefines``.
    :returns: ``(new_shares, new_velocities)``.
    """
    dt = 1.0 / defines.ticks_per_quarter
    params, second_order = _ode_params(defines)
    flows, accelerations = calculate_full_dynamics(
        shares, velocities, params=params, second_order=second_order, resistances=resistances
    )
    new_velocities = tuple(v + a * dt for v, a in zip(velocities, accelerations, strict=True))
    stepped = [
        max(0.0, min(1.0, w + (f + v) * dt))
        for w, f, v in zip(shares, flows, new_velocities, strict=True)
    ]
    total = sum(stepped)
    normalized = tuple(w / total for w in stepped) if total > 0.0 else _seed_vector(defines)
    return normalized, new_velocities


class WealthDistributionSystem(SystemBase):
    """Phase 1 SHADOW: the national 4-bracket wealth-share axis.

    Runs at position 21.5 (end of the Consequence phase, just before the
    Epistemic Horizon observer): it reads the tick's ``class_consciousness``
    as ODE resistance and writes ONLY its own axis — the national vector to
    graph metadata and the ``wealth_share`` bracket projection onto
    ``social_class`` nodes. Nothing consumes either yet (Phase 2 owner-gated).
    """

    name: ClassVar[str] = "Wealth Distribution"
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Advance (or seed) the national vector and project it onto nodes.

        First tick (no metadata): seed from ``equilibrium_w1..w4`` with zero
        velocity. Subsequent ticks: one Euler step of
        :func:`~babylon.formulas.class_dynamics.calculate_full_dynamics`.
        """
        defines = services.defines.class_dynamics
        tick = context.get("tick", 0) if isinstance(context, dict) else getattr(context, "tick", 0)
        metadata = getattr(graph, "graph", None)
        if not isinstance(metadata, dict):  # pragma: no cover — BabylonGraph always has it
            return
        prior = metadata.get("wealth_distribution")
        if prior is None:
            shares = _seed_vector(defines)
            velocities: _Vector = (0.0, 0.0, 0.0, 0.0)
        else:
            shares, velocities = _advance(
                tuple(prior["shares"]),
                tuple(prior["velocities"]),
                _bracket_resistances(graph),
                defines,
            )
        metadata["wealth_distribution"] = {
            "shares": list(shares),
            "velocities": list(velocities),
            "tick": int(tick),
        }
        nodes = sorted(graph.query_nodes(node_type="social_class"), key=lambda n: n.id)
        for node in nodes:
            role = _coerce_role(node.attributes.get("role"))
            if role is None:
                continue  # honest absence: no role, no bracket, no projection
            graph.update_node(node.id, wealth_share=shares[_BRACKET_BY_ROLE[role]])
