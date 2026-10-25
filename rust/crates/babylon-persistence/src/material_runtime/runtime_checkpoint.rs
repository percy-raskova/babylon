//! Owned checkpoint and organizer witnesses shared by Open and Archive admission.
use super::{
    CampaignId, CapturedMaterialTick, GenericClient, MaterialComponentIdentity,
    MaterialEnvelopeRead, MaterialReadAuthority, MaterialRuntimeError, MaterialWorldRegister,
    OrderedPracticeActionBatch, StoredMaterialTick, StoredTickReadSource,
};
use crate::organizer_archive::CapturedOrganizerProjection;
use crate::organizer_runtime::CapturedOrganizerCommand;
use babylon_practice_contract::OrganizerPeriodJournalEntries;
use babylon_practice_contract::{OrganizerConfig, OrganizerState};
use postgres::Row;
use std::borrow::Cow;

pub(super) struct CapturedRuntimeCheckpoint {
    campaign: CampaignId,
    tick: u64,
    current: CapturedMaterialTick,
    prior: Option<CapturedMaterialTick>,
    lookup: Vec<Row>,
    actions: Row,
    command: CapturedOrganizerCommand,
    projection: CapturedOrganizerProjection,
}

impl CapturedRuntimeCheckpoint {
    pub(super) const fn tick(&self) -> u64 {
        self.tick
    }

    pub(super) fn capture(
        client: &mut impl GenericClient,
        campaign: CampaignId,
        tick: u64,
    ) -> Result<Self, MaterialRuntimeError> {
        let tick_sql = i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?;
        let current =
            CapturedMaterialTick::capture(client, StoredTickReadSource::Runtime, campaign, tick)?;
        let prior = if tick > 1 {
            Some(CapturedMaterialTick::capture(
                client,
                StoredTickReadSource::Runtime,
                campaign,
                tick - 1,
            )?)
        } else {
            None
        };
        let lookup =
            super::capture_material_lookup(client, StoredTickReadSource::Runtime, campaign, tick)?;
        let actions = client.query_opt("SELECT layout_version,action_batch_digest,exact_action_batch_bytes FROM babylon_state.tick_action_batch_v1 WHERE campaign_id=$1::uuid AND resolve_tick=$2", &[campaign.as_uuid(), &tick_sql])?.ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
        let command = crate::organizer_runtime::capture_pending(client, campaign, tick)?;
        let projection = crate::organizer_archive::capture_projection(client, campaign, tick)?;
        Ok(Self {
            campaign,
            tick,
            current,
            prior,
            lookup,
            actions,
            command,
            projection,
        })
    }

    pub(super) fn admit(
        self,
        authority: MaterialReadAuthority<'_, '_>,
        envelope_read: MaterialEnvelopeRead,
    ) -> Result<StoredMaterialTick<'static>, MaterialRuntimeError> {
        use crate::production_projection::diagnostics::{Stage, Timing};
        let (lookup, prior_lookup) =
            super::admit_archive_lookup(self.lookup, self.tick, authority.opening)?;
        // Retain only the small organizer input from the fully authenticated
        // previous period. Release its decoded graph/register before the current.
        let prior_organizer = if let Some(prior) = self.prior {
            let _prior_timing = Timing::start(Stage::ArchivePriorCheckpoint, self.tick - 1);
            let prior = prior.admit(
                self.campaign,
                self.tick - 1,
                authority,
                prior_lookup.ok_or(MaterialRuntimeError::InvalidCheckpoint)?,
                MaterialEnvelopeRead::AuthenticatedRead,
            )?;
            authority.components.validate_sections(&prior.sections)?;
            if prior.identity.foundation_digest() != authority.foundation_digest {
                return Err(MaterialRuntimeError::InvalidCheckpoint);
            }
            Some((
                prior.register.organizer_config().cloned(),
                prior.register.organizer_state().cloned(),
            ))
        } else {
            None
        };
        let current_timing = Timing::start(Stage::ArchiveCurrentCheckpoint, self.tick);
        let stored =
            self.current
                .admit(self.campaign, self.tick, authority, lookup, envelope_read)?;
        drop(current_timing);
        let validation_timing = Timing::start(Stage::ArchiveOrganizerValidation, self.tick);
        if stored.identity.foundation_digest() != authority.foundation_digest {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        authority.components.validate_sections(&stored.sections)?;
        let accepted = admit_actions(
            authority.components,
            self.tick,
            &stored.register,
            prior_organizer,
            self.command,
        )?;
        authority.components.validate_actions(
            self.tick,
            self.actions.try_get(0)?,
            self.actions.try_get::<_, &[u8]>(1)?,
            self.actions.try_get::<_, &[u8]>(2)?,
            accepted.as_ref(),
        )?;
        self.projection.validate(&stored.register)?;
        drop(validation_timing);
        // Cold callers supply no borrowed state/receipt witness. Keep the owned
        // complete proof for runtime restore; Archive can then release that proof.
        Ok(StoredMaterialTick {
            identity: stored.identity,
            envelope: stored.envelope,
            graph: stored.graph,
            material: stored.material,
            sections: stored.sections,
            register: Cow::Owned(stored.register.into_owned()),
            events: stored.events,
            lookup_identity: stored.lookup_identity,
            lookup_chain: stored.lookup_chain,
        })
    }
}

fn admit_actions(
    components: &MaterialComponentIdentity,
    tick: u64,
    register: &MaterialWorldRegister,
    prior: Option<(Option<OrganizerConfig>, Option<OrganizerState>)>,
    command: CapturedOrganizerCommand,
) -> Result<Option<OrderedPracticeActionBatch>, MaterialRuntimeError> {
    let Some(config) = register.organizer_config() else {
        return Ok(None);
    };
    let prior_state = if let Some((prior_config, prior_state)) = prior {
        if prior_config.as_ref() != Some(config) {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        prior_state.ok_or(MaterialRuntimeError::InvalidCheckpoint)?
    } else {
        babylon_practice_contract::initial_organizer_state(config)
            .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?
    };
    let command = command.admit()?;
    if command.as_ref().is_some_and(|(_, consumed)| {
        consumed.and_then(|period| u64::try_from(period).ok()) != Some(tick)
    }) {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    let commitment = command.as_ref().map(|(commitment, _)| commitment);
    let receipt = register
        .organizer_journal()
        .and_then(|journal| {
            journal
                .periods
                .iter()
                .flat_map(OrganizerPeriodJournalEntries::receipts)
                .find(|row| row.actor_id == config.controlled_actor_id && row.period == tick)
        })
        .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
    if receipt.commitment_id != commitment.map(|input| input.commitment_id) {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    babylon_practice_contract::organizer_action_batch(
        config,
        &prior_state,
        commitment,
        components.session_id().clone(),
    )
    .map(Some)
    .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)
}
