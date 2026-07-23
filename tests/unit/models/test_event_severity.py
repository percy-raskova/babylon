"""Contract tests for :mod:`babylon.models.event_severity` (T1.1 Unit U1).

Covers the acceptance bar from ``ai/_inbox/t11-seam-severity-design.md`` U1: every taxonomy key
is a real ``EventType`` value; the row model is frozen + ``extra="forbid"``; ``derive_severity``
covers all five :class:`~babylon.models.event_severity.EventKind` values; the generated drift
table carries a declared rationale for every non-zero cell; and no ``babylon.engine``/
``babylon.domain`` module reads :func:`~babylon.models.event_severity.resolve_severity` (the
Amendment-S read-only-projection tripwire).

The reconciliation pin (:data:`_EXPECTED_TIERS`) plus the mutation test at the bottom prove the
derivation is load-bearing, not a lookup table in disguise: flipping one declared row's
``terminal_proximity`` changes that member's derived tier AND would red the pin.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.models.enums.events import EventType
from babylon.models.event_severity import (
    DRIFT_TABLE,
    SEVERITY_BY_EVENT,
    SEVERITY_TAXONOMY,
    DriftRow,
    EventKind,
    EventKindRow,
    EventSeverity,
    SeverityTier,
    TerminalProximity,
    _build_severity_by_event,
    derive_severity,
    resolve_severity,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _row_for(event_type: EventType) -> EventKindRow:
    """Fetch the declared :class:`EventKindRow` for ``event_type`` (test helper, not exported)."""
    for row in SEVERITY_TAXONOMY:
        if row.event_type is event_type:
            return row
    raise AssertionError(f"no SEVERITY_TAXONOMY row for {event_type!r}")


class TestEveryTaxonomyKeyIsARealEventType:
    """Structural: ``event_type: EventType`` makes this a type-system guarantee."""

    def test_taxonomy_has_exactly_47_rows(self) -> None:
        assert len(SEVERITY_TAXONOMY) == 62  # 47 day-one + 13 P25 (ADR128) + 2 institution (ADR136)

    def test_no_duplicate_event_type_across_rows(self) -> None:
        seen = {row.event_type for row in SEVERITY_TAXONOMY}
        assert len(seen) == len(SEVERITY_TAXONOMY)

    def test_every_row_event_type_is_an_event_type_instance(self) -> None:
        for row in SEVERITY_TAXONOMY:
            assert isinstance(row.event_type, EventType)


class TestEventKindRowFrozenAndExtraForbid:
    """Frozen + extra="forbid": a malformed row is a loud import-time failure."""

    def test_row_is_frozen(self) -> None:
        row = EventKindRow(
            event_type=EventType.SURPLUS_EXTRACTION,
            kind=EventKind.FLOW,
            terminal_proximity=TerminalProximity.NA,
            salience_floor="informational",
        )
        with pytest.raises(ValidationError):
            row.kind = EventKind.ACT  # type: ignore[misc]

    def test_extra_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.SURPLUS_EXTRACTION,
                kind=EventKind.FLOW,
                terminal_proximity=TerminalProximity.NA,
                salience_floor="informational",
                bogus_field="nope",  # type: ignore[call-arg]
            )


class TestEventKindRowShapeValidation:
    """Every kind-specific shape constraint reds loudly rather than silently dropping data."""

    def test_crossing_requires_non_na_proximity(self) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.MASS_AWAKENING,
                kind=EventKind.CROSSING,
                terminal_proximity=TerminalProximity.NA,
            )

    def test_crossing_forbids_salience_floor(self) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.MASS_AWAKENING,
                kind=EventKind.CROSSING,
                terminal_proximity=TerminalProximity.INTRA_LEVEL,
                salience_floor="warning",
            )

    def test_crossing_forbids_base_crossing(self) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.MASS_AWAKENING,
                kind=EventKind.CROSSING,
                terminal_proximity=TerminalProximity.INTRA_LEVEL,
                base_crossing=EventType.UPRISING,
            )

    @pytest.mark.parametrize("kind", [EventKind.FLOW, EventKind.ACT])
    def test_flow_and_act_require_non_na_terminal_proximity_to_be_na(self, kind: EventKind) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.STATE_REPRESSION,
                kind=kind,
                terminal_proximity=TerminalProximity.INTRA_LEVEL,
                salience_floor="warning",
            )

    @pytest.mark.parametrize("kind", [EventKind.FLOW, EventKind.ACT])
    def test_flow_and_act_require_a_salience_floor(self, kind: EventKind) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.STATE_REPRESSION,
                kind=kind,
                terminal_proximity=TerminalProximity.NA,
            )

    @pytest.mark.parametrize("kind", [EventKind.FLOW, EventKind.ACT])
    def test_flow_and_act_salience_floor_may_never_be_critical(self, kind: EventKind) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.STATE_REPRESSION,
                kind=kind,
                terminal_proximity=TerminalProximity.NA,
                salience_floor="critical",
            )

    def test_alarm_requires_na_proximity(self) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.CALIBRATION_AXIOM_VIOLATION,
                kind=EventKind.ALARM,
                terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
            )

    def test_alarm_forbids_salience_floor(self) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.CALIBRATION_AXIOM_VIOLATION,
                kind=EventKind.ALARM,
                terminal_proximity=TerminalProximity.NA,
                salience_floor="critical",
            )

    def test_pattern_requires_base_crossing(self) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.PATTERN_SHIFT,
                kind=EventKind.PATTERN,
                terminal_proximity=TerminalProximity.NA,
            )

    def test_pattern_forbids_salience_floor(self) -> None:
        with pytest.raises(ValidationError):
            EventKindRow(
                event_type=EventType.PATTERN_SHIFT,
                kind=EventKind.PATTERN,
                terminal_proximity=TerminalProximity.NA,
                base_crossing=EventType.ENDGAME_REACHED,
                salience_floor="critical",
            )


class TestDeriveSeverityCoversAllFiveKinds:
    """The pure rule (design §2), exercised directly for every EventKind."""

    def test_alarm_is_always_critical(self) -> None:
        assert derive_severity(EventKind.ALARM, TerminalProximity.NA) == "critical"

    def test_crossing_terminal_adjacent_is_critical(self) -> None:
        assert (
            derive_severity(EventKind.CROSSING, TerminalProximity.TERMINAL_ADJACENT) == "critical"
        )

    def test_crossing_intra_level_is_informational(self) -> None:
        assert derive_severity(EventKind.CROSSING, TerminalProximity.INTRA_LEVEL) == "informational"

    def test_flow_returns_its_salience_floor(self) -> None:
        assert derive_severity(EventKind.FLOW, TerminalProximity.NA, "warning") == "warning"
        assert (
            derive_severity(EventKind.FLOW, TerminalProximity.NA, "informational")
            == "informational"
        )

    def test_act_returns_its_salience_floor(self) -> None:
        assert derive_severity(EventKind.ACT, TerminalProximity.NA, "warning") == "warning"

    def test_pattern_returns_its_base_crossing_tier(self) -> None:
        assert (
            derive_severity(EventKind.PATTERN, TerminalProximity.NA, None, "critical") == "critical"
        )
        assert (
            derive_severity(EventKind.PATTERN, TerminalProximity.NA, None, "informational")
            == "informational"
        )


class TestDeriveSeverityRaisesOnMalformedInput:
    """Explicit exception handling: malformed calls fail loud, never default silently."""

    def test_crossing_na_proximity_raises(self) -> None:
        with pytest.raises(ValueError, match="CROSSING requires terminal_proximity"):
            derive_severity(EventKind.CROSSING, TerminalProximity.NA)

    @pytest.mark.parametrize("kind", [EventKind.FLOW, EventKind.ACT])
    def test_flow_and_act_missing_floor_raises(self, kind: EventKind) -> None:
        with pytest.raises(ValueError, match="requires a declared salience_floor"):
            derive_severity(kind, TerminalProximity.NA)

    @pytest.mark.parametrize("kind", [EventKind.FLOW, EventKind.ACT])
    def test_flow_and_act_critical_floor_raises(self, kind: EventKind) -> None:
        with pytest.raises(ValueError, match="may never be 'critical'"):
            derive_severity(kind, TerminalProximity.NA, "critical")

    def test_pattern_missing_base_crossing_tier_raises(self) -> None:
        with pytest.raises(ValueError, match="base_crossing's resolved tier"):
            derive_severity(EventKind.PATTERN, TerminalProximity.NA)


class TestSeverityByEventSpotChecks:
    """A handful of representative resolved tiers, cross-referenced against the design."""

    def test_severity_by_event_has_47_entries(self) -> None:
        assert len(SEVERITY_BY_EVENT) == 62  # 47 day-one + 13 P25 (ADR128) + 2 institution (ADR136)

    def test_alarm_family_kind_is_flow_not_alarm(self) -> None:
        # Open owner question §9.1: FLOW (not ALARM) preserves current informational tier.
        for event_type in (
            EventType.CALIBRATION_AXIOM_VIOLATION,
            EventType.CALIBRATION_QCEW_CARRY_FORWARD,
            EventType.CALIBRATION_PHI_HOUR_OUTLIER,
        ):
            assert _row_for(event_type).kind is EventKind.FLOW
            assert SEVERITY_BY_EVENT[event_type] == "informational"

    def test_no_alarm_kind_row_exists_day_one(self) -> None:
        assert not any(row.kind is EventKind.ALARM for row in SEVERITY_TAXONOMY)

    def test_act_members_stay_warning(self) -> None:
        for event_type in (
            EventType.STATE_REPRESSION,
            EventType.POGROM,
            EventType.LOCKOUT,
            EventType.VIGILANTISM,
        ):
            assert SEVERITY_BY_EVENT[event_type] == "warning"

    def test_pattern_members_inherit_their_base_crossing(self) -> None:
        assert SEVERITY_BY_EVENT[EventType.RED_SETTLER_TRAP_DETECTED] == "critical"
        assert SEVERITY_BY_EVENT[EventType.PATTERN_SHIFT] == "critical"


class TestResolveSeverity:
    """:func:`resolve_severity` — the loud unclassified-> warning floor (Constitution III.11)."""

    def test_a_classified_type_resolves_its_tier_not_unclassified(self) -> None:
        severity = resolve_severity(EventType.UPRISING)
        assert severity.tier == "critical"
        assert severity.unclassified is False

    def test_an_unclassified_type_resolves_warning_and_flagged(self) -> None:
        # POPULATION_DEATH is a real EventType absent from SEVERITY_TAXONOMY.
        severity = resolve_severity(EventType.POPULATION_DEATH)
        assert severity.tier == "warning"
        assert severity.unclassified is True

    def test_unclassified_never_degrades_to_informational(self) -> None:
        severity = resolve_severity(EventType.ORGANIZATIONAL_ACTION)
        assert severity.tier != "informational"

    def test_returns_a_frozen_event_severity(self) -> None:
        severity = resolve_severity(EventType.UPRISING)
        with pytest.raises(ValidationError):
            severity.tier = "warning"  # type: ignore[misc]


class TestDriftTable:
    """The generated old-tier -> new-tier reconciliation (design §7)."""

    def test_every_drift_row_actually_differs(self) -> None:
        for row in DRIFT_TABLE:
            assert row.old_tier != row.new_tier

    def test_every_drift_row_has_a_nonempty_rationale(self) -> None:
        for row in DRIFT_TABLE:
            assert row.rationale.strip() != ""

    def test_drift_table_has_exactly_16_rows(self) -> None:
        assert len(DRIFT_TABLE) == 16

    def test_a_stable_critical_member_is_not_in_the_drift_table(self) -> None:
        drifted = {row.event_type for row in DRIFT_TABLE}
        assert EventType.ECONOMIC_CRISIS not in drifted

    def test_bifurcation_threshold_drifted_warning_to_critical(self) -> None:
        row = next(r for r in DRIFT_TABLE if r.event_type is EventType.BIFURCATION_THRESHOLD)
        assert row.old_tier == "warning"
        assert row.new_tier == "critical"

    def test_mass_awakening_drifted_warning_to_informational(self) -> None:
        row = next(r for r in DRIFT_TABLE if r.event_type is EventType.MASS_AWAKENING)
        assert row.old_tier == "warning"
        assert row.new_tier == "informational"


#: The reconciliation pin — the "declared-intended tier per member" the design's mutation test
#: requires. Hand-authored independently of SEVERITY_TAXONOMY's row order so it is a genuine pin,
#: not a restatement of the same code path.
_EXPECTED_TIERS: dict[EventType, SeverityTier] = {
    # Critical (22 = 14 stable + 8 promoted).
    EventType.ECONOMIC_CRISIS: "critical",
    EventType.CLASS_DECOMPOSITION: "critical",
    EventType.SUPERWAGE_CRISIS: "critical",
    EventType.UPRISING: "critical",
    EventType.ENDGAME_REACHED: "critical",
    EventType.POWER_VACUUM: "critical",
    EventType.REVOLUTIONARY_OFFENSIVE: "critical",
    EventType.FASCIST_REVANCHISM: "critical",
    EventType.SPONTANEOUS_RIOT: "critical",
    EventType.PERIPHERAL_REVOLT: "critical",
    EventType.ECOLOGICAL_OVERSHOOT: "critical",
    EventType.RED_BROWN_COUP: "critical",
    EventType.DOCTRINE_TRAP_SPRUNG: "critical",
    EventType.SECESSION_DECLARED: "critical",
    EventType.RED_SETTLER_TRAP_DETECTED: "critical",
    EventType.FASCIST_RECRUITMENT: "critical",
    EventType.DOCTRINE_PURGE_FAILED: "critical",
    EventType.MARKET_CORRECTION: "critical",
    EventType.BIFURCATION_THRESHOLD: "critical",
    EventType.CO_OPTIVE_BREAKDOWN: "critical",
    EventType.LEVEL_TRANSITION: "critical",
    EventType.PATTERN_SHIFT: "critical",
    # --- P25 electoral machine (ADR128), derived tiers ---
    # CROSSING TERMINAL_ADJACENT -> critical; PATTERN inherits BIFURCATION_THRESHOLD (critical).
    EventType.ELECTIONS_SUSPENDED: "critical",
    EventType.POPULAR_FRONT_CALLED: "critical",
    EventType.INSTITUTION_BONAPARTIST_MODE: "critical",  # P25 U10/ADR136
    # ACT/FLOW warning floors.
    EventType.GOVERNMENT_FORMED: "warning",
    EventType.POLICY_STRUCK: "warning",
    EventType.POLICY_PREEMPTED: "warning",
    EventType.CAPITAL_STRIKE: "warning",
    EventType.LINE_STRUGGLE_SPLIT: "warning",
    EventType.INSTITUTION_FACTION_SHIFT: "informational",  # P25 U10/ADR136
    # ACT/FLOW informational floors; CROSSING INTRA_LEVEL -> informational.
    EventType.ELECTION_HELD: "informational",
    EventType.POLICY_ENACTED: "informational",
    EventType.HOPE_SPIKE: "informational",
    EventType.LEGITIMATION_REFRESH: "informational",
    EventType.DELIVERY_GAP_CROSSED: "informational",
    EventType.DISILLUSION_WINDOW_OPEN: "informational",
    # Warning (4, all ACT).
    EventType.STATE_REPRESSION: "warning",
    EventType.POGROM: "warning",
    EventType.LOCKOUT: "warning",
    EventType.VIGILANTISM: "warning",
    # Informational (21 = 13 stable + 8 demoted).
    EventType.SURPLUS_EXTRACTION: "informational",
    EventType.IMPERIAL_SUBSIDY: "informational",
    EventType.CONSCIOUSNESS_TRANSMISSION: "informational",
    EventType.DISPOSSESSION_EVENT: "informational",
    EventType.VALUE_TRANSFER: "informational",
    EventType.RESERVE_ARMY_PRESSURE: "informational",
    EventType.POPULATION_ATTRITION: "informational",
    EventType.EDGE_MODE_TRANSITION: "informational",
    EventType.LATENT_CONTRADICTION_RELEASE: "informational",
    EventType.ASPECT_REVERSAL: "informational",
    EventType.CALIBRATION_AXIOM_VIOLATION: "informational",
    EventType.CALIBRATION_QCEW_CARRY_FORWARD: "informational",
    EventType.CALIBRATION_PHI_HOUR_OUTLIER: "informational",
    EventType.EXCESSIVE_FORCE: "informational",
    EventType.MASS_AWAKENING: "informational",
    EventType.FASCIST_DRIFT: "informational",
    EventType.DISPOSSESSION_CASCADE: "informational",
    EventType.ORGANIZATIONAL_FRACTURE: "informational",
    EventType.DOCTRINE_TRAP_ESCAPED: "informational",
    EventType.ENTITY_DEATH: "informational",
    EventType.CRISIS_PHASE_TRANSITION: "informational",
}


class TestReconciliationPin:
    """Pins every member's derived tier against the hand-authored intended table.

    This is the test the design's mutation requirement names: a code/registry mutation that
    changes a member's derived tier must red THIS test, proving the derivation is load-bearing.
    """

    def test_expected_tiers_covers_every_taxonomy_member(self) -> None:
        assert set(_EXPECTED_TIERS) == {row.event_type for row in SEVERITY_TAXONOMY}

    def test_severity_by_event_matches_the_pinned_intended_table_exactly(self) -> None:
        assert SEVERITY_BY_EVENT == _EXPECTED_TIERS


class TestMutationFlippingTerminalProximity:
    """Mutation test (design §4 U1): flip one row's terminal_proximity.

    Proves two things: (1) :func:`derive_severity` returns a different tier for the mutated row,
    and (2) rebuilding the generated table from the mutated taxonomy disagrees with
    :data:`_EXPECTED_TIERS` — i.e. :class:`TestReconciliationPin`'s pin test would RED were this
    mutation applied to the real module. That is what makes the check load-bearing rather than a
    disguised lookup table: an error in either declared field changes real behavior.
    """

    def test_flipping_mass_awakening_proximity_changes_its_tier_and_reds_the_pin(self) -> None:
        original = _row_for(EventType.MASS_AWAKENING)
        assert original.kind is EventKind.CROSSING
        assert original.terminal_proximity is TerminalProximity.INTRA_LEVEL
        assert SEVERITY_BY_EVENT[EventType.MASS_AWAKENING] == "informational"

        mutated_row = original.model_copy(
            update={"terminal_proximity": TerminalProximity.TERMINAL_ADJACENT}
        )
        mutated_taxonomy = tuple(
            mutated_row if row.event_type is EventType.MASS_AWAKENING else row
            for row in SEVERITY_TAXONOMY
        )
        mutated_table = _build_severity_by_event(mutated_taxonomy)

        # (1) derive_severity itself returns a different tier under the flipped input.
        original_tier = derive_severity(original.kind, original.terminal_proximity)
        mutated_tier = derive_severity(mutated_row.kind, mutated_row.terminal_proximity)
        assert original_tier != mutated_tier
        assert original_tier == "informational"
        assert mutated_tier == "critical"

        # (2) the mutated table disagrees with the pinned intended tier for this member —
        # exactly the disagreement that would red TestReconciliationPin if this mutation were
        # applied to the real SEVERITY_TAXONOMY.
        assert mutated_table[EventType.MASS_AWAKENING] != _EXPECTED_TIERS[EventType.MASS_AWAKENING]

    def test_flipping_a_rows_kind_changes_its_derived_tier(self) -> None:
        original = _row_for(EventType.STATE_REPRESSION)
        assert original.kind is EventKind.ACT

        # ACT/warning -> CROSSING requires a real terminal_proximity too; simulate the flip at
        # the pure-function level (design's own illustrative example: "an ALARM -> FLOW").
        act_tier = derive_severity(EventKind.ACT, TerminalProximity.NA, "warning")
        alarm_tier = derive_severity(EventKind.ALARM, TerminalProximity.NA)
        assert act_tier != alarm_tier
        assert act_tier == "warning"
        assert alarm_tier == "critical"


class TestSeverityNeverNumericAndReadOnlyProjection:
    """E-2 (no numbers in events) + the Amendment-S read-only-projection tripwire."""

    def test_severity_tier_is_a_closed_string_literal(self) -> None:
        from typing import get_args

        assert set(get_args(SeverityTier)) == {"critical", "warning", "informational"}

    def test_no_engine_or_domain_module_references_event_severity(self) -> None:
        """Grep gate: severity is a G∘P read-only projection (Amendment-S), never read back
        into physics. Nothing under babylon/engine or babylon/domain may import this module or
        call its resolver — U6 promotes this to a standing seam-algebra sentinel; this is the
        day-one guard named by U1's acceptance bar.
        """
        pattern = re.compile(r"\bevent_severity\b|\bresolve_severity\b")
        offenders: list[str] = []
        for subpackage in ("engine", "domain"):
            root = _REPO_ROOT / "src" / "babylon" / subpackage
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if pattern.search(text):
                    offenders.append(str(path.relative_to(_REPO_ROOT)))
        assert offenders == [], (
            f"babylon/engine or babylon/domain references event_severity: {offenders} — "
            "severity is a read-only G∘P projection and must never feed back into physics"
        )


class TestDriftRowAndEventSeverityAreFrozen:
    """Every Pydantic construct here is frozen + extra=forbid (design §4 unit conventions)."""

    def test_drift_row_is_frozen(self) -> None:
        row = DriftRow(
            event_type=EventType.MASS_AWAKENING,
            old_tier="warning",
            new_tier="informational",
            rationale="test",
        )
        with pytest.raises(ValidationError):
            row.new_tier = "critical"  # type: ignore[misc]

    def test_event_severity_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            EventSeverity(tier="critical", unclassified=False, bogus="nope")  # type: ignore[call-arg]
