//! The transcendental crossing seam (ADR176 r21, reaffirmed ADR188): `exp`
//! and `ln` cross into the Rust engine via the `libm` crate, version-pinned
//! at `0.2.16` with `default-features = false`, never via `f64::exp` /
//! `f64::ln` (those route to the *platform* libm — glibc/musl/Apple's — and
//! are banned workspace-wide by `rust/clippy.toml`'s `disallowed-methods`
//! row).
//!
//! **Why this satisfies "pinned soft-float," verified in the vendored
//! source** (`~/.cargo/registry/src/index.crates.io-*/libm-0.2.16/`; already
//! present as a transitive Bevy/glam/naga dependency before this crossing —
//! `rust/Cargo.lock:3297-3299` — so the source, checksum, and license are
//! already vetted; `default-features = false` promotes it to a direct
//! dependency and drops the `arch` feature):
//!
//! - It is the pure-Rust MUSL libm port: `#![no_std]`, no C, no platform
//!   libm.
//! - License `MIT` (`libm-0.2.16/Cargo.toml:36`), already on
//!   `rust/deny.toml`'s allowlist — no new license exception.
//! - **`ln` (`libm::log`) has NO architecture dispatch at all** —
//!   `src/math/log.rs` contains no `select_implementation!` invocation; it
//!   is unconditionally the soft-float implementation.
//! - **`exp`'s only dispatch is unreachable on every target Babylon
//!   ships.** `src/math/exp.rs:86-90`:
//!   ```text
//!   select_implementation! { name: x87_exp, use_arch_required: x86_no_sse, args: x, }
//!   ```
//!   `use_arch_required` ignores the `arch` feature flag entirely
//!   (`src/math/support/macros.rs:48-58`) — the guard is the `x86_no_sse`
//!   cfg, which `configure.rs:114-117` emits only when
//!   `target_arch == "x86"` (32-bit) **and** the target lacks the `sse`
//!   feature (legacy i586). That predicate is false on `x86_64` (a distinct
//!   `target_arch`, SSE2 baseline) and false on `aarch64`. On both of
//!   Babylon's targets, `libm::exp` takes the generic soft-float path.
//!
//! Therefore `libm::exp` and `libm::log` at `default-features = false` are
//! bit-identical across `x86_64` and `aarch64` by inspection of the dispatch
//! predicates; `tests/transcendental_goldens.rs` turns that inspection into
//! an executable guard (`assert_eq!` on `f64::to_bits()`, zero tolerance).

/// The exponential function, *e*ˣ, crossed via `libm::exp` (pinned
/// soft-float — see the module doc). Infallible: `f64` has no domain
/// restriction for `exp`; overflow saturates to `f64::INFINITY`, underflow
/// flushes to `0.0`, both per IEEE-754 `f64` semantics.
#[must_use]
pub fn exp(x: f64) -> f64 {
    libm::exp(x)
}

/// The natural logarithm, crossed via `libm::log` (pinned soft-float — see
/// the module doc). Infallible at this seam: this wrapper performs no
/// domain check itself — `libm::log` returns `NaN` for negative arguments
/// and `-inf` for `0.0`/`-0.0` per IEEE-754 `f64` semantics. Domain
/// rejection at the BSL intrinsic boundary is Task 2's job, not this
/// wrapper's.
#[must_use]
pub fn ln(x: f64) -> f64 {
    libm::log(x)
}
