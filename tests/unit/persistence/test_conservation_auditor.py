"""Unit tests for ConservationAuditor and determinism hash (T063 / GATE-1)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from babylon.persistence.audit_models import AuditSeverity
from babylon.persistence.conservation_audit import (
    ConservationAlarmEvent,
    ConservationAuditor,
    _InvariantResult,
    compute_determinism_hash,
    grade_severity,
)
from babylon.persistence.hex_state import DynamicHexState


def _make_hex(session_id: UUID, tick: int, h3: str, c: float = 1.0) -> DynamicHexState:
    return DynamicHexState(
        session_id=session_id,
        tick=tick,
        h3_index=h3,
        county_fips="26163",
        state_fips="26",
        region_id="east_north_central",
        c=c,
        v=1.0,
        s=1.0,
        k=1.0,
        biocapacity_stock=1.0,
        energy_stock=1.0,
        raw_material_stock=1.0,
        internet_access_pct=0.5,
        surveillance_coupling=0.5,
    )


@pytest.mark.cross_scale
class TestGradeSeverity:
    def test_ok_when_within_epsilon(self) -> None:
        assert grade_severity(1e-11, epsilon=1e-10) is AuditSeverity.OK

    def test_ok_at_exact_epsilon(self) -> None:
        assert grade_severity(1e-10, epsilon=1e-10) is AuditSeverity.OK

    def test_warn_above_epsilon(self) -> None:
        assert grade_severity(1e-9, epsilon=1e-10) is AuditSeverity.WARN

    def test_warn_at_1e6_threshold(self) -> None:
        assert grade_severity(1e-6, epsilon=1e-10) is AuditSeverity.WARN

    def test_alarm_above_1e6(self) -> None:
        assert grade_severity(1e-5, epsilon=1e-10) is AuditSeverity.ALARM

    def test_sign_does_not_matter(self) -> None:
        assert grade_severity(-1e-5, epsilon=1e-10) is AuditSeverity.ALARM


@pytest.mark.cross_scale
class TestDeterminismHash:
    """GATE-1 / Constitution III.7: same inputs -> same hash."""

    def test_determinism_hash_is_64_hex_chars(self) -> None:
        sid = uuid4()
        h = compute_determinism_hash(
            tick=0,
            rng_seed=42,
            hex_rows=[_make_hex(sid, 0, "872d34a89ffffff")],
        )
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_inputs_same_hash(self) -> None:
        sid = uuid4()
        rows = [_make_hex(sid, 0, "872d34a89ffffff")]
        a = compute_determinism_hash(tick=0, rng_seed=42, hex_rows=rows)
        b = compute_determinism_hash(tick=0, rng_seed=42, hex_rows=rows)
        assert a == b

    def test_different_tick_different_hash(self) -> None:
        sid = uuid4()
        rows = [_make_hex(sid, 0, "872d34a89ffffff")]
        a = compute_determinism_hash(tick=0, rng_seed=42, hex_rows=rows)
        b = compute_determinism_hash(tick=1, rng_seed=42, hex_rows=rows)
        assert a != b

    def test_different_seed_different_hash(self) -> None:
        sid = uuid4()
        rows = [_make_hex(sid, 0, "872d34a89ffffff")]
        a = compute_determinism_hash(tick=0, rng_seed=42, hex_rows=rows)
        b = compute_determinism_hash(tick=0, rng_seed=43, hex_rows=rows)
        assert a != b

    def test_order_independent(self) -> None:
        """Hex rows in different order produce the same hash (sort by h3_index)."""
        sid = uuid4()
        r1 = _make_hex(sid, 0, "872d34a89ffffff", c=1.0)
        r2 = _make_hex(sid, 0, "872d34b0bffffff", c=2.0)
        a = compute_determinism_hash(tick=0, rng_seed=42, hex_rows=[r1, r2])
        b = compute_determinism_hash(tick=0, rng_seed=42, hex_rows=[r2, r1])
        assert a == b


@pytest.mark.cross_scale
class TestConservationAuditor:
    """End-of-tick auditor produces rows + alarm events."""

    def test_empty_registry_produces_no_rows(self) -> None:
        auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)
        rows, alarms = auditor.evaluate(session_id=uuid4(), tick=0, hex_rows=[])
        assert rows == []
        assert alarms == []

    def test_registered_evaluator_returns_audit_row(self) -> None:
        def fake_evaluator(pre, post, ctx):  # noqa: ARG001
            return [
                _InvariantResult(
                    scale="county",
                    invariant_name="hex_to_county_sum_c",
                    computed_value=10.0,
                    expected_value=10.0,
                )
            ]

        auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)
        auditor.register_invariant("hex_to_county_sum_c", fake_evaluator)

        sid = uuid4()
        rows, alarms = auditor.evaluate(
            session_id=sid, tick=0, hex_rows=[_make_hex(sid, 0, "872d34a89ffffff")]
        )
        assert len(rows) == 1
        assert rows[0].severity is AuditSeverity.OK
        assert rows[0].scale == "county"
        assert rows[0].invariant_name == "hex_to_county_sum_c"
        assert alarms == []  # OK severity → no alarm event

    def test_alarm_severity_emits_event(self) -> None:
        def bad_evaluator(pre, post, ctx):  # noqa: ARG001
            return [
                _InvariantResult(
                    scale="county",
                    invariant_name="hex_to_county_sum_c",
                    computed_value=10.0,
                    expected_value=11.0,  # residual = -1.0 → ALARM
                )
            ]

        auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)
        auditor.register_invariant("hex_to_county_sum_c", bad_evaluator)

        sid = uuid4()
        rows, alarms = auditor.evaluate(
            session_id=sid, tick=0, hex_rows=[_make_hex(sid, 0, "872d34a89ffffff")]
        )
        assert rows[0].severity is AuditSeverity.ALARM
        assert len(alarms) == 1
        assert isinstance(alarms[0], ConservationAlarmEvent)
        assert alarms[0].residual == -1.0

    def test_default_invariant_names_enumerate_22(self) -> None:
        """audit_log.yaml 16 aggregation + 5 per-stage + spec-063 pairing."""
        names = ConservationAuditor.default_invariant_names()
        assert len(names) == 22
        # Sanity: a few canonical names appear.
        assert "hex_to_county_sum_c" in names
        assert "global_phi_balance" in names
        assert "production_grows_v_plus_s_by_labor_increment" in names
        assert "paired_cross_border_emission" in names

    def test_all_rows_in_tick_share_determinism_hash(self) -> None:
        def make_evaluator(name: str, computed: float):  # type: ignore[no-untyped-def]
            def evaluator(pre, post, ctx):  # noqa: ARG001
                return [
                    _InvariantResult(
                        scale="county",
                        invariant_name=name,
                        computed_value=computed,
                        expected_value=computed,
                    )
                ]

            return evaluator

        auditor = ConservationAuditor(epsilon=1e-10, rng_seed=42)
        auditor.register_invariant("hex_to_county_sum_c", make_evaluator("c", 1.0))
        auditor.register_invariant("hex_to_county_sum_v", make_evaluator("v", 2.0))

        sid = uuid4()
        rows, _ = auditor.evaluate(
            session_id=sid, tick=0, hex_rows=[_make_hex(sid, 0, "872d34a89ffffff")]
        )
        assert len({r.determinism_hash for r in rows}) == 1
