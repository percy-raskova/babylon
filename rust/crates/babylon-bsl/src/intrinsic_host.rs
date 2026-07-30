//! The named-intrinsic call boundary (§2.7: transcendentals "are **never**
//! language primitives — they exist only as named intrinsics with pinned
//! deterministic implementations"). Phase 1 defines the trait only; the
//! kernel's intrinsic table (Phase 2, gated on the Task 8 ruling — ADR176
//! r21, pinned soft-float libm + golden vectors) is the first real
//! implementation.

use crate::evaluator::{EvalError, Value};

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
