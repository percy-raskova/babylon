//! The clock, the pacing defaults, and the virtual-time discipline (B3
//! wave-1 Task 2, plan `docs/superpowers/plans/2026-08-17-b3-null-hypothesis-viewer.md`
//! §2.1/§2.4). Owns `RunState`, the fixed speed table, the bounded
//! catch-up loop's pure arithmetic core (`ticks_due`), the phase-locked
//! heartbeat (`TickPhase`) and the controls readout — `advance_ticks`
//! (below) replaces `loop_ui::advance_on_space` as the crate's ONE
//! tick-advancing system.
//!
//! **I4 — the virtual-time discipline.** `time.delta_secs()` is read in
//! exactly one place in this whole crate: the line inside `advance_ticks`
//! that adds it to `RunState.accumulator`. Everything downstream of that
//! line — `ticks_due`, `TickPhase`, the readout — is pure arithmetic over
//! that accumulator, never a second read of the clock. Tests drive this
//! deterministically via `bevy::time::TimeUpdateStrategy::ManualDuration`,
//! never the wall clock (memory `program-15-gauntlet`: "wall-clock tests
//! = determinism poison").
//!
//! RED (this commit): `ticks_due` does not exist yet — the pure-arithmetic
//! tests below fail to compile, and so does the crate's `tests/time_controls.rs`,
//! which references `RunState`/`advance_ticks`/`TickPhase`/the readout,
//! none of which exist yet either. Mirrors the `918f9df2` "module absent"
//! RED-commit precedent already established on this branch.

#[cfg(test)]
mod tests {
    use super::ticks_due;

    /// The plan's own worked example (§2.1): "2.5 intervals accumulated
    /// yields exactly 2 ticks and 0.5 remaining."
    #[test]
    fn two_point_five_intervals_yields_two_ticks_and_a_half_remainder() {
        let (ticks, remainder) = ticks_due(2.5, 1.0, 8);
        assert_eq!(ticks, 2);
        assert!((remainder - 0.5).abs() < 1e-6, "got {remainder}");
    }

    /// The plan's own worked example (§2.1): "30 intervals accumulated
    /// yields exactly `max` ticks and a clamped remainder (no
    /// 1,000-tick fast-forward after a stall)." The remainder clamps to
    /// `max * interval`, not to zero — a stalled frame is still allowed
    /// one more full batch's worth of backlog, never more.
    #[test]
    fn thirty_intervals_clamp_to_max_ticks_and_a_clamped_remainder() {
        let (ticks, remainder) = ticks_due(30.0, 1.0, 8);
        assert_eq!(
            ticks, 8,
            "a stalled frame must never advance past `max` ticks in one call"
        );
        assert!(
            (remainder - 8.0).abs() < 1e-6,
            "the leftover accumulator must itself be clamped to at most max*interval, got {remainder}"
        );
    }

    #[test]
    fn zero_accumulator_yields_zero_ticks() {
        let (ticks, remainder) = ticks_due(0.0, 1.0, 8);
        assert_eq!(ticks, 0);
        assert!((remainder - 0.0).abs() < 1e-9, "got {remainder}");
    }

    /// A negative accumulator cannot occur through normal operation (the
    /// only writer, `advance_ticks`, only ever adds a non-negative
    /// `delta_secs()` or resets to `0.0`) — sanitized defensively rather
    /// than trusted, so a future caller cannot propagate a negative
    /// backlog forward.
    #[test]
    fn negative_accumulator_yields_zero_ticks() {
        let (ticks, remainder) = ticks_due(-5.0, 1.0, 8);
        assert_eq!(ticks, 0);
        assert!((remainder - 0.0).abs() < 1e-9, "got {remainder}");
    }
}
