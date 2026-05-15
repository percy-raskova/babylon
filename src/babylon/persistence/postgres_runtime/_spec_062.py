"""Spec 062 cross-scale extensions for :class:`PostgresRuntime`.

The two methods exported here are monkey-patched onto ``PostgresRuntime`` at
module load time by :func:`_legacy._attach_spec_062_methods`. They implement
FR-008a per-tick transactional atomicity and the
``get_last_committed_tick`` crash-recovery helper.

Design:
- :func:`persist_tick_atomic` wraps every INSERT into the four dynamic_*
  table families in a single ``with conn.transaction():`` block. INSERT
  statements use ``ON CONFLICT ... DO NOTHING`` so re-running the same
  envelope after a crash is idempotent.
- :func:`get_last_committed_tick` returns the highest tick for which a
  hex_state row exists (since the envelope is atomic, ``dynamic_hex_state``
  is sufficient — every committed envelope writes at least one hex row).

See Also:
    ``specs/062-cross-scale-integration/contracts/persistence.yaml``.
    :mod:`babylon.persistence.envelope`:
        :class:`PerTickTransactionEnvelope`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.postgres_runtime._legacy import PostgresRuntime


_HEX_INSERT = """
INSERT INTO dynamic_hex_state (
    session_id, tick, h3_index,
    county_fips, state_fips, region_id,
    c, v, s, k,
    biocapacity_stock, energy_stock, raw_material_stock,
    internet_access_pct, surveillance_coupling
) VALUES (
    %(session_id)s, %(tick)s, %(h3_index)s,
    %(county_fips)s, %(state_fips)s, %(region_id)s,
    %(c)s, %(v)s, %(s)s, %(k)s,
    %(biocapacity_stock)s, %(energy_stock)s, %(raw_material_stock)s,
    %(internet_access_pct)s, %(surveillance_coupling)s
)
ON CONFLICT (session_id, tick, h3_index) DO NOTHING
"""

_EXTERNAL_INSERT = """
INSERT INTO dynamic_external_node_state (
    session_id, tick, node_id, kind,
    phi_year_inflow, bilateral_trade_value, bilateral_trade_tons, erdi_ratio
) VALUES (
    %(session_id)s, %(tick)s, %(node_id)s, %(kind)s,
    %(phi_year_inflow)s, %(bilateral_trade_value)s,
    %(bilateral_trade_tons)s, %(erdi_ratio)s
)
ON CONFLICT (session_id, tick, node_id) DO NOTHING
"""

_BOUNDARY_INSERT = """
INSERT INTO boundary_flow_register (
    session_id, tick,
    source_node_id, source_kind,
    dest_node_id, dest_kind,
    flow_type, magnitude
) VALUES (
    %(session_id)s, %(tick)s,
    %(source_node_id)s, %(source_kind)s,
    %(dest_node_id)s, %(dest_kind)s,
    %(flow_type)s, %(magnitude)s
)
ON CONFLICT (session_id, tick, source_node_id, dest_node_id, flow_type)
DO NOTHING
"""

_AUDIT_INSERT = """
INSERT INTO conservation_audit_log (
    session_id, tick, scale, invariant_name,
    computed_value, expected_value, residual, severity,
    determinism_hash, created_at_utc
) VALUES (
    %(session_id)s, %(tick)s, %(scale)s, %(invariant_name)s,
    %(computed_value)s, %(expected_value)s, %(residual)s, %(severity)s,
    %(determinism_hash)s, %(created_at_utc)s
)
ON CONFLICT (session_id, tick, scale, invariant_name) DO NOTHING
"""


# Spec-065: per-tick county-resolution subsystem state inserts.
_CONSCIOUSNESS_INSERT = """
INSERT INTO dynamic_consciousness_state (
    session_id, tick, county_fips,
    p_acquiescence, p_revolution,
    ideology_r, ideology_l, ideology_f
) VALUES (
    %(session_id)s, %(tick)s, %(county_fips)s,
    %(p_acquiescence)s, %(p_revolution)s,
    %(ideology_r)s, %(ideology_l)s, %(ideology_f)s
)
ON CONFLICT (session_id, tick, county_fips) DO NOTHING
"""

_DEMOGRAPHICS_INSERT = """
INSERT INTO dynamic_demographics_state (
    session_id, tick, county_fips, population
) VALUES (
    %(session_id)s, %(tick)s, %(county_fips)s, %(population)s
)
ON CONFLICT (session_id, tick, county_fips) DO NOTHING
"""

_EMPLOYMENT_INSERT = """
INSERT INTO dynamic_employment_state (
    session_id, tick, county_fips, employment_proxy
) VALUES (
    %(session_id)s, %(tick)s, %(county_fips)s, %(employment_proxy)s
)
ON CONFLICT (session_id, tick, county_fips) DO NOTHING
"""


def _hex_row_dict(row: Any) -> dict[str, Any]:
    """Serialize a DynamicHexState row to psycopg param dict."""
    return {
        "session_id": str(row.session_id),
        "tick": row.tick,
        "h3_index": row.h3_index,
        "county_fips": row.county_fips,
        "state_fips": row.state_fips,
        "region_id": row.region_id,
        "c": row.c,
        "v": row.v,
        "s": row.s,
        "k": row.k,
        "biocapacity_stock": row.biocapacity_stock,
        "energy_stock": row.energy_stock,
        "raw_material_stock": row.raw_material_stock,
        "internet_access_pct": row.internet_access_pct,
        "surveillance_coupling": row.surveillance_coupling,
    }


def _external_row_dict(row: Any) -> dict[str, Any]:
    return {
        "session_id": str(row.session_id),
        "tick": row.tick,
        "node_id": row.node_id,
        "kind": row.kind.value if hasattr(row.kind, "value") else row.kind,
        "phi_year_inflow": row.phi_year_inflow,
        "bilateral_trade_value": row.bilateral_trade_value,
        "bilateral_trade_tons": row.bilateral_trade_tons,
        "erdi_ratio": row.erdi_ratio,
    }


def _boundary_row_dict(row: Any) -> dict[str, Any]:
    return {
        "session_id": str(row.session_id),
        "tick": row.tick,
        "source_node_id": row.source_node_id,
        "source_kind": row.source_kind.value
        if hasattr(row.source_kind, "value")
        else row.source_kind,
        "dest_node_id": row.dest_node_id,
        "dest_kind": row.dest_kind.value if hasattr(row.dest_kind, "value") else row.dest_kind,
        "flow_type": row.flow_type.value if hasattr(row.flow_type, "value") else row.flow_type,
        "magnitude": row.magnitude,
    }


def _audit_row_dict(row: Any) -> dict[str, Any]:
    return {
        "session_id": str(row.session_id),
        "tick": row.tick,
        "scale": row.scale,
        "invariant_name": row.invariant_name,
        "computed_value": row.computed_value,
        "expected_value": row.expected_value,
        "residual": row.residual,
        "severity": row.severity.value if hasattr(row.severity, "value") else row.severity,
        "determinism_hash": row.determinism_hash,
        "created_at_utc": row.created_at_utc,
    }


def _consciousness_row_dict(row: Any) -> dict[str, Any]:
    return {
        "session_id": str(row.session_id),
        "tick": row.tick,
        "county_fips": row.county_fips,
        "p_acquiescence": row.p_acquiescence,
        "p_revolution": row.p_revolution,
        "ideology_r": row.ideology_r,
        "ideology_l": row.ideology_l,
        "ideology_f": row.ideology_f,
    }


def _demographics_row_dict(row: Any) -> dict[str, Any]:
    return {
        "session_id": str(row.session_id),
        "tick": row.tick,
        "county_fips": row.county_fips,
        "population": row.population,
    }


def _employment_row_dict(row: Any) -> dict[str, Any]:
    return {
        "session_id": str(row.session_id),
        "tick": row.tick,
        "county_fips": row.county_fips,
        "employment_proxy": row.employment_proxy,
    }


def persist_tick_atomic(self: PostgresRuntime, envelope: PerTickTransactionEnvelope) -> None:
    """Persist every row in the envelope inside one Postgres transaction.

    Spec 062 FR-008a. If any INSERT raises (CHECK violation, constraint
    failure, deadlock, network error), the entire transaction rolls back
    and no row of the envelope is visible to subsequent reads.
    Idempotent on retry-after-crash via ``ON CONFLICT DO NOTHING`` on every
    composite primary key.

    The seven buffered INSERTs (hex_state, external_node, boundary_register,
    audit_log, plus the spec-065 trio: consciousness_state, demographics_state,
    employment_state) execute in a fixed order so that any constraint
    violation in a later table still rolls back the earlier inserts.
    """
    with self._pool.connection() as conn, conn.transaction():
        if envelope.hex_state_rows:
            conn.cursor().executemany(
                _HEX_INSERT,
                [_hex_row_dict(r) for r in envelope.hex_state_rows],
            )
        if envelope.external_node_rows:
            conn.cursor().executemany(
                _EXTERNAL_INSERT,
                [_external_row_dict(r) for r in envelope.external_node_rows],
            )
        if envelope.boundary_register_rows:
            conn.cursor().executemany(
                _BOUNDARY_INSERT,
                [_boundary_row_dict(r) for r in envelope.boundary_register_rows],
            )
        if envelope.audit_log_rows:
            conn.cursor().executemany(
                _AUDIT_INSERT,
                [_audit_row_dict(r) for r in envelope.audit_log_rows],
            )
        # Spec-065: per-tick county-resolution subsystem state rows.
        if envelope.consciousness_state_rows:
            conn.cursor().executemany(
                _CONSCIOUSNESS_INSERT,
                [_consciousness_row_dict(r) for r in envelope.consciousness_state_rows],
            )
        if envelope.demographics_state_rows:
            conn.cursor().executemany(
                _DEMOGRAPHICS_INSERT,
                [_demographics_row_dict(r) for r in envelope.demographics_state_rows],
            )
        if envelope.employment_state_rows:
            conn.cursor().executemany(
                _EMPLOYMENT_INSERT,
                [_employment_row_dict(r) for r in envelope.employment_state_rows],
            )


def get_last_committed_tick(self: PostgresRuntime, session_id: UUID) -> int | None:
    """Return the largest tick for which an envelope was committed.

    Returns ``None`` if no envelope has been committed for ``session_id``.
    Used by crash-recovery code to resume from the correct tick.
    """
    with self._pool.connection() as conn:
        cur = conn.execute(
            "SELECT MAX(tick) FROM dynamic_hex_state WHERE session_id = %s",
            (str(session_id),),
        )
        result = cur.fetchone()
        if result is None or result[0] is None:
            return None
        return int(result[0])


__all__ = ["persist_tick_atomic", "get_last_committed_tick"]
