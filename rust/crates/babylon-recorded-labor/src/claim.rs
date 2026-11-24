//! By the claim: the kinds of money a household's purse holds, and the split of hours by those kinds.
//! The one place where hours and money meet is `split_hours`: no rate, only the shares of one purse.
mod kind;
mod mix;
mod purses;
mod split;

#[cfg(test)]
mod tests;

pub use kind::Claim;
pub use mix::Mix;
pub use purses::{ClaimError, Paid, Purses};
pub use split::{split_hours, ClaimHours};
