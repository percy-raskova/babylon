"""Vol II Circulation sub-stage (Spec 063 T055 / T018).

Per-tick transformation that consumes the year-scoped :class:`LODESYearMatrix`
plus the current in-memory hex ``v`` vector and produces (a) the next-tick
hex ``v`` vector for in-study-area hexes and (b) boundary register rows for
every flow that exits the study area, each paired with a wage-repatriation
``TRADE_EDGE`` row per FR-030a.

This is a **sub-stage** of :class:`ImperialRentSystem` (pipeline slot 5c per
spec 062 FR-053), not a top-level System. The sub-stage signature differs
from :class:`babylon.kernel.system_protocol.System` because the caller is
``ImperialRentSystem.step()`` and supplies the boundary register and session
metadata directly.

**County-keyed reconciliation (Vol II Circulation program, Unit U4;
owner ruling 7, #39/Amendment U — ADR120/ADR123).** No production code ever
stamps a ``hex`` graph node — territories are COUNTY-keyed; hex res-7 is
immutable substrate. The LODES OD matrix is genuinely hex-resolution (it
models commute flows between H3 cells), so the reconciliation is a BINDING
at the boundary, not a rewrite of the math: :meth:`step` reads/writes a
``v`` value per eligible county ``Territory`` node and uses the
constructor-injected :class:`~babylon.domain.dialectics.instances.scale.
ScaleAdjunction` (``allocate ⊣ aggregate``) to push each county's aggregate
``v`` down to hex grain before the unchanged matrix-vector algorithm runs,
then sum the resulting hex-grain post-state back up to its county parent
for the ``update_node`` write. Boundary register rows are UNAFFECTED — they
key on ``NodeKind.HEX`` (a register-row label), not a graph node id, so hex
ids inside the register are not "hex stamping" and carry no county binding.
See :func:`babylon.persistence.hex_hydrator.read_hex_county_adjunction` for
the real, session-scoped adjunction builder.

Constitution constraints:

- **II.6 + GATE-2**: no DB I/O during the step body; the OD matrix is loaded
  once at session init and passed in via constructor.
- **II.12 GATE-4**: the matrix is ``scipy.sparse.csr_matrix``; the formula
  is expressed as a single matrix-vector multiplication for the in-area
  portion (FR-009 / FR-016).
- **II.13 GATE-5**: this is the deterministic min-cost flow component only.
  Slime-mold conductivity (the emergent component of II.13) is out of scope.
- **III.7**: identical pre-state + identical OD matrix → bit-identical
  post-state and boundary rows (FR-014).

See also:
    ``specs/063-vol-ii-circulation/spec.md`` FR-008 .. FR-016, FR-030a/b/c.
    ``specs/063-vol-ii-circulation/data-model.md`` §1.3.
    :mod:`babylon.domain.economics.lodes_commute_matrix`:
        :class:`LODESCommuteMatrixLoader`, :class:`LODESYearMatrix`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

import numpy as np

from babylon.domain.dialectics.instances.scale import ScaleAdjunction
from babylon.domain.economics.boundary_flow_register import (
    BoundaryEdgeKind,
    BoundaryFlowRegister,
    NodeKind,
)
from babylon.domain.economics.tick.graph_bridge import resolve_county_identity
from babylon.kernel.system_base import SystemBase
from babylon.models.enums import NodeType

if TYPE_CHECKING:
    from babylon.domain.economics.lodes_commute_matrix import (
        LODESCommuteMatrixLoader,
    )
    from babylon.engine.systems.cross_border_commute import (
        CrossBorderCommuteClassifier,
    )
    from babylon.kernel.graph_protocol import GraphProtocol

logger = logging.getLogger(__name__)

# FR-010 / SC-002 — conservation residual tolerance multiplier.
_CONSERVATION_REL_TOL = 1e-9


@dataclass(frozen=True)
class CirculationStepResult:
    """Outcome record for one Vol II Circulation sub-stage execution.

    Returned from :meth:`Vol2CirculationStep.step` so callers (tests,
    instrumentation, the conservation auditor) can verify FR-010 invariants
    without re-walking the graph.
    """

    tick: int
    pre_total_v: float
    post_total_v_in_area: float
    boundary_out_total_v: float
    rows_emitted: int
    od_year_used: int
    conservation_residual: float
    wall_time_ms: float = 0.0


class CirculationConservationViolation(RuntimeError):
    """Raised when FR-010 conservation invariant is violated mid-tick.

    Aborts the per-tick transaction (spec 062 FR-008a) so the engine state
    rolls back cleanly. Audit log entry is recorded by the auditor.
    """


class Vol2CirculationStep:
    """Sub-stage 5c: variable-capital redistribution across hexes per LODES OD.

    The sub-stage executes the formula::

        v[A, t+1] = sum_j(OD[j, A] × v[j, t] / row_sum[j])  for in-area A

    For origins ``j`` with ``row_sum[j] == 0`` (uninhabited cells), ``v[j]``
    carries forward unchanged and no boundary rows are emitted from ``j``
    (FR-011). For destinations outside the study area, the share is recorded
    as a ``COMMUTE_OUT`` row in the boundary register plus a paired
    observational ``TRADE_EDGE`` row representing wage repatriation
    (FR-030a — the paired row does NOT modify the in-area ``v`` vector).

    Construction takes the loader so the year-scoped matrix is fetched
    lazily at each ``step()`` call (the loader caches the current year, so
    repeated step calls in a year share the same CSR matrix). It also takes
    the hex<->county :class:`ScaleAdjunction` binding (see the module
    docstring's "County-keyed reconciliation" section) so the read/write
    endpoints of the per-hex ``v`` vector go through county ``Territory``
    nodes, never hex nodes.
    """

    def __init__(
        self,
        *,
        od_loader: LODESCommuteMatrixLoader,
        hex_county_adjunction: ScaleAdjunction,
        classifier: CrossBorderCommuteClassifier | None = None,
    ) -> None:
        self._od_loader = od_loader
        self._hex_county_adjunction = hex_county_adjunction
        self._classifier = classifier

    def step(  # noqa: C901, PLR0915 — FR-009/010/011/030a/conservation are inherently coupled; splitting would harm clarity
        self,
        *,
        graph: GraphProtocol,
        register: BoundaryFlowRegister,
        session_id: UUID,
        tick: int,
        simulated_year: int,
    ) -> CirculationStepResult:
        """Execute one tick of Vol II Circulation.

        Args:
            graph: In-memory graph; eligible county ``Territory`` nodes
                (``resolve_county_identity(node) is not None``) carry the
                county-grain ``v`` attribute. Modified in-place: post-step
                ``v`` values are ALLOCATED to hex grain (read), run through
                the unchanged hex-resolution algorithm, then AGGREGATED
                back and written to ``graph.nodes[territory_id]["v"]`` for
                each eligible county — never to a hex node (none exist).
            register: Per-tick boundary register buffer; receives the
                ``COMMUTE_OUT`` + paired ``TRADE_EDGE`` rows.
            session_id: UUID of the active session (for register rows).
            tick: Current tick number (for register rows).
            simulated_year: The calendar year mapped to this tick. The
                loader applies FR-004 nearest-year clamp internally if
                needed; the actually-consumed year is returned in
                :attr:`CirculationStepResult.od_year_used`.

        Returns:
            :class:`CirculationStepResult` summarizing the operation.

        Raises:
            CirculationConservationViolation: if the FR-010 conservation
                invariant fails for any reason (precision drift, matrix
                corruption, etc.). The per-tick transaction MUST be rolled
                back by the caller.
        """
        import time

        t0 = time.perf_counter()
        protocol = SystemBase._wrap_graph(graph)
        year_matrix = self._od_loader.load_year(simulated_year)
        od_year_used = year_matrix.year

        # ── 1. Snapshot pre-state v, ALLOCATED from county grain to hex grain ─
        # #39/Amendment U (owner ruling 7): no production code stamps a hex
        # node -- territories are COUNTY-keyed. Read each eligible county
        # Territory node's v, then ALLOCATE it down to hex grain by the
        # constructor-injected ScaleAdjunction's per-hex share (left adjoint)
        # so the hex-resolution algorithm below runs UNCHANGED (ADR120/123
        # disposition: a boundary binding, not a rewrite of the math).
        county_v: dict[str, float] = {}
        fips_to_node: dict[str, str] = {}
        for node in sorted(
            protocol.query_nodes(node_type=NodeType.TERRITORY),
            key=lambda n: n.id,
        ):
            fips = resolve_county_identity(node)
            if fips is None:
                continue
            county_v[fips] = float(node.attributes.get("v", 0.0))
            fips_to_node[fips] = str(node.id)

        # allocate() fails loud (KeyError) when the adjunction names a
        # county this graph carries no eligible Territory for -- a
        # session/adjunction mismatch is a wiring bug, not a zero
        # (Constitution III.11).
        hex_v: dict[str, float] = self._hex_county_adjunction.allocate(county_v)

        pre_total_v = float(sum(hex_v.values()))

        # ── 2. Build pre-state row vector aligned to the LODES matrix ───────
        # Origins not in the matrix get a 0 contribution (their v carries forward
        # but doesn't flow anywhere via Vol II). Origins in the matrix but with
        # row_sum == 0 also carry forward (FR-011).
        n_origins = year_matrix.matrix.shape[0]
        n_dests = year_matrix.matrix.shape[1]
        v_pre_vec = np.zeros(n_origins, dtype=np.float64)
        for hex_id, idx in year_matrix.origin_hex_to_row.items():
            v_pre_vec[idx] = hex_v.get(hex_id, 0.0)

        # ── 3. Compute normalized v_pre vector (FR-011 zero-row-sum guard) ──
        row_sums = year_matrix.row_sums
        with np.errstate(divide="ignore", invalid="ignore"):
            normalized = np.where(row_sums > 0, v_pre_vec / row_sums, 0.0)

        # ── 4. Sparse matrix-vector multiplication for new column totals ────
        # contribution[dest_col] = sum_j(OD[j, dest_col] * normalized[j])
        # FR-009 + FR-016 — the in-area portion is exactly this MV product.
        contributions = np.asarray(year_matrix.matrix.T @ normalized).ravel()
        if contributions.shape != (n_dests,):
            raise ValueError(f"contributions shape {contributions.shape} != expected ({n_dests},)")

        # ── 5. Build v_post additively + emit boundary rows ─────────────────
        # The post-state for any in-graph hex is the SUM of three contributions:
        #   (a) incoming flow from other origins (matrix.T @ normalized for HEX cols)
        #   (b) FR-011 carry-forward: if the hex is in the matrix as origin with
        #       row_sum == 0, its pre-state v is preserved (it had nowhere to send)
        #   (c) hexes NOT in the matrix as origin keep their pre-state v entirely
        v_post_vec = np.asarray(contributions)
        hex_v_post: dict[str, float] = dict.fromkeys(hex_v, 0.0)

        # (a) incoming flow from in-area destination columns
        for hex_id, col_idx in year_matrix.dest_to_col.items():
            if year_matrix.dest_kind_by_col[col_idx] != NodeKind.HEX:
                continue
            if hex_id in hex_v_post:
                hex_v_post[hex_id] += float(v_post_vec[col_idx])

        # (b) FR-011 zero-row-sum carry-forward (hex's own pre-state preserved
        # because nothing flowed out of it)
        for hex_id, row_idx in year_matrix.origin_hex_to_row.items():
            if hex_id in hex_v_post and row_sums[row_idx] == 0:
                hex_v_post[hex_id] += hex_v.get(hex_id, 0.0)

        # (c) hexes not in matrix as origin — no LODES presence; carry forward fully
        for hex_id, v_pre_val in hex_v.items():
            if hex_id not in year_matrix.origin_hex_to_row:
                hex_v_post[hex_id] += v_pre_val

        # ── 6. Emit boundary register rows for external destinations ────────
        # Iterate the CSR matrix nonzeros to attribute per-(origin, ext-dest) magnitudes.
        boundary_out_total = 0.0
        rows_emitted = 0
        coo = year_matrix.matrix.tocoo()
        row_to_origin = {idx: hex_id for hex_id, idx in year_matrix.origin_hex_to_row.items()}
        for r_idx, c_idx, v_count in zip(coo.row, coo.col, coo.data, strict=True):
            r = int(r_idx)
            c = int(c_idx)
            dest_kind = year_matrix.dest_kind_by_col[c]
            if dest_kind != NodeKind.EXTERNAL:
                continue  # in-area dests already handled by step (a) above
            row_sum_j = float(row_sums[r])
            if row_sum_j == 0:
                continue
            origin_hex = row_to_origin[r]
            raw_dest_id = year_matrix.dest_node_id_by_col[c]
            # FR-027 emission-time classification: when a classifier is
            # wired, reclassify the destination so Canadian-coded blocks
            # route to dest_node_id='canada' rather than the loader's
            # default 'rest_of_usa'.
            if self._classifier is not None:
                classification = self._classifier.classify(raw_dest_id)
                dest_id = classification.dest_node_id
            else:
                dest_id = raw_dest_id
            share = float(v_count) / row_sum_j
            magnitude = share * v_pre_vec[r]
            if magnitude == 0:
                continue
            register.record(
                session_id=session_id,
                tick=tick,
                source_node_id=origin_hex,
                source_kind=NodeKind.HEX,
                dest_node_id=dest_id,
                dest_kind=NodeKind.EXTERNAL,
                flow_type=BoundaryEdgeKind.COMMUTE_OUT,
                magnitude=magnitude,
            )
            # FR-030a — paired TRADE_EDGE for wage repatriation; observational only.
            register.record(
                session_id=session_id,
                tick=tick,
                source_node_id=dest_id,
                source_kind=NodeKind.EXTERNAL,
                dest_node_id=origin_hex,
                dest_kind=NodeKind.HEX,
                flow_type=BoundaryEdgeKind.TRADE_EDGE,
                magnitude=magnitude,
            )
            rows_emitted += 2
            boundary_out_total += magnitude

        # ── 6. Validate FR-010 conservation ─────────────────────────────────
        post_total_v_in_area = float(sum(hex_v_post.values()))
        residual = abs(pre_total_v - (post_total_v_in_area + boundary_out_total))
        tolerance = _CONSERVATION_REL_TOL * max(pre_total_v, 1.0)
        if residual > tolerance:
            raise CirculationConservationViolation(
                f"Vol II Circulation conservation residual {residual:.6e} exceeds "
                f"tolerance {tolerance:.6e} for tick {tick}: "
                f"pre={pre_total_v:.6f} post_in_area={post_total_v_in_area:.6f} "
                f"boundary_out={boundary_out_total:.6f}"
            )

        # ── 7. AGGREGATE hex_v_post back to county grain, write back ────────
        # The write endpoint mirrors the read endpoint's binding: sum
        # (right adjoint) the hex-grain post-state back up to its county
        # parent -- an extensive quantity, never averaged -- and write the
        # county Territory node's v. hex_v_post's key set equals hex_v's
        # (built above from allocate()), which is exactly the adjunction's
        # full child set, so aggregate() cannot KeyError here; fips_to_node
        # covers every adjunction parent because county_v (built from the
        # SAME eligible-territory loop) already had to for allocate() to
        # have succeeded above.
        county_v_post = self._hex_county_adjunction.aggregate(hex_v_post)
        for fips, v_post_val in county_v_post.items():
            protocol.update_node(fips_to_node[fips], v=v_post_val)

        wall_time_ms = (time.perf_counter() - t0) * 1000.0
        return CirculationStepResult(
            tick=tick,
            pre_total_v=pre_total_v,
            post_total_v_in_area=post_total_v_in_area,
            boundary_out_total_v=boundary_out_total,
            rows_emitted=rows_emitted,
            od_year_used=od_year_used,
            conservation_residual=residual,
            wall_time_ms=wall_time_ms,
        )


__all__ = [
    "CirculationConservationViolation",
    "CirculationStepResult",
    "Vol2CirculationStep",
]
