//! The named-intrinsic call boundary (§2.7: transcendentals "are **never**
//! language primitives — they exist only as named intrinsics with pinned
//! deterministic implementations"). Phase 1 defined the trait only.
//! `{exp, log}` now dispatch too (Task 2 of the #576 intrinsic-host train —
//! R10/ADR176 r21, pinned soft-float libm + golden vectors, via
//! `babylon_kernel::transcendental`); `rng-draw` dispatches as of Task 5
//! (ADR188 Row 11, D69, plan §3.2/§3.3) — the kernel-seeded, KEYED (never
//! streamed) deterministic draw, via `babylon_kernel::KernelRng`.
//! `round-half-even` remains future work — ADR188 Row 3 is ratified but not
//! yet landed in `declarations::DECLARABLE_INTRINSICS`
//! (`declarations.rs:742-746`).
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
use babylon_graph::substrate::NodeId;
use babylon_kernel::{KernelRng, SessionId};
use std::collections::HashMap;

/// The non-operand half of a draw key (plan §3.3/§3.5, D69): `session` and
/// `tick` are kernel-supplied and are **never operands** — a rule cannot
/// name them, only the driver that runs the tick can. `domain` is the
/// firing rule's own id string (§3.3's "domain = the rule id", chosen over
/// D69's enum operand — undeclarable today without a §5.6-CAS-touching
/// grammar widening, and content cannot even NAME a stream this way, only
/// mint a new rule, which is already hash-covered content). `subject` is
/// the CURRENT subject's Task-3 content id (`babylon_bsl::scenario::
/// LoadedScenario::node_content_ids`), never its `NodeId` handle — keying
/// on the handle would be replay-deterministic but insertion-history-
/// dependent (plan §3.4), exactly the butterfly ADR176 r20 forbids.
///
/// `node_content_ids` is the SAME Task-3 map, threaded through so
/// `evaluator::eval_intrinsic` can resolve the §2.6 chapter C8 element
/// stack (`EvalEnv::elements`) — `it`/`:as` may name a node OTHER than
/// `self` (a neighbor materialized by `exists`/`for-each`/a fold) — to
/// content ids too, the same grain-invariance guarantee `subject` gets.
/// This is plumbing only in this task (Task 4, #576 intrinsic-host train):
/// no intrinsic reads any of it yet — `rng-draw` (Task 5) is the first
/// consumer, per plan §3.3's `stable_key` composition.
pub struct DrawContext<'a> {
    /// The host's construction-time session id — never an operand (D69).
    pub session: &'a SessionId,
    /// The host's construction-time tick — never an operand (D69).
    pub tick: u64,
    /// The firing rule's own id string (§3.3).
    pub domain: &'a str,
    /// The current subject's Task-3 content id (§3.4).
    pub subject: &'a str,
    /// The Task-3 `NodeId -> content id` map, for resolving `it`/`:as`
    /// elements that name a node other than `self`.
    ///
    /// **Type-distinct, not value-distinct (review round 2, #576 I2).**
    /// `None` means "no scenario was hydrated in this call path" — this
    /// crate's own hand-built `MemoryGraph` fixtures, which never go
    /// through `scenario::load_scenario`. `Some(map)` means "hydrated",
    /// even when `map` is empty (a declarations-only scenario, zero
    /// `(node …)` forms) — a `NodeId` miss against `Some(map)` is ALWAYS a
    /// hard error, `map.is_empty()` or not, because `is_empty()` alone
    /// cannot distinguish "never hydrated" from "hydrated with zero
    /// nodes", and only the FORMER legitimizes the NodeId-Debug fallback.
    /// Collapsing that distinction into one `&HashMap` + an
    /// `is_empty()`-gated fallback (the review-round-1 shape) let a
    /// pre-populated caller graph + a declarations-only scenario silently
    /// feed insertion-order `NodeId` handles into `stable_key` — see
    /// `evaluator::element_content_id`'s own doc for the full failure
    /// scenario this type distinction closes.
    pub node_content_ids: Option<&'a HashMap<NodeId, String>>,
}

/// The full context one `IntrinsicHost::call` sees: the optional
/// [`DrawContext`] (`None` for a pure-expression caller — `:expr` binding
/// resolution, the arithmetic conformance vectors — which makes `rng-draw`
/// fail loud rather than silently draw `0.0`, plan §3.5) plus the §2.6
/// chapter C8 element stack, already resolved to content ids,
/// OUTERMOST-FIRST (`EvalEnv::elements`'s own order) — a `Element::Node`
/// resolves to its bare content id; a `Element::Edge` resolves to its two
/// endpoints' content ids composed by `framed` into ONE chain entry
/// (plan §3.5's own wording: "its two endpoints' content ids, framed").
///
/// Every intrinsic that is not `rng-draw` ignores this entirely —
/// `floor`/`exp`/`log` gain the parameter only because the trait's
/// signature is shared, never because they read it.
pub struct IntrinsicCallCtx<'a> {
    /// `None` for a pure-expression caller (see this struct's own doc).
    pub draw_context: Option<&'a DrawContext<'a>>,
    /// The resolved element-content-id chain, outermost-first. Empty for
    /// every call made with no element stack in scope (no enclosing
    /// `exists`/`for-each`/fold/selection).
    pub element_content_ids: Vec<String>,
}

impl IntrinsicCallCtx<'_> {
    /// The context a pure-expression caller passes: no [`DrawContext`], no
    /// element chain. Named for the same "pure-expression caller" class
    /// this module's own doc and `EvalEnv::graph`'s doc already use —
    /// `:expr` binding resolution, the arithmetic conformance vectors,
    /// and every `EmptyIntrinsicHost` test path.
    #[must_use]
    pub fn context_free() -> Self {
        Self {
            draw_context: None,
            element_content_ids: Vec::new(),
        }
    }
}

/// Compose string segments into ONE string, injective by construction
/// (plan §3.3): each segment is emitted as `<decimal-len> ":" <segment>`,
/// segments joined by `"|"` — mirroring `babylon_kernel::rng::seed_for`'s
/// own length-prefix discipline, so two different segment chains can never
/// render to the same string (no ambiguity from where one segment ends and
/// the next begins).
#[must_use]
pub(crate) fn framed(segments: &[&str]) -> String {
    segments
        .iter()
        .map(|segment| format!("{}:{segment}", segment.len()))
        .collect::<Vec<_>>()
        .join("|")
}

/// Dispatches a named intrinsic call. The declared signature/cost checks
/// (`E-LOAD-020`/`E-LOAD-021`) are load-time gates; a host's failure here is
/// the evaluator's defense-in-depth, not the primary rejection point.
pub trait IntrinsicHost {
    /// Dispatch `name` over already-evaluated positional args, with the
    /// calling context (`ctx`, Task 4 of the #576 intrinsic-host train —
    /// plan §3.5) available for an intrinsic that needs it (`rng-draw`,
    /// Task 5). Every intrinsic implemented today (`floor`/`exp`/`log`) is
    /// context-free and ignores `ctx` entirely.
    ///
    /// # Errors
    ///
    /// [`EvalError`] when `name` is not provided by this host, or when the
    /// pinned implementation itself rejects the inputs.
    fn call(
        &self,
        name: &str,
        args: &[Value],
        ctx: IntrinsicCallCtx<'_>,
    ) -> Result<Value, EvalError>;
}

/// A host with no registered intrinsics at all — every call fails loud.
/// Used by Phase-1 tests that exercise only arithmetic/comparison/boolean
/// forms, which never cross the intrinsic boundary.
pub struct EmptyIntrinsicHost;

impl IntrinsicHost for EmptyIntrinsicHost {
    fn call(
        &self,
        name: &str,
        _args: &[Value],
        _ctx: IntrinsicCallCtx<'_>,
    ) -> Result<Value, EvalError> {
        Err(EvalError::plain(format!(
            "no intrinsic registered: {name} (the kernel table is Phase 2)"
        )))
    }
}

/// The kernel's intrinsic table, as far as it is implemented today: `floor`
/// (ADR188 Row 2), `{exp, log}` (R10/ADR176 r21, ADR188 cap, Task 2 of the
/// #576 intrinsic-host train) — both cross via `babylon_kernel::
/// transcendental`, pinned soft-float `libm 0.2.16` — and `rng-draw`
/// (ADR188 Row 11, D69, Task 5 of the same train) — the kernel-seeded,
/// KEYED draw, via `babylon_kernel::KernelRng`. `round-half-even` remains
/// undispatchable: it is declarable in principle (ADR188 Row 3, ratified)
/// but not yet in `declarations::DECLARABLE_INTRINSICS`, so a call to it
/// still fails loud exactly as [`EmptyIntrinsicHost`] would, rather than
/// silently succeeding with a placeholder value.
pub struct KernelIntrinsicHost;

impl IntrinsicHost for KernelIntrinsicHost {
    fn call(
        &self,
        name: &str,
        args: &[Value],
        ctx: IntrinsicCallCtx<'_>,
    ) -> Result<Value, EvalError> {
        match name {
            "floor" => eval_floor(args),
            "exp" => eval_exp(args),
            "log" => eval_log(args),
            "rng-draw" => eval_rng_draw(args, &ctx),
            other => Err(EvalError::plain(format!(
                "no intrinsic registered: {other} ('floor' — ADR188 Row 2 —, the \
                 {{exp, log}} transcendental pair — R10/ADR176 r21 — and 'rng-draw' \
                 — ADR188 Row 11, D69 — are implemented today; round-half-even \
                 remains Phase 2 work, ADR188 Row 3 ratified but not yet landed in \
                 DECLARABLE_INTRINSICS)"
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

/// The `exp` intrinsic (R10/ADR176 r21, ADR188 cap): `Real → Real`, *e*ˣ via
/// the pinned soft-float crossing (`babylon_kernel::transcendental::exp`,
/// `libm 0.2.16`, `default-features = false` — see that module's doc for the
/// verified dispatch analysis).
///
/// **Domain.** `exp` has no mathematical domain restriction over the reals
/// (`babylon_kernel::transcendental::exp`'s own doc: "`f64` has no domain
/// restriction for `exp`"), so the only argument-side rejection is
/// non-finiteness: `NaN`/`±inf` are not real numbers, so never a legal
/// input, coded [`EvalCode::TranscendentalOutOfDomain`] (`E-EVAL-043`).
/// **This check is load-bearing, not defense in depth mirroring `floor`'s**:
/// `exp(-inf)` is mathematically `0.0` — a FINITE result — so without this
/// check a `NEG_INFINITY` argument would silently succeed with
/// `Ok(Value::Real(0.0))` rather than being refused.
///
/// **Result.** A finite input can still overflow the pinned crossing to
/// `±inf` (e.g. `exp(1e10)`); that is [`EvalCode::NonFinite`] (`E-EVAL-014`),
/// the same code §4.3 already uses for every other binary64 operation
/// producing a non-finite result — never a new code for the same law
/// re-checked at a new call site.
///
/// **A non-`Real`-lane argument is refused, never coerced** — same
/// no-coercions rule as `eval_floor` above (§3.1, §3.3): the intrinsic-call
/// boundary does not promote `Int` to `Real`.
///
/// # Errors
///
/// [`EvalError`] coded [`EvalCode::TranscendentalOutOfDomain`]
/// (`E-EVAL-043`) for a non-finite argument; coded [`EvalCode::NonFinite`]
/// (`E-EVAL-014`) for a non-finite result; [`EvalError::plain`] for a
/// malformed call (wrong arity or a non-`Real` argument).
fn eval_exp(args: &[Value]) -> Result<Value, EvalError> {
    let [Value::Real(x)] = args else {
        return Err(EvalError::plain(format!(
            "exp takes exactly one Real-lane argument, got {args:?}"
        )));
    };
    let x = *x;
    if !x.is_finite() {
        return Err(EvalError::coded(
            EvalCode::TranscendentalOutOfDomain,
            format!(
                "exp of a non-finite value ({x}): E-EVAL-043 — NaN/±inf are not \
                 real numbers, so never a legal e^x argument (R10/ADR176 r21)"
            ),
        ));
    }
    let result = babylon_kernel::transcendental::exp(x);
    if !result.is_finite() {
        return Err(EvalError::coded(
            EvalCode::NonFinite,
            format!("exp({x}) produced a non-finite result ({result}): E-EVAL-014"),
        ));
    }
    Ok(Value::Real(result))
}

/// The `log` intrinsic (R10/ADR176 r21, ADR188 cap): `Real → Real`, the
/// natural logarithm via the pinned soft-float crossing
/// (`babylon_kernel::transcendental::ln`).
///
/// **Domain: `(0, ∞)`.** Unlike `exp`, `log` has a genuine mathematical
/// domain restriction, checked in two steps mirroring [`eval_exp`]'s
/// structure: a non-finite argument (`NaN`/`±inf`) is refused first, coded
/// [`EvalCode::TranscendentalOutOfDomain`] (`E-EVAL-043`) — load-bearing for
/// the same reason as `exp`'s: `log(+inf)` clears the `x <= 0.0` check below
/// (`+inf > 0.0`) and would otherwise fall through to the crossing, which
/// returns `+inf` — itself non-finite, so the call would still fail, but
/// coded [`EvalCode::NonFinite`] instead of the domain code, which is the
/// wrong reason. A non-positive argument is refused second, same code:
/// `x <= 0.0` catches `-0.0` too (`-0.0 <= 0.0` is `true`) — the mirror of
/// `floor`'s negative-zero row, which *accepts* `-0.0` because `-0.0 < 0.0`
/// is `false`. `log` rejects it instead, because `0.0`/`-0.0` sit exactly
/// on the excluded domain boundary.
///
/// **Result.** As `exp`: a non-finite result from the crossing itself
/// (unreachable for any finite `x > 0.0` at `f64` precision, but checked
/// as defense in depth per this crate's own precedent, e.g. `Ratio`'s
/// re-check in `evaluator.rs`) is [`EvalCode::NonFinite`] (`E-EVAL-014`).
///
/// # Errors
///
/// [`EvalError`] coded [`EvalCode::TranscendentalOutOfDomain`]
/// (`E-EVAL-043`) for a non-finite or non-positive argument; coded
/// [`EvalCode::NonFinite`] (`E-EVAL-014`) for a non-finite result;
/// [`EvalError::plain`] for a malformed call (wrong arity or a non-`Real`
/// argument).
fn eval_log(args: &[Value]) -> Result<Value, EvalError> {
    let [Value::Real(x)] = args else {
        return Err(EvalError::plain(format!(
            "log takes exactly one Real-lane argument, got {args:?}"
        )));
    };
    let x = *x;
    if !x.is_finite() {
        return Err(EvalError::coded(
            EvalCode::TranscendentalOutOfDomain,
            format!(
                "log of a non-finite value ({x}): E-EVAL-043 — outside log's \
                 (0, ∞) domain (R10/ADR176 r21)"
            ),
        ));
    }
    if x <= 0.0 {
        return Err(EvalError::coded(
            EvalCode::TranscendentalOutOfDomain,
            format!(
                "log of a non-positive value ({x}): E-EVAL-043 — log's ratified \
                 domain is (0, ∞); -0.0 is rejected too (-0.0 <= 0.0)"
            ),
        ));
    }
    let result = babylon_kernel::transcendental::ln(x);
    if !result.is_finite() {
        return Err(EvalError::coded(
            EvalCode::NonFinite,
            format!("log({x}) produced a non-finite result ({result}): E-EVAL-014"),
        ));
    }
    Ok(Value::Real(result))
}

/// The `rng-draw` intrinsic (ADR188 Row 11, D69, plan §3.2/§3.3, Task 5 of
/// the #576 intrinsic-host train): `Int → Real`, the kernel-seeded, KEYED
/// (never streamed) deterministic draw on `[0, 1)`.
///
/// **Not a transcendental.** No libm crossing, no golden vector — the
/// crossing is `babylon_kernel::KernelRng::for_carrier(…).next_f64()`, which
/// is already fully pinned and tested at the kernel layer (`rng.rs`'s own
/// conformance vector). This function's only job is composing the carrier
/// key and calling that crossing exactly once.
///
/// **The carrier key (plan §3.3):**
///
/// ```text
/// session      := ctx.draw_context.session   (kernel-supplied, never an operand — D69)
/// tick         := ctx.draw_context.tick      (kernel-supplied, never an operand — D69)
/// domain       := ctx.draw_context.domain    (the firing rule's own id string)
/// stable_key   := framed( subject_content_id
///                       , element_content_id … outermost→innermost
///                       , slot )
/// ```
///
/// `stable_key` is built by [`framed`] over the subject's content id, then
/// every resolved element in `ctx.element_content_ids` (outermost-first,
/// the SAME order the §2.6 chapter C8 element stack keeps), then the draw
/// slot rendered as its decimal `i64` text — one call, one draw, at stream
/// index 0. **The host holds no state**: a fresh [`KernelRng`] is
/// constructed for this call alone and discarded when it returns, so a
/// skipped draw (a guard suppressing one subject's call) cannot shift any
/// OTHER subject's draw — there is no shared stream position to perturb
/// (D69's own load-bearing clause, preserved verbatim by this
/// implementation, not merely by convention).
///
/// **The slot argument is refused, never coerced, if it is not `Int`** —
/// same no-coercions rule as `eval_floor`/`eval_exp`/`eval_log` (§3.1,
/// §3.3): `kernel_signature("rng-draw")` declares `:params (int)`, and this
/// is the host's own defense-in-depth re-check, not the primary rejection
/// point (no static typechecker exists yet to enforce a declared `:params`
/// type against a call site's argument type — the same gap those three
/// functions' own docs already name).
///
/// **A call with no [`DrawContext`] is a loud `Err`, never a silent
/// `0.0`** (III.11) — `ctx.draw_context` is `None` for every pure-expression
/// caller (`:expr` binding resolution, the arithmetic conformance vectors,
/// every `EmptyIntrinsicHost` test path); a driver that never supplied a
/// session/tick has no carrier key to compose, so this fails loud naming
/// the missing session/tick rather than guessing one.
///
/// # Errors
///
/// [`EvalError::plain`] for a malformed call (wrong arity or a non-`Int`
/// slot argument) or for a call reached with no [`DrawContext`] in scope.
fn eval_rng_draw(args: &[Value], ctx: &IntrinsicCallCtx<'_>) -> Result<Value, EvalError> {
    let [Value::Int(slot)] = args else {
        return Err(EvalError::plain(format!(
            "rng-draw takes exactly one Int-lane argument (the draw slot), got {args:?}"
        )));
    };
    let Some(draw_context) = ctx.draw_context else {
        return Err(EvalError::plain(
            "rng-draw called with no DrawContext — missing session/tick \
             (III.11: a driver that never supplied a session/tick fails \
             loud, never silently draws 0.0)"
                .to_owned(),
        ));
    };
    let slot_text = slot.to_string();
    let mut segments: Vec<&str> = Vec::with_capacity(ctx.element_content_ids.len() + 2);
    segments.push(draw_context.subject);
    for element in &ctx.element_content_ids {
        segments.push(element.as_str());
    }
    segments.push(&slot_text);
    let stable_key = framed(&segments);
    let mut rng = KernelRng::for_carrier(
        draw_context.session,
        draw_context.tick,
        draw_context.domain,
        &stable_key,
    );
    Ok(Value::Real(rng.next_f64()))
}

#[cfg(test)]
mod tests {
    use super::{EvalCode, IntrinsicCallCtx, IntrinsicHost, KernelIntrinsicHost, Value};

    fn floor(x: f64) -> Result<Value, crate::evaluator::EvalError> {
        KernelIntrinsicHost.call("floor", &[Value::Real(x)], IntrinsicCallCtx::context_free())
    }

    fn exp(x: f64) -> Result<Value, crate::evaluator::EvalError> {
        KernelIntrinsicHost.call("exp", &[Value::Real(x)], IntrinsicCallCtx::context_free())
    }

    fn log(x: f64) -> Result<Value, crate::evaluator::EvalError> {
        KernelIntrinsicHost.call("log", &[Value::Real(x)], IntrinsicCallCtx::context_free())
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
        assert!(KernelIntrinsicHost
            .call("floor", &[Value::Int(3)], IntrinsicCallCtx::context_free())
            .is_err());
        assert!(KernelIntrinsicHost
            .call("floor", &[], IntrinsicCallCtx::context_free())
            .is_err());
        assert!(KernelIntrinsicHost
            .call(
                "floor",
                &[Value::Real(1.0), Value::Real(2.0)],
                IntrinsicCallCtx::context_free()
            )
            .is_err());
    }

    #[test]
    fn an_undeclared_name_fails_loud_exactly_like_the_empty_host() {
        // `exp` is no longer undeclared as of this task — see the `exp`/`log`
        // tests below. `round-half-even` stays failing: ADR188 Row 3 is
        // ratified but not yet landed in `declarations::DECLARABLE_INTRINSICS`
        // (`declarations.rs:742-746`).
        assert!(KernelIntrinsicHost
            .call(
                "round-half-even",
                &[Value::Real(1.0)],
                IntrinsicCallCtx::context_free()
            )
            .is_err());
    }

    #[test]
    fn exp_of_zero_is_one() {
        assert_eq!(exp(0.0), Ok(Value::Real(1.0)));
    }

    #[test]
    fn log_of_one_is_zero() {
        assert_eq!(log(1.0), Ok(Value::Real(0.0)));
    }

    #[test]
    fn log_of_zero_is_transcendental_out_of_domain() {
        let err = log(0.0).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::TranscendentalOutOfDomain));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-043");
    }

    #[test]
    fn log_of_a_negative_value_is_transcendental_out_of_domain() {
        let err = log(-1.0).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::TranscendentalOutOfDomain));
    }

    /// The mirror of `floor_of_negative_zero_is_accepted_zero_not_rejected`:
    /// there, `-0.0 < 0.0` is `false`, so `floor` accepts. Here, `log`'s own
    /// domain check is `x <= 0.0`, and `-0.0 <= 0.0` is `true` — so `log`
    /// rejects, and a mutation that swapped this comparison for `<` (making
    /// `-0.0` slip through to `babylon_kernel::transcendental::ln`, which
    /// returns `-inf` for `0.0`/`-0.0`) would flip this test, catching the
    /// swap at the domain guard rather than downstream at the non-finite
    /// result guard.
    #[test]
    fn log_of_negative_zero_is_rejected_not_accepted() {
        let err = log(-0.0).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::TranscendentalOutOfDomain));
    }

    #[test]
    fn exp_of_a_large_value_overflows_to_a_non_finite_result() {
        let err = exp(1e10).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::NonFinite));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-014");
    }

    #[test]
    fn exp_rejects_a_non_real_argument_rather_than_coercing() {
        assert!(KernelIntrinsicHost
            .call("exp", &[Value::Int(5)], IntrinsicCallCtx::context_free())
            .is_err());
        assert!(KernelIntrinsicHost
            .call("exp", &[], IntrinsicCallCtx::context_free())
            .is_err());
    }

    /// The non-finite-**input** guard, isolated from the non-finite-**result**
    /// guard below. `exp(-inf)` is mathematically `0.0` — a FINITE result —
    /// so without a dedicated input check, this call would silently SUCCEED
    /// with `Ok(Value::Real(0.0))` rather than being refused. This is the
    /// case that proves the input guard is load-bearing, not dead code
    /// duplicating the result guard's coverage.
    #[test]
    fn exp_of_negative_infinity_is_rejected_at_the_input_guard_not_silently_zero() {
        let err = exp(f64::NEG_INFINITY).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::TranscendentalOutOfDomain));
    }

    #[test]
    fn exp_of_positive_infinity_is_rejected_at_the_input_guard() {
        let err = exp(f64::INFINITY).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::TranscendentalOutOfDomain));
    }

    #[test]
    fn exp_of_nan_is_rejected_at_the_input_guard() {
        let err = exp(f64::NAN).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::TranscendentalOutOfDomain));
    }

    /// `log`'s own non-finite-input differentiator: `+inf` clears the
    /// `x <= 0.0` domain check (`+inf > 0.0`), so without a dedicated
    /// finite-input guard this call would fall through to
    /// `babylon_kernel::transcendental::ln(f64::INFINITY)` — which returns
    /// `+inf`, itself non-finite, so the call would still fail, but coded
    /// `NonFinite` (`E-EVAL-014`) instead of `TranscendentalOutOfDomain`
    /// (`E-EVAL-043`). A mutation deleting the input guard flips this
    /// test's code assertion even though it stays `Err` either way.
    #[test]
    fn log_of_positive_infinity_is_rejected_at_the_input_guard_not_the_result_guard() {
        let err = log(f64::INFINITY).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::TranscendentalOutOfDomain));
    }

    #[test]
    fn log_of_nan_is_rejected_at_the_input_guard() {
        let err = log(f64::NAN).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::TranscendentalOutOfDomain));
    }

    #[test]
    fn log_rejects_a_non_real_argument_rather_than_coercing() {
        assert!(KernelIntrinsicHost
            .call("log", &[Value::Int(5)], IntrinsicCallCtx::context_free())
            .is_err());
        assert!(KernelIntrinsicHost
            .call("log", &[], IntrinsicCallCtx::context_free())
            .is_err());
    }

    // ---- Task 4.1 (#576 intrinsic-host train, plan §3.5): the `DrawContext`
    // seam RED probe. `rng-draw` itself is Task 5's — this is NOT a
    // production dispatcher, it is a minimal test double proving the
    // `ctx: IntrinsicCallCtx` parameter really reaches `IntrinsicHost::call`,
    // by refusing exactly the shape §3.6's error table names: "`rng-draw`
    // with no `DrawContext`" is an uncoded `EvalError::plain`, "a driver
    // that never supplied a session/tick" (III.11 — loud failure, never a
    // silent `0.0`).
    struct DrawContextProbeHost;

    impl IntrinsicHost for DrawContextProbeHost {
        fn call(
            &self,
            name: &str,
            _args: &[Value],
            ctx: IntrinsicCallCtx<'_>,
        ) -> Result<Value, crate::evaluator::EvalError> {
            if name == "rng-draw" && ctx.draw_context.is_none() {
                return Err(crate::evaluator::EvalError::plain(
                    "rng-draw called with no DrawContext — missing session/tick \
                     (III.11: a driver that never supplied a session/tick fails \
                     loud, never silently draws 0.0)"
                        .to_owned(),
                ));
            }
            Ok(Value::Real(0.5))
        }
    }

    #[test]
    fn a_host_call_for_rng_draw_with_no_draw_context_names_the_missing_session_and_tick() {
        let ctx = IntrinsicCallCtx::context_free();
        let err = DrawContextProbeHost.call("rng-draw", &[], ctx).unwrap_err();
        assert!(err.message.contains("session"), "{}", err.message);
        assert!(err.message.contains("tick"), "{}", err.message);
    }

    // ---- `framed` (plan §3.3): the length-prefix injectivity property
    // `evaluator::eval_intrinsic` relies on when it renders an `Element::
    // Edge`'s two endpoints into ONE chain entry (Task 4.3).
    #[test]
    fn framed_renders_each_segment_length_prefixed_and_pipe_joined() {
        assert_eq!(super::framed(&["ab", "c"]), "2:ab|1:c");
        assert_eq!(super::framed(&["a"]), "1:a");
        assert_eq!(super::framed(&[]), "");
    }

    /// The whole point of the discipline: naive concatenation would let
    /// `("ab", "c")` and `("a", "bc")` collide on `"abc"`. Length-prefixing
    /// makes that impossible.
    #[test]
    fn framed_is_injective_where_naive_concatenation_would_collide() {
        assert_ne!(super::framed(&["ab", "c"]), super::framed(&["a", "bc"]));
    }
}
