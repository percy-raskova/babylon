//! The transcribed severity taxonomy (B3 wave-1 Task 4, plan
//! `docs/superpowers/plans/2026-08-17-b3-null-hypothesis-viewer.md` §2.2):
//! `derive_severity` reproduces `src/babylon/models/event_severity.py`'s
//! own pure rule (`:229`) verbatim for the four kind arms this crate's
//! landed content ever exercises (ALARM and PATTERN never appear on the
//! wire here — no landed `.bsl` pack emits an invariant-residual or a
//! distinguished-cell event, so this table omits both rather than
//! declaring dead rows), and [`SEVERITY_TAXONOMY`] transcribes the 12
//! rows `event_severity.py::SEVERITY_TAXONOMY` declares for the
//! `EventType`s this wave's two stories actually emit (§2.2's own table).
//!
//! **The drift guard.** `tests/unit/render/test_rust_narration_parity.py`
//! (Task 4.6) parses [`SEVERITY_TAXONOMY`] and asserts every row's
//! `(kind, proximity)` matches the Python module's own
//! `SEVERITY_TAXONOMY` — a §9b-parity-guard-shaped check, the same
//! FFI-boundary-no-import-can-cross precedent `palette.rs`'s own module
//! doc names for `test_rust_theme_parity.py`.
//!
//! RED (this commit): none of `EventKind`, `TerminalProximity`,
//! `SeverityTier`, `derive_severity`, `SeverityRow`, `SEVERITY_TAXONOMY`,
//! `severity_for` exist yet — the test module below fails to compile,
//! mirroring the `d4f353d9` "module absent" RED-commit precedent
//! (`ui/time.rs`'s own module doc).

#[cfg(test)]
mod tests {
    use super::{derive_severity, severity_for, EventKind, SeverityTier, TerminalProximity};

    // ---- derive_severity's four rule arms (event_severity.py:252-274) ----

    #[test]
    fn alarm_always_derives_critical() {
        assert_eq!(
            derive_severity(EventKind::Alarm, TerminalProximity::Na, None),
            Ok(SeverityTier::Critical)
        );
    }

    #[test]
    fn crossing_terminal_adjacent_derives_critical() {
        assert_eq!(
            derive_severity(
                EventKind::Crossing,
                TerminalProximity::TerminalAdjacent,
                None
            ),
            Ok(SeverityTier::Critical)
        );
    }

    #[test]
    fn crossing_terminal_approach_derives_warning() {
        assert_eq!(
            derive_severity(
                EventKind::Crossing,
                TerminalProximity::TerminalApproach,
                None
            ),
            Ok(SeverityTier::Warning)
        );
    }

    #[test]
    fn crossing_intra_level_derives_informational() {
        assert_eq!(
            derive_severity(EventKind::Crossing, TerminalProximity::IntraLevel, None),
            Ok(SeverityTier::Informational)
        );
    }

    #[test]
    fn flow_derives_its_declared_salience_floor_never_critical() {
        assert_eq!(
            derive_severity(
                EventKind::Flow,
                TerminalProximity::Na,
                Some(SeverityTier::Warning)
            ),
            Ok(SeverityTier::Warning)
        );
        assert!(
            derive_severity(
                EventKind::Flow,
                TerminalProximity::Na,
                Some(SeverityTier::Critical)
            )
            .is_err(),
            "a FLOW/ACT floor of Critical is the exact fabrication the taxonomy forbids \
             (event_severity.py's own _validate_flow_or_act_shape)"
        );
    }

    #[test]
    fn act_derives_its_declared_salience_floor_never_critical() {
        assert_eq!(
            derive_severity(
                EventKind::Act,
                TerminalProximity::Na,
                Some(SeverityTier::Informational)
            ),
            Ok(SeverityTier::Informational)
        );
    }

    /// `event_severity.py:229`'s own `ValueError` arm: a CROSSING row with
    /// `terminal_proximity = NA` is a loud error, never a default tier.
    #[test]
    fn crossing_with_na_proximity_is_a_loud_error_not_a_default() {
        let result = derive_severity(EventKind::Crossing, TerminalProximity::Na, None);
        assert!(
            result.is_err(),
            "CROSSING with NA proximity must be a loud Err, never a silently \
             defaulted tier — got {result:?}"
        );
    }

    // ---- SEVERITY_TAXONOMY's 12 transcribed rows resolve to §2.2's table ----

    #[test]
    fn the_twelve_transcribed_rows_resolve_to_the_declared_table() {
        let expected: &[(&str, SeverityTier)] = &[
            ("TERMINAL_DECISION", SeverityTier::Critical),
            ("CONTROL_RATIO_CRISIS", SeverityTier::Critical),
            ("CLASS_DECOMPOSITION", SeverityTier::Critical),
            ("SUPERWAGE_CRISIS", SeverityTier::Critical),
            ("LEGITIMATION_CRISIS", SeverityTier::Warning),
            ("LEGITIMATION_RECOVERY", SeverityTier::Informational),
            ("MASS_AWAKENING", SeverityTier::Informational),
            ("ENTITY_DEATH", SeverityTier::Informational),
            ("LIFECYCLE_TRANSITION", SeverityTier::Informational),
            ("CONSCIOUSNESS_TRANSMISSION", SeverityTier::Informational),
            ("VALUE_TRANSFER", SeverityTier::Informational),
            ("DISPOSSESSION_EVENT", SeverityTier::Informational),
        ];
        assert_eq!(
            expected.len(),
            12,
            "this test's own table must name 12 rows"
        );
        for (event_type, tier) in expected {
            assert_eq!(
                severity_for(event_type),
                *tier,
                "{event_type} must resolve to {tier:?}"
            );
        }
    }

    #[test]
    fn flow_and_act_events_never_resolve_critical() {
        for event_type in [
            "LIFECYCLE_TRANSITION",
            "CONSCIOUSNESS_TRANSMISSION",
            "VALUE_TRANSFER",
            "DISPOSSESSION_EVENT",
        ] {
            assert_ne!(
                severity_for(event_type),
                SeverityTier::Critical,
                "{event_type} is FLOW — it must never resolve critical"
            );
        }
    }

    #[test]
    fn an_unclassified_event_type_resolves_to_the_loud_warning_floor() {
        assert_eq!(
            severity_for("SOME_FUTURE_EVENT_TYPE_NOT_IN_THE_TABLE"),
            SeverityTier::Warning,
            "event_severity.py::resolve_severity's own loud floor: unclassified -> \
             warning, never a quiet informational degrade"
        );
    }
}
