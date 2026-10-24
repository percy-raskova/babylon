//! One read-only cursor over an explicitly selected national campaign.
use super::{BoundaryFacts, MaterialAudit, Refusal as MaterialRefusal, Scope};
use crate::archive_revision::{ArchiveDossierBounds, ArchiveDossierState, ArchiveReadScope};
use crate::observer_reader::{ObserverEconomyReader, ObserverMaterialCursor, ObserverVisibility};
use crate::{ArchivePageRef, ArchiveSubjectKind, SemanticArchiveReader};

use postgres::Config;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::time::Instant;
use uuid::Uuid;

#[derive(Debug, PartialEq, Eq)]
pub enum Refusal {
    Version,
    Hash,
    Period,
    Reader,
    Archive,
    ChangedBoundary,
    Duration,
    Material(MaterialRefusal),
}
impl std::fmt::Display for Refusal {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "material audit read refused: {self:?}")
    }
}
impl std::error::Error for Refusal {}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub version: u64,
    pub tick: u64,
    pub tick_content_hash: String,
}
impl Request {
    /// # Errors
    /// Refuses unsupported versions, tick zero and noncanonical hashes.
    pub fn validate(&self) -> Result<(), Refusal> {
        if self.version != 1 {
            return Err(Refusal::Version);
        }
        if self.tick == 0 {
            return Err(Refusal::Period);
        }
        if self.tick_content_hash.len() != 64
            || !self
                .tick_content_hash
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err(Refusal::Hash);
        }
        Ok(())
    }
}

#[derive(Serialize)]
pub struct ArchiveFacts {
    pub expected_tick: u64,
    pub durable_tick: u64,
    pub processed_tick: u64,
    pub pending_count: u64,
    pub pending_scope: &'static str,
    pub observation_mode: &'static str,
    pub captured_tail_tick: u64,
    pub captured_tail_tick_content_hash: String,
    pub dossier_sha256: String,
}

#[derive(Serialize)]
pub struct BoundaryRead {
    pub version: u8,
    pub scope: &'static str,
    pub facts: BoundaryFacts,
    pub archive: ArchiveFacts,
    pub production_read_elapsed_ns: u64,
    pub audit_elapsed_ns: u64,
}

#[derive(Serialize)]
pub struct ArchiveBoundaryRead {
    pub version: u8,
    pub scope: &'static str,
    pub campaign: String,
    pub foundation_sha256: String,
    pub graph_foundation_sha256: String,
    pub policy_sha256: String,
    pub tick: u64,
    pub tick_content_hash: String,
    pub archive: ArchiveFacts,
    pub archive_read_elapsed_ns: u64,
}

#[derive(PartialEq, Eq)]
struct FoundationHeaders {
    preset: String,
    duration: babylon_kernel::clock::CampaignDuration,
    content: Vec<u8>,
    material_foundation: Vec<u8>,
    graph_foundation: Vec<u8>,
    graph_source: Vec<u8>,
    geography: String,
}
impl FoundationHeaders {
    fn validate(
        &self,
        expected: [u8; 32],
        expected_graph: [u8; 32],
        tick: u64,
    ) -> Result<(), Refusal> {
        crate::economic_content::validate_economic_header(
            &self.preset,
            self.duration,
            &self.content,
            &self.material_foundation,
            tick,
        )
        .map_err(|_| Refusal::ChangedBoundary)?;
        if self.preset != "national-world"
            || self.geography != "national-counties"
            || self.material_foundation.as_slice() != expected
            || expected_graph == [0; 32]
            || self.graph_foundation.as_slice() != expected_graph
            || self.graph_source.len() != 32
            || self.graph_source.iter().all(|b| *b == 0)
        {
            return Err(Refusal::ChangedBoundary);
        }
        Ok(())
    }
}

fn capture_foundation_headers(
    reader: &SemanticArchiveReader,
    scope: Scope,
    expected_graph: [u8; 32],
    tick: u64,
) -> Result<FoundationHeaders, Refusal> {
    let mut client = reader
        .connect("connect qualification Archive foundation header reader")
        .map_err(|_| Refusal::Reader)?;
    // One statement joins two already granted views in the same snapshot.
    // These headers bind the supervisor's previously authenticated opening;
    // they do not rehash the full foundation or admit opaque material bytes.
    let row = client
        .query_opt(
            "SELECT m.campaign_id,m.preset_id,m.duration_kind,m.final_period,\
             m.content_sha256,m.foundation_sha256,\
             g.foundation_sha256 AS graph_foundation_sha256,g.source_sha256,g.geography_scope \
             FROM public.v_material_campaign_identity_v2 m \
             JOIN public.v_observer_economy_foundation_v1 g USING(campaign_id) \
             WHERE m.campaign_id=$1",
            &[scope.campaign.as_uuid()],
        )
        .map_err(|_| Refusal::Reader)?
        .ok_or(Refusal::ChangedBoundary)?;
    let campaign: Uuid = row.try_get("campaign_id").map_err(|_| Refusal::Reader)?;
    if &campaign != scope.campaign.as_uuid() {
        return Err(Refusal::ChangedBoundary);
    }
    let headers = FoundationHeaders {
        preset: row.try_get("preset_id").map_err(|_| Refusal::Reader)?,
        duration: crate::material_runtime::read_duration(&row)
            .map_err(|_| Refusal::ChangedBoundary)?,
        content: row.try_get("content_sha256").map_err(|_| Refusal::Reader)?,
        material_foundation: row
            .try_get("foundation_sha256")
            .map_err(|_| Refusal::Reader)?,
        graph_foundation: row
            .try_get("graph_foundation_sha256")
            .map_err(|_| Refusal::Reader)?,
        graph_source: row.try_get("source_sha256").map_err(|_| Refusal::Reader)?,
        geography: row
            .try_get("geography_scope")
            .map_err(|_| Refusal::Reader)?,
    };
    headers.validate(scope.foundation, expected_graph, tick)?;
    Ok(headers)
}

/// Read the required dossiers without a second full material reconstruction.
/// The caller supplies both distinct foundation identities from its fully
/// authenticated opening. The graph hash is a component of the composite
/// material foundation; the two identities must never be conflated.
/// This independently authenticates Archive bytes and membership, and binds
/// retained headers; it supplies no material-accounting admission.
/// # Errors
/// Refuses incomplete/corrupted dossiers, changed headers or committed identity.
pub fn read_archive_boundary(
    scope: Scope,
    expected_graph: [u8; 32],
    reader: &SemanticArchiveReader,
    request: &Request,
) -> Result<ArchiveBoundaryRead, Refusal> {
    request.validate()?;
    let started = Instant::now();
    let headers = capture_foundation_headers(reader, scope, expected_graph, request.tick)?;
    let tail = capture_tail(reader, scope)?;
    tail.admits(request)?;
    let archive = archive_facts(reader, scope, request, &tail)?;
    if capture_foundation_headers(reader, scope, expected_graph, request.tick)? != headers {
        return Err(Refusal::ChangedBoundary);
    }
    verify_tail(reader, scope, &tail)?;
    Ok(ArchiveBoundaryRead {
        version: 1,
        scope: "authenticated_archive_dossiers_and_retained_foundation_headers_only",
        campaign: scope.campaign.as_uuid().to_string(),
        foundation_sha256: super::hex(&scope.foundation),
        graph_foundation_sha256: super::hex(&expected_graph),
        policy_sha256: super::hex(&scope.policy),
        tick: request.tick,
        tick_content_hash: request.tick_content_hash.clone(),
        archive,
        archive_read_elapsed_ns: nanos(started.elapsed().as_nanos())?,
    })
}

pub struct ReadSession {
    scope: Scope,
    observer: Config,
    archive: SemanticArchiveReader,
    cursor: Option<ObserverMaterialCursor>,
    audit: MaterialAudit,
    period: u64,
}
impl ReadSession {
    /// # Errors
    /// Refuses invalid scope or credentials outside the confined reader contract.
    pub fn new(scope: Scope, observer: &Config, archive_dsn: &str) -> Result<Self, Refusal> {
        let audit = MaterialAudit::new(scope).map_err(Refusal::Material)?;
        // Admit authority before any costly capture. This capability is dropped;
        // the cursor cannot extend the foundation graph's lifetime.
        ObserverEconomyReader::connect(observer, ObserverVisibility::FullObserver)
            .map_err(|_| Refusal::Reader)?;
        let archive = SemanticArchiveReader::from_dsn(archive_dsn).map_err(|_| Refusal::Archive)?;
        Ok(Self {
            scope,
            observer: observer.clone(),
            archive,
            cursor: None,
            audit,
            period: 0,
        })
    }

    /// # Errors
    /// Refuses an incomplete Archive boundary, altered committed identity or
    /// invalid accounting. No cursor or fold changes on failure.
    pub fn read(&mut self, request: &Request) -> Result<BoundaryRead, Refusal> {
        request.validate()?;
        if self.period.checked_add(1) != Some(request.tick) {
            return Err(Refusal::Period);
        }
        let tail = capture_tail(&self.archive, self.scope)?;
        tail.admits(request)?;
        let archive = archive_facts(&self.archive, self.scope, request, &tail)?;
        let started = Instant::now();
        let mut cursor = self.cursor.clone();
        let observation = {
            let reader =
                ObserverEconomyReader::connect(&self.observer, ObserverVisibility::FullObserver)
                    .map_err(|_| Refusal::Reader)?;
            reader
                .committed_material_observation_with_cursor(
                    self.scope.campaign,
                    request.tick,
                    &mut cursor,
                )
                .map_err(|_| Refusal::Reader)?
        };
        let production_read_elapsed_ns = nanos(started.elapsed().as_nanos())?;
        if super::hex(
            observation
                .accounting
                .identity
                .tick_content_hash()
                .as_bytes(),
        ) != request.tick_content_hash
        {
            return Err(Refusal::ChangedBoundary);
        }
        // Dossier reads and material reconstruction used separate confined
        // transactions. Recheck the exact acknowledged tail before publication.
        verify_tail(&self.archive, self.scope, &tail)?;
        let register = cursor
            .as_ref()
            .and_then(ObserverMaterialCursor::current_register)
            .ok_or(Refusal::Reader)?;
        let audit_started = Instant::now();
        let mut audit = self.audit.clone();
        let facts = audit
            .read(&observation, register)
            .map_err(Refusal::Material)?;
        let audit_elapsed_ns = nanos(audit_started.elapsed().as_nanos())?;
        let result = BoundaryRead {
            version: 1,
            scope: "authenticated_material_and_archive_facts_only",
            facts,
            archive,
            production_read_elapsed_ns,
            audit_elapsed_ns,
        };
        self.cursor = cursor;
        self.audit = audit;
        self.period = request.tick;
        Ok(result)
    }
}

#[derive(Debug, PartialEq, Eq)]
struct CapturedTail {
    tick: u64,
    hash: String,
}
impl CapturedTail {
    fn admits(&self, request: &Request) -> Result<(), Refusal> {
        if request.tick > self.tick
            || (request.tick == self.tick && request.tick_content_hash != self.hash)
        {
            return Err(Refusal::ChangedBoundary);
        }
        Ok(())
    }
}

fn capture_tail(reader: &SemanticArchiveReader, scope: Scope) -> Result<CapturedTail, Refusal> {
    let marker = reader
        .committed_tick_status(scope.campaign)
        .map_err(|_| Refusal::Archive)?
        .ok_or(Refusal::Archive)?;
    Ok(CapturedTail {
        tick: marker.resolve_tick(),
        hash: super::hex(marker.tick_content_hash()),
    })
}

fn verify_tail(
    reader: &SemanticArchiveReader,
    scope: Scope,
    captured: &CapturedTail,
) -> Result<(), Refusal> {
    if &capture_tail(reader, scope)? != captured {
        return Err(Refusal::ChangedBoundary);
    }
    Ok(())
}

fn archive_facts(
    reader: &SemanticArchiveReader,
    scope: Scope,
    request: &Request,
    tail: &CapturedTail,
) -> Result<ArchiveFacts, Refusal> {
    verify_tail(reader, scope, tail)?;
    let progress = reader
        .archive_verification_status(scope.campaign)
        .map_err(|_| Refusal::Archive)?
        .ok_or(Refusal::Archive)?;
    let observation_mode = horizons(
        tail,
        request,
        progress.durable_tick(),
        progress.processed_tick(),
    )?;
    let mut requested_hash = [0_u8; 32];
    for (index, byte) in requested_hash.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&request.tick_content_hash[index * 2..index * 2 + 2], 16)
            .map_err(|_| Refusal::Hash)?;
    }
    let read_scope = ArchiveReadScope::committed(scope.campaign, request.tick, requested_hash)
        .map_err(|_| Refusal::Archive)?;
    let mut dossier = Sha256::new();
    for (kind, subject) in [
        (ArchiveSubjectKind::County, "26163"),
        (ArchiveSubjectKind::Organization, "2616301"),
    ] {
        let subject =
            ArchivePageRef::try_new(kind, subject.to_owned()).map_err(|_| Refusal::Archive)?;
        let read = reader
            .dossier_as_of(&read_scope, &subject, &ArchiveDossierBounds::default())
            .map_err(|_| Refusal::Archive)?;
        if read.scope != read_scope
            || read.subject != subject
            || read.durable_tick != progress.durable_tick()
            || read.processed_tick != progress.processed_tick()
        {
            return Err(Refusal::Archive);
        }
        let ArchiveDossierState::Ready {
            page,
            verified_through_tick,
        } = read.state
        else {
            return Err(Refusal::Archive);
        };
        if verified_through_tick != request.tick
            || page.content_source.tick() > request.tick
            || page.markdown.is_empty()
            || page.citations.is_empty()
        {
            return Err(Refusal::Archive);
        }
        dossier.update(page.revision_id);
        dossier.update(page.content_sha256);
        dossier.update(Sha256::digest(page.markdown.as_bytes()));
    }
    verify_tail(reader, scope, tail)?;
    Ok(ArchiveFacts {
        expected_tick: request.tick,
        durable_tick: progress.durable_tick(),
        processed_tick: progress.processed_tick(),
        // The confined verification view computes the contiguous prefix from
        // *matching-hash* consumption markers. Coverage proves no pending prefix
        // through this requested tick, not the absence of later pending work.
        pending_count: 0,
        pending_scope: "requested_prefix",
        observation_mode,
        captured_tail_tick: tail.tick,
        captured_tail_tick_content_hash: tail.hash.clone(),
        dossier_sha256: super::hex(&dossier.finalize()),
    })
}

fn horizons(
    tail: &CapturedTail,
    request: &Request,
    durable: u64,
    processed: u64,
) -> Result<&'static str, Refusal> {
    tail.admits(request)?;
    if durable != tail.tick || processed < request.tick || processed > durable {
        return Err(Refusal::Archive);
    }
    Ok(if request.tick == tail.tick {
        "live_latest"
    } else {
        "historical"
    })
}

fn nanos(value: u128) -> Result<u64, Refusal> {
    u64::try_from(value).map_err(|_| Refusal::Duration)
}

#[cfg(test)]
mod tests {
    use super::{CapturedTail, Refusal, Request};

    #[test]
    fn archive_header_binding_requires_both_foundations_and_the_national_source() {
        use babylon_kernel::clock::CampaignDuration;
        let mut header = super::FoundationHeaders {
            preset: "national-world".into(),
            duration: CampaignDuration::Continuous,
            content: vec![1; 32],
            material_foundation: vec![2; 32],
            graph_foundation: vec![3; 32],
            graph_source: vec![3; 32],
            geography: "national-counties".into(),
        };
        assert!(header.validate([2; 32], [3; 32], 1).is_ok());
        assert_eq!(
            header.validate([4; 32], [3; 32], 1),
            Err(Refusal::ChangedBoundary)
        );
        header.graph_foundation = vec![4; 32];
        assert_eq!(
            header.validate([2; 32], [3; 32], 1),
            Err(Refusal::ChangedBoundary)
        );
        header.graph_foundation = vec![3; 32];
        header.graph_source = vec![0; 32];
        assert_eq!(
            header.validate([2; 32], [3; 32], 1),
            Err(Refusal::ChangedBoundary)
        );
        header.graph_source = vec![3; 32];
        header.geography = "michigan-control".into();
        assert_eq!(
            header.validate([2; 32], [3; 32], 1),
            Err(Refusal::ChangedBoundary)
        );
        header.geography = "national-counties".into();
        header.content.clear();
        assert_eq!(
            header.validate([2; 32], [3; 32], 1),
            Err(Refusal::ChangedBoundary)
        );
    }

    #[test]
    fn historical_scope_keeps_its_own_hash_and_global_horizons() {
        let tail = CapturedTail {
            tick: 7,
            hash: "b".repeat(64),
        };
        let request = Request {
            version: 1,
            tick: 3,
            tick_content_hash: "a".repeat(64),
        };
        assert_eq!(super::horizons(&tail, &request, 7, 5), Ok("historical"));
        assert_eq!(
            super::horizons(&tail, &request, 7, 2),
            Err(Refusal::Archive)
        );
        assert_eq!(
            super::horizons(&tail, &request, 8, 5),
            Err(Refusal::Archive)
        );
        assert_eq!(
            super::horizons(&tail, &request, 7, 8),
            Err(Refusal::Archive)
        );
        let latest = Request {
            version: 1,
            tick: 7,
            tick_content_hash: tail.hash.clone(),
        };
        assert_eq!(super::horizons(&tail, &latest, 7, 6), Err(Refusal::Archive));
        assert_eq!(super::horizons(&tail, &latest, 7, 7), Ok("live_latest"));
        let wrong_latest = Request {
            tick_content_hash: "a".repeat(64),
            ..latest
        };
        assert_eq!(
            super::horizons(&tail, &wrong_latest, 7, 7),
            Err(Refusal::ChangedBoundary)
        );
    }

    #[test]
    fn refuses_unsupported_duplicate_or_unknown_request_fields() {
        for bytes in [
            r#"{"version":1,"tick":1,"tick":2,"tick_content_hash":"bad"}"#,
            r#"{"version":1,"tick":1,"tick_content_hash":"bad","advance":true}"#,
            r#"{"version":1.0,"tick":1,"tick_content_hash":"bad"}"#,
        ] {
            assert!(serde_json::from_str::<Request>(bytes).is_err());
        }
        let request = Request {
            version: 2,
            tick: 1,
            tick_content_hash: "a".repeat(64),
        };
        assert_eq!(request.validate(), Err(Refusal::Version));
    }

    #[test]
    fn requests_select_an_exact_positive_boundary_without_mutation() {
        let mut request = Request {
            version: 1,
            tick: 0,
            tick_content_hash: "a".repeat(64),
        };
        assert_eq!(request.validate(), Err(Refusal::Period));
        request.tick = 1;
        request.tick_content_hash = "A".repeat(64);
        assert_eq!(request.validate(), Err(Refusal::Hash));
        request.tick_content_hash = "a".repeat(64);
        assert_eq!(request.validate(), Ok(()));
    }
}
