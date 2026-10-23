//! Complete typed known-only rendering witness. Markdown is never its authority.

#[cfg(test)]
mod tests;

#[path = "emission/manifest.rs"]
mod manifest;

pub(crate) use manifest::{ArchiveEmissionLink, ArchiveEmissionManifest};

#[cfg(test)]
use crate::{ArchiveCitation, ArchivePageRef, ArchiveSignal, ArchiveSubject, SemanticArchiveError};
