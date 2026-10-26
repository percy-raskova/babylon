//! External `BSL`/`BSCN`/`TOML` content package resolution and profile admission.

mod admission;
mod audit;
mod error;
mod manifest;
mod resolver;

#[cfg(test)]
mod tests;

pub use admission::admit_michigan_regional_package;
pub use admission::content_package_build_identity;
pub use admission::validate_profile_sources;
pub use audit::audit_catalog_coefficients;
pub use audit::audit_resolved_rules;
pub use audit::audit_rule_set;
pub use audit::AuditedRule;
pub use audit::CoefficientAudit;
pub use audit::CoefficientBasis;
pub use audit::CoefficientNormalization;
pub use audit::CoefficientRow;
pub use audit::CoefficientUnit;
pub use audit::ContentAudit;
pub use error::PackageError;
pub use manifest::HostProfile;
pub use manifest::LoadedPackage;
pub use manifest::LoadedSource;
pub use manifest::PackageDependency;
pub use manifest::PackageEntrypoint;
pub use manifest::PackageManifest;
pub use manifest::PackageReplacement;
pub use manifest::SourceKind;
pub use manifest::CONTENT_ABI;
pub use manifest::MAX_PACKAGE_SOURCE_BYTES;
pub use manifest::PACKAGE_FORMAT_VERSION;
pub use manifest::PACKAGE_MANIFEST_FILE;
pub use resolver::resolve_content_packages;
pub use resolver::ResolvedContentSet;
pub use resolver::ResolvedPackage;
pub use resolver::ResolvedSourceUnit;
