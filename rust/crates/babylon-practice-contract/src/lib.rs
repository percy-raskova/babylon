#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

#[allow(clippy::unreadable_literal)]
mod generated;

pub use generated::*;

pub mod admission {}
pub mod budget {}
pub mod codec {}
pub mod topology {}
