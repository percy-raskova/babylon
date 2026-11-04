//! Leaf implementation for the parent module; public paths stay on the parent.

use super::{
    CityPdEncounter, OrganizerAidPending, OrganizerAidResolution, OrganizerMaterialAidPreview,
};

use super::{collection_preview, material_preview, OrganizerCollectionPreview};

use babylon_practice_contract::{
    OrganizerCommand, OrganizerCommitment, OrganizerPreview, OrganizerView,
};

use postgres::{GenericClient, IsolationLevel};

use serde::{Deserialize, Serialize};

use crate::identity::CampaignId;
use crate::material_runtime::{
    DurableMaterialRuntime, MaterialRuntimeError, MaterialRuntimeFoundation,
};
use crate::runtime_session::RuntimeSessionErrorCode;
use crate::ArchiveEvidenceClass;
use babylon_graph::stable_element::{StableElementKey, StableElementResolver};
use babylon_graph::substrate::GraphSubstrate;
use babylon_kernel::clock::CampaignDuration;
use babylon_material_circuit::MaterialCatalog;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_practice_contract::OrganizerCollectionResolution;
use babylon_practice_contract::OrganizerPeriodJournal;
use postgres::Row;
use std::collections::BTreeSet;

/// The portion of the controlled body's incidence authorized for this view.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerBodyPart {
    /// Handle valid only within this reconstructed graph session.
    pub runtime_hyperedge_id: u64,
    /// Stable structural key's scenario component.
    pub scenario: String,
    /// Stable structural key's local-name component.
    pub local_name: String,
    /// Sorted intersection of actual incidence with the actor's disclosed positions.
    pub contributors: Vec<u64>,
    /// Attribution of the authored incidence.
    pub evidence_class: ArchiveEvidenceClass,
}

/// A missing authenticated read is distinct from an affirmative absence.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrganizerBodyDisclosure {
    /// No authenticated, attributed projection is available.
    Unavailable,
    /// An authenticated graph establishes absence for this actor.
    KnownAbsent,
    /// Only the allowed incidence is disclosed.
    Partial(OrganizerBodyPart),
}

/// The authenticated material source behind a body disclosure.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrganizerBodySource {
    /// The attributed graph belongs to the admitted opening foundation.
    Foundation {
        /// Exact authenticated material foundation digest.
        foundation_digest: [u8; 32],
    },
    /// The attributed graph belongs to an authenticated committed tail.
    Committed {
        /// Exact durable tick identity.
        tick_content_hash: [u8; 32],
        /// Nominal material world identity recorded by that tick.
        world_hash: [u8; 32],
    },
}

/// Campaign, actor and period to which this disclosure belongs.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerBodyScope {
    /// Campaign owning the source.
    pub campaign_id: [u8; 16],
    /// Controlled actor for this disclosure.
    pub actor_id: u64,
    /// Committed period represented by this disclosure.
    pub period: u64,
    /// Captured organizer content identity.
    pub content_digest: [u8; 32],
    /// Authenticated source, absent when no source is available.
    pub source: Option<OrganizerBodySource>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerSnapshot {
    pub view: OrganizerView,
    pub body: OrganizerBodyDisclosure,
    pub body_scope: OrganizerBodyScope,
    pub city_pd_encounters: Vec<CityPdEncounter>,
    pub pending: Option<OrganizerCommitment>,
    pub duration: CampaignDuration,
    pub aid: Vec<OrganizerMaterialAidPreview>,
    pub pending_aid: Vec<OrganizerAidPending>,
    pub aid_resolutions: Vec<OrganizerAidResolution>,
    #[serde(deserialize_with = "collection_preview::required_nullable")]
    pub collection: Option<OrganizerCollectionPreview>,
    pub collection_resolutions: Vec<OrganizerCollectionResolution>,
}

/// Bind received aid disclosures to the exact authenticated material register.
pub(crate) fn aid_snapshot_matches(
    catalog: &MaterialCatalog,
    register: &babylon_tick::material_world::MaterialWorldRegister,
    snapshot: &OrganizerSnapshot,
) -> Result<bool, RuntimeSessionErrorCode> {
    let config = register
        .organizer_config()
        .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
    let state = register
        .organizer_state()
        .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
    let journal = register
        .organizer_journal()
        .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
    let mut expected_view = babylon_practice_contract::organizer_view(
        config,
        state,
        journal,
        config.controlled_actor_id,
    )
    .map_err(|_| RuntimeSessionErrorCode::OrganizerRefused)?;
    expected_view.public_workplace_contact = register.public_venue().is_some();
    let encounters_match = encounter_snapshot_matches(register, snapshot)?;
    Ok(encounters_match
        && expected_view == snapshot.view
        && material_preview::projections(catalog, register.state(), config, state.period)?
            == snapshot.aid
        && state
            .pending_aid
            .iter()
            .map(material_preview::pending)
            .collect::<Vec<_>>()
            == snapshot.pending_aid
        && journal
            .latest()
            .map(material_preview::resolutions)
            .unwrap_or_default()
            == snapshot.aid_resolutions)
}

/// Audit a response against an already authenticated register. Live admission
/// separately validates the captured PostgreSQL projection before serialization.
pub(crate) fn encounter_snapshot_matches(
    register: &babylon_tick::material_world::MaterialWorldRegister,
    snapshot: &OrganizerSnapshot,
) -> Result<bool, RuntimeSessionErrorCode> {
    Ok(super::encounter::projections(register)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?
        == snapshot.city_pd_encounters)
}

pub(crate) fn captured_organizer_snapshot(
    catalog: &MaterialCatalog,
    register: &babylon_tick::material_world::MaterialWorldRegister,
    pending: Option<OrganizerCommitment>,
    duration: CampaignDuration,
) -> Result<OrganizerSnapshot, RuntimeSessionErrorCode> {
    let config = register
        .organizer_config()
        .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
    let state = register
        .organizer_state()
        .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
    let journal = register
        .organizer_journal()
        .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
    let mut view = babylon_practice_contract::organizer_view(
        config,
        state,
        journal,
        config.controlled_actor_id,
    )
    .map_err(|_| RuntimeSessionErrorCode::OrganizerRefused)?;
    view.public_workplace_contact = register.public_venue().is_some();
    Ok(OrganizerSnapshot {
        body: OrganizerBodyDisclosure::Unavailable,
        body_scope: OrganizerBodyScope {
            campaign_id: config.campaign_id,
            actor_id: view.actor_id,
            period: view.period,
            content_digest: view.content_digest,
            source: None,
        },
        city_pd_encounters: super::encounter::projections(register)
            .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?,
        aid: material_preview::projections(catalog, register.state(), config, state.period)?,
        pending_aid: state
            .pending_aid
            .iter()
            .map(material_preview::pending)
            .collect(),
        aid_resolutions: journal
            .latest()
            .map(material_preview::resolutions)
            .unwrap_or_default(),
        collection: collection_preview::projection(register.state(), config, state.period)?,
        collection_resolutions: collection_history(journal, &view),
        view,
        pending,
        duration,
    })
}

/// Opening-only attribution retained privately across runtime reconstruction.
pub(crate) struct OrganizerBodyAttribution {
    actor: StableElementKey,
    body: Option<StableElementKey>,
    members: BTreeSet<StableElementKey>,
}

fn body_attribution_from_graph(
    graph: &impl GraphSubstrate,
    resolver: &StableElementResolver,
    actor_id: u64,
) -> Option<OrganizerBodyAttribution> {
    if resolver.scenario_scope() != crate::national_economy::NATIONAL_SCENARIO_ID {
        return None;
    }
    let actor = resolver
        .node_handle_by_local_name("wayne-organizing-collective")
        .ok()?;
    let actor_key = resolver.node_key(actor).ok()?.clone();
    let bodies = graph.hyperedges_of(actor, "ORGANIZATION_BODY").ok()?;
    let (body, members) = match bodies.as_slice() {
        [] => (None, BTreeSet::new()),
        [body] => {
            let key = resolver.hyperedge_key(*body).ok()?.clone();
            if !matches!(&key, StableElementKey::Hyperedge { local_name, .. } if *local_name == format!("organizer-participant-body-{actor_id}"))
            {
                return None;
            }
            let mut members = BTreeSet::new();
            for member in graph.members_of(*body).ok()? {
                members.insert(resolver.node_key(member).ok()?.clone());
            }
            (Some(key), members)
        }
        _ => return None,
    };
    Some(OrganizerBodyAttribution {
        actor: actor_key,
        body,
        members,
    })
}

/// Capture only the authenticated Designed national opening's body provenance.
pub(crate) fn opening_body_attribution(
    foundation: &MaterialRuntimeFoundation,
) -> Option<OrganizerBodyAttribution> {
    use crate::economic_catalog::SourceArtifactKind;
    let catalog = foundation
        .graph_foundation
        .content_bundle()
        .economic_catalog()?;
    let config = catalog.organizer_config()?;
    if foundation.register.organizer_config() != Some(config) {
        return None;
    }
    let policy = crate::national_economy::NationalGamePolicy::from_captured_bytes(
        catalog.source(SourceArtifactKind::NationalGamePolicy)?,
    )
    .ok()?;
    if policy.organizer.evidence_class != "Designed" {
        return None;
    }
    body_attribution_from_graph(
        foundation.graph.graph(),
        foundation.graph.stable_resolver(),
        config.controlled_actor_id,
    )
}

fn project_body(
    graph: &impl GraphSubstrate,
    resolver: &StableElementResolver,
    view: &OrganizerView,
    attribution: Option<&OrganizerBodyAttribution>,
) -> Result<OrganizerBodyDisclosure, RuntimeSessionErrorCode> {
    let Some(attribution) = attribution else {
        return Ok(OrganizerBodyDisclosure::Unavailable);
    };
    let Ok(actor) = resolver.node_handle_by_local_name("wayne-organizing-collective") else {
        return Ok(OrganizerBodyDisclosure::Unavailable);
    };
    let bodies = graph
        .hyperedges_of(actor, "ORGANIZATION_BODY")
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    if resolver.node_key(actor).ok() != Some(&attribution.actor) {
        return Ok(OrganizerBodyDisclosure::Unavailable);
    }
    if bodies.is_empty() {
        return Ok(if attribution.body.is_none() {
            OrganizerBodyDisclosure::KnownAbsent
        } else {
            OrganizerBodyDisclosure::Unavailable
        });
    }
    let [body] = bodies.as_slice() else {
        return Err(RuntimeSessionErrorCode::StorageRefused);
    };
    let StableElementKey::Hyperedge {
        scenario,
        local_name,
    } = resolver
        .hyperedge_key(*body)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?
    else {
        return Err(RuntimeSessionErrorCode::StorageRefused);
    };
    if resolver.hyperedge_key(*body).ok() != attribution.body.as_ref() {
        return Ok(OrganizerBodyDisclosure::Unavailable);
    }
    if *local_name != format!("organizer-participant-body-{}", view.actor_id) {
        return Err(RuntimeSessionErrorCode::StorageRefused);
    }
    let members = graph
        .members_of(*body)
        .map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
    let mut contributors = Vec::new();
    for position in &view.positions {
        let name = format!("organizer-contributor-{}", position.contributor_id);
        let Ok(node) = resolver.node_handle_by_local_name(&name) else {
            continue;
        };
        if !members.contains(&node) {
            continue;
        }
        if resolver
            .node_key(node)
            .ok()
            .is_none_or(|key| !attribution.members.contains(key))
        {
            return Ok(OrganizerBodyDisclosure::Unavailable);
        }
        contributors.push(position.contributor_id);
    }
    contributors.sort_unstable();
    contributors.dedup();
    Ok(OrganizerBodyDisclosure::Partial(OrganizerBodyPart {
        runtime_hyperedge_id: body.0,
        scenario: scenario.clone(),
        local_name: local_name.clone(),
        contributors,
        evidence_class: ArchiveEvidenceClass::Designed,
    }))
}

// Collection amounts and outcomes follow the actor's retained practice
// receipts, joined to their original command and period.
pub(crate) fn collection_history(
    journal: &OrganizerPeriodJournal,
    view: &OrganizerView,
) -> Vec<OrganizerCollectionResolution> {
    journal
        .periods
        .iter()
        .flat_map(|entries| &entries.collection_receipts)
        .filter(|row| {
            row.practice.actor_id == view.actor_id
                && row.fact.period <= view.period
                && view.receipts.iter().any(|receipt| {
                    receipt.actor_id == view.actor_id
                        && receipt.receipt_id == row.practice.receipt_id
                        && receipt.period == row.practice.period
                        && receipt.period == row.fact.period
                        && receipt.commitment_id == Some(row.fact.original_commitment_id)
                })
        })
        .cloned()
        .collect()
}

pub(crate) fn decode_commitment(bytes: &[u8]) -> Result<OrganizerCommitment, MaterialRuntimeError> {
    if bytes.len() > 8192 {
        return Err(MaterialRuntimeError::Bounds);
    }
    let value: OrganizerCommitment =
        serde_json::from_slice(bytes).map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
    if serde_json::to_vec(&value).map_err(|_| MaterialRuntimeError::OrganizerStorage)? != bytes {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    babylon_practice_contract::validate_organizer_commitment(&value)
        .map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
    Ok(value)
}

pub(crate) fn stored_commitment(
    row: &Row,
    campaign: CampaignId,
) -> Result<OrganizerCommitment, MaterialRuntimeError> {
    let value = decode_commitment(&row.get::<_, Vec<u8>>("commitment_bytes"))?;
    let command =
        serde_json::to_vec(&value.command).map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
    if value.command.campaign_id != *campaign.canonical_bytes()
        || row.get::<_, Vec<u8>>("command_bytes") != command
        || row.get::<_, Vec<u8>>("nonce") != value.command.nonce
        || u64::try_from(row.get::<_, i64>("resolves_period")).ok() != Some(value.resolves_period)
        || row.get::<_, Vec<u8>>("commitment_sha256") != value.commitment_id
    {
        return Err(MaterialRuntimeError::OrganizerStorage);
    }
    Ok(value)
}

pub(crate) fn pending(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    period: u64,
) -> Result<Option<OrganizerCommitment>, MaterialRuntimeError> {
    capture_pending(client, campaign, period)?
        .admit()
        .map(|value| value.map(|(commitment, _)| commitment))
}

/// Commitment and consumption are read together from the exact mutable command row.
pub(crate) struct CapturedOrganizerCommand {
    campaign: CampaignId,
    row: Option<Row>,
}

pub(crate) fn capture_pending(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    period: u64,
) -> Result<CapturedOrganizerCommand, MaterialRuntimeError> {
    let period = i64::try_from(period).map_err(|_| MaterialRuntimeError::Bounds)?;
    let row = client.query_opt("SELECT commitment_bytes,command_bytes,nonce,resolves_period,commitment_sha256,consumed_period FROM babylon_state.organizer_command_v1 WHERE campaign_id=$1 AND resolves_period=$2", &[campaign.as_uuid(), &period])?;
    Ok(CapturedOrganizerCommand { campaign, row })
}

impl CapturedOrganizerCommand {
    pub(crate) fn admit(
        self,
    ) -> Result<Option<(OrganizerCommitment, Option<i64>)>, MaterialRuntimeError> {
        self.row
            .map(|row| {
                let commitment = stored_commitment(&row, self.campaign)?;
                let consumed = row.try_get("consumed_period")?;
                Ok((commitment, consumed))
            })
            .transpose()
    }
}

pub(crate) fn classify(error: &MaterialRuntimeError) -> RuntimeSessionErrorCode {
    match error {
        MaterialRuntimeError::DatabaseLockRefused(_) => RuntimeSessionErrorCode::StorageBusy,
        MaterialRuntimeError::DatabaseStatementCanceled(_) => {
            RuntimeSessionErrorCode::StorageCanceled
        }
        MaterialRuntimeError::TailConflict => RuntimeSessionErrorCode::StaleExpectedTail,
        _ => RuntimeSessionErrorCode::StorageRefused,
    }
}

impl DurableMaterialRuntime {
    /// Reconstruct the sole current next-period batch from durable accepted inputs.
    /// # Errors
    /// Refuses stale storage or a malformed captured practice contract.
    pub fn next_action_batch(&self) -> Result<OrderedPracticeActionBatch, MaterialRuntimeError> {
        let session = self.session().graph_session().session_identity().clone();
        let register = self.session().material();
        let next = self
            .session()
            .completed_tick()
            .checked_add(1)
            .ok_or(MaterialRuntimeError::Bounds)?;
        if let (Some(config), Some(state)) =
            (register.organizer_config(), register.organizer_state())
        {
            let mut client = self.organizer_connection()?;
            self.require_organizer_tail(&mut client)?;
            let commitment = pending(&mut client, self.campaign_id(), next)?;
            return babylon_practice_contract::organizer_action_batch(
                config,
                state,
                commitment.as_ref(),
                session,
            )
            .map_err(|_| MaterialRuntimeError::OrganizerStorage);
        }
        OrderedPracticeActionBatch::empty(session, next).map_err(|_| MaterialRuntimeError::Bounds)
    }

    /// Whether captured campaign content enables the bounded organizer loop.
    #[must_use]
    pub fn has_organizer(&self) -> bool {
        self.session().material().organizer_config().is_some()
    }
    /// Read the controlled organization and its durable pending ruling.
    /// # Errors
    /// Refuses unavailable authority, stale storage or malformed accepted inputs.
    pub fn organizer_snapshot(&self) -> Result<OrganizerSnapshot, RuntimeSessionErrorCode> {
        let register = self.session().material();
        let state = register
            .organizer_state()
            .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
        let mut client = self
            .organizer_connection()
            .map_err(|error| classify(&error))?;
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(MaterialRuntimeError::from)
            .map_err(|error| classify(&error))?;
        self.require_organizer_tail(&mut tx)
            .map_err(|error| classify(&error))?;
        let pending = pending(
            &mut tx,
            self.campaign_id(),
            state
                .period
                .checked_add(1)
                .ok_or(RuntimeSessionErrorCode::CommitRefused)?,
        )
        .map_err(|error| classify(&error))?;
        let tick =
            i64::try_from(state.period).map_err(|_| RuntimeSessionErrorCode::StorageRefused)?;
        let future: bool = tx.query_one("SELECT EXISTS (SELECT 1 FROM babylon_state.organizer_encounter_v1 WHERE campaign_id=$1 AND resolve_tick>$2) OR EXISTS (SELECT 1 FROM babylon_meta.archive_knowledge_grant_v1 WHERE campaign_id=$1 AND grant_key LIKE 'city-pd-%' AND granted_tick>$2)", &[self.campaign_id().as_uuid(), &tick])
            .map_err(MaterialRuntimeError::from).map_err(|error| classify(&error))?.get(0);
        if future {
            return Err(RuntimeSessionErrorCode::StorageRefused);
        }
        crate::organizer_archive::capture_projection(&mut tx, self.campaign_id(), state.period)
            .and_then(|projection| projection.validate(register))
            .map_err(|error| classify(&error))?;
        tx.commit()
            .map_err(MaterialRuntimeError::from)
            .map_err(|error| classify(&error))?;
        let mut snapshot = captured_organizer_snapshot(
            self.session().catalog(),
            register,
            pending,
            self.session().duration(),
        )?;
        if snapshot.body_scope.campaign_id != *self.campaign_id().canonical_bytes()
            || snapshot.view.period != self.session().completed_tick()
        {
            return Err(RuntimeSessionErrorCode::StorageRefused);
        }
        let source = match self.tail() {
            None if snapshot.view.period == 0 => OrganizerBodySource::Foundation {
                foundation_digest: self.session().foundation_digest(),
            },
            Some(tail) if tail.resolve_tick() == snapshot.view.period => {
                OrganizerBodySource::Committed {
                    tick_content_hash: *tail.tick_content_hash().as_bytes(),
                    world_hash: tail.result_world_hash(),
                }
            }
            _ => return Err(RuntimeSessionErrorCode::StorageRefused),
        };
        let graph_session = self.session().graph_session();
        snapshot.body = project_body(
            graph_session.graph(),
            graph_session.stable_resolver(),
            &snapshot.view,
            self.body_attribution.as_ref(),
        )?;
        snapshot.body_scope.source = Some(source);
        Ok(snapshot)
    }
    /// Preview a ruling from the current actor-safe knowledge and commitments.
    /// # Errors
    /// Refuses stale, unsupported or completed campaign scopes.
    pub fn preview_organizer_command(
        &self,
        command: &OrganizerCommand,
    ) -> Result<OrganizerPreview, RuntimeSessionErrorCode> {
        let register = self.session().material();
        let config = register
            .organizer_config()
            .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
        let state = register
            .organizer_state()
            .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
        if command.campaign_id != *self.campaign_id().canonical_bytes() {
            return Err(RuntimeSessionErrorCode::OrganizerRefused);
        }
        let mut client = self
            .organizer_connection()
            .map_err(|error| classify(&error))?;
        self.require_organizer_tail(&mut client)
            .map_err(|error| classify(&error))?;
        if !self.session().duration().can_advance(state.period) {
            return Err(RuntimeSessionErrorCode::HorizonComplete);
        }
        babylon_practice_contract::preview_organizer(config, state, command)
            .map_err(|_| RuntimeSessionErrorCode::OrganizerRefused)
    }
    /// Durably admit one immutable ruling without advancing the campaign.
    /// # Errors
    /// Refuses invalid authority, stale scope, conflicting nonce reuse or storage failure.
    pub fn submit_organizer_command(
        &self,
        command: &OrganizerCommand,
    ) -> Result<OrganizerCommitment, RuntimeSessionErrorCode> {
        let register = self.session().material();
        let config = register
            .organizer_config()
            .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
        let state = register
            .organizer_state()
            .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
        if command.campaign_id != *self.campaign_id().canonical_bytes()
            || command.actor_id != config.controlled_actor_id
            || command.authority_id != config.input_authority_id
        {
            return Err(RuntimeSessionErrorCode::OrganizerRefused);
        }
        let command_bytes =
            serde_json::to_vec(command).map_err(|_| RuntimeSessionErrorCode::InvalidRequest)?;
        let mut client = self
            .organizer_connection()
            .map_err(|error| classify(&error))?;
        let mut tx = client
            .transaction()
            .map_err(MaterialRuntimeError::from)
            .map_err(|error| classify(&error))?;
        tx.batch_execute("SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on")
            .map_err(MaterialRuntimeError::from)
            .map_err(|error| classify(&error))?;
        tx.query_one("SELECT campaign_id FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1 FOR UPDATE", &[self.campaign_id().as_uuid()]).map_err(MaterialRuntimeError::from).map_err(|error| classify(&error))?;
        if let Some(row) = tx.query_opt("SELECT commitment_bytes,command_bytes,nonce,resolves_period,commitment_sha256 FROM babylon_state.organizer_command_v1 WHERE campaign_id=$1 AND nonce=$2", &[self.campaign_id().as_uuid(), &&command.nonce[..]]).map_err(MaterialRuntimeError::from).map_err(|error| classify(&error))? {
            if row.get::<_,Vec<u8>>("command_bytes") != command_bytes { return Err(RuntimeSessionErrorCode::OrganizerNonceConflict); }
            return stored_commitment(&row, self.campaign_id()).map_err(|error| classify(&error));
        }
        self.require_organizer_tail(&mut tx)
            .map_err(|error| classify(&error))?;
        if !self.session().duration().can_advance(state.period) {
            return Err(RuntimeSessionErrorCode::HorizonComplete);
        }
        let accepted = babylon_practice_contract::admit_organizer(config, state, command)
            .map_err(|_| RuntimeSessionErrorCode::OrganizerRefused)?;
        if pending(&mut tx, self.campaign_id(), accepted.resolves_period)
            .map_err(|error| classify(&error))?
            .is_some()
        {
            return Err(RuntimeSessionErrorCode::OrganizerAlreadyCommitted);
        }
        let bytes =
            serde_json::to_vec(&accepted).map_err(|_| RuntimeSessionErrorCode::InvalidRequest)?;
        let period = i64::try_from(accepted.resolves_period)
            .map_err(|_| RuntimeSessionErrorCode::InvalidRequest)?;
        tx.execute("INSERT INTO babylon_state.organizer_command_v1 (campaign_id,nonce,resolves_period,command_bytes,commitment_bytes,commitment_sha256) VALUES ($1,$2,$3,$4,$5,$6)", &[self.campaign_id().as_uuid(),&&command.nonce[..],&period,&command_bytes,&bytes,&&accepted.commitment_id[..]]).map_err(MaterialRuntimeError::from).map_err(|error| classify(&error))?;
        tx.commit()
            .map_err(MaterialRuntimeError::from)
            .map_err(|error| classify(&error))?;
        Ok(accepted)
    }
    fn require_organizer_tail(
        &self,
        client: &mut impl GenericClient,
    ) -> Result<(), MaterialRuntimeError> {
        let row = client.query_one("SELECT count(*),coalesce(max(resolve_tick),0),coalesce(bool_and(envelope_layout_version=3),true) FROM babylon_state.tick_commit WHERE campaign_id=$1", &[self.campaign_id().as_uuid()])?;
        let count: i64 = row.try_get(0)?;
        let tick: i64 = row.try_get(1)?;
        let versions: bool = row.try_get(2)?;
        if count != tick
            || !versions
            || u64::try_from(tick).ok() != Some(self.session().completed_tick())
        {
            return Err(MaterialRuntimeError::TailConflict);
        }
        let marker = if tick == 0 {
            None
        } else {
            client.query_opt("SELECT tick_content_hash,envelope_digest FROM babylon_state.tick_commit WHERE campaign_id=$1 AND resolve_tick=$2", &[self.campaign_id().as_uuid(), &tick])?
        };
        match (self.tail(), self.tail_envelope_digest(), marker) {
            (None, None, None) if tick == 0 => Ok(()),
            (Some(expected), Some(digest), Some(row))
                if u64::try_from(tick).ok() == Some(expected.resolve_tick())
                    && row.try_get::<_, Vec<u8>>(0)? == expected.tick_content_hash().as_bytes()
                    && row.try_get::<_, Vec<u8>>(1)? == digest =>
            {
                Ok(())
            }
            _ => Err(MaterialRuntimeError::TailConflict),
        }
    }
}

#[cfg(test)]
mod collection_history_tests {
    use super::*;
    use crate::organizer_aid_fixture as fixture;
    use babylon_bsl::structural_verbs::CollectingSink;
    use babylon_material_circuit::{
        AccountId, CashTransferPurpose, CircuitAccounting, HistoricalCostBook,
    };
    use babylon_practice_contract::{
        OrganizerChoice, OrganizerCollectionMandate, OrganizerCollectionOutcome,
        OrganizerGiftConsent,
    };
    use babylon_tick::material_world::MaterialWorldRegister;
    use fixture::Session;

    fn partial_collection_session() -> Session {
        let foundation =
            crate::michigan_dynamic_hex_foundation().expect("the Michigan hex foundation builds");
        let base = fixture::authored_session(foundation, fixture::config(), false, false);
        let catalog = base.catalog().clone();
        let mut material = base.material().state().clone();
        let CircuitAccounting::Monetary(economy) = &mut material.accounting else {
            panic!("monetary collection fixture");
        };
        let payer = catalog.aid_mandates[0].payer;
        let AccountId::Organization(organization) = payer else {
            panic!("existing captured organizational payer");
        };
        let total = economy
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow");
        // Conserved Designed opening allocation: the existing payer's six
        // micros become donor savings. Actual close alone produces the gift.
        economy
            .book
            .transfer_cash(
                payer,
                AccountId::Household(fixture::household()),
                fixture::money(6),
                CashTransferPurpose::PublicTransfer,
            )
            .expect("the fixture transfer stays funded");
        assert_eq!(
            economy
                .book
                .total_cash_and_reserves()
                .expect("the fixture book totals without overflow"),
            total
        );
        let costs = economy.costs.snapshot();
        economy.costs = HistoricalCostBook::open(
            &economy.book,
            costs.stocks,
            costs.freight,
            costs.equity,
            costs.equipment,
        )
        .expect("the fixture opens the authored source");
        let recurring = economy
            .recurring
            .as_mut()
            .expect("the fixture set the optional field before this borrow");
        recurring.household_purchases[0].target_closing_stock = 4;
        recurring.household_purchases[0].enabled = false;
        for row in &mut recurring.attendance {
            row.planned_hours = 0;
        }
        let mut config = fixture::config();
        let binding = &config.aid_bindings[0];
        config.collection = Some(OrganizerCollectionMandate {
            mandate_id: [93; 32],
            source_hash: [94; 32],
            actor_id: config.controlled_actor_id,
            contributor_id: binding.donor_contributor_id,
            household_principal_id: binding.donor_principal_id,
            organization_account_id: organization.as_bytes(),
            social_class_target: binding.social_class_target,
            labor_unit_id: catalog.aid_mandates[0].labor_unit_id.as_bytes(),
            cash_consent: OrganizerGiftConsent::Accept,
            maximum_cash_micros: 8,
            protected_cash_floor_micros: 2,
            collection_hours: 2,
        });
        fixture::try_session(
            foundation,
            &format!(
                "{}\n{}\n{}",
                fixture::MATERIAL,
                fixture::PRODUCTS,
                fixture::PRACTICE,
            ),
            fixture::Materials {
                catalog: catalog.into_definition(),
                state: material,
            },
            config,
        )
        .expect("the fixture opens a session")
    }

    fn current_view(register: &MaterialWorldRegister) -> OrganizerView {
        let config = register
            .organizer_config()
            .expect("the fixture register carries organizer config");
        babylon_practice_contract::organizer_view(
            config,
            register
                .organizer_state()
                .expect("the fixture register carries organizer state"),
            register
                .organizer_journal()
                .expect("the fixture register carries organizer journal"),
            config.controlled_actor_id,
        )
        .expect("the fixture call `organizer_view` succeeds for the authored inputs")
    }

    #[test]
    fn organizer_body_refuses_matching_namespace_without_attribution() {
        use babylon_graph::memory::MemoryGraph;
        use std::collections::HashMap;

        let session = partial_collection_session();
        let view = current_view(session.material());
        let mut graph = MemoryGraph::new();
        let actor = graph.add_node("ORGANIZATION").expect("actor");
        let contributor = graph.add_node("PARTICIPANT_BODY").expect("contributor");
        let body = graph
            .add_hyperedge("ORGANIZATION_BODY", &[actor, contributor])
            .expect("body");
        let names = HashMap::from([
            (actor, "wayne-organizing-collective".to_owned()),
            (contributor, "organizer-contributor-101".to_owned()),
        ]);
        let edges = HashMap::from([(
            body,
            format!("organizer-participant-body-{}", view.actor_id),
        )]);
        let resolver = StableElementResolver::seal(
            &graph,
            crate::national_economy::NATIONAL_SCENARIO_ID,
            &names,
            &edges,
        )
        .expect("sealed graph");
        assert_eq!(
            project_body(&graph, &resolver, &view, None),
            Ok(OrganizerBodyDisclosure::Unavailable),
            "a matching namespace is not source attribution"
        );
    }

    #[test]
    fn organizer_body_projection_limits_disclosure() {
        use babylon_graph::memory::MemoryGraph;
        use babylon_practice_contract::OrganizerPosition;
        use std::collections::HashMap;

        let session = partial_collection_session();
        let mut snapshot = captured_organizer_snapshot(
            session.catalog(),
            session.material(),
            None,
            session.duration(),
        )
        .expect("the captured organizer situation is available");
        let wire = serde_json::to_value(&snapshot).expect("snapshot serializes");
        assert!(
            wire.get("body").is_some(),
            "body disclosure must be explicit"
        );
        assert!(
            wire.get("body_scope").is_some(),
            "body scope must be explicit"
        );

        snapshot.view.positions = [101, 102]
            .into_iter()
            .map(|contributor_id| OrganizerPosition {
                contributor_id,
                label: "Disclosed".into(),
                promised_hours: 1,
                concern: String::new(),
                objection: String::new(),
                review_condition: String::new(),
            })
            .collect();
        let build = |hidden: u64, partner_first: bool, with_body: bool| {
            let mut graph = MemoryGraph::new();
            let mut names = HashMap::new();
            let mut node = |name: String, kind: &str| {
                let id = graph.add_node(kind).expect("fixture node");
                names.insert(id, name);
                id
            };
            let actor = node("wayne-organizing-collective".into(), "ORGANIZATION");
            let partner = node("partner-private".into(), "ORGANIZATION");
            let first = node("organizer-contributor-101".into(), "PARTICIPANT_BODY");
            let second = node("organizer-contributor-102".into(), "PARTICIPANT_BODY");
            let hidden_node = node(
                format!("organizer-contributor-{hidden}"),
                "PARTICIPANT_BODY",
            );
            graph
                .update_node(
                    partner,
                    "private/balance",
                    if hidden == 103 { 1.0 } else { 2.0 },
                )
                .expect("private partner data");
            let mut edges = HashMap::new();
            if partner_first {
                let id = graph
                    .add_hyperedge("ORGANIZATION_BODY", &[partner, hidden_node])
                    .expect("partner body");
                edges.insert(id, "partner-body".into());
            }
            if with_body {
                let id = graph
                    .add_hyperedge("ORGANIZATION_BODY", &[actor, first, second, hidden_node])
                    .expect("controlled body");
                edges.insert(
                    id,
                    format!("organizer-participant-body-{}", snapshot.view.actor_id),
                );
            }
            if !partner_first {
                let id = graph
                    .add_hyperedge("ORGANIZATION_BODY", &[partner, hidden_node])
                    .expect("partner body");
                edges.insert(id, "partner-body".into());
            }
            let resolver = StableElementResolver::seal(
                &graph,
                crate::national_economy::NATIONAL_SCENARIO_ID,
                &names,
                &edges,
            )
            .expect("sealed graph");
            (graph, resolver)
        };
        let (graph, resolver) = build(103, false, true);
        let attribution = body_attribution_from_graph(&graph, &resolver, snapshot.view.actor_id)
            .expect("attributed opening");
        let disclosed = project_body(&graph, &resolver, &snapshot.view, Some(&attribution))
            .expect("projection");
        let OrganizerBodyDisclosure::Partial(part) = &disclosed else {
            panic!("controlled body is partial")
        };
        assert_eq!(part.contributors, [101, 102]);
        assert_eq!(
            part.local_name,
            format!("organizer-participant-body-{}", snapshot.view.actor_id)
        );
        assert_eq!(part.scenario, crate::national_economy::NATIONAL_SCENARIO_ID);
        assert_eq!(
            part.runtime_hyperedge_id,
            resolver
                .hyperedge_handle_by_local_name(&part.local_name)
                .expect("actual body")
                .0
        );
        let (other_graph, other_resolver) = build(104, false, true);
        let other = project_body(
            &other_graph,
            &other_resolver,
            &snapshot.view,
            Some(&attribution),
        )
        .expect("projection");
        assert_eq!(
            serde_json::to_vec(&disclosed).expect("serialize"),
            serde_json::to_vec(&other).expect("serialize"),
            "hidden inputs do not affect disclosure"
        );
        let (reopened, reopened_resolver) = build(104, true, true);
        let OrganizerBodyDisclosure::Partial(reopened_part) = project_body(
            &reopened,
            &reopened_resolver,
            &snapshot.view,
            Some(&attribution),
        )
        .expect("reopened projection") else {
            panic!("body survives reopen")
        };
        assert_ne!(
            part.runtime_hyperedge_id,
            reopened_part.runtime_hyperedge_id
        );
        assert_eq!(
            (&part.scenario, &part.local_name, &part.contributors),
            (
                &reopened_part.scenario,
                &reopened_part.local_name,
                &reopened_part.contributors
            )
        );
        let (absent, absent_resolver) = build(104, false, false);
        let absent_attribution =
            body_attribution_from_graph(&absent, &absent_resolver, snapshot.view.actor_id)
                .expect("attributed absence");
        assert_eq!(
            project_body(
                &absent,
                &absent_resolver,
                &snapshot.view,
                Some(&absent_attribution)
            ),
            Ok(OrganizerBodyDisclosure::KnownAbsent)
        );
        let mut unproven_view = snapshot.view.clone();
        let mut unproven = unproven_view.positions[0].clone();
        unproven.contributor_id = 104;
        unproven_view.positions.push(unproven);
        assert_eq!(
            project_body(
                &other_graph,
                &other_resolver,
                &unproven_view,
                Some(&attribution)
            ),
            Ok(OrganizerBodyDisclosure::Unavailable),
            "a newly disclosed incidence needs its own attribution"
        );
        let unknown_graph = MemoryGraph::new();
        let unknown_resolver = StableElementResolver::seal(
            &unknown_graph,
            "unattributed",
            &HashMap::new(),
            &HashMap::new(),
        )
        .expect("other scenario can be sealed");
        assert_eq!(
            project_body(&unknown_graph, &unknown_resolver, &snapshot.view, None),
            Ok(OrganizerBodyDisclosure::Unavailable),
            "an unattributed source is not affirmative absence"
        );
        snapshot.body = disclosed.clone();
        let wire = serde_json::to_value(&snapshot).expect("projected snapshot serializes");
        assert_eq!(
            wire["body"]["Partial"]["runtime_hyperedge_id"],
            part.runtime_hyperedge_id
        );
        assert_eq!(wire["body"]["Partial"]["local_name"], part.local_name);
        assert_eq!(
            wire["body"]["Partial"]["contributors"],
            serde_json::json!([101, 102])
        );
    }

    #[test]
    fn partial_detail_survives_later_ordinary_period_and_canonical_reopen() {
        let mut session = partial_collection_session();
        let accepted = fixture::commitment(&session, OrganizerChoice::Collect);
        let first = fixture::prepare(&session, Some(&accepted));
        let mut sink = CollectingSink::default();
        fixture::commit(&mut session, &mut sink, first);
        let original = session
            .material()
            .organizer_journal()
            .and_then(|journal| journal.latest())
            .expect("the fixture register carries organizer journal entries")
            .collection_receipts[0]
            .clone();
        assert_eq!(original.fact.requested_cash_micros, 8);
        assert_eq!(original.fact.collected_cash_micros, 4);
        assert_eq!(
            original.fact.outcome,
            OrganizerCollectionOutcome::PartiallyCollected,
        );
        assert_eq!(original.fact.performed_hours, 2);
        assert_eq!(original.fact.original_commitment_id, accepted.commitment_id);
        assert_eq!(
            collection_history(
                session
                    .material()
                    .organizer_journal()
                    .expect("the fixture register carries organizer journal"),
                &current_view(session.material()),
            ),
            vec![original.clone()],
        );
        let later = fixture::prepare(&session, None);
        fixture::commit(&mut session, &mut sink, later);
        let reopened = MaterialWorldRegister::decode_external(
            session.catalog(),
            session.material().canonical_bytes().to_vec(),
        )
        .expect("the committed canonical bytes decode");
        assert_eq!(reopened, *session.material());
        let journal = reopened
            .organizer_journal()
            .expect("the fixture register carries organizer journal");
        let view = current_view(&reopened);
        assert_eq!(view.period, 2);
        assert!(view
            .receipts
            .iter()
            .any(|row| row.period == 2 && row.choice == OrganizerChoice::Hold));
        assert!(view.receipts.iter().any(|row| {
            row.receipt_id == original.practice.receipt_id
                && row.period == original.fact.period
                && row.commitment_id == Some(accepted.commitment_id)
        }));
        assert_eq!(collection_history(journal, &view), vec![original]);
    }

    #[test]
    fn collection_projection_excludes_future_and_nonwindow_actual_facts() {
        let mut session = partial_collection_session();
        let opening_view = current_view(session.material());
        let accepted = fixture::commitment(&session, OrganizerChoice::Collect);
        let first = fixture::prepare(&session, Some(&accepted));
        let mut sink = CollectingSink::default();
        fixture::commit(&mut session, &mut sink, first);
        let reopened = MaterialWorldRegister::decode_external(
            session.catalog(),
            session.material().canonical_bytes().to_vec(),
        )
        .expect("the committed canonical bytes decode");
        let journal = reopened
            .organizer_journal()
            .expect("the fixture register carries organizer journal");
        assert_eq!(
            journal
                .periods
                .iter()
                .map(|entries| entries.collection_receipts.len())
                .sum::<usize>(),
            1
        );
        assert_eq!(collection_history(journal, &opening_view).len(), 0);
        // Restrict only the presentation window, never the canonical successful
        // receipt. A fact outside retained practice IDs must not be disclosed.
        let mut no_retained_receipts = current_view(&reopened);
        no_retained_receipts.receipts.clear();
        assert_eq!(collection_history(journal, &no_retained_receipts).len(), 0);
    }
}
