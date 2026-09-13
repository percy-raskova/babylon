//! Durable organizer admission and actor-safe snapshots on the existing runtime.

use babylon_practice_contract::{
    admit_organizer, organizer_action_batch, organizer_view, preview_organizer,
    validate_organizer_commitment, OrganizerCommand, OrganizerCommitment, OrganizerPreview,
    OrganizerView,
};
use postgres::GenericClient;
use serde::{Deserialize, Serialize};

use crate::{
    identity::CampaignId,
    material_runtime::{DurableMaterialRuntime, MaterialRuntimeError},
    runtime_session::RuntimeSessionErrorCode,
};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerSnapshot {
    pub view: OrganizerView,
    pub pending: Option<OrganizerCommitment>,
    pub horizon_tick: u64,
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
    validate_organizer_commitment(&value).map_err(|_| MaterialRuntimeError::OrganizerStorage)?;
    Ok(value)
}

fn stored_commitment(
    row: &postgres::Row,
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
    let period = i64::try_from(period).map_err(|_| MaterialRuntimeError::Bounds)?;
    let row = client.query_opt("SELECT commitment_bytes,command_bytes,nonce,resolves_period,commitment_sha256 FROM babylon_state.organizer_command_v1 WHERE campaign_id=$1 AND resolves_period=$2", &[campaign.as_uuid(), &period])?;
    row.map(|row| stored_commitment(&row, campaign)).transpose()
}

fn classify(error: &MaterialRuntimeError) -> RuntimeSessionErrorCode {
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
    pub fn next_action_batch(
        &self,
    ) -> Result<babylon_practice_contract::OrderedPracticeActionBatch, MaterialRuntimeError> {
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
            return organizer_action_batch(config, state, commitment.as_ref(), session)
                .map_err(|_| MaterialRuntimeError::OrganizerStorage);
        }
        babylon_practice_contract::OrderedPracticeActionBatch::empty(session, next)
            .map_err(|_| MaterialRuntimeError::Bounds)
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
        let config = register
            .organizer_config()
            .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
        let state = register
            .organizer_state()
            .ok_or(RuntimeSessionErrorCode::OrganizerUnavailable)?;
        let view = organizer_view(config, state, config.controlled_actor_id)
            .map_err(|_| RuntimeSessionErrorCode::OrganizerRefused)?;
        let mut client = self
            .organizer_connection()
            .map_err(|error| classify(&error))?;
        self.require_organizer_tail(&mut client)
            .map_err(|error| classify(&error))?;
        let pending = pending(
            &mut client,
            self.campaign_id(),
            state
                .period
                .checked_add(1)
                .ok_or(RuntimeSessionErrorCode::CommitRefused)?,
        )
        .map_err(|error| classify(&error))?;
        Ok(OrganizerSnapshot {
            view,
            pending,
            horizon_tick: self.session().horizon(),
        })
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
        if state.period >= self.session().horizon() {
            return Err(RuntimeSessionErrorCode::HorizonComplete);
        }
        preview_organizer(config, state, command)
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
        tx.query_one("SELECT campaign_id FROM babylon_state.material_campaign_foundation_v2 WHERE campaign_id=$1 FOR UPDATE", &[self.campaign_id().as_uuid()]).map_err(MaterialRuntimeError::from).map_err(|error| classify(&error))?;
        if let Some(row) = tx.query_opt("SELECT commitment_bytes,command_bytes,nonce,resolves_period,commitment_sha256 FROM babylon_state.organizer_command_v1 WHERE campaign_id=$1 AND nonce=$2", &[self.campaign_id().as_uuid(), &&command.nonce[..]]).map_err(MaterialRuntimeError::from).map_err(|error| classify(&error))? {
            if row.get::<_,Vec<u8>>("command_bytes") != command_bytes { return Err(RuntimeSessionErrorCode::OrganizerNonceConflict); }
            return stored_commitment(&row, self.campaign_id()).map_err(|error| classify(&error));
        }
        self.require_organizer_tail(&mut tx)
            .map_err(|error| classify(&error))?;
        if state.period >= self.session().horizon() {
            return Err(RuntimeSessionErrorCode::HorizonComplete);
        }
        let accepted = admit_organizer(config, state, command)
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
        let row = client.query_one("SELECT COALESCE(MAX(resolve_tick),0) FROM babylon_state.tick_commit WHERE campaign_id=$1", &[self.campaign_id().as_uuid()])?;
        if u64::try_from(row.get::<_, i64>(0)).ok() != Some(self.session().completed_tick()) {
            return Err(MaterialRuntimeError::TailConflict);
        }
        Ok(())
    }
}
