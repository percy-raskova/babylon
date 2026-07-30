//! The kernel RNG service (spec §9, R8): one pinned algorithm, seeded per
//! `(session_id, tick, salt)`.
//!
//! **Algorithm choice (Phase-1 engineering call, not amendment-gated — R8
//! already authorizes the stream divergence from Python's MT19937):**
//! `ChaCha8Rng` (`rand_chacha`). Rationale: (1) it takes an exact 32-byte
//! seed, which is exactly a SHA-256 digest's width — the seeding derivation
//! below needs no truncation/expansion step, unlike a generator wanting a
//! `u64` or `[u8; 16]` seed; (2) it is a pure-Rust, no-`unsafe`,
//! platform-independent stream-cipher construction with strong statistical
//! properties and no OS-entropy dependency (fully deterministic from its
//! seed, required for III.7); (3) 8 rounds is the documented "fast, still
//! no known practical distinguisher" configuration — this is not a
//! cryptographic-security use case, so `ChaCha8` is preferred over
//! `ChaCha20` purely for speed with no correctness cost. This choice and
//! the conformance vector below are pinned in
//! ``docs/reference/determinism-contract.rst``'s RNG chapter.
//!
//! **Streams differ from Python by design (R8):** this is the pinned
//! Rust-side replacement, not a port. Python's MT19937 streams are a
//! closed epoch; stochastic baselines re-bless at cutover under
//! ensemble-envelope comparison, not byte replay.
use crate::clock::SessionId;
use rand_chacha::ChaCha8Rng;
use rand_core::{RngCore, SeedableRng};
use sha2::{Digest, Sha256};

/// Mirrors `kernel/system_base.py::_SYSTEM_RNG_SEED_SALT` structurally
/// (same salt constant, same mixing shape: `session_id ‖ tick ‖ salt`) —
/// NOT the same stream, per R8.
pub const SEED_SALT: u64 = 0x0BA1_AC1A;

/// Derive the 32-byte `ChaCha8Rng` seed for `(session_id, tick)`:
/// `SHA-256(session_id_utf8 ‖ tick_le8 ‖ salt_le8)`.
///
/// Byte layout is pinned (little-endian 8-byte tick and salt, no
/// separators) — the conformance vector in the determinism contract's RNG
/// chapter is derived from exactly this construction.
#[must_use]
pub fn seed_for(session_id: &SessionId, tick: u64) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(session_id.as_bytes());
    hasher.update(tick.to_le_bytes());
    hasher.update(SEED_SALT.to_le_bytes());
    hasher.finalize().into()
}

/// The kernel's one pinned RNG. Constructed only via [`KernelRng::for_tick`]
/// — there is deliberately no `from_entropy()`: every stream is a pure
/// function of `(session_id, tick)` (III.7).
pub struct KernelRng(ChaCha8Rng);

impl KernelRng {
    /// The stream for one `(session_id, tick)` pair.
    #[must_use]
    pub fn for_tick(session_id: &SessionId, tick: u64) -> Self {
        Self(ChaCha8Rng::from_seed(seed_for(session_id, tick)))
    }

    /// The next 64 uniformly distributed bits.
    pub fn next_u64(&mut self) -> u64 {
        self.0.next_u64()
    }

    /// A uniform draw on `[0, 1)`: the top 53 bits of one `u64` scaled by
    /// 2⁻⁵³ — every representable value is an exact multiple of 2⁻⁵³, so
    /// the mapping is bit-deterministic across platforms (no libm, no
    /// rounding-mode dependence).
    #[allow(clippy::cast_precision_loss)] // 53-bit value: exact in f64 by construction
    pub fn next_f64(&mut self) -> f64 {
        let bits53 = self.0.next_u64() >> 11;
        (bits53 as f64) * (1.0 / (1u64 << 53) as f64)
    }
}

#[cfg(test)]
mod tests {
    use super::{seed_for, KernelRng, SEED_SALT};
    use crate::clock::SessionId;

    #[test]
    fn same_session_and_tick_reproduce_the_same_stream() {
        let sid = SessionId::new("s1").unwrap();
        let mut a = KernelRng::for_tick(&sid, 7);
        let mut b = KernelRng::for_tick(&sid, 7);
        for _ in 0..8 {
            assert_eq!(a.next_u64(), b.next_u64());
        }
    }

    #[test]
    fn different_ticks_diverge() {
        let sid = SessionId::new("s1").unwrap();
        let mut a = KernelRng::for_tick(&sid, 7);
        let mut b = KernelRng::for_tick(&sid, 8);
        assert_ne!(a.next_u64(), b.next_u64());
    }

    #[test]
    fn different_sessions_diverge() {
        let a_id = SessionId::new("s1").unwrap();
        let b_id = SessionId::new("s2").unwrap();
        assert_ne!(seed_for(&a_id, 7), seed_for(&b_id, 7));
    }

    #[test]
    fn the_salt_is_the_python_constant() {
        // Structural mirror of _SYSTEM_RNG_SEED_SALT = 0xBA1AC1A.
        assert_eq!(SEED_SALT, 0xBA1_AC1A);
    }

    #[test]
    fn next_f64_is_in_the_half_open_unit_interval() {
        let sid = SessionId::new("s").unwrap();
        let mut rng = KernelRng::for_tick(&sid, 1);
        for _ in 0..1000 {
            let v = rng.next_f64();
            assert!((0.0..1.0).contains(&v), "{v}");
        }
    }

    /// The within-implementation replay conformance vector (plan Task 5
    /// Step 2): generated ONCE from this implementation and pinned — any
    /// future divergence is a determinism regression, never "the RNG got
    /// better". Mirrored in the determinism contract's RNG chapter.
    #[test]
    fn conformance_vector_first_four_u64s() {
        let sid = SessionId::new("conformance").unwrap();
        let mut rng = KernelRng::for_tick(&sid, 1);
        let observed = [
            rng.next_u64(),
            rng.next_u64(),
            rng.next_u64(),
            rng.next_u64(),
        ];
        // Filled from the first green run (2026-07-30) and byte-pinned
        // thereafter.
        let pinned: [u64; 4] = [
            0x72ed_9fd7_0ec2_c906,
            0xdd0b_655d_190f_def7,
            0x2858_d116_c1f6_e5fb,
            0x9a16_ceb3_838f_e695,
        ];
        assert_eq!(observed, pinned);
    }
}
