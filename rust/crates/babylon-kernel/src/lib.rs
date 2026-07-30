//! The Program 27 kernel: scalars, `Currency`, `ContentDigest`, the sim clock,
//! the event-bus port, and the RNG service (spec §6, §9). No `unsafe`; every
//! public item is doc-commented (`RUSTDOCFLAGS='-D warnings' cargo doc` gate).
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

pub mod clock;
pub mod currency;
pub mod grid;
pub mod scalars;

pub use clock::{EmptySessionId, SessionId, SimClock};
pub use currency::{round_half_even_div, Currency, CurrencyOverflow};
pub use grid::{quantize, GRID_PRECISION};
pub use scalars::{
    Balance, Coefficient, Ideology, Intensity, OutOfBoundsError, Probability, Ratio,
};
