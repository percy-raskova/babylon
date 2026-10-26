//! Typed refusals at the external content package boundary.

use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::io::Error;
use std::path::PathBuf;

use super::manifest::HostProfile;

/// One refusal while loading, resolving or admitting a content package.
#[derive(Debug)]
pub enum PackageError {
    /// A package file could not be read.
    Io { path: PathBuf, error: Error },
    /// The manifest exceeds its bounded transport size.
    ManifestTooLarge { path: PathBuf, limit: usize },
    /// The manifest is not UTF-8.
    ManifestUtf8 { path: PathBuf },
    /// The manifest is not valid TOML or carries an unknown field.
    ManifestToml { path: PathBuf, message: String },
    /// The manifest schema revision is not supported.
    UnsupportedFormatVersion { version: u32 },
    /// The content ABI revision is not supported.
    UnsupportedContentAbi { abi: String },
    /// The host profile is not one of the supported profiles.
    UnsupportedHostProfile { profile: String },
    /// An entrypoint kind is not one of the closed source kinds.
    UnsupportedSourceKind { kind: String },
    /// The package id is empty or malformed.
    InvalidPackageId { id: String },
    /// The package version is empty or malformed.
    InvalidVersion { version: String },
    /// No package was offered for resolution.
    EmptyPackageSet,
    /// More packages were offered than one resolution admits.
    TooManyPackages { limit: usize },
    /// A package declares more entrypoints than one resolution admits.
    TooManyEntrypoints { package: String, limit: usize },
    /// A package declares more dependencies than one resolution admits.
    TooManyDependencies { package: String, limit: usize },
    /// A package declares more replacements than one resolution admits.
    TooManyReplacements { package: String, limit: usize },
    /// Two packages or entrypoints claim one package identity.
    DuplicatePackageId { id: String },
    /// One package declares one logical source id twice.
    DuplicateSourceId { package: String, source_id: String },
    /// One package declares the same exact dependency twice.
    DuplicateDependency { package: String, dependency: String },
    /// A source path is not a normalized relative forward-slash path.
    InvalidSourcePath { path: String, reason: &'static str },
    /// A source path resolves outside its package root.
    SourceOutsidePackage { path: String },
    /// A source path is a symbolic link.
    SourceSymlink { path: String },
    /// A source exceeds the bounded package source size.
    SourceTooLarge { path: String, limit: usize },
    /// A source is not UTF-8.
    SourceNotUtf8 { path: String },
    /// A source's exact bytes disagree with its declared SHA-256.
    DigestMismatch {
        source_id: String,
        expected: [u8; 32],
        actual: [u8; 32],
    },
    /// A digest field is not exactly 64 lowercase hexadecimal characters.
    MalformedDigest { field: &'static str, value: String },
    /// A declared dependency is absent from the offered package set.
    MissingDependency { package: String, dependency: String },
    /// A dependency's exact version label differs from the declaration.
    DependencyVersionMismatch {
        package: String,
        dependency: String,
        expected: String,
        actual: String,
    },
    /// A dependency's exact manifest digest differs from the declaration.
    DependencyDigestMismatch {
        package: String,
        dependency: String,
        expected: [u8; 32],
        actual: [u8; 32],
    },
    /// Dependencies form a cycle, so no topological order exists.
    DependencyCycle { packages: Vec<String> },
    /// Two packages replace one source without an explicit chain.
    ReplacementConflict {
        source_id: String,
        first: String,
        second: String,
    },
    /// A replacement names a digest the current source does not have.
    ReplacementDigestMismatch {
        source_id: String,
        expected: [u8; 32],
        actual: [u8; 32],
    },
    /// A replacement names a source its dependency does not provide.
    UnknownReplacementSource {
        package: String,
        dependency_id: String,
        source_id: String,
    },
    /// A replacement has no matching entrypoint in the replacing package.
    ReplacementWithoutEntrypoint { package: String, source_id: String },
    /// A replacement changes the source's declared kind.
    ReplacementKindMismatch {
        source_id: String,
        first: String,
        second: String,
    },
    /// Two packages select different host profiles.
    HostProfileConflict { first: String, second: String },
    /// The resolved source kinds do not match the selected host profile.
    ProfileSourceKinds {
        profile: HostProfile,
        reason: String,
    },
    /// A source unit is larger than one captured content chunk admits.
    ContentTooLarge {
        source_id: String,
        limit: usize,
        actual: usize,
    },
    /// One rule/source unit could not be parsed or typed by the existing language loader.
    RuleSetRefused { reason: String },
    /// A rule anchor names no registered rule/phase identity.
    UnknownRuleId { rule_id: String },
    /// A scenario coefficient is defined but no rule reads it.
    UnconsumedDial { name: String },
    /// A rule action writes state the scenario never listed.
    UnlistedStateActionPair { rule_id: String, field: String },
    /// Two rules declare different costs for one state/action pair.
    DuplicateCost {
        pair: String,
        first_rule: String,
        second_rule: String,
    },
    /// A catalog coefficient declares no positive basis.
    MissingCoefficientBasis { coefficient: String },
    /// A catalog coefficient names no declared unit.
    MissingCoefficientUnit { coefficient: String },
    /// The catalog's shared normalizing constant is inconsistent.
    InconsistentNormalizingConstant { reason: String },
}

impl std::fmt::Display for PackageError {
    #[allow(
        clippy::too_many_lines,
        reason = "one flat match publishes every package refusal without a nested helper"
    )]
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Io { path, error } => {
                write!(formatter, "package file {} is unreadable: {error}", path.display())
            }
            Self::ManifestTooLarge { path, limit } => write!(
                formatter,
                "package manifest {} exceeds its {limit}-byte transport bound",
                path.display()
            ),
            Self::ManifestUtf8 { path } => {
                write!(formatter, "package manifest {} is not UTF-8", path.display())
            }
            Self::ManifestToml { path, message } => write!(
                formatter,
                "package manifest {} is not valid TOML: {message}",
                path.display()
            ),
            Self::UnsupportedFormatVersion { version } => {
                write!(formatter, "package format_version {version} is not supported")
            }
            Self::UnsupportedContentAbi { abi } => {
                write!(formatter, "content_abi {abi} is not supported")
            }
            Self::UnsupportedHostProfile { profile } => {
                write!(formatter, "host_profile {profile:?} is not supported")
            }
            Self::UnsupportedSourceKind { kind } => {
                write!(formatter, "entrypoint kind {kind:?} is not supported")
            }
            Self::InvalidPackageId { id } => write!(formatter, "package id {id:?} is malformed"),
            Self::InvalidVersion { version } => {
                write!(formatter, "package version {version:?} is malformed")
            }
            Self::EmptyPackageSet => write!(formatter, "package resolution was offered no packages"),
            Self::TooManyPackages { limit } => {
                write!(formatter, "package resolution exceeds its {limit}-package bound")
            }
            Self::TooManyEntrypoints { package, limit } => write!(
                formatter,
                "package {package} exceeds its {limit}-entrypoint bound"
            ),
            Self::TooManyDependencies { package, limit } => write!(
                formatter,
                "package {package} exceeds its {limit}-dependency bound"
            ),
            Self::TooManyReplacements { package, limit } => write!(
                formatter,
                "package {package} exceeds its {limit}-replacement bound"
            ),
            Self::DuplicatePackageId { id } => {
                write!(formatter, "package id {id} is declared more than once")
            }
            Self::DuplicateSourceId { package, source_id } => write!(
                formatter,
                "package {package} declares source {source_id} more than once"
            ),
            Self::DuplicateDependency {
                package,
                dependency,
            } => write!(
                formatter,
                "package {package} declares dependency {dependency} more than once"
            ),
            Self::InvalidSourcePath { path, reason } => {
                write!(formatter, "source path {path:?} is refused: {reason}")
            }
            Self::SourceOutsidePackage { path } => {
                write!(formatter, "source path {path:?} escapes its package root")
            }
            Self::SourceSymlink { path } => {
                write!(formatter, "source path {path:?} is a symbolic link")
            }
            Self::SourceTooLarge { path, limit } => {
                write!(formatter, "source {path} exceeds its {limit}-byte bound")
            }
            Self::SourceNotUtf8 { path } => write!(formatter, "source {path} is not UTF-8"),
            Self::DigestMismatch {
                source_id,
                expected,
                actual,
            } => write!(
                formatter,
                "source {source_id} digest {} does not match declared {}",
                hex(actual),
                hex(expected)
            ),
            Self::MalformedDigest { field, value } => {
                write!(formatter, "{field} {value:?} is not a lowercase SHA-256 digest")
            }
            Self::MissingDependency {
                package,
                dependency,
            } => write!(
                formatter,
                "package {package} requires absent dependency {dependency}"
            ),
            Self::DependencyVersionMismatch {
                package,
                dependency,
                expected,
                actual,
            } => write!(
                formatter,
                "package {package} requires dependency {dependency} version {expected}, found {actual}"
            ),
            Self::DependencyDigestMismatch {
                package,
                dependency,
                expected,
                actual,
            } => write!(
                formatter,
                "package {package} requires dependency {dependency} manifest {}, found {}",
                hex(expected),
                hex(actual)
            ),
            Self::DependencyCycle { packages } => {
                write!(formatter, "dependency cycle among packages {packages:?}")
            }
            Self::ReplacementConflict {
                source_id,
                first,
                second,
            } => write!(
                formatter,
                "source {source_id} is replaced by both {first} and {second} without an explicit chain"
            ),
            Self::ReplacementDigestMismatch {
                source_id,
                expected,
                actual,
            } => write!(
                formatter,
                "source {source_id} replacement expected {}, found {}",
                hex(expected),
                hex(actual)
            ),
            Self::UnknownReplacementSource {
                package,
                dependency_id,
                source_id,
            } => write!(
                formatter,
                "package {package} replaces {source_id}, which dependency {dependency_id} does not provide"
            ),
            Self::ReplacementWithoutEntrypoint { package, source_id } => write!(
                formatter,
                "package {package} replaces {source_id} without supplying its complete unit"
            ),
            Self::ReplacementKindMismatch {
                source_id,
                first,
                second,
            } => write!(
                formatter,
                "source {source_id} replacement changes kind from {first} to {second}"
            ),
            Self::HostProfileConflict { first, second } => write!(
                formatter,
                "packages select different host profiles: {first} and {second}"
            ),
            Self::ProfileSourceKinds { profile, reason } => write!(
                formatter,
                "host profile {} refuses the resolved sources: {reason}",
                profile.manifest_name()
            ),
            Self::ContentTooLarge {
                source_id,
                limit,
                actual,
            } => write!(
                formatter,
                "content unit {source_id} of {actual} bytes exceeds the {limit}-byte chunk bound"
            ),
            Self::RuleSetRefused { reason } => {
                write!(formatter, "rule content set refused: {reason}")
            }
            Self::UnknownRuleId { rule_id } => write!(
                formatter,
                "rule {rule_id} names no registered phase-system identity"
            ),
            Self::UnconsumedDial { name } => write!(
                formatter,
                "scenario dial {name} is defined but no rule reads it"
            ),
            Self::UnlistedStateActionPair { rule_id, field } => write!(
                formatter,
                "rule {rule_id} writes unlisted state field {field}"
            ),
            Self::DuplicateCost {
                pair,
                first_rule,
                second_rule,
            } => write!(
                formatter,
                "rules {first_rule} and {second_rule} both declare a cost for {pair}; one valuation per pair is required"
            ),
            Self::MissingCoefficientBasis { coefficient } => write!(
                formatter,
                "catalog coefficient {coefficient} declares no positive basis"
            ),
            Self::MissingCoefficientUnit { coefficient } => write!(
                formatter,
                "catalog coefficient {coefficient} names no declared unit"
            ),
            Self::InconsistentNormalizingConstant { reason } => {
                write!(formatter, "catalog normalizing constant is inconsistent: {reason}")
            }
        }
    }
}

impl std::error::Error for PackageError {}

fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;

    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut output, "{byte:02x}").expect("writing to a String cannot fail");
    }
    output
}
