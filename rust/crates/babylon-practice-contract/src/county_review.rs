//! The County Review kernel: exact splits and the household roster.
//!
//! Pure counting rules. No engine types, no floating point and no identifier
//! settles a tie. Appendix D of the County Review design is the source of every
//! split.

mod decimal;
mod roster;
mod split;
mod types;

pub use roster::*;
pub use split::*;
pub use types::*;
