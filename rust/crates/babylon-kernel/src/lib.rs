//! The Program 27 kernel: scalars, `Currency`, `ContentDigest`, the sim clock,
//! the event-bus port, and the RNG service (spec §6, §9). No `unsafe`; every
//! public item is doc-commented (`RUSTDOCFLAGS='-D warnings' cargo doc` gate).
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod clock;
pub mod content_digest;
pub mod currency;
pub mod event_bus;
pub mod grid;
pub mod replay;
pub mod rng;
pub mod scalars;
pub mod tick_content_hash;
pub mod transcendental;

pub use clock::{EmptySessionId, SessionId, SimClock};
pub use content_digest::{defines_hash_of, sha256_of, ContentDigest};
pub use currency::{round_half_even_div, Currency, CurrencyOverflow};
pub use event_bus::{
    BlockedEvent, Event, EventBus, Handler, HandlerFailure, Intercept, Interceptor,
};
pub use grid::{quantize, GRID_PRECISION};
pub use replay::{
    ReplayIdentityError, ReplaySeed, ReplaySessionIdV1, RngDomainV2, RngLayoutVersion,
    RngSeedContext,
};
pub use rng::{seed_for, seed_for_v2, KernelRng, SEED_SALT};
pub use scalars::{
    Balance, Coefficient, Ideology, Intensity, OutOfBoundsError, Probability, Ratio,
};
pub use tick_content_hash::{
    OrderedPracticeActionBatchDigestV1, PreparedEnvironmentDigestV1, RefDigestV1,
    StableWorldDigestV1, TickContentHashError, TickContentHashV1, TickContentPartsV1,
    TickContentPreimageV1, TickPayloadDigestV1,
};
pub use transcendental::{exp, ln};
