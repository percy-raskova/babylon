//! Immutable checkpoint admission shared by runtime and full-observer reads.

#[cfg(test)]
mod tests;

#[path = "component_identity/identity.rs"]
mod identity;

pub(crate) use identity::MaterialComponentIdentity;
