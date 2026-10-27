//! Strict package manifests, bounded source loading and exact digest verification.

use std::fs;
use std::io::Error;
use std::io::ErrorKind;
use std::path::Path;
use std::path::PathBuf;

use babylon_kernel::content_digest;
use serde::Deserialize;

use super::error::PackageError;
use crate::sqlite_store::TickIdentityPolicy;

/// The one manifest file name a package root must provide.
pub const PACKAGE_MANIFEST_FILE: &str = "manifest.toml";
/// The only supported manifest schema revision.
pub const PACKAGE_FORMAT_VERSION: u32 = 1;
/// The only supported content ABI revision.
pub const CONTENT_ABI: &str = "babylon-content-v1";
/// Bounded transport size of one manifest.
pub const MAX_PACKAGE_MANIFEST_BYTES: usize = 65_536;
/// Bounded size of one source unit.
pub const MAX_PACKAGE_SOURCE_BYTES: usize = 4_194_304;
/// Bounded number of packages in one resolution.
pub const MAX_PACKAGES: usize = 64;
/// Bounded entrypoints per package.
pub const MAX_PACKAGE_ENTRYPOINTS: usize = 64;
/// Bounded dependencies per package.
pub const MAX_PACKAGE_DEPENDENCIES: usize = 64;
/// Bounded replacements per package.
pub const MAX_PACKAGE_REPLACEMENTS: usize = 64;
/// Bounded package identity length.
pub const MAX_PACKAGE_ID_BYTES: usize = 128;
/// Bounded package version length.
pub const MAX_PACKAGE_VERSION_BYTES: usize = 64;
/// Bounded logical source identity length.
pub const MAX_SOURCE_ID_BYTES: usize = 128;

/// One of the two supported host profiles.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HostProfile {
    /// The complete Michigan defines unit admitted by the ordinary economic builder.
    MichiganRegionalV6,
    /// The bounded authored graph fixture admitted by the replay-session builder.
    AuthoredGraphV1,
}

impl HostProfile {
    /// Return the exact manifest spelling.
    #[must_use]
    pub const fn manifest_name(self) -> &'static str {
        match self {
            Self::MichiganRegionalV6 => "michigan-regional-v6",
            Self::AuthoredGraphV1 => "authored-graph-v1",
        }
    }

    fn parse(value: &str) -> Option<Self> {
        match value {
            "michigan-regional-v6" => Some(Self::MichiganRegionalV6),
            "authored-graph-v1" => Some(Self::AuthoredGraphV1),
            _ => None,
        }
    }

    /// Return what this profile adjudicates about each period's material tick
    /// identity.
    ///
    /// The store publishes this policy durably at campaign creation and enforces
    /// it on every commit, so the profile that admitted the campaign is what
    /// decides whether an absent identity is honest or a lost period.
    #[must_use]
    pub const fn tick_identity_policy(self) -> TickIdentityPolicy {
        match self {
            Self::MichiganRegionalV6 => TickIdentityPolicy::Required,
            Self::AuthoredGraphV1 => TickIdentityPolicy::DeclaredAbsence,
        }
    }
}

/// One closed source-unit kind.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum SourceKind {
    /// The typed numeric defines unit.
    Defines,
    /// A scenario declaration unit.
    Scenario,
    /// A declaration-only prelude unit.
    Prelude,
    /// A BSL rule unit.
    Rules,
}

impl SourceKind {
    /// Return the exact manifest spelling.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Defines => "defines",
            Self::Scenario => "scenario",
            Self::Prelude => "prelude",
            Self::Rules => "rules",
        }
    }

    fn parse(value: &str) -> Option<Self> {
        match value {
            "defines" => Some(Self::Defines),
            "scenario" => Some(Self::Scenario),
            "prelude" => Some(Self::Prelude),
            "rules" => Some(Self::Rules),
            _ => None,
        }
    }
}

/// One exact package dependency.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PackageDependency {
    id: String,
    version: String,
    manifest_sha256: [u8; 32],
}

impl PackageDependency {
    /// Return the exact package identity.
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
}

/// One ordered source unit declared by a package.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PackageEntrypoint {
    source_id: String,
    kind: SourceKind,
    path: String,
    sha256: [u8; 32],
}

impl PackageEntrypoint {
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

    /// Return the normalized package-relative path.
    #[must_use]
    pub fn path(&self) -> &str {
        &self.path
    }

    /// Return the exact source digest.
    #[must_use]
    pub const fn sha256(&self) -> [u8; 32] {
        self.sha256
    }
}

/// One whole-unit replacement declared by a package.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PackageReplacement {
    dependency_id: String,
    source_id: String,
    expected_sha256: [u8; 32],
}

impl PackageReplacement {
    /// Return the direct dependency whose source this replacement supersedes.
    #[must_use]
    pub fn dependency_id(&self) -> &str {
        &self.dependency_id
    }

    /// Return the stable logical source identity being replaced.
    #[must_use]
    pub fn source_id(&self) -> &str {
        &self.source_id
    }

    /// Return the digest the replaced source must currently have.
    #[must_use]
    pub const fn expected_sha256(&self) -> [u8; 32] {
        self.expected_sha256
    }
}

/// One validated, immutable package manifest.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PackageManifest {
    id: String,
    version: String,
    host_profile: HostProfile,
    dependencies: Vec<PackageDependency>,
    entrypoints: Vec<PackageEntrypoint>,
    replacements: Vec<PackageReplacement>,
}

impl PackageManifest {
    /// Return the supported schema revision.
    #[must_use]
    pub const fn format_version(&self) -> u32 {
        PACKAGE_FORMAT_VERSION
    }

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

    /// Return the supported content ABI.
    #[must_use]
    pub const fn content_abi(&self) -> &'static str {
        CONTENT_ABI
    }

    /// Return the selected host profile.
    #[must_use]
    pub const fn host_profile(&self) -> HostProfile {
        self.host_profile
    }

    /// Return the ordered exact dependencies.
    #[must_use]
    pub fn dependencies(&self) -> &[PackageDependency] {
        &self.dependencies
    }

    /// Return the ordered source entrypoints.
    #[must_use]
    pub fn entrypoints(&self) -> &[PackageEntrypoint] {
        &self.entrypoints
    }

    /// Return the declared whole-unit replacements.
    #[must_use]
    pub fn replacements(&self) -> &[PackageReplacement] {
        &self.replacements
    }
}

/// One source unit with its exact declared bytes already verified.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LoadedSource {
    source_id: String,
    kind: SourceKind,
    path: String,
    sha256: [u8; 32],
    bytes: Vec<u8>,
}

impl LoadedSource {
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

    /// Return the normalized package-relative path.
    #[must_use]
    pub fn path(&self) -> &str {
        &self.path
    }

    /// Return the exact source digest.
    #[must_use]
    pub const fn sha256(&self) -> [u8; 32] {
        self.sha256
    }

    /// Return the exact UTF-8 source bytes.
    #[must_use]
    pub fn bytes(&self) -> &[u8] {
        &self.bytes
    }
}

/// One loaded package: manifest identity plus verified source units.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LoadedPackage {
    root: PathBuf,
    manifest_path: PathBuf,
    manifest: PackageManifest,
    manifest_sha256: [u8; 32],
    sources: Vec<LoadedSource>,
}

impl LoadedPackage {
    /// Load one package root and verify every declared source digest.
    ///
    /// # Errors
    ///
    /// Refuses a missing or malformed manifest, an unknown field, an unsupported
    /// schema or ABI revision, an unsafe source path, a symlink escape, a source
    /// outside its size bound, non-UTF-8 source bytes, or a digest mismatch.
    pub fn load(root: &Path) -> Result<Self, PackageError> {
        let canonical_root = fs::canonicalize(root).map_err(|error| PackageError::Io {
            path: root.to_path_buf(),
            error,
        })?;
        let manifest_path = canonical_root.join(PACKAGE_MANIFEST_FILE);
        let metadata = fs::symlink_metadata(&manifest_path).map_err(|error| PackageError::Io {
            path: manifest_path.clone(),
            error,
        })?;
        if metadata.file_type().is_symlink() {
            return Err(PackageError::SourceSymlink {
                path: PACKAGE_MANIFEST_FILE.to_owned(),
            });
        }
        if !metadata.is_file() {
            return Err(PackageError::Io {
                path: manifest_path.clone(),
                error: Error::new(
                    ErrorKind::InvalidInput,
                    "the package manifest is not a regular file",
                ),
            });
        }
        if usize::try_from(metadata.len()).map_or(true, |len| len > MAX_PACKAGE_MANIFEST_BYTES) {
            return Err(PackageError::ManifestTooLarge {
                path: manifest_path.clone(),
                limit: MAX_PACKAGE_MANIFEST_BYTES,
            });
        }
        let manifest_bytes = fs::read(&manifest_path).map_err(|error| PackageError::Io {
            path: manifest_path.clone(),
            error,
        })?;
        let text =
            std::str::from_utf8(&manifest_bytes).map_err(|_| PackageError::ManifestUtf8 {
                path: manifest_path.clone(),
            })?;
        let raw: RawManifest =
            toml::from_str(text).map_err(|error| PackageError::ManifestToml {
                path: manifest_path.clone(),
                message: error.to_string(),
            })?;
        let manifest = validate_manifest(raw)?;
        let sources = load_sources(&canonical_root, &manifest)?;
        Ok(Self {
            root: canonical_root,
            manifest_path,
            manifest,
            manifest_sha256: content_digest::sha256_of(&manifest_bytes),
            sources,
        })
    }

    /// Return the canonical package root.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Return the exact manifest path.
    #[must_use]
    pub fn manifest_path(&self) -> &Path {
        &self.manifest_path
    }

    /// Return the validated manifest.
    #[must_use]
    pub const fn manifest(&self) -> &PackageManifest {
        &self.manifest
    }

    /// Return the SHA-256 of the exact manifest bytes.
    #[must_use]
    pub const fn manifest_sha256(&self) -> [u8; 32] {
        self.manifest_sha256
    }

    /// Return the ordered verified source units.
    #[must_use]
    pub fn sources(&self) -> &[LoadedSource] {
        &self.sources
    }

    /// Build one first-party package from in-memory sources.
    ///
    /// The generated manifest is parsed by the same strict schema as an installed
    /// package, and every supplied source passes the same path, size, UTF-8 and
    /// SHA-256 verification before resolution sees it. `origin` names the
    /// logical root in diagnostics; nothing is read from the filesystem.
    ///
    /// # Errors
    ///
    /// Refuses an invalid package/source identity, a missing or duplicate
    /// supplied path, a source outside its size bound, non-UTF-8 bytes, or a
    /// digest mismatch.
    pub fn from_embedded_sources(
        origin: &str,
        id: &str,
        version: &str,
        host_profile: HostProfile,
        sources: &[EmbeddedSource<'_>],
    ) -> Result<Self, PackageError> {
        validate_package_id(id)?;
        validate_version(version)?;
        for source in sources {
            validate_source_id(source.source_id)?;
            validate_relative_path(source.path)?;
        }
        let manifest_text = embedded_manifest(id, version, host_profile, sources);
        let raw: RawManifest =
            toml::from_str(&manifest_text).map_err(|error| PackageError::ManifestToml {
                path: PathBuf::from(origin),
                message: error.to_string(),
            })?;
        let manifest = validate_manifest(raw)?;
        let loaded = load_embedded_sources(&manifest, sources)?;
        let root = PathBuf::from(origin);
        Ok(Self {
            manifest_path: root.join(PACKAGE_MANIFEST_FILE),
            root,
            manifest,
            manifest_sha256: content_digest::sha256_of(manifest_text.as_bytes()),
            sources: loaded,
        })
    }
}

/// One in-memory first-party source offered beside a generated package manifest.
///
/// Embedded defaults are not a second admission bypass: the package constructor
/// validates the generated manifest and every supplied source through the same
/// digest, path and UTF-8 checks a directory-backed package uses.
#[derive(Clone, Copy, Debug)]
pub struct EmbeddedSource<'a> {
    /// Stable logical source identity.
    pub source_id: &'a str,
    /// Closed source kind.
    pub kind: SourceKind,
    /// Normalized package-relative path.
    pub path: &'a str,
    /// Exact source bytes.
    pub bytes: &'a [u8],
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawManifest {
    format_version: u32,
    id: String,
    version: String,
    content_abi: String,
    host_profile: String,
    dependencies: Vec<RawDependency>,
    entrypoints: Vec<RawEntrypoint>,
    replacements: Vec<RawReplacement>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawDependency {
    id: String,
    version: String,
    manifest_sha256: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawEntrypoint {
    source_id: String,
    kind: String,
    path: String,
    sha256: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawReplacement {
    dependency_id: String,
    source_id: String,
    expected_sha256: String,
}

#[allow(
    clippy::too_many_lines,
    reason = "one manifest validation keeps the complete required-field contract in one place"
)]
fn validate_manifest(raw: RawManifest) -> Result<PackageManifest, PackageError> {
    if raw.format_version != PACKAGE_FORMAT_VERSION {
        return Err(PackageError::UnsupportedFormatVersion {
            version: raw.format_version,
        });
    }
    if raw.content_abi != CONTENT_ABI {
        return Err(PackageError::UnsupportedContentAbi {
            abi: raw.content_abi,
        });
    }
    validate_package_id(&raw.id)?;
    validate_version(&raw.version)?;
    let package_id = raw.id.clone();
    let host_profile =
        HostProfile::parse(&raw.host_profile).ok_or(PackageError::UnsupportedHostProfile {
            profile: raw.host_profile,
        })?;
    if raw.entrypoints.len() > MAX_PACKAGE_ENTRYPOINTS {
        return Err(PackageError::TooManyEntrypoints {
            package: package_id,
            limit: MAX_PACKAGE_ENTRYPOINTS,
        });
    }
    if raw.dependencies.len() > MAX_PACKAGE_DEPENDENCIES {
        return Err(PackageError::TooManyDependencies {
            package: package_id,
            limit: MAX_PACKAGE_DEPENDENCIES,
        });
    }
    if raw.replacements.len() > MAX_PACKAGE_REPLACEMENTS {
        return Err(PackageError::TooManyReplacements {
            package: package_id,
            limit: MAX_PACKAGE_REPLACEMENTS,
        });
    }
    let dependencies = raw
        .dependencies
        .into_iter()
        .map(|dependency| {
            validate_package_id(&dependency.id)?;
            validate_version(&dependency.version)?;
            Ok(PackageDependency {
                manifest_sha256: parse_digest(
                    "dependencies.manifest_sha256",
                    &dependency.manifest_sha256,
                )?,
                id: dependency.id,
                version: dependency.version,
            })
        })
        .collect::<Result<Vec<_>, PackageError>>()?;
    let mut dependency_ids: Vec<&str> = dependencies.iter().map(PackageDependency::id).collect();
    dependency_ids.sort_unstable();
    if let Some(pair) = dependency_ids.windows(2).find(|pair| pair[0] == pair[1]) {
        return Err(PackageError::DuplicateDependency {
            package: package_id,
            dependency: pair[0].to_owned(),
        });
    }
    let entrypoints = raw
        .entrypoints
        .into_iter()
        .map(|entrypoint| {
            validate_source_id(&entrypoint.source_id)?;
            validate_relative_path(&entrypoint.path)?;
            let kind =
                SourceKind::parse(&entrypoint.kind).ok_or(PackageError::UnsupportedSourceKind {
                    kind: entrypoint.kind,
                })?;
            Ok(PackageEntrypoint {
                sha256: parse_digest("entrypoints.sha256", &entrypoint.sha256)?,
                source_id: entrypoint.source_id,
                kind,
                path: entrypoint.path,
            })
        })
        .collect::<Result<Vec<_>, PackageError>>()?;
    let replacements = raw
        .replacements
        .into_iter()
        .map(|replacement| {
            validate_package_id(&replacement.dependency_id)?;
            validate_source_id(&replacement.source_id)?;
            Ok(PackageReplacement {
                expected_sha256: parse_digest(
                    "replacements.expected_sha256",
                    &replacement.expected_sha256,
                )?,
                dependency_id: replacement.dependency_id,
                source_id: replacement.source_id,
            })
        })
        .collect::<Result<Vec<_>, PackageError>>()?;
    let mut source_ids: Vec<&str> = entrypoints
        .iter()
        .map(PackageEntrypoint::source_id)
        .collect();
    source_ids.sort_unstable();
    if let Some(pair) = source_ids.windows(2).find(|pair| pair[0] == pair[1]) {
        return Err(PackageError::DuplicateSourceId {
            package: package_id,
            source_id: pair[0].to_owned(),
        });
    }
    let mut replacement_ids: Vec<&str> = replacements
        .iter()
        .map(PackageReplacement::source_id)
        .collect();
    replacement_ids.sort_unstable();
    if let Some(pair) = replacement_ids.windows(2).find(|pair| pair[0] == pair[1]) {
        return Err(PackageError::DuplicateSourceId {
            package: package_id,
            source_id: pair[0].to_owned(),
        });
    }
    Ok(PackageManifest {
        id: raw.id,
        version: raw.version,
        host_profile,
        dependencies,
        entrypoints,
        replacements,
    })
}

fn load_sources(
    canonical_root: &Path,
    manifest: &PackageManifest,
) -> Result<Vec<LoadedSource>, PackageError> {
    let mut sources = Vec::with_capacity(manifest.entrypoints().len());
    for entrypoint in manifest.entrypoints() {
        sources.push(load_source(canonical_root, entrypoint)?);
    }
    Ok(sources)
}

fn load_source(
    canonical_root: &Path,
    entrypoint: &PackageEntrypoint,
) -> Result<LoadedSource, PackageError> {
    let joined = canonical_root.join(entrypoint.path());
    let metadata = fs::symlink_metadata(&joined).map_err(|error| PackageError::Io {
        path: joined.clone(),
        error,
    })?;
    if metadata.file_type().is_symlink() {
        return Err(PackageError::SourceSymlink {
            path: entrypoint.path().to_owned(),
        });
    }
    if !metadata.is_file() {
        return Err(PackageError::InvalidSourcePath {
            path: entrypoint.path().to_owned(),
            reason: "the entrypoint is not a regular file",
        });
    }
    let canonical = fs::canonicalize(&joined).map_err(|error| PackageError::Io {
        path: joined,
        error,
    })?;
    if !canonical.starts_with(canonical_root) {
        return Err(PackageError::SourceOutsidePackage {
            path: entrypoint.path().to_owned(),
        });
    }
    if usize::try_from(metadata.len()).map_or(true, |len| len > MAX_PACKAGE_SOURCE_BYTES) {
        return Err(PackageError::SourceTooLarge {
            path: entrypoint.path().to_owned(),
            limit: MAX_PACKAGE_SOURCE_BYTES,
        });
    }
    let bytes = fs::read(&canonical).map_err(|error| PackageError::Io {
        path: canonical,
        error,
    })?;
    verify_source_bytes(entrypoint, bytes)
}

fn load_embedded_sources(
    manifest: &PackageManifest,
    sources: &[EmbeddedSource<'_>],
) -> Result<Vec<LoadedSource>, PackageError> {
    let mut loaded = Vec::with_capacity(manifest.entrypoints().len());
    for entrypoint in manifest.entrypoints() {
        let supplied = sources
            .iter()
            .find(|source| {
                source.source_id == entrypoint.source_id() && source.path == entrypoint.path()
            })
            .ok_or_else(|| PackageError::InvalidSourcePath {
                path: entrypoint.path().to_owned(),
                reason: "the embedded package supplies no bytes for this entrypoint",
            })?;
        if supplied.kind != entrypoint.kind() {
            return Err(PackageError::InvalidSourcePath {
                path: entrypoint.path().to_owned(),
                reason: "the embedded source kind disagrees with its manifest entrypoint",
            });
        }
        loaded.push(verify_source_bytes(entrypoint, supplied.bytes.to_vec())?);
    }
    if loaded.len() != sources.len() {
        return Err(PackageError::InvalidSourcePath {
            path: "embedded package".to_owned(),
            reason: "the embedded package supplies a source no entrypoint declares",
        });
    }
    Ok(loaded)
}

fn verify_source_bytes(
    entrypoint: &PackageEntrypoint,
    bytes: Vec<u8>,
) -> Result<LoadedSource, PackageError> {
    if bytes.len() > MAX_PACKAGE_SOURCE_BYTES {
        return Err(PackageError::SourceTooLarge {
            path: entrypoint.path().to_owned(),
            limit: MAX_PACKAGE_SOURCE_BYTES,
        });
    }
    std::str::from_utf8(&bytes).map_err(|_| PackageError::SourceNotUtf8 {
        path: entrypoint.path().to_owned(),
    })?;
    let actual = content_digest::sha256_of(&bytes);
    if actual != entrypoint.sha256() {
        return Err(PackageError::DigestMismatch {
            source_id: entrypoint.source_id().to_owned(),
            expected: entrypoint.sha256(),
            actual,
        });
    }
    Ok(LoadedSource {
        source_id: entrypoint.source_id().to_owned(),
        kind: entrypoint.kind(),
        path: entrypoint.path().to_owned(),
        sha256: actual,
        bytes,
    })
}

fn embedded_manifest(
    id: &str,
    version: &str,
    host_profile: HostProfile,
    sources: &[EmbeddedSource<'_>],
) -> String {
    use std::fmt::Write as _;

    let mut manifest = format!(
        "format_version = {PACKAGE_FORMAT_VERSION}\nid = \"{id}\"\nversion = \"{version}\"\ncontent_abi = \"{CONTENT_ABI}\"\nhost_profile = \"{}\"\ndependencies = []\nreplacements = []\n",
        host_profile.manifest_name()
    );
    for source in sources {
        write!(
            manifest,
            "\n[[entrypoints]]\nsource_id = \"{}\"\nkind = \"{}\"\npath = \"{}\"\nsha256 = \"{}\"\n",
            source.source_id,
            source.kind.as_str(),
            source.path,
            hex_sha256(&content_digest::sha256_of(source.bytes)),
        )
        .expect("writing to a String cannot fail");
    }
    manifest
}

fn hex_sha256(bytes: &[u8; 32]) -> String {
    use std::fmt::Write as _;

    let mut output = String::with_capacity(64);
    for byte in bytes {
        write!(&mut output, "{byte:02x}").expect("writing to a String cannot fail");
    }
    output
}

fn validate_package_id(id: &str) -> Result<(), PackageError> {
    if id.is_empty()
        || id.len() > MAX_PACKAGE_ID_BYTES
        || !id.contains('.')
        || !id
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
    {
        return Err(PackageError::InvalidPackageId { id: id.to_owned() });
    }
    Ok(())
}

fn validate_version(version: &str) -> Result<(), PackageError> {
    if version.is_empty()
        || version.len() > MAX_PACKAGE_VERSION_BYTES
        || !version
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-' | b'+'))
    {
        return Err(PackageError::InvalidVersion {
            version: version.to_owned(),
        });
    }
    Ok(())
}

fn validate_source_id(source_id: &str) -> Result<(), PackageError> {
    if source_id.is_empty()
        || source_id.len() > MAX_SOURCE_ID_BYTES
        || source_id.starts_with('/')
        || source_id.contains('\\')
        || source_id
            .split('/')
            .any(|component| component.is_empty() || component == "." || component == "..")
    {
        return Err(PackageError::InvalidSourcePath {
            path: source_id.to_owned(),
            reason: "a source id is a non-empty normalized forward-slash identity",
        });
    }
    Ok(())
}

fn validate_relative_path(path: &str) -> Result<(), PackageError> {
    if path.is_empty()
        || path.starts_with('/')
        || path.contains('\\')
        || path.contains(':')
        || path
            .split('/')
            .any(|component| component.is_empty() || component == "." || component == "..")
    {
        return Err(PackageError::InvalidSourcePath {
            path: path.to_owned(),
            reason: "paths are normalized forward-slash relative components",
        });
    }
    Ok(())
}

fn parse_digest(field: &'static str, value: &str) -> Result<[u8; 32], PackageError> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    {
        return Err(PackageError::MalformedDigest {
            field,
            value: value.to_owned(),
        });
    }
    let mut digest = [0_u8; 32];
    for (index, pair) in value.as_bytes().chunks_exact(2).enumerate() {
        let text = std::str::from_utf8(pair).map_err(|_| PackageError::MalformedDigest {
            field,
            value: value.to_owned(),
        })?;
        digest[index] =
            u8::from_str_radix(text, 16).map_err(|_| PackageError::MalformedDigest {
                field,
                value: value.to_owned(),
            })?;
    }
    Ok(digest)
}
