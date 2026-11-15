//! Foundation-bound geography of operating and financial principals.
use super::model::FlowResult;
use super::{CountyInternalPoint, EconomicFlowError, FlowAccount};
use crate::economic_catalog::{CapturedEconomicCatalog, EconomicSourceView};
use crate::michigan_economy;
use crate::national_economy::grain::{
    CatchmentId, ContributionDestination, FinancialDomainId, NationalGenerationWitness,
};
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{AccountId, MonetaryBook};
use std::collections::BTreeMap;

pub(super) fn project(
    catalog: &CapturedEconomicCatalog,
    book: &MonetaryBook,
) -> FlowResult<Vec<FlowAccount>> {
    let view = catalog.view();
    let opening = view.opening;
    let mut locations = BTreeMap::new();
    let rows = opening
        .sites
        .iter()
        .map(|site| (AccountId::Site(site.site_id), site.location))
        .chain(opening.households.iter().map(|household| {
            (
                AccountId::Household(household.principal_id),
                household.location,
            )
        }))
        .chain(
            opening
                .orders
                .principals
                .iter()
                .map(|row| (AccountId::Household(row.id), row.location)),
        )
        .chain(
            opening
                .institutions
                .locations
                .iter()
                .map(|row| (row.account, row.location)),
        );
    for (account, location) in rows {
        if locations
            .insert(account, location)
            .is_some_and(|previous| previous != location)
        {
            return Err(EconomicFlowError::AccountGeographyMismatch);
        }
    }
    let functions: BTreeMap<AccountId, EconomicFunction> = opening
        .sites
        .iter()
        .map(|row| (AccountId::Site(row.site_id), row.function))
        .collect();
    let membership = catalog
        .national_generation()
        .map(catchments)
        .transpose()?
        .unwrap_or_default();
    book.cash_accounts()
        .map(|(&account, _)| {
            let location = locations.get(&account).copied();
            let industry = functions
                .get(&account)
                .map(|value| value.source_key().to_owned());
            let catchment = membership
                .get(&account)
                .map(|&(id, hub)| {
                    if location != Some(hub) {
                        return Err(EconomicFlowError::AccountGeographyMismatch);
                    }
                    Ok(format!("catchment:{}", michigan_economy::digest_hex(&id.0)))
                })
                .transpose()?;
            let county_internal_point = match (location, view.sources) {
                (
                    Some(EconomicLocation::County(county)),
                    EconomicSourceView::National { counties, .. },
                ) => {
                    let row = counties
                        .county(county.geoid())
                        .map_err(|_| EconomicFlowError::AccountGeographyMismatch)?;
                    let anchor = row.internal_point();
                    Some(CountyInternalPoint {
                        longitude: anchor.longitude().to_owned(),
                        latitude: anchor.latitude().to_owned(),
                    })
                }
                _ => None,
            };
            Ok(FlowAccount {
                account: account.into(),
                location: location.map(|key| key.to_string()),
                industry,
                catchment,
                county_internal_point,
            })
        })
        .collect()
}

/// Resolve representative memberships through their captured destination identities.
/// Source counties identify the membership evidence; only the captured hub locates the account.
fn catchments(
    witness: &NationalGenerationWitness,
) -> FlowResult<BTreeMap<AccountId, (CatchmentId, EconomicLocation)>> {
    let hubs: BTreeMap<_, _> = witness
        .catchments
        .iter()
        .map(|row| (row.id, row.key.hub))
        .collect();
    let mut counties = BTreeMap::new();
    let mut accounts = BTreeMap::new();
    for row in &witness.counties {
        let group = match row.destination {
            ContributionDestination::Detailed(_) => None,
            ContributionDestination::Representative {
                catchment,
                position,
            } => {
                let hub = *hubs
                    .get(&catchment)
                    .ok_or(EconomicFlowError::AccountGeographyMismatch)?;
                let location = EconomicLocation::domestic_county(hub)
                    .map_err(|_| EconomicFlowError::AccountGeographyMismatch)?;
                let domain = FinancialDomainId {
                    location,
                    representative: Some((catchment, position)),
                };
                accounts.insert(
                    AccountId::Public(domain.public_account()),
                    (catchment, location),
                );
                Some((catchment, location))
            }
        };
        counties.insert(row.controls.county, group);
    }
    let destinations = witness
        .source_incidence
        .iter()
        .map(|r| (AccountId::Site(r.destination_site), r.source_county))
        .chain(
            witness
                .household_incidence
                .iter()
                .map(|r| (AccountId::Household(r.destination), r.county)),
        );
    for (account, source_county) in destinations {
        add_destination(&mut accounts, &counties, account, source_county)?;
    }
    Ok(accounts)
}

fn add_destination(
    accounts: &mut BTreeMap<AccountId, (CatchmentId, EconomicLocation)>,
    counties: &BTreeMap<CountyGeoid, Option<(CatchmentId, EconomicLocation)>>,
    account: AccountId,
    source_county: CountyGeoid,
) -> FlowResult<()> {
    if let Some(&group) = counties
        .get(&source_county)
        .ok_or(EconomicFlowError::AccountGeographyMismatch)?
        .as_ref()
    {
        if accounts
            .insert(account, group)
            .is_some_and(|old| old != group)
        {
            return Err(EconomicFlowError::AccountGeographyMismatch);
        }
    }
    Ok(())
}
