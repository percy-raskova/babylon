//! Durable organizer admission and actor-safe snapshots on the existing runtime.

use babylon_practice_contract::{
    admit_organizer, organizer_action_batch, organizer_view, preview_organizer,
    validate_organizer_commitment, OrganizerCommand, OrganizerCommitment, OrganizerPreview,
    OrganizerView,
};
mod collection_preview;
mod material_preview;
pub use collection_preview::OrganizerCollectionPreview;
pub use material_preview::*;

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
    pub duration: babylon_kernel::clock::CampaignDuration,
    pub aid: Vec<OrganizerMaterialAidPreview>,
    pub pending_aid: Vec<OrganizerAidPending>,
    pub aid_resolutions: Vec<OrganizerAidResolution>,
    #[serde(deserialize_with = "collection_preview::required_nullable")]
    pub collection: Option<OrganizerCollectionPreview>,
    pub collection_resolutions: Vec<babylon_practice_contract::OrganizerCollectionResolution>,
}

// Collection amounts and outcomes follow the actor's retained practice
// receipts, joined to their original command and period.
fn collection_history(
    state: &babylon_practice_contract::OrganizerState,
    view: &OrganizerView,
) -> Vec<babylon_practice_contract::OrganizerCollectionResolution> {
    state
        .collection_receipts
        .iter()
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
    capture_pending(client, campaign, period)?
        .admit()
        .map(|value| value.map(|(commitment, _)| commitment))
}

/// Commitment and consumption are read together from the exact mutable command row.
pub(crate) struct CapturedOrganizerCommand {
    campaign: CampaignId,
    row: Option<postgres::Row>,
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
            aid: material_preview::projections(register.state(), config, state.period)
                .map_err(|_| RuntimeSessionErrorCode::OrganizerRefused)?,
            pending_aid: state
                .pending_aid
                .iter()
                .map(material_preview::pending)
                .collect(),
            aid_resolutions: material_preview::resolutions(state),
            collection: collection_preview::projection(register.state(), config, state.period)?,
            collection_resolutions: collection_history(state, &view),
            view,
            pending,
            duration: self.session().duration(),
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
        if !self.session().duration().can_advance(state.period) {
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

    fn partial_collection_session() -> fixture::Session {
        let foundation = crate::michigan_dynamic_hex_foundation().unwrap();
        let base = fixture::authored_session(foundation, fixture::config(), false, false);
        let mut material = base.material().state().clone();
        let CircuitAccounting::Monetary(economy) = &mut material.accounting else {
            panic!("monetary collection fixture");
        };
        let payer = economy.aid.mandates[0].payer;
        let AccountId::Organization(organization) = payer else {
            panic!("existing captured organizational payer");
        };
        let total = economy.book.total_cash_and_reserves().unwrap();
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
            .unwrap();
        assert_eq!(economy.book.total_cash_and_reserves().unwrap(), total);
        let costs = economy.costs.snapshot();
        economy.costs = HistoricalCostBook::open(
            &economy.book,
            costs.stocks,
            costs.freight,
            costs.equity,
            costs.equipment,
        )
        .unwrap();
        let recurring = economy.recurring.as_mut().unwrap();
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
            labor_unit_id: economy.aid.mandates[0].labor_unit_id.as_bytes(),
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
            material,
            config,
        )
        .unwrap()
    }

    fn current_view(register: &MaterialWorldRegister) -> OrganizerView {
        let config = register.organizer_config().unwrap();
        organizer_view(
            config,
            register.organizer_state().unwrap(),
            config.controlled_actor_id,
        )
        .unwrap()
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
            .organizer_state()
            .unwrap()
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
                session.material().organizer_state().unwrap(),
                &current_view(session.material()),
            ),
            vec![original.clone()],
        );
        let later = fixture::prepare(&session, None);
        fixture::commit(&mut session, &mut sink, later);
        let reopened = MaterialWorldRegister::decode(session.material().canonical_bytes()).unwrap();
        assert_eq!(reopened, *session.material());
        let state = reopened.organizer_state().unwrap();
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
        assert_eq!(collection_history(state, &view), vec![original]);
    }

    #[test]
    fn collection_projection_excludes_future_and_nonwindow_actual_facts() {
        let mut session = partial_collection_session();
        let opening_view = current_view(session.material());
        let accepted = fixture::commitment(&session, OrganizerChoice::Collect);
        let first = fixture::prepare(&session, Some(&accepted));
        let mut sink = CollectingSink::default();
        fixture::commit(&mut session, &mut sink, first);
        let reopened = MaterialWorldRegister::decode(session.material().canonical_bytes()).unwrap();
        let state = reopened.organizer_state().unwrap();
        assert_eq!(state.collection_receipts.len(), 1);
        assert!(collection_history(state, &opening_view).is_empty());
        // Restrict only the presentation window, never the canonical successful
        // receipt. A fact outside retained practice IDs must not be disclosed.
        let mut no_retained_receipts = current_view(&reopened);
        no_retained_receipts.receipts.clear();
        assert!(collection_history(state, &no_retained_receipts).is_empty());
    }
}
