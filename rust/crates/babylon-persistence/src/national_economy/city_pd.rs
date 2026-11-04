//! Designed national City PD capture, bound to an existing resident time account.

use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AccountId, CashAccount, InstitutionLocation, OrganizationAccountId, PublicAccountId,
    PublicAllocation, PublicTransferTreatment,
};
use babylon_practice_contract::PublicVenueHistory;
use babylon_practice_contract::PublicVenuePolicy;
use babylon_practice_contract::{CityPdConfig, CITY_PD_SCHEMA_VERSION};

use crate::economic_catalog::{
    EconomicCatalogError, EconomicCatalogInput, EconomicOpening, SourceArtifactKind,
};
use crate::national_economy::{
    NationalAidCapture, NationalGamePolicy, VenueLogReader, NATIONAL_SCENARIO_ID,
};

use std::result::Result as StdResult;

type Result<T> = StdResult<T, EconomicCatalogError>;
const AMOUNT: i128 = 24_000_000;

pub(crate) fn actor_key() -> StableElementKey {
    StableElementKey::Node {
        scenario: NATIONAL_SCENARIO_ID.into(),
        local_name: "wayne-city-pd".into(),
    }
}

pub(crate) fn actor_id() -> Result<u64> {
    let digest = content_digest::sha256_of(
        &actor_key()
            .canonical_bytes()
            .map_err(|_| EconomicCatalogError::Identity)?,
    );
    let id = u64::from_be_bytes(
        digest[..8]
            .try_into()
            .map_err(|_| EconomicCatalogError::Identity)?,
    );
    if id == 0 {
        return Err(EconomicCatalogError::Identity);
    }
    Ok(id)
}

pub(crate) fn public_venue(input: &EconomicCatalogInput) -> Result<PublicVenueHistory> {
    let organizer = input
        .organizer
        .as_ref()
        .ok_or(EconomicCatalogError::Identity)?;
    let source = input
        .sources
        .iter()
        .find(|row| row.kind() == SourceArtifactKind::NationalGamePolicy)
        .ok_or(EconomicCatalogError::Source(
            SourceArtifactKind::NationalGamePolicy,
        ))?;
    let captured = NationalGamePolicy::from_captured_bytes(source.bytes())
        .map_err(|_| EconomicCatalogError::Source(SourceArtifactKind::NationalGamePolicy))?;
    let reader = match captured.organizer.venue_log_reader {
        VenueLogReader::ControlledOrganizer => organizer.controlled_actor_id,
        VenueLogReader::WorkplaceCommittee => organizer.workplace_partner.actor_id,
    };
    let policy = PublicVenuePolicy::new(
        organizer.campaign_id,
        organizer.workplace_id,
        organizer.controlled_actor_id,
        organizer.workplace_partner.actor_id,
        organizer.workplace_partner.authority_id,
        actor_id()?,
        reader,
        organizer.content_digest,
        source.digest(),
    )
    .map_err(|_| EconomicCatalogError::Identity)?;
    let notice = babylon_practice_contract::initial_public_venue_notice(&policy)
        .map_err(|_| EconomicCatalogError::Identity)?;
    Ok(PublicVenueHistory {
        policy,
        records: vec![notice],
    })
}

pub(crate) fn assemble(
    campaign: [u8; 16],
    input: &EconomicCatalogInput,
    opening: &EconomicOpening,
    aid: &NationalAidCapture,
) -> Result<CityPdConfig> {
    let source = input
        .sources
        .iter()
        .find(|row| row.kind() == SourceArtifactKind::NationalGamePolicy)
        .ok_or(EconomicCatalogError::Source(
            SourceArtifactKind::NationalGamePolicy,
        ))?;
    let policy = NationalGamePolicy::from_captured_bytes(source.bytes())
        .map_err(|_| EconomicCatalogError::Identity)?;
    if campaign == [0; 16] || policy.default_wage.micro_units() != AMOUNT {
        return Err(EconomicCatalogError::Identity);
    }
    let resident = aid.children.get(1).ok_or(EconomicCatalogError::Identity)?;
    let county: EconomicLocation = "county:26163"
        .parse()
        .map_err(|_| EconomicCatalogError::Identity)?;
    if resident.location != county || resident.eligible == 0 {
        return Err(EconomicCatalogError::Identity);
    }
    let household = opening
        .households
        .iter()
        .filter(|row| row.principal_id == resident.principal && row.location == county)
        .collect::<Vec<_>>();
    let time = opening
        .policies
        .household_time_policy
        .iter()
        .filter(|row| row.principal_id == resident.principal)
        .collect::<Vec<_>>();
    if household.len() != 1 || time.len() != 1 || time[0].eligible_persons != resident.eligible {
        return Err(EconomicCatalogError::Identity);
    }
    let actor_digest = content_digest::sha256_of(
        &actor_key()
            .canonical_bytes()
            .map_err(|_| EconomicCatalogError::Identity)?,
    );
    let actor_id = u64::from_be_bytes(
        actor_digest[..8]
            .try_into()
            .map_err(|_| EconomicCatalogError::Identity)?,
    );
    let mut authority_preimage = b"babylon.city-pd-authority.v1\0".to_vec();
    authority_preimage.extend_from_slice(&campaign);
    authority_preimage.extend_from_slice(&actor_id.to_be_bytes());
    let mut authority_id = [0; 16];
    authority_id.copy_from_slice(&content_digest::sha256_of(&authority_preimage)[..16]);
    let mut public_preimage = b"NationalPublicProvisioningV1\0".to_vec();
    public_preimage.extend_from_slice(&county.canonical_bytes());
    let public_account_id = content_digest::sha256_of(&public_preimage);
    let agency_account_id =
        content_digest::sha256_of(b"babylon.national-wayne-city-pd-account.v1\0");
    let mut entitlement = b"babylon.city-pd-investigator-entitlement.v1\0".to_vec();
    entitlement.extend_from_slice(&resident.principal.as_bytes());
    entitlement.extend_from_slice(&time[0].labor_unit_id.as_bytes());
    let investigator_entitlement_id = content_digest::sha256_of(&entitlement);
    let mut content = b"babylon.city-pd-national-policy.v1\0".to_vec();
    let organizer = input
        .organizer
        .as_ref()
        .ok_or(EconomicCatalogError::Identity)?;
    if organizer.campaign_id != campaign {
        return Err(EconomicCatalogError::Identity);
    }
    content.extend_from_slice(&campaign);
    content.extend_from_slice(&actor_digest);
    content.extend_from_slice(&public_account_id);
    content.extend_from_slice(&agency_account_id);
    content.extend_from_slice(&investigator_entitlement_id);
    // This Designed desk is attached to the captured workplace committee;
    // neither a street location nor a census membership is inferred.
    content.extend_from_slice(b"wayne-workplace-public-contact-desk\0");
    content.extend_from_slice(&organizer.workplace_id.to_be_bytes());
    content.extend_from_slice(&organizer.workplace_partner.actor_id.to_be_bytes());
    content.extend_from_slice(&1_u64.to_be_bytes());
    content.extend_from_slice(&AMOUNT.to_be_bytes());
    content.extend_from_slice(&0_u32.to_be_bytes());
    let config = CityPdConfig {
        schema_version: CITY_PD_SCHEMA_VERSION,
        campaign_id: campaign,
        actor_id,
        authority_id,
        county: *b"26163",
        public_account_id,
        agency_account_id,
        investigator_household_account_id: resident.principal.as_bytes(),
        investigator_entitlement_id,
        labor_unit_id: time[0].labor_unit_id.as_bytes(),
        visit_hours: 1,
        hourly_wage_micros: AMOUNT,
        visit_cost_micros: AMOUNT,
        appropriation_micros: AMOUNT,
        appropriation_priority: 0,
        content_digest: content_digest::sha256_of(&content),
        policy_source_digest: source.digest(),
    };
    babylon_practice_contract::validate_city_pd_config(&config)
        .map_err(|_| EconomicCatalogError::Identity)?;
    Ok(config)
}

pub(crate) fn add_opening(opening: &mut EconomicOpening, config: &CityPdConfig) -> Result<()> {
    let county: EconomicLocation = "county:26163"
        .parse()
        .map_err(|_| EconomicCatalogError::Identity)?;
    let public = PublicAccountId::from_bytes(config.public_account_id);
    let agency =
        AccountId::Organization(OrganizationAccountId::from_bytes(config.agency_account_id));
    if opening
        .institutional_cash
        .iter()
        .any(|row| row.id == agency)
        || opening
            .institutions
            .locations
            .iter()
            .any(|row| row.account == agency)
        || opening
            .institutions
            .public_budgets
            .iter()
            .filter(|row| row.public_account == public)
            .count()
            != 1
        || opening
            .institutions
            .locations
            .iter()
            .filter(|row| row.account == AccountId::Public(public) && row.location == county)
            .count()
            != 1
    {
        return Err(EconomicCatalogError::Identity);
    }
    let budget = opening
        .institutions
        .public_budgets
        .iter_mut()
        .find(|row| row.public_account == public)
        .ok_or(EconomicCatalogError::Identity)?;
    budget.period_cap = Currency::from_micro_units(
        budget
            .period_cap
            .micro_units()
            .checked_add(AMOUNT)
            .ok_or(EconomicCatalogError::Arithmetic)?,
    );
    opening.institutional_cash.push(CashAccount {
        id: agency,
        cash: Currency::from_micro_units(0),
    });
    opening.institutions.locations.push(InstitutionLocation {
        account: agency,
        location: county,
    });
    opening
        .institutions
        .public_allocations
        .push(PublicAllocation {
            public_account: public,
            recipient: agency,
            treatment: PublicTransferTreatment::AgencyAppropriation,
            priority: 0,
            amount_per_period: Currency::from_micro_units(AMOUNT),
        });
    Ok(())
}
