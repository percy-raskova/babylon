//! The County Review kernel: exact splits, the household roster, places, the session, the
//! preview, the fogged projection and the codec.
//!
//! Pure counting rules. No engine types, no floating point and no identifier
//! settles a tie. Appendix D of the County Review design is the source of every
//! split.

mod codec;
mod decimal;
mod place;
mod preview;
mod projection;
mod roster;
mod session;
mod split;
mod types;

pub use codec::*;
pub use place::*;
pub use preview::*;
pub use projection::*;
pub use roster::*;
pub use session::*;
pub use split::*;
pub use types::*;
