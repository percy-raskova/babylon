//! Per-intrinsic golden vectors for `babylon_kernel::transcendental` (ADR176
//! r21, Task 1 of the #576 intrinsic-host train).
//!
//! **Zero-tolerance contract:** these are `assert_eq!` on `f64::to_bits()`,
//! never `abs(a - b) < eps`. `libm 0.2.16` at `default-features = false` is
//! pinned soft-float on every target Babylon ships (`x86_64`, `aarch64`) —
//! see `babylon_kernel::transcendental`'s module doc for the verified
//! dispatch analysis. Any drift here is a determinism regression, never
//! "the math got better" (the `rng.rs:191-192` precedent).
//!
//! Constants are placeholders (`0x0`) until the first green run (Task 1.3);
//! filled from that run, byte-pinned thereafter.

use babylon_kernel::transcendental::{exp, ln};

/// `exp` roster: zeros (both signs), unit inputs, a mid-range value, the two
/// boundary values nearest `f64::exp`'s overflow edge (`709.0` finite,
/// `709.782712893384` the largest finite-result argument), the underflow
/// edge (`-745.0`, near where `exp` flushes to `0.0`), and a tiny positive
/// input (`1e-300`).
#[test]
fn exp_golden_vectors() {
    let roster: [(f64, u64); 9] = [
        (0.0, 0x0),
        (-0.0, 0x0),
        (1.0, 0x0),
        (-1.0, 0x0),
        (0.5, 0x0),
        (709.0, 0x0),
        (709.782_712_893_384, 0x0),
        (-745.0, 0x0),
        (1e-300, 0x0),
    ];
    for (x, expected_bits) in roster {
        let observed = exp(x).to_bits();
        assert_eq!(
            observed, expected_bits,
            "exp({x}) = 0x{observed:016x}, expected 0x{expected_bits:016x}"
        );
    }
}

/// `ln` roster: the identity point (`1.0`), a small integer, a fraction, the
/// smallest positive normal `f64`, another small integer, a very large
/// magnitude, and a value one ULP above `1.0` (probing rounding near the
/// zero crossing).
#[test]
fn ln_golden_vectors() {
    let roster: [(f64, u64); 7] = [
        (1.0, 0x0),
        (2.0, 0x0),
        (0.5, 0x0),
        (f64::MIN_POSITIVE, 0x0),
        (3.0, 0x0),
        (1e300, 0x0),
        (1.000_000_000_000_000_2, 0x0),
    ];
    for (x, expected_bits) in roster {
        let observed = ln(x).to_bits();
        assert_eq!(
            observed, expected_bits,
            "ln({x}) = 0x{observed:016x}, expected 0x{expected_bits:016x}"
        );
    }
}
