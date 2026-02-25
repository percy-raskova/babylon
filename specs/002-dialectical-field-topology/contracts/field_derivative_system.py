"""Contract: FieldDerivativeSystem (System #15).

Computes spatial derivatives (gradient, Laplacian), temporal derivatives
(df/dt, d2f/dt2), principal contradiction, and continuity residuals.

Reference: FR-003 (gradient), FR-004 (Laplacian), FR-005 (curvature)
Reference: FR-006 (temporal derivatives), FR-008 (principal contradiction)
Reference: FR-009 (continuity residuals)
Reference: R-004 (Ollivier-Ricci via scipy), R-006 (system ordering — position 15)

System Protocol: step(graph, services, context) -> None
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType


class FieldDerivativeSystemContract:
    """Contract for FieldDerivativeSystem.

    Execution Order: 15 (after ContradictionFieldSystem)

    Inputs (read from graph):
        - Node: contradiction_fields: dict[str, float]
        - persistent_data["contradiction_history"]: rolling window

    Outputs (written to graph):
        - Node: field_derivatives: dict[str, dict]
            field_name -> {
                "laplacian": float,
                "df_dt": float | None,
                "d2f_dt2": float | None,
            }
        - Edge: field_gradients: dict[str, float]
            field_name -> gradient value (f(target) - f(source))
        - Edge: ricci_curvature: float (cached, only on topology change)
        - Edge: ricci_computed_tick: int
        - Graph attr: principal_contradiction: dict
            {"field_name": str, "max_abs_df_dt": float, "changed": bool}
        - Node: continuity_residuals: dict[str, dict]
            field_name -> {
                "delta_f": float,
                "net_flow": float,
                "residual": float,
                "mechanism": str | None,
            }

    Invariants:
        - df_dt is None (not 0.0) when < 2 ticks history (EC-001)
        - d2f_dt2 is None (not 0.0) when < 3 ticks history (EC-001)
        - Laplacian at isolated nodes (degree 0) is 0.0 with warning (EC-002)
        - Curvature recomputed only on topology change (FR-005)
        - Principal contradiction tie: larger total magnitude wins,
          then exploitation preferred (EC-004)
    """

    @property
    def name(self) -> str:
        """System identifier."""
        return "field_derivative"

    def step(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Compute all derivatives and principal contradiction.

        Algorithm:
            1. Auto-wrap graph if not GraphProtocol
            2. For each registered field:
                a. Spatial: compute gradient on every edge
                b. Spatial: compute Laplacian at every node
                c. Temporal: compute df/dt, d2f/dt2 from history
                d. Continuity: compute residual = delta_f - net_flow
            3. If topology changed since last curvature computation:
                a. Compute Ollivier-Ricci curvature for all edges
                b. Cache on edge attributes with tick stamp
            4. Identify principal contradiction:
                a. For each field, find max |df/dt| across all nodes
                b. Field with largest max |df/dt| is principal
                c. Tie-break: total magnitude, then exploitation preferred
                d. Record whether principal changed from previous tick
            5. Write all results to graph attributes
        """
        ...
