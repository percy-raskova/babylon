//! Authored foreground detail selected from the admitted national opening.

use super::{Builder, NationalOpeningError as Error, Result};
use crate::national_economy::NationalAidCapture;
use crate::national_household_refinement;
use crate::national_household_refinement::{
    AuthoredCommitment, ForegroundSelection, NationalDetailPartition,
};

use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{AccountId, GoodId, SiteId, UnitId};

pub(super) fn partition(
    builder: &Builder<'_>,
    aid: &NationalAidCapture,
) -> Result<NationalDetailPartition> {
    let mut selection = ForegroundSelection::default();
    let mut payer = None;
    for mandate in &aid.mandates {
        let AccountId::Organization(account) = mandate.payer else {
            return Err(Error::Identity);
        };
        if payer.is_some_and(|existing| existing != account) {
            return Err(Error::Identity);
        }
        payer = Some(account);
    }
    selection
        .organizations
        .insert(payer.ok_or(Error::Identity)?);
    for child in &aid.children {
        selection.household_principals.insert(child.principal);
        selection.household_principals.insert(child.parent);
    }
    for term in &builder.opening.employment {
        if selection.household_principals.contains(&term.payee) {
            selection.workplaces.insert(term.site_id);
        }
    }
    let mut commitments = Vec::with_capacity(aid.mandates.len());
    for mandate in &aid.mandates {
        let recipient = aid
            .children
            .iter()
            .find(|child| child.principal == mandate.recipient)
            .ok_or(Error::Identity)?;
        selection.commitments.insert(mandate.id);
        commitments.push(AuthoredCommitment {
            id: mandate.id,
            donor: mandate.donor,
            recipient: mandate.recipient,
            location: recipient.location,
            good_id: mandate.good_id,
            unit_id: mandate.unit_id,
            maximum_quantity: mandate.maximum_quantity,
        });
        if let Some(site) = partner_workplace(
            builder,
            recipient.location,
            mandate.good_id,
            mandate.unit_id,
        ) {
            selection.partner_workplaces.insert(site);
        }
    }
    national_household_refinement::consolidate_background(
        &builder.opening,
        &builder.household_keys,
        &builder.opening.policies.household_time,
        selection,
        &commitments,
    )
    .map_err(Error::Detail)
}

fn partner_workplace(
    builder: &Builder<'_>,
    location: EconomicLocation,
    good_id: GoodId,
    unit_id: UnitId,
) -> Option<SiteId> {
    let mut selected = None;
    for site in &builder.opening.sites {
        if site.location != location {
            continue;
        }
        let Some(recipe) = builder.policy.recipes.get(&site.function) else {
            continue;
        };
        let Some(commodity) = builder.policy.commodities.get(&recipe.output) else {
            continue;
        };
        if commodity.good_id != good_id || commodity.unit_id != unit_id {
            continue;
        }
        if selected.is_none_or(|current| site.site_id < current) {
            selected = Some(site.site_id);
        }
    }
    selected
}
