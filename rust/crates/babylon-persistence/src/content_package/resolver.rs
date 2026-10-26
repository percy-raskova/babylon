//! Deterministic package dependency resolution and whole-unit replacement.

use std::collections::BTreeMap;
use std::collections::BTreeSet;

use babylon_kernel::content_digest;

use super::audit;
use super::error::PackageError;
use super::manifest::HostProfile;
use super::manifest::LoadedPackage;
use super::manifest::SourceKind;
use super::manifest::MAX_PACKAGES;

const RESOLUTION_DOMAIN: &[u8] = b"babylon.content-package-resolved.v1\0";

/// One package in deterministic resolution order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResolvedPackage {
    id: String,
    version: String,
    manifest_sha256: [u8; 32],
    host_profile: HostProfile,
}

impl ResolvedPackage {
    /// Return the globally qualified package identity.
    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }

    /// Return the exact human version label.
    #[must_use]
    pub fn version(&self) -> &str {
        &self.version
    }

    /// Return the exact manifest digest.
    #[must_use]
    pub const fn manifest_sha256(&self) -> [u8; 32] {
        self.manifest_sha256
    }

    /// Return the selected host profile.
    #[must_use]
    pub const fn host_profile(&self) -> HostProfile {
        self.host_profile
    }
}

/// One effective source unit after replacements are applied.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResolvedSourceUnit {
    source_id: String,
    kind: SourceKind,
    origin: String,
    sha256: [u8; 32],
    bytes: Vec<u8>,
}

impl ResolvedSourceUnit {
    /// Return the stable logical source identity.
    #[must_use]
    pub fn source_id(&self) -> &str {
        &self.source_id
    }

    /// Return the closed source kind.
    #[must_use]
    pub const fn kind(&self) -> SourceKind {
        self.kind
    }

    /// Return the package that supplied the effective bytes.
    #[must_use]
    pub fn origin(&self) -> &str {
        &self.origin
    }

    /// Return the exact effective digest.
    #[must_use]
    pub const fn sha256(&self) -> [u8; 32] {
        self.sha256
    }

    /// Return the exact effective bytes.
    #[must_use]
    pub fn bytes(&self) -> &[u8] {
        &self.bytes
    }
}

/// The complete deterministic resolution of one package set.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResolvedContentSet {
    packages: Vec<ResolvedPackage>,
    units: Vec<ResolvedSourceUnit>,
    canonical_bytes: Vec<u8>,
    digest: [u8; 32],
}

impl ResolvedContentSet {
    /// Return the host profile every package selected.
    ///
    /// A resolved set always contains at least the packages that produced it.
    #[must_use]
    pub fn host_profile(&self) -> HostProfile {
        self.packages
            .first()
            .map_or(HostProfile::MichiganRegionalV6, |package| {
                package.host_profile
            })
    }

    /// Return the packages in deterministic topological order.
    #[must_use]
    pub fn packages(&self) -> &[ResolvedPackage] {
        &self.packages
    }

    /// Return the effective source units in first-declaration order.
    #[must_use]
    pub fn units(&self) -> &[ResolvedSourceUnit] {
        &self.units
    }

    /// Return one effective source unit by logical identity.
    #[must_use]
    pub fn unit(&self, source_id: &str) -> Option<&ResolvedSourceUnit> {
        self.units.iter().find(|unit| unit.source_id == source_id)
    }

    /// Return every effective unit of one closed kind in declaration order.
    pub fn units_of(&self, kind: SourceKind) -> impl Iterator<Item = &ResolvedSourceUnit> {
        self.units.iter().filter(move |unit| unit.kind == kind)
    }

    /// Return the canonical identity bytes of this exact resolution.
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.canonical_bytes
    }

    /// Return the SHA-256 of the canonical resolution bytes.
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }
}

/// Resolve exact dependencies and whole-unit replacements into one source set.
///
/// # Errors
///
/// Refuses a duplicate package identity, a missing dependency, a mismatched
/// dependency version or manifest digest, a dependency cycle, two packages
/// replacing one source without an explicit chain, a replacement digest or kind
/// mismatch, a replacement without its complete unit, disagreeing host profiles,
/// or rule content that fails the load-bearing refusal audit.
pub fn resolve_content_packages(
    packages: &[LoadedPackage],
) -> Result<ResolvedContentSet, PackageError> {
    if packages.is_empty() {
        return Err(PackageError::EmptyPackageSet);
    }
    if packages.len() > MAX_PACKAGES {
        return Err(PackageError::TooManyPackages {
            limit: MAX_PACKAGES,
        });
    }
    let by_id = index_packages(packages)?;
    let order = resolution_order(&by_id)?;
    verify_dependencies(&by_id, &order)?;
    let host_profile = common_host_profile(&order)?;
    let packages_resolved = order
        .iter()
        .map(|package| ResolvedPackage {
            id: package.manifest().id().to_owned(),
            version: package.manifest().version().to_owned(),
            manifest_sha256: package.manifest_sha256(),
            host_profile: package.manifest().host_profile(),
        })
        .collect::<Vec<_>>();
    let units = effective_units(&order)?;
    let canonical_bytes = canonical_resolution(&packages_resolved, &units, host_profile);
    let digest = content_digest::sha256_of(&canonical_bytes);
    let resolved = ResolvedContentSet {
        packages: packages_resolved,
        units,
        canonical_bytes,
        digest,
    };
    audit::audit_resolved_rules(&resolved)?;
    Ok(resolved)
}

fn index_packages(
    packages: &[LoadedPackage],
) -> Result<BTreeMap<&str, &LoadedPackage>, PackageError> {
    let mut by_id = BTreeMap::new();
    for package in packages {
        let id = package.manifest().id();
        if by_id.insert(id, package).is_some() {
            return Err(PackageError::DuplicatePackageId { id: id.to_owned() });
        }
    }
    Ok(by_id)
}

fn resolution_order<'a>(
    by_id: &BTreeMap<&'a str, &'a LoadedPackage>,
) -> Result<Vec<&'a LoadedPackage>, PackageError> {
    let mut indegree: BTreeMap<&str, usize> = by_id.keys().map(|id| (*id, 0)).collect();
    let mut dependents: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for (id, package) in by_id {
        for dependency in package.manifest().dependencies() {
            if !by_id.contains_key(dependency.id()) {
                return Err(PackageError::MissingDependency {
                    package: (*id).to_owned(),
                    dependency: dependency.id().to_owned(),
                });
            }
            *indegree
                .get_mut(id)
                .expect("every package identity starts at zero indegree") += 1;
            dependents.entry(dependency.id()).or_default().push(*id);
        }
    }
    let mut ready: BTreeSet<&str> = indegree
        .iter()
        .filter_map(|(id, count)| (*count == 0).then_some(*id))
        .collect();
    let mut order = Vec::with_capacity(by_id.len());
    while let Some(id) = ready.pop_first() {
        let package = by_id
            .get(id)
            .expect("a ready identity always names an offered package");
        order.push(*package);
        for dependent in dependents.get(id).into_iter().flatten() {
            let count = indegree
                .get_mut(dependent)
                .expect("every dependent has an indegree row");
            *count -= 1;
            if *count == 0 {
                ready.insert(dependent);
            }
        }
    }
    if order.len() != by_id.len() {
        let mut packages = indegree
            .into_iter()
            .filter_map(|(id, count)| (count > 0).then_some(id.to_owned()))
            .collect::<Vec<_>>();
        packages.sort();
        return Err(PackageError::DependencyCycle { packages });
    }
    Ok(order)
}

fn verify_dependencies(
    by_id: &BTreeMap<&str, &LoadedPackage>,
    order: &[&LoadedPackage],
) -> Result<(), PackageError> {
    for package in order {
        for dependency in package.manifest().dependencies() {
            let target = by_id
                .get(dependency.id())
                .expect("presence was proven before cycle detection");
            if target.manifest().version() != dependency.version() {
                return Err(PackageError::DependencyVersionMismatch {
                    package: package.manifest().id().to_owned(),
                    dependency: dependency.id().to_owned(),
                    expected: dependency.version().to_owned(),
                    actual: target.manifest().version().to_owned(),
                });
            }
            if target.manifest_sha256() != dependency.manifest_sha256() {
                return Err(PackageError::DependencyDigestMismatch {
                    package: package.manifest().id().to_owned(),
                    dependency: dependency.id().to_owned(),
                    expected: dependency.manifest_sha256(),
                    actual: target.manifest_sha256(),
                });
            }
        }
    }
    Ok(())
}

fn common_host_profile(order: &[&LoadedPackage]) -> Result<HostProfile, PackageError> {
    let mut profiles = order
        .iter()
        .map(|package| package.manifest().host_profile());
    let Some(first) = profiles.next() else {
        return Err(PackageError::EmptyPackageSet);
    };
    for profile in profiles {
        if profile != first {
            return Err(PackageError::HostProfileConflict {
                first: first.manifest_name().to_owned(),
                second: profile.manifest_name().to_owned(),
            });
        }
    }
    Ok(first)
}

fn effective_units(order: &[&LoadedPackage]) -> Result<Vec<ResolvedSourceUnit>, PackageError> {
    let mut units: Vec<ResolvedSourceUnit> = Vec::new();
    let mut positions: BTreeMap<String, usize> = BTreeMap::new();
    for package in order {
        let manifest = package.manifest();
        let package_id = manifest.id();
        for replacement in manifest.replacements() {
            if !manifest
                .dependencies()
                .iter()
                .any(|dependency| dependency.id() == replacement.dependency_id())
            {
                return Err(PackageError::UnknownReplacementSource {
                    package: package_id.to_owned(),
                    dependency_id: replacement.dependency_id().to_owned(),
                    source_id: replacement.source_id().to_owned(),
                });
            }
            if !manifest
                .entrypoints()
                .iter()
                .any(|entrypoint| entrypoint.source_id() == replacement.source_id())
            {
                return Err(PackageError::ReplacementWithoutEntrypoint {
                    package: package_id.to_owned(),
                    source_id: replacement.source_id().to_owned(),
                });
            }
        }
        for source in package.sources() {
            let source_id = source.source_id();
            let replacement = manifest
                .replacements()
                .iter()
                .find(|replacement| replacement.source_id() == source_id);
            if let Some(&position) = positions.get(source_id) {
                let current = units
                    .get(position)
                    .expect("a recorded position always names one effective unit");
                let Some(replacement) = replacement else {
                    return Err(PackageError::ReplacementConflict {
                        source_id: source_id.to_owned(),
                        first: current.origin.clone(),
                        second: package_id.to_owned(),
                    });
                };
                if current.kind != source.kind() {
                    return Err(PackageError::ReplacementKindMismatch {
                        source_id: source_id.to_owned(),
                        first: current.kind.as_str().to_owned(),
                        second: source.kind().as_str().to_owned(),
                    });
                }
                if current.origin != replacement.dependency_id() {
                    return Err(PackageError::ReplacementConflict {
                        source_id: source_id.to_owned(),
                        first: current.origin.clone(),
                        second: package_id.to_owned(),
                    });
                }
                if current.sha256 != replacement.expected_sha256() {
                    return Err(PackageError::ReplacementDigestMismatch {
                        source_id: source_id.to_owned(),
                        expected: replacement.expected_sha256(),
                        actual: current.sha256,
                    });
                }
                units[position] = ResolvedSourceUnit {
                    source_id: source_id.to_owned(),
                    kind: source.kind(),
                    origin: package_id.to_owned(),
                    sha256: source.sha256(),
                    bytes: source.bytes().to_vec(),
                };
            } else {
                if let Some(replacement) = replacement {
                    return Err(PackageError::UnknownReplacementSource {
                        package: package_id.to_owned(),
                        dependency_id: replacement.dependency_id().to_owned(),
                        source_id: source_id.to_owned(),
                    });
                }
                positions.insert(source_id.to_owned(), units.len());
                units.push(ResolvedSourceUnit {
                    source_id: source_id.to_owned(),
                    kind: source.kind(),
                    origin: package_id.to_owned(),
                    sha256: source.sha256(),
                    bytes: source.bytes().to_vec(),
                });
            }
        }
    }
    Ok(units)
}

fn canonical_resolution(
    packages: &[ResolvedPackage],
    units: &[ResolvedSourceUnit],
    host_profile: HostProfile,
) -> Vec<u8> {
    let mut output = Vec::new();
    output.extend_from_slice(RESOLUTION_DOMAIN);
    push_u32(
        &mut output,
        u32::try_from(packages.len()).expect("packages are bounded at load"),
    );
    push_u8(&mut output, host_profile_code(host_profile));
    for package in packages {
        push_str(&mut output, &package.id);
        push_str(&mut output, &package.version);
        output.extend_from_slice(&package.manifest_sha256);
    }
    push_u32(
        &mut output,
        u32::try_from(units.len()).expect("units are bounded at load"),
    );
    for unit in units {
        push_str(&mut output, &unit.source_id);
        push_u8(&mut output, source_kind_code(unit.kind));
        push_str(&mut output, &unit.origin);
        output.extend_from_slice(&unit.sha256);
    }
    output
}

fn push_u32(output: &mut Vec<u8>, value: u32) {
    output.extend_from_slice(&value.to_be_bytes());
}

fn push_u8(output: &mut Vec<u8>, value: u8) {
    output.push(value);
}

fn push_str(output: &mut Vec<u8>, value: &str) {
    push_u32(
        output,
        u32::try_from(value.len()).expect("package identities are bounded at load"),
    );
    output.extend_from_slice(value.as_bytes());
}

const fn host_profile_code(profile: HostProfile) -> u8 {
    match profile {
        HostProfile::MichiganRegionalV6 => 1,
        HostProfile::AuthoredGraphV1 => 2,
    }
}

const fn source_kind_code(kind: SourceKind) -> u8 {
    match kind {
        SourceKind::Defines => 1,
        SourceKind::Scenario => 2,
        SourceKind::Prelude => 3,
        SourceKind::Rules => 4,
    }
}
