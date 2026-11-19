//! The County Review kernel: exact splits, the household roster, places and the session.
//!
//! Pure counting rules. No engine types, no floating point and no identifier
//! settles a tie. Appendix D of the County Review design is the source of every
//! split.

mod decimal;
mod place;
mod roster;
mod session;
mod split;
mod types;

pub use place::*;
pub use roster::*;
pub use session::*;
pub use split::*;
pub use types::*;
