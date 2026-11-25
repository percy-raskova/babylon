//! Designed national City PD capture, bound to an existing resident time account.

use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{
    AccountId, CashAccount, InstitutionLocation, LaborCompensation, OrganizationAccountId,
    PublicAccountId, PublicAllocation, PublicTransferTreatment, SiteId,
};
use babylon_practice_contract::PublicVenueHistory;
use babylon_practice_contract::PublicVenuePolicy;
use babylon_practice_contract::{CityPdConfig, CITY_PD_SCHEMA_VERSION};

use crate::economic_catalog::{
    EconomicCatalogError, EconomicCatalogInput, EconomicOpening, EconomicSiteSeed,
    EconomicSiteSource, SourceArtifactKind,
};
use crate::national_economy::{
    GameCityPdPolicy, NationalAidCapture, NationalGamePolicy, NationalOpeningError, VenueLogReader,
    NATIONAL_SCENARIO_ID,
};

use std::result::Result as StdResult;

type Result<T> = StdResult<T, EconomicCatalogError>;

pub(crate) fn actor_key() -> StableElementKey {
    StableElementKey::Node {
        scenario: NATIONAL_SCENARIO_ID.into(),
        local_name: "wayne-city-pd".into(),
    }
}

pub(crate) fn actor_id() -> Result<u64> {
    actor_id_of(&actor_key())
}

/// The nonzero actor identifier a stable key derives: the first eight bytes of its digest.
pub(crate) fn actor_id_of(key: &StableElementKey) -> Result<u64> {
    let digest = content_digest::sha256_of(
        &key.canonical_bytes()
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
    if campaign == [0; 16] {
        return Err(EconomicCatalogError::Identity);
    }
    let terms = policy
        .city_pd
        .as_ref()
        .ok_or(EconomicCatalogError::Opening(
            "City PD terms need a national policy that carries [city_pd]",
        ))?;
    let books = Books::of(&policy, terms)?;
    let county: EconomicLocation = "county:26163"
        .parse()
        .map_err(|_| EconomicCatalogError::Identity)?;
    let (principal, labor_unit) = investigator(opening, aid, county)?;
    let actor_digest = content_digest::sha256_of(
        &actor_key()
            .canonical_bytes()
            .map_err(|_| EconomicCatalogError::Identity)?,
    );
    let actor_id = actor_id()?;
    let authority_id = authority_id(campaign, actor_id);
    let public_account_id = public_account_id(county);
    let payroll_site_account_id = payroll_site(
        opening,
        county,
        PublicAccountId::from_bytes(public_account_id),
        terms.positions,
        books.payroll,
    )?;
    let agency_account_id =
        content_digest::sha256_of(b"babylon.national-wayne-city-pd-account.v1\0");
    let mut entitlement = b"babylon.city-pd-investigator-entitlement.v1\0".to_vec();
    entitlement.extend_from_slice(&principal);
    entitlement.extend_from_slice(&labor_unit);
    let investigator_entitlement_id = content_digest::sha256_of(&entitlement);
    let mut content = b"babylon.city-pd-national-policy.v2\0".to_vec();
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
    content.extend_from_slice(&terms.visit_hours.to_be_bytes());
    content.extend_from_slice(&books.wage.to_be_bytes());
    content.extend_from_slice(&books.visit_cost.to_be_bytes());
    content.extend_from_slice(&books.appropriation.to_be_bytes());
    content.extend_from_slice(&0_u32.to_be_bytes());
    content.extend_from_slice(&payroll_site_account_id);
    content.extend_from_slice(&terms.positions.to_be_bytes());
    content.extend_from_slice(&policy.work_hours_per_person.to_be_bytes());
    content.extend_from_slice(&books.payroll.to_be_bytes());
    content.extend_from_slice(&terms.visits_per_period.to_be_bytes());
    let config = CityPdConfig {
        schema_version: CITY_PD_SCHEMA_VERSION,
        campaign_id: campaign,
        actor_id,
        authority_id,
        county: *b"26163",
        public_account_id,
        agency_account_id,
        investigator_household_account_id: principal,
        investigator_entitlement_id,
        labor_unit_id: labor_unit,
        visit_hours: terms.visit_hours,
        hourly_wage_micros: books.wage,
        visit_cost_micros: books.visit_cost,
        appropriation_micros: books.appropriation,
        appropriation_priority: 0,
        payroll_site_account_id,
        payroll_positions: terms.positions,
        payroll_hours_per_position: policy.work_hours_per_person,
        payroll_micros: books.payroll,
        visits_per_period: terms.visits_per_period,
        content_digest: content_digest::sha256_of(&content),
        policy_source_digest: source.digest(),
    };
    babylon_practice_contract::validate_city_pd_config(&config)
        .map_err(|_| EconomicCatalogError::Identity)?;
    Ok(config)
}

fn authority_id(campaign: [u8; 16], actor_id: u64) -> [u8; 16] {
    let mut preimage = b"babylon.city-pd-authority.v1\0".to_vec();
    preimage.extend_from_slice(&campaign);
    preimage.extend_from_slice(&actor_id.to_be_bytes());
    let mut id = [0; 16];
    id.copy_from_slice(&content_digest::sha256_of(&preimage)[..16]);
    id
}

/// The county-scoped public account that the national opening already holds.
pub(crate) fn public_account_id(county: EconomicLocation) -> [u8; 32] {
    let mut preimage = b"NationalPublicProvisioningV1\0".to_vec();
    preimage.extend_from_slice(&county.canonical_bytes());
    content_digest::sha256_of(&preimage)
}

/// The City PD's three numbers and its payroll, each worked out from the scenario's wage.
struct Books {
    wage: i128,
    visit_cost: i128,
    appropriation: i128,
    payroll: i128,
}

impl Books {
    /// One number used to do three jobs. They are now the scenario's wage, the price of the
    /// visit hours and the appropriation for the visits allowed in a period; the payroll is the
    /// positions times a period's hours times the wage.
    fn of(policy: &NationalGamePolicy, terms: &GameCityPdPolicy) -> Result<Self> {
        // Until the City PD's payroll reads the observed wage (Task 8), only a single wage serves.
        let wage = policy
            .wages
            .single()
            .ok_or(EconomicCatalogError::NationalOpening(
                NationalOpeningError::Policy,
            ))?
            .micro_units();
        let visit_cost = i128::from(terms.visit_hours)
            .checked_mul(wage)
            .ok_or(EconomicCatalogError::Arithmetic)?;
        let appropriation = i128::from(terms.visits_per_period)
            .checked_mul(visit_cost)
            .ok_or(EconomicCatalogError::Arithmetic)?;
        let payroll = i128::from(terms.positions)
            .checked_mul(i128::from(policy.work_hours_per_person))
            .and_then(|hours| hours.checked_mul(wage))
            .ok_or(EconomicCatalogError::Arithmetic)?;
        Ok(Self {
            wage,
            visit_cost,
            appropriation,
            payroll,
        })
    }
}

/// The resident investigator household and its labor unit, checked against the opening.
fn investigator(
    opening: &EconomicOpening,
    aid: &NationalAidCapture,
    county: EconomicLocation,
) -> Result<([u8; 32], [u8; 32])> {
    let resident = aid.children.get(1).ok_or(EconomicCatalogError::Identity)?;
    if resident.location != county || resident.eligible == 0 {
        return Err(EconomicCatalogError::Identity);
    }
    let household = opening
        .households
        .iter()
        .filter(|row| row.principal_id == resident.principal && row.location == county)
        .count();
    let time = opening
        .policies
        .household_time_policy
        .iter()
        .filter(|row| row.principal_id == resident.principal)
        .collect::<Vec<_>>();
    if household != 1 || time.len() != 1 || time[0].eligible_persons != resident.eligible {
        return Err(EconomicCatalogError::Identity);
    }
    Ok((
        resident.principal.as_bytes(),
        time[0].labor_unit_id.as_bytes(),
    ))
}

/// The public workplace that already employs the force: the county's public-provisioning site of
/// local government with the most employee persons. The opening carries source ownership on a site's
/// source, so the choice reads that ownership; it never reads an identifier to break a tie.
fn payroll_site(
    opening: &EconomicOpening,
    county: EconomicLocation,
    public: PublicAccountId,
    positions: u64,
    payroll: i128,
) -> Result<[u8; 32]> {
    let EconomicLocation::County(geoid) = county else {
        return Err(EconomicCatalogError::Identity);
    };
    let mut best: Option<(u64, &EconomicSiteSeed)> = None;
    let mut tied = false;
    for site in &opening.sites {
        if site.location != county
            || site.function != EconomicFunction::PublicProvisioning
            || !is_local_government(&site.source, geoid.geoid())
        {
            continue;
        }
        let employees = employee_persons(opening, site.site_id)?;
        match best {
            Some((most, _)) if employees < most => {}
            Some((most, _)) if employees == most => tied = true,
            _ => {
                best = Some((employees, site));
                tied = false;
            }
        }
    }
    let Some((employees, site)) = best else {
        return Err(EconomicCatalogError::Opening(
            "City PD payroll site: no local-government public-provisioning site in Wayne",
        ));
    };
    if tied {
        return Err(EconomicCatalogError::Opening(
            "City PD payroll site: two sites employ equally many persons",
        ));
    }
    if employees < positions {
        return Err(EconomicCatalogError::Opening(
            "City PD payroll site: it employs fewer persons than the City PD has positions",
        ));
    }
    let recipient = AccountId::Site(site.site_id);
    let mut grant = 0_i128;
    for row in &opening.institutions.public_allocations {
        if row.public_account == public
            && row.recipient == recipient
            && row.treatment == PublicTransferTreatment::ProviderOperatingGrant
        {
            grant = grant
                .checked_add(row.amount_per_period.micro_units())
                .ok_or(EconomicCatalogError::Arithmetic)?;
        }
    }
    if grant < payroll {
        return Err(EconomicCatalogError::Opening(
            "City PD payroll site: its provider grant is smaller than the payroll",
        ));
    }
    Ok(site.site_id.as_bytes())
}

fn is_local_government(source: &EconomicSiteSource, county: CountyGeoid) -> bool {
    match source {
        EconomicSiteSource::Qcew(key) => {
            key.county == county && key.ownership == QcewOwnership::LocalGovernment
        }
        EconomicSiteSource::Designed {
            source_ownership, ..
        } => *source_ownership == Some(QcewOwnership::LocalGovernment),
        EconomicSiteSource::MichiganSector { .. } => false,
    }
}

/// Persons the site employs for a wage: staffing members whose terms there are a wage.
fn employee_persons(opening: &EconomicOpening, site: SiteId) -> Result<u64> {
    let mut total = 0_u64;
    for pool in opening
        .staffing
        .iter()
        .filter(|pool| pool.pool.site_id() == site)
    {
        for member in &pool.members {
            let paid = opening.employment.iter().any(|terms| {
                terms.site_id == site
                    && terms.member_id == member.member.member_id()
                    && matches!(terms.compensation, LaborCompensation::Wage(_))
            });
            if paid {
                total = total
                    .checked_add(member.employed)
                    .ok_or(EconomicCatalogError::Arithmetic)?;
            }
        }
    }
    Ok(total)
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
            .checked_add(config.appropriation_micros)
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
            amount_per_period: Currency::from_micro_units(config.appropriation_micros),
        });
    Ok(())
}

#[cfg(test)]
mod tests {
    use babylon_graph::stable_element::StableElementKey;
    use babylon_kernel::currency::Currency;
    use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
    use babylon_kernel::economic_location::EconomicLocation;
    use babylon_material_circuit::{
        AccountId, EquipmentPosition, FinancialInstitutions, HouseholdTimeAccounting,
        LogisticsNodeId, PublicAccountId, PublicAllocation, PublicTransferTreatment,
        RollingProcessSupply, SiteId,
    };

    use crate::economic_catalog::{
        CatalogAccounting, CatalogCapacity, CatalogLogistics, CatalogOpeningOrders,
        CatalogPolicies, EconomicCatalogError, EconomicOpening, EconomicSiteSeed,
        EconomicSiteSource,
    };

    const PUBLIC: [u8; 32] = [7; 32];

    fn wayne() -> EconomicLocation {
        "county:26163".parse().expect("Wayne is a county location")
    }

    /// An opening that holds nothing: tests add the sites and allocations they need.
    fn empty_opening() -> EconomicOpening {
        EconomicOpening {
            commodity_labels: vec![],
            commodities: vec![],
            recipes: vec![],
            household_templates: vec![],
            sites: vec![],
            households: vec![],
            staffing: vec![],
            employment: vec![],
            accounting: CatalogAccounting::Monetary,
            institutional_cash: vec![],
            institutions: FinancialInstitutions::empty(),
            equity: vec![],
            equipment: vec![],
            equipment_position: EquipmentPosition::default(),
            capacity: CatalogCapacity::Rolling(RollingProcessSupply::CapturedNameplate(vec![])),
            policies: CatalogPolicies {
                company_portfolios: None,
                company_payouts: vec![],
                aid_mandates: vec![],
                household_time: HouseholdTimeAccounting::NotModeled,
                household_time_policy: vec![],
                offers: vec![],
                replenishment: vec![],
                household_purchases: vec![],
                service_inputs: vec![],
                service_connections: vec![],
            },
            logistics: CatalogLogistics {
                supplier_routes: vec![],
                route_stages: vec![],
                memberships: vec![],
                shared_capacity: vec![],
            },
            orders: CatalogOpeningOrders {
                principals: vec![],
                goods: vec![],
                final_demand: vec![],
            },
            maintenance: None,
        }
    }

    /// A Wayne public-provisioning site of local government, which employs nobody.
    fn local_government_site(tag: u8) -> EconomicSiteSeed {
        EconomicSiteSeed {
            site_id: SiteId::from_bytes([tag; 32]),
            label: format!("Local government {tag}"),
            subject: StableElementKey::Node {
                scenario: "city-pd-payroll-site-test".into(),
                local_name: format!("site-{tag}"),
            },
            location: wayne(),
            logistics_node_id: LogisticsNodeId::from_bytes([tag; 32]),
            source: EconomicSiteSource::Designed {
                key: format!("site-{tag}"),
                source_ownership: Some(QcewOwnership::LocalGovernment),
            },
            function: EconomicFunction::PublicProvisioning,
            processes: vec![],
            merchant: None,
            opening_stock: vec![],
            opening_cash: Currency::from_micro_units(0),
        }
    }

    fn grant(opening: &mut EconomicOpening, site: u8, micros: i128) {
        opening
            .institutions
            .public_allocations
            .push(PublicAllocation {
                public_account: PublicAccountId::from_bytes(PUBLIC),
                recipient: AccountId::Site(SiteId::from_bytes([site; 32])),
                treatment: PublicTransferTreatment::ProviderOperatingGrant,
                priority: 0,
                amount_per_period: Currency::from_micro_units(micros),
            });
    }

    fn payroll_site(
        opening: &EconomicOpening,
        positions: u64,
        payroll: i128,
    ) -> Result<[u8; 32], EconomicCatalogError> {
        super::payroll_site(
            opening,
            wayne(),
            PublicAccountId::from_bytes(PUBLIC),
            positions,
            payroll,
        )
    }

    fn refusal(result: Result<[u8; 32], EconomicCatalogError>) -> &'static str {
        match result {
            Err(EconomicCatalogError::Opening(reason)) => reason,
            other => panic!("the payroll site must be refused by name, got {other:?}"),
        }
    }

    #[test]
    fn a_county_with_no_local_government_site_has_no_payroll_site() {
        let mut opening = empty_opening();
        assert!(refusal(payroll_site(&opening, 0, 0)).contains("no local-government"));
        // A site of another ownership is not one.
        let mut private = local_government_site(1);
        private.source = EconomicSiteSource::Designed {
            key: "private".into(),
            source_ownership: Some(QcewOwnership::Private),
        };
        opening.sites.push(private);
        assert!(refusal(payroll_site(&opening, 0, 0)).contains("no local-government"));
    }

    #[test]
    fn two_sites_that_employ_equally_many_persons_are_a_tie_that_no_identifier_breaks() {
        let mut opening = empty_opening();
        opening.sites.push(local_government_site(1));
        opening.sites.push(local_government_site(2));
        grant(&mut opening, 1, 10);
        grant(&mut opening, 2, 10);
        assert!(refusal(payroll_site(&opening, 0, 10)).contains("equally many"));
        // The order of the sites does not turn the tie into a choice.
        opening.sites.reverse();
        assert!(refusal(payroll_site(&opening, 0, 10)).contains("equally many"));
    }

    #[test]
    fn a_provider_grant_smaller_than_the_payroll_is_refused() {
        let mut opening = empty_opening();
        opening.sites.push(local_government_site(1));
        grant(&mut opening, 1, 9);
        assert!(refusal(payroll_site(&opening, 0, 10)).contains("smaller than the payroll"));
        // A grant of a different treatment does not count towards it.
        opening
            .institutions
            .public_allocations
            .push(PublicAllocation {
                public_account: PublicAccountId::from_bytes(PUBLIC),
                recipient: AccountId::Site(SiteId::from_bytes([1; 32])),
                treatment: PublicTransferTreatment::AgencyAppropriation,
                priority: 0,
                amount_per_period: Currency::from_micro_units(100),
            });
        assert!(refusal(payroll_site(&opening, 0, 10)).contains("smaller than the payroll"));
    }

    #[test]
    fn a_site_whose_grants_cover_the_payroll_is_the_payroll_site() {
        let mut opening = empty_opening();
        opening.sites.push(local_government_site(1));
        grant(&mut opening, 1, 4);
        grant(&mut opening, 1, 6);
        assert_eq!(payroll_site(&opening, 0, 10), Ok([1; 32]));
    }
}
