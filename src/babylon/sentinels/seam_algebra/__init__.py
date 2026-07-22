"""Seam-algebra: the unified boundary computation over a construct→consumer graph.

T1.1 Unit 3 (``ai/_inbox/t11-seam-severity-design.md`` §3). Six sibling sentinel
families — inert, unconsumed, coupling, liveness, vocabulary, dangling — each
prove a narrower version of the same claim: "a declared construct is actually
reached by real production code." This family gives that claim ONE
graph-theoretic home (Lawvere 1991 co-Heyting boundaries):

- **Ambient graph G** — every declared :class:`~babylon.sentinels.seam_algebra.
  registry.ConstructNode` plus every ``read``/``call``/``import``/``publish``
  :class:`~babylon.sentinels.seam_algebra.registry.ExpectedConsumer` edge,
  extracted statically via :mod:`ast` (never an import, never an engine run).
- **Live subgraph L** — constructs transitively reachable from the declared
  production entry points (the 30-system tick, the verb resolvers, the
  projection/``observe()`` registry).
- **Seam = ∂L** — every declared construct outside ``L`` is a **disconnected
  subsystem**: a nonempty core severed from production.

Day-one closes F-EC-1 (``anisotropic_observation_error`` — zero production
callers) as the family's first disconnected-subsystem finding, held open by a
dated exemption pending a BD ruling (retire vs. wire as R-EC-2).

Layer 0.5 (same rank as :mod:`babylon.config`): imports nothing above
:mod:`babylon.sentinels` itself.
"""

from babylon.sentinels.seam_algebra.checks import (
    build_live_set,
    check_disconnected_subsystems,
    main,
)
from babylon.sentinels.seam_algebra.registry import (
    CONSTRUCT_REGISTRY,
    EDGE_REGISTRY,
    ORIGIN_FAMILIES,
    PRODUCTION_ENTRY_POINTS,
    SEAM_ALGEBRA_EXEMPTIONS,
    ConstructNode,
    ExpectedConsumer,
)

__all__ = [
    "CONSTRUCT_REGISTRY",
    "EDGE_REGISTRY",
    "ORIGIN_FAMILIES",
    "PRODUCTION_ENTRY_POINTS",
    "SEAM_ALGEBRA_EXEMPTIONS",
    "ConstructNode",
    "ExpectedConsumer",
    "build_live_set",
    "check_disconnected_subsystems",
    "main",
]
