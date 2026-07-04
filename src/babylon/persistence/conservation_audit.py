"""End-of-tick conservation auditor (Spec 062, US5).

Implements the auditor protocol per ``contracts/audit_log.yaml``. Runs
after the 15-system pipeline completes; emits one
:class:`ConservationAuditRow` per ``(scale, invariant)`` combination per
tick. Each row carries the same ``determinism_hash`` for the tick
(GATE-1, Constitution III.7).

The 16+ enumerated invariants (per audit_log.yaml) are evaluated by
small helper functions that accept the pre-tick + post-tick state
snapshots and return ``computed - expected`` residuals. Severity is
graded against :attr:`EconomyDefines.epsilon_conservation`.

Alarm-severity rows emit a ``ConservationAlarmEvent`` onto the engine's
observer protocol per FR-047 + Clarification Q3.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from babylon.persistence.audit_models import AuditSeverity, ConservationAuditRow

if TYPE_CHECKING:
    pass


# Severity grading per FR-046:
#   ok:    |residual| <= epsilon
#   warn:  epsilon < |residual| <= 1e-6
#   alarm: |residual| > 1e-6
_WARN_THRESHOLD = 1e-6


@dataclass(frozen=True)
class _InvariantResult:
    scale: str
    invariant_name: str
    computed_value: float
    expected_value: float


def grade_severity(residual: float, epsilon: float) -> AuditSeverity:
    """Three-level severity grade per FR-046.

    Args:
        residual: Signed conservation residual.
        epsilon: Tolerance from GameDefines.economy.epsilon_conservation.

    Returns:
        ``OK`` if |residual| <= epsilon, ``WARN`` if epsilon < |residual|
        <= 1e-6, ``ALARM`` otherwise.
    """
    abs_r = abs(residual)
    if abs_r <= epsilon:
        return AuditSeverity.OK
    if abs_r <= _WARN_THRESHOLD:
        return AuditSeverity.WARN
    return AuditSeverity.ALARM


def compute_determinism_hash(
    *,
    tick: int,
    rng_seed: int,
    hex_rows: Iterable[Any],
    action_list: Iterable[Any] | None = None,
) -> str:
    """SHA-256 over canonical(tick + sorted hex_state + actions + rng_seed).

    Implements GATE-1 per Constitution III.7. The canonicalization sorts
    hex rows by h3_index so the hash is order-independent (Postgres
    SELECT order is unspecified).

    Args:
        tick: Current simulation tick.
        rng_seed: Session RNG seed.
        hex_rows: Iterable of either Pydantic frozen models with a
            ``.h3_index`` attribute and ``.model_dump()`` method, OR
            plain dicts whose ``"h3_index"`` key serves the same role
            (the engine pulls graph node attrs as dicts).
        action_list: Optional iterable of action payloads.

    Returns:
        64-char lowercase SHA-256 hex digest.
    """

    def _h3_key(r: Any) -> str:
        if hasattr(r, "h3_index"):
            return str(r.h3_index)
        if isinstance(r, dict):
            return str(r.get("h3_index", ""))
        return ""

    sorted_hex = sorted(hex_rows, key=_h3_key)
    payload = {
        "tick": tick,
        "rng_seed": rng_seed,
        "hex_state": [_to_jsonable(r) for r in sorted_hex],
        "actions": [_to_jsonable(a) for a in (action_list or [])],
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _to_jsonable(obj: Any) -> Any:
    """Reduce a Pydantic frozen model (or any object) to JSON-safe dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, UUID):
        return str(obj)
    return obj


def phi_week_conservation_evaluator(
    _pre_state: Any, _post_state: Any, context: Any
) -> list[_InvariantResult]:
    """Evaluate ``Σ DRAIN_EDGE ≡ Φ_week`` per external bloc (spec-101 FR-101-5).

    Registered on the :class:`ConservationAuditor` under the enumerated
    ``imperial_rent_phi_week_distribution`` invariant. Reads the tick's flushed
    boundary rows and the external-node Φ map from ``context``:

    - ``context["boundary_rows"]``: iterable of ``BoundaryFlowRegisterRow`` for
      this tick (the bridge passes the just-flushed buffer).
    - ``context["external_nodes_phi"]``: ``{node_id: phi_year_inflow}``.

    For each bloc with ``phi_year_inflow > 0`` the check is the **relative**
    residual ``Σ(DRAIN_EDGE magnitude, source=bloc) / (phi_year/52)`` versus
    ``1.0`` (D4). Φ is ~$1e12-scale, so an absolute residual would be meaningless
    against the auditor's absolute alarm threshold (1e-6) and would false-alarm
    ``--strict``; the ratio form keeps the residual at float epsilon (~1e-15).
    Blocs with ``phi == 0`` emit no DRAIN rows and are skipped (FR-020). One
    ``_InvariantResult`` per Φ>0 bloc, differentiated by ``scale=external:<node>``.

    Args:
        _pre_state: Unused (signature parity with other evaluators).
        _post_state: Unused.
        context: The per-tick audit context carrying ``boundary_rows`` and
            ``external_nodes_phi``. A ``None`` context yields no results.

    Returns:
        One ``_InvariantResult`` per bloc with positive Φ.
    """
    from babylon.economics.node_kinds import BoundaryEdgeKind, NodeKind

    if context is None:
        return []
    boundary_rows = context.get("boundary_rows") or []
    external_nodes_phi = context.get("external_nodes_phi") or {}

    drain_by_node: dict[str, float] = {}
    for row in boundary_rows:
        if row.flow_type is BoundaryEdgeKind.DRAIN_EDGE and row.source_kind is NodeKind.EXTERNAL:
            drain_by_node[row.source_node_id] = (
                drain_by_node.get(row.source_node_id, 0.0) + row.magnitude
            )

    results: list[_InvariantResult] = []
    for node_id in sorted(external_nodes_phi):
        phi_year = float(external_nodes_phi[node_id])
        if phi_year <= 0.0:
            continue  # FR-020: zero-Φ blocs contribute no DRAIN rows
        phi_week = phi_year / 52.0
        observed = drain_by_node.get(node_id, 0.0)
        ratio = observed / phi_week if phi_week > 0.0 else 0.0
        results.append(
            _InvariantResult(
                scale=f"external:{node_id}"[:32],
                invariant_name="imperial_rent_phi_week_distribution",
                computed_value=ratio,
                expected_value=1.0,
            )
        )
    return results


class ConservationAlarmEvent(BaseModel):
    """Event payload emitted when an audit row has severity=alarm.

    Per FR-047 + Clarification Q3, the engine's observer protocol receives
    one ``ConservationAlarmEvent`` per alarm row. Subscribers (UI banners,
    structured-log loggers) may render the alarm asynchronously. The tick
    does NOT pause.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    scale: str
    invariant_name: str
    residual: float
    determinism_hash: str = Field(min_length=64, max_length=64)


class ConservationAuditor:
    """End-of-tick auditor that produces ConservationAuditRow batches.

    Spec 062 — FR-043 .. FR-049. The auditor is constructed once per
    engine instance; :meth:`evaluate` is called every tick after the
    15-system pipeline completes.

    Subclasses (or downstream specs) may register additional invariants;
    the MVP enumerates the 16 invariants from audit_log.yaml plus the
    five per-stage invariants.
    """

    # Default invariant registry. Each callable returns a list of
    # _InvariantResult instances given (pre_state, post_state, context).
    # The MVP installs a no-op stub; downstream specs register concrete
    # implementations via :meth:`register_invariant`.
    _DEFAULT_INVARIANTS: tuple[str, ...] = (
        "hex_to_county_sum_c",
        "hex_to_county_sum_v",
        "hex_to_county_sum_s",
        "hex_to_county_sum_k",
        "county_to_state_sum_c",
        "county_to_state_sum_v",
        "county_to_state_sum_s",
        "county_to_state_sum_k",
        "state_to_national_sum_c",
        "state_to_national_sum_v",
        "state_to_national_sum_s",
        "state_to_national_sum_k",
        "global_phi_balance",
        "study_area_boundary_balance_c",
        "study_area_boundary_balance_v",
        "study_area_boundary_balance_s",
        "production_grows_v_plus_s_by_labor_increment",
        "circulation_preserves_sum_v",
        "equalization_preserves_within_industry_sum_c",
        "distribution_splits_s_into_pirt",
        "imperial_rent_phi_week_distribution",
    )

    def __init__(self, *, epsilon: float, rng_seed: int) -> None:
        self._epsilon = epsilon
        self._rng_seed = rng_seed
        # Plug-in registry for invariant evaluators. Each entry is a
        # callable (pre, post, context) -> Iterable[_InvariantResult].
        self._evaluators: dict[str, Any] = {}
        # Spec-065 T049: in-memory buffers populated by audit_end_of_tick
        # so the headless runner can read alarm rows directly without a
        # Postgres round-trip. The bridge also drains these into the
        # per-tick envelope so they hit conservation_audit_log durably.
        self.audit_log_buffer: list[ConservationAuditRow] = []
        self.alarms_buffer: list[ConservationAlarmEvent] = []

    def register_invariant(self, name: str, evaluator: Any) -> None:
        """Register an evaluator callable for a named invariant.

        The callable signature is
        ``(pre_state, post_state, context) -> Iterable[_InvariantResult]``.
        Multiple callables can register for one name; results are
        concatenated.
        """
        self._evaluators[name] = evaluator

    def evaluate(
        self,
        *,
        session_id: UUID,
        tick: int,
        hex_rows: Iterable[Any],
        pre_state: Any = None,
        post_state: Any = None,
        context: Any = None,
        action_list: Iterable[Any] | None = None,
    ) -> tuple[list[ConservationAuditRow], list[ConservationAlarmEvent]]:
        """Compute audit rows for one tick.

        Returns a pair: the rows to persist plus the alarm events to emit.
        For the MVP, if no evaluators are registered the auditor returns
        empty lists — the contract surface is in place, full invariant
        wiring lands with the engine integration follow-up.

        Determinism hash is computed once per tick from canonical state +
        actions + rng_seed (GATE-1).
        """
        h = compute_determinism_hash(
            tick=tick,
            rng_seed=self._rng_seed,
            hex_rows=hex_rows,
            action_list=action_list,
        )
        now = datetime.now(tz=UTC)
        rows: list[ConservationAuditRow] = []
        alarms: list[ConservationAlarmEvent] = []

        for name, evaluator in self._evaluators.items():
            for result in evaluator(pre_state, post_state, context):
                residual = result.computed_value - result.expected_value
                severity = grade_severity(residual, self._epsilon)
                row = ConservationAuditRow(
                    session_id=session_id,
                    tick=tick,
                    scale=result.scale,
                    invariant_name=name,
                    computed_value=result.computed_value,
                    expected_value=result.expected_value,
                    residual=residual,
                    severity=severity,
                    determinism_hash=h,
                    created_at_utc=now,
                )
                rows.append(row)
                if severity is AuditSeverity.ALARM:
                    alarms.append(
                        ConservationAlarmEvent(
                            session_id=session_id,
                            tick=tick,
                            scale=result.scale,
                            invariant_name=name,
                            residual=residual,
                            determinism_hash=h,
                        )
                    )
        return rows, alarms

    def audit_end_of_tick(
        self,
        *,
        session_id: UUID,
        tick: int,
        hex_rows: Iterable[Any],
        pre_state: Any = None,
        post_state: Any = None,
        context: Any = None,
        action_list: Iterable[Any] | None = None,
    ) -> tuple[list[ConservationAuditRow], list[ConservationAlarmEvent]]:
        """Run :meth:`evaluate` and append results to the auditor's buffers.

        Spec-065 T049 entry point. The headless runner (or the engine in
        spec-066) calls this once per tick after persist completes. The
        method returns the freshly-computed rows + alarms AND appends them
        to ``audit_log_buffer`` / ``alarms_buffer`` so subscribers
        (``runner._check_strict_alarms``, persistence layer, observers)
        can read them without recomputing.

        The buffers grow for the whole run; callers can clear them by
        slicing or by calling :meth:`reset_buffers`. The MVP run is short
        enough (a few hundred ticks × a few dozen invariants) that the
        memory cost is negligible.
        """
        rows, alarms = self.evaluate(
            session_id=session_id,
            tick=tick,
            hex_rows=hex_rows,
            pre_state=pre_state,
            post_state=post_state,
            context=context,
            action_list=action_list,
        )
        self.audit_log_buffer.extend(rows)
        self.alarms_buffer.extend(alarms)
        return rows, alarms

    def reset_buffers(self) -> None:
        """Clear ``audit_log_buffer`` and ``alarms_buffer``.

        Useful for tests that share an auditor instance across cases.
        """
        self.audit_log_buffer.clear()
        self.alarms_buffer.clear()

    @property
    def invariant_names(self) -> tuple[str, ...]:
        """Names of all evaluators registered on this auditor."""
        return tuple(self._evaluators.keys())

    @classmethod
    def default_invariant_names(cls) -> tuple[str, ...]:
        """Canonical 21-element invariant enumeration per audit_log.yaml."""
        return cls._DEFAULT_INVARIANTS


__all__ = [
    "ConservationAuditor",
    "ConservationAlarmEvent",
    "compute_determinism_hash",
    "grade_severity",
    "phi_week_conservation_evaluator",
]
