//! Read-only context regenerated from one checked campaign capture. Current
//! quantities and flows remain authoritative in material state and receipts.

use super::EconomicOpening;
use crate::{
    michigan_economy::MichiganEconomy, michigan_material::MichiganMaterialCatalog,
    michigan_sectors::MichiganCountySectors, national_cohorts::NationalCohortReference,
    national_counties::NationalCountyReference,
    national_resident_workforce::NationalResidentWorkforceReference,
    national_transport::NationalTransportReference, world_reference::WorldReference,
};
use babylon_kernel::clock::CampaignDuration;

/// Source observations retain their native missingness and scope. A control
/// importer never lends its Michigan identities to a national or foreign actor.
#[derive(Clone, Copy)]
pub enum EconomicSourceView<'a> {
    MichiganControl {
        catalog: &'a MichiganMaterialCatalog,
        counties: &'a MichiganEconomy,
        sectors: &'a MichiganCountySectors,
    },
    National {
        counties: &'a NationalCountyReference,
        cohorts: &'a NationalCohortReference,
        residents: &'a NationalResidentWorkforceReference,
        world: &'a WorldReference,
        transport: &'a NationalTransportReference,
    },
}

/// Immutable presentation context. The digest covers the complete source table,
/// importer/compiler version and captured policy, rather than one source file.
/// Opening orders are identity evidence; their finite roster does not constrain
/// later recurring orders or restore retired orders to the current material state.
#[derive(Clone, Copy)]
pub struct EconomicProjectionView<'a> {
    pub scenario_id: &'a str,
    pub preset_id: &'a str,
    pub duration: CampaignDuration,
    pub source_digest: [u8; 32],
    pub opening: &'a EconomicOpening,
    pub sources: EconomicSourceView<'a>,
}
