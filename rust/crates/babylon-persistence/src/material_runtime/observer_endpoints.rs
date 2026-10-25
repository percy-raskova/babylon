//! One complete admission per endpoint in the observer's repeatable-read snapshot.

use super::{
    material_storage, CampaignId, GenericClient, MaterialComponentIdentity, MaterialReadAuthority,
    MaterialRuntimeError, MaterialWorldRegister, RegisterWitnesses, StoredMaterialTick,
    StoredTickReadSource,
};
use crate::production_projection::diagnostics::{Stage, Timing};
use babylon_material_circuit::MaterialCatalog;
use material_storage::AdmittedReceiptWitness;
use material_storage::OpeningRegister;

#[derive(Clone, Copy)]
pub(crate) struct ObserverEndpointLookup<'a, 'w> {
    pub(crate) opening: &'a OpeningRegister,
    pub(crate) current_chain: [u8; 32],
    pub(crate) previous_chain: Option<[u8; 32]>,
    pub(crate) registers: RegisterWitnesses<'w>,
    pub(crate) receipt: Option<&'w AdmittedReceiptWitness>,
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

#[allow(
    clippy::too_many_arguments,
    reason = "the campaign catalog is a distinct authority beside the endpoint lookup"
)]
pub(crate) fn read_observer_material_endpoints<'w>(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    scope: &str,
    foundation_digest: [u8; 32],
    components: &MaterialComponentIdentity,
    lookup: ObserverEndpointLookup<'_, 'w>,
    catalog: &MaterialCatalog,
) -> Result<(StoredMaterialTick<'w>, Option<StoredMaterialTick<'w>>), MaterialRuntimeError> {
    if tick == 0 {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    let authority = MaterialReadAuthority {
        scope,
        foundation_digest,
        components,
        opening: lookup.opening,
        catalog,
        lookup_chain: Some(lookup.current_chain),
        witnesses: lookup.registers,
        receipt_witness: lookup.receipt,
        previous: None,
    };
    let previous = if tick > 1 {
        let chain = lookup
            .previous_chain
            .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
        Some(AuthenticatedPreviousMaterialTick {
            campaign,
            stored: read_endpoint(
                client,
                campaign,
                tick - 1,
                MaterialReadAuthority {
                    lookup_chain: Some(chain),
                    receipt_witness: None,
                    ..authority
                },
            )?,
        })
    } else {
        None
    };
    let current = read_endpoint(
        client,
        campaign,
        tick,
        MaterialReadAuthority {
            previous: previous.as_ref(),
            ..authority
        },
    )?;
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
