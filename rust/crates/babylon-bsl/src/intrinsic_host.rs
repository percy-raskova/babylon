//! The named-intrinsic call boundary (§2.7: transcendentals "are **never**
//! language primitives — they exist only as named intrinsics with pinned
//! deterministic implementations"). Phase 1 defines the trait only; the
//! kernel's full intrinsic table (Phase 2, gated on the Task 8 ruling —
//! ADR176 r21, pinned soft-float libm + golden vectors) is future work for
//! the `{exp, log}` transcendental pair and `round-half-even`.
//!
//! `floor` (ADR188 Row 2, §3.10 / Draft-Ruling Register D97) lands early
//! and separately from that gate: it is not a transcendental, needs no
//! pinned soft-float libm crate, and crosses via `f64::floor` — IEEE-754's
//! own `roundToIntegralTowardNegative`, exactly specified by the standard
//! itself (not by §4.3, whose closed basic-op list is `+ − × ÷` and
//! comparison only; its golden-vector clause is for transcendentals). ADR188's
//! "libm golden vectors at implementation" consequence therefore does not
//! apply to this rider — there is no libm crossing to pin a vector against
//! — and this is that consequence's explicit disposition, not a silent
//! omission. [`KernelIntrinsicHost`] is this crate's first non-empty,
//! non-test-only [`IntrinsicHost`] — wired into `babylon-tick::run_once_into`
//! (the production seam the CLI driver and `babylon-client`'s engine link
//! both call), not merely constructed in a test module.

use crate::evaluator::{EvalCode, EvalError, Value};

/// Dispatches a named intrinsic call. The declared signature/cost checks
/// (`E-LOAD-020`/`E-LOAD-021`) are load-time gates; a host's failure here is
/// the evaluator's defense-in-depth, not the primary rejection point.
pub trait IntrinsicHost {
    /// Dispatch `name` over already-evaluated positional args.
    ///
    /// # Errors
    ///
    /// [`EvalError`] when `name` is not provided by this host, or when the
    /// pinned implementation itself rejects the inputs.
    fn call(&self, name: &str, args: &[Value]) -> Result<Value, EvalError>;
}

/// A host with no registered intrinsics at all — every call fails loud.
/// Used by Phase-1 tests that exercise only arithmetic/comparison/boolean
/// forms, which never cross the intrinsic boundary.
pub struct EmptyIntrinsicHost;

impl IntrinsicHost for EmptyIntrinsicHost {
    fn call(&self, name: &str, _args: &[Value]) -> Result<Value, EvalError> {
        Err(EvalError::plain(format!(
            "no intrinsic registered: {name} (the kernel table is Phase 2)"
        )))
    }
}

/// The kernel's intrinsic table, as far as it is implemented today: `floor`
/// alone (ADR188 Row 2). `{exp, log}` and `round-half-even` remain
/// undispatchable here — they are declarable (`declarations::
/// DECLARABLE_INTRINSICS` for the first pair) but their evaluation is
/// Phase 2 work this host does not perform, so a call to either fails loud
/// exactly as [`EmptyIntrinsicHost`] would, rather than silently succeeding
/// with a placeholder value.
pub struct KernelIntrinsicHost;

impl IntrinsicHost for KernelIntrinsicHost {
    fn call(&self, name: &str, args: &[Value]) -> Result<Value, EvalError> {
        match name {
            "floor" => eval_floor(args),
            other => Err(EvalError::plain(format!(
                "no intrinsic registered: {other} (only 'floor' — ADR188 Row 2 — is \
                 implemented today; the {{exp, log}} transcendental cap and \
                 round-half-even remain Phase 2 work)"
            ))),
        }
    }
}

/// `2^63` as an `f64` — the exact, exclusive upper bound a `floor` result
/// must clear to convert losslessly to `i64` (`i64::MAX` itself is not
/// exactly representable in binary64; rounding it up to the nearest
/// representable value gives this constant, per `i64::MAX as f64`).
const I64_DOMAIN_CEILING: f64 = 9_223_372_036_854_775_808.0;

/// The `floor` intrinsic (ADR188 Row 2 rider): `Real → int`.
///
/// **Domain: `[0, ∞)`, matching the ratified call sites** — the frozen
/// estate's integer-PEOPLE demotions (`vitality.py::_calculate_deaths`:
/// `population` guarded `> 0` and `attrition_rate` clamped to `[0, 1]`
/// before `deaths = int(population * attrition_rate)`;
/// `decomposition.py`: `la_population <= 0` returns early, and
/// `enforcer_fraction`/`proletariat_fraction` are pydantic-constrained
/// non-negative fractions (`config/defines/territory.py`) before
/// `enforcer_pop_gain`/`proletariat_pop`). Not a claim of §3.4 — the
/// intensivity kind rule says nothing about sign — and not "wealth
/// counts" either: `decomposition.py`'s wealth lines
/// (`enforcer_wealth_gain`/`proletariat_wealth`) are NOT `int()`-demoted,
/// only the population lines are. On the ratified domain `floor` and
/// `trunc` — the rider's own paired candidate name, ADR188 Row 2 — are the
/// SAME function, which is exactly why the rider does not have to choose
/// between them. This implementation therefore does not choose either: a
/// negative argument is refused rather than silently rounded one way or
/// the other, so no unratified convention for the disputed domain is
/// baked in by construction (III.11 — a loud failure, never a
/// silently-picked default, matches the §3.3 anti-clamp precedent this
/// document already sets for bounded-scalar arithmetic).
///
/// **A non-`Real`-lane argument is refused, never coerced.** §3.3 promotes
/// `Int` to `Real` only *within* a binary64 expression (`+ − × ÷` and
/// comparison); it says nothing about the intrinsic-call boundary, and no
/// static typechecker exists yet to enforce a declared `:params` type
/// against a call site's argument type (Phase 2 work — §2.7). A bare
/// `(floor 5)` — an `Int` literal, not the result of arithmetic — is
/// therefore an uncoded, structural rejection here: consistent with the
/// no-coercions rule (§3.1) and with `IntrinsicHost`'s own contract that a
/// host's failure is defense-in-depth, not the primary rejection point.
/// Every ratified call site passes the *result* of `population * rate`,
/// which the evaluator's binary64 promotion already makes `Real` before it
/// ever reaches this function.
///
/// # Errors
///
/// [`EvalError`] coded [`EvalCode::DemotionOutOfDomain`] (`E-EVAL-039`) for
/// a negative, non-finite, or `i64`-overflowing argument; [`EvalError::plain`]
/// for a malformed call (wrong arity or a non-`Real` argument — a load-time
/// gate's defense-in-depth, per this module's `IntrinsicHost` contract).
fn eval_floor(args: &[Value]) -> Result<Value, EvalError> {
    let [Value::Real(x)] = args else {
        return Err(EvalError::plain(format!(
            "floor takes exactly one Real-lane argument, got {args:?}"
        )));
    };
    let x = *x;
    if !x.is_finite() {
        return Err(EvalError::coded(
            EvalCode::DemotionOutOfDomain,
            format!(
                "floor of a non-finite value ({x}): E-EVAL-039 — outside the \
                 ratified [0, ∞) domain (ADR188 Row 2)"
            ),
        ));
    }
    if x < 0.0 {
        return Err(EvalError::coded(
            EvalCode::DemotionOutOfDomain,
            format!(
                "floor of a negative value ({x}): E-EVAL-039 — ADR188 Row 2 ratifies \
                 the demotion over [0, ∞) (integer-people counts); floor and trunc \
                 disagree below zero and this rider does not pick one"
            ),
        ));
    }
    let floored = x.floor();
    if floored >= I64_DOMAIN_CEILING {
        return Err(EvalError::coded(
            EvalCode::DemotionOutOfDomain,
            format!("floor({x}) = {floored} exceeds Int's i64 domain (§3.1): E-EVAL-039"),
        ));
    }
    #[allow(clippy::cast_possible_truncation)]
    // In range by the check above; never a silent wraparound.
    Ok(Value::Int(floored as i64))
}

#[cfg(test)]
mod tests {
    use super::{EvalCode, IntrinsicHost, KernelIntrinsicHost, Value};

    fn floor(x: f64) -> Result<Value, crate::evaluator::EvalError> {
        KernelIntrinsicHost.call("floor", &[Value::Real(x)])
    }

    #[test]
    fn floor_of_zero_is_zero() {
        assert_eq!(floor(0.0), Ok(Value::Int(0)));
    }

    /// The mutation-catching case: a ceiling (or round-half-even, or any
    /// convention that rounds up) would answer `4`, not `3`. If a future
    /// edit flips `x.floor()` to `x.ceil()` — or reverses the comparison
    /// direction anywhere in this function — this assertion fails.
    #[test]
    fn floor_of_a_fractional_value_rounds_toward_zero_not_away_from_it() {
        assert_eq!(floor(3.9), Ok(Value::Int(3)));
        assert_eq!(floor(0.1), Ok(Value::Int(0)));
    }

    #[test]
    fn floor_of_an_exact_integer_is_unchanged() {
        assert_eq!(floor(5.0), Ok(Value::Int(5)));
    }

    /// The domain boundary: `floor` and `trunc` are the SAME function on
    /// `[0, ∞)`, so a large positive value in range must succeed exactly
    /// like the small ones above.
    #[test]
    fn floor_of_a_large_in_range_value_succeeds() {
        assert_eq!(floor(1_000_000.7), Ok(Value::Int(1_000_000)));
    }

    #[test]
    fn floor_of_a_negative_value_is_e_eval_039_not_a_silent_pick() {
        let err = floor(-0.1).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::DemotionOutOfDomain));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-039");
    }

    #[test]
    fn floor_of_negative_zero_is_accepted_zero_not_rejected() {
        // -0.0 < 0.0 is false in IEEE-754, so this stays in-domain — a
        // regression guard against an implementation that tests the sign
        // bit instead of the value.
        assert_eq!(floor(-0.0), Ok(Value::Int(0)));
    }

    #[test]
    fn floor_of_nan_is_e_eval_039() {
        let err = floor(f64::NAN).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::DemotionOutOfDomain));
    }

    #[test]
    fn floor_of_infinity_is_e_eval_039() {
        assert_eq!(
            floor(f64::INFINITY).unwrap_err().code,
            Some(EvalCode::DemotionOutOfDomain)
        );
        assert_eq!(
            floor(f64::NEG_INFINITY).unwrap_err().code,
            Some(EvalCode::DemotionOutOfDomain)
        );
    }

    #[test]
    fn floor_of_a_value_exceeding_i64_range_is_e_eval_039_never_a_wraparound() {
        let err = floor(1e30).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::DemotionOutOfDomain));
    }

    #[test]
    fn floor_at_exactly_the_i64_domain_ceiling_is_rejected() {
        // i64::MAX itself is not exactly representable in f64; the nearest
        // representable value is 2^63, which is already one past the true
        // maximum — so a floor result AT that boundary must reject, not
        // silently saturate to i64::MAX.
        let err = floor(super::I64_DOMAIN_CEILING).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::DemotionOutOfDomain));
    }

    /// The accept side of that same boundary, at real magnitude — not
    /// `1e6` (too small to catch a mutated ceiling; a verifier confirmed a
    /// ceiling of `2_000_000.0` still passed the whole suite before this
    /// row existed, and that mutation already rejects a US-population-scale
    /// call site, ~3.3e8). `9_223_372_036_854_774_784.0` is the LARGEST
    /// `f64` strictly below `2^63` (binary64's spacing near `2^63` is
    /// `2^10 = 1024`, so `2^63 - 1024`) and fits exactly in `i64` — it must
    /// succeed, byte-exact, never rejected and never rounded to a
    /// different in-range value.
    #[test]
    fn floor_accepts_the_largest_f64_strictly_below_the_i64_domain_ceiling() {
        assert_eq!(
            floor(9_223_372_036_854_774_784.0),
            Ok(Value::Int(9_223_372_036_854_774_784))
        );
    }

    #[test]
    fn floor_rejects_a_non_real_argument_rather_than_coercing() {
        assert!(KernelIntrinsicHost.call("floor", &[Value::Int(3)]).is_err());
        assert!(KernelIntrinsicHost.call("floor", &[]).is_err());
        assert!(KernelIntrinsicHost
            .call("floor", &[Value::Real(1.0), Value::Real(2.0)])
            .is_err());
    }

    #[test]
    fn an_undeclared_name_fails_loud_exactly_like_the_empty_host() {
        assert!(KernelIntrinsicHost
            .call("exp", &[Value::Real(1.0)])
            .is_err());
        assert!(KernelIntrinsicHost
            .call("round-half-even", &[Value::Real(1.0)])
            .is_err());
    }
}
