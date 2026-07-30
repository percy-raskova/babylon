//! The Program 27 quantization retraction (`THE_FORMALISM` II.1, `L-GRID`):
//! ports `babylon.kernel.math.quantize` byte-for-byte. `ROUND_HALF_UP`, ties
//! away from zero, on the 10⁻⁶ grid.
//!
//! This is a **cross-language conformance surface**: the test vector below
//! was verified against the live Python (`babylon.kernel.math.quantize`)
//! on 2026-07-30 before this file was written — transcription discipline,
//! not assumption.

/// Decimal digits of the grid: values live on multiples of 10⁻⁶.
pub const GRID_PRECISION: u32 = 6;
const GRID: f64 = 1_000_000.0; // 10^GRID_PRECISION

/// Snap `value` onto the 10⁻⁶ grid, `ROUND_HALF_UP` (ties away from zero) —
/// the exact algorithm in `src/babylon/kernel/math.py::quantize`.
#[must_use]
pub fn quantize(value: f64) -> f64 {
    if value >= 0.0 {
        (value * GRID + 0.5).floor() / GRID
    } else {
        -((-value * GRID + 0.5).floor()) / GRID
    }
}

#[cfg(test)]
mod tests {
    use super::quantize;

    /// Cross-language conformance vector: expected values computed by
    /// running `babylon.kernel.math.quantize` in Python (verified
    /// 2026-07-30: `0.123456789 -> 0.123457`, `-0.123456789 -> -0.123457`,
    /// `0.0 -> 0.0`, `1.0000005 -> 1.000001`, `-1.0000005 -> -1.000001`).
    #[test]
    fn matches_the_python_quantize_conformance_vector() {
        let cases: &[(f64, f64)] = &[
            (0.123_456_789, 0.123_457),
            (-0.123_456_789, -0.123_457),
            (0.0, 0.0),
            (1.000_000_5, 1.000_001), // half-away-from-zero tie
            (-1.000_000_5, -1.000_001),
        ];
        for &(input, expected) in cases {
            assert!(
                (quantize(input) - expected).abs() < 1e-12,
                "quantize({input}) = {}, expected {expected}",
                quantize(input)
            );
        }
    }

    #[test]
    fn is_idempotent() {
        // L-GRID: q ∘ q = q
        let v = 0.987_654_321;
        assert!((quantize(quantize(v)) - quantize(v)).abs() < 1e-15);
    }

    #[test]
    fn negative_zero_input_stays_on_the_grid() {
        // -0.0 >= 0.0 is true in IEEE-754, so it takes the positive branch;
        // the output is 0.0 (positive), not -0.0 — pinned so the tick hash's
        // bit-pattern encoding never sees a quantized -0.0.
        let q = quantize(-0.0);
        assert_eq!(q.to_bits(), 0.0_f64.to_bits());
    }
}
