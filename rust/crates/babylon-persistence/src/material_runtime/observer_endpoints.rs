//! One complete admission per endpoint in the observer's repeatable-read snapshot.

use super::journal_snapshot::JournalSnapshot;
use super::{
    material_storage, CampaignId, GenericClient, MaterialComponentIdentity, MaterialReadAuthority,
    MaterialRuntimeError, MaterialWorldRegister, ObserverReadAuthority, RegisterWitnesses,
    StoredMaterialTick, StoredTickReadSource,
};
use crate::observer_reader::ObserverEconomyError;
use crate::production_projection::diagnostics::{Stage, Timing};
use material_storage::AdmittedReceiptWitness;
use material_storage::OpeningRegister;
use postgres::Config;
use std::thread::Builder;

#[derive(Clone, Copy)]
pub(crate) struct ObserverEndpointLookup<'a, 'w> {
    pub(crate) opening: &'a OpeningRegister,
    pub(crate) current_chain: [u8; 32],
    pub(crate) previous_chain: Option<[u8; 32]>,
    pub(crate) registers: RegisterWitnesses<'w>,
    pub(crate) receipt: Option<&'w AdmittedReceiptWitness>,
    pub(crate) journal_connection: Option<&'a Config>,
}

// Only the two-endpoint reader constructs this witness, after complete envelope,
// marker, checkpoint and action admission in the caller's current SQL snapshot.
// It cannot become a campaign cache or be constructed from a partial row read.
pub(super) struct AuthenticatedPreviousMaterialTick<'w> {
    campaign: CampaignId,
    stored: StoredMaterialTick<'w>,
}

impl AuthenticatedPreviousMaterialTick<'_> {
    pub(super) fn register_for(
        &self,
        campaign: CampaignId,
        current: &StoredMaterialTick<'_>,
        components: &MaterialComponentIdentity,
    ) -> Result<&MaterialWorldRegister, MaterialRuntimeError> {
        if self.campaign != campaign
            || self.stored.identity.resolve_tick().checked_add(1)
                != Some(current.identity.resolve_tick())
            || self.stored.identity.foundation_digest() != current.identity.foundation_digest()
            || self.stored.identity.result_world_hash() != current.identity.prior_world_hash()
            || self.stored.graph.scenario_scope() != current.graph.scenario_scope()
        {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        components.validate_sections(&self.stored.sections)?;
        Ok(&self.stored.register)
    }
}

pub(crate) fn read_observer_material_endpoints<'w>(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    read: ObserverReadAuthority<'_>,
    lookup: ObserverEndpointLookup<'_, 'w>,
) -> Result<(StoredMaterialTick<'w>, Option<StoredMaterialTick<'w>>), ObserverEconomyError> {
    if tick == 0 {
        return Err(ObserverEconomyError::InvalidProjection);
    }
    let ObserverReadAuthority {
        scope,
        foundation_digest,
        components,
        catalog,
        resolver,
    } = read;
    let authority = MaterialReadAuthority {
        scope,
        foundation_digest,
        components,
        opening: lookup.opening,
        catalog,
        resolver,
        lookup_chain: Some(lookup.current_chain),
        witnesses: lookup.registers,
        receipt_witness: lookup.receipt,
        previous: None,
    };
    let mut captured = None;
    let previous = if tick > 1 {
        let chain = lookup
            .previous_chain
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        let prior_authority = MaterialReadAuthority {
            lookup_chain: Some(chain),
            receipt_witness: None,
            ..authority
        };
        let prior = if let Some(config) = lookup.journal_connection {
            let snapshot = JournalSnapshot::export(client)?;
            std::thread::scope(|scope| {
                let child = Builder::new()
                    .name("journal-endpoint".into())
                    .spawn_scoped(scope, || snapshot.capture(config, campaign, tick))
                    .map_err(|_| ObserverEconomyError::Database)?;
                let prior = read_endpoint(client, campaign, tick - 1, prior_authority);
                let current = child.join();
                // Preserve the serial reader's evidence failure order and join
                // before either envelope can be used as authority for the next.
                let prior = prior.map_err(|_| ObserverEconomyError::InvalidProjection)?;
                captured = Some(current.map_err(|_| ObserverEconomyError::Database)??);
                Ok::<_, ObserverEconomyError>(prior)
            })?
        } else {
            read_endpoint(client, campaign, tick - 1, prior_authority)
                .map_err(|_| ObserverEconomyError::InvalidProjection)?
        };
        Some(AuthenticatedPreviousMaterialTick {
            campaign,
            stored: prior,
        })
    } else {
        None
    };
    let current_authority = MaterialReadAuthority {
        previous: previous.as_ref(),
        ..authority
    };
    let current = if let Some(rows) = captured {
        let _timing = Timing::start(Stage::AuthenticatedEnvelope, tick);
        rows.authenticate(
            client,
            StoredTickReadSource::FullObserver,
            campaign,
            tick,
            current_authority,
        )
    } else {
        read_endpoint(client, campaign, tick, current_authority)
    }
    .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    Ok((current, previous.map(|previous| previous.stored)))
}

fn read_endpoint<'w>(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    authority: MaterialReadAuthority<'_, 'w>,
) -> Result<StoredMaterialTick<'w>, MaterialRuntimeError> {
    let _timing = Timing::start(Stage::AuthenticatedEnvelope, tick);
    super::read_authenticated_material_tick(
        client,
        StoredTickReadSource::FullObserver,
        campaign,
        tick,
        authority,
    )
}
