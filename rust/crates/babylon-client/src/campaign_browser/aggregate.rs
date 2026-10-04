//! Comparable campaign totals from the same disclosed owners and material principals.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;

use babylon_persistence::{
    observer_reader::ObserverEconomySnapshot, production_observation::ProductionFinalDemandAccount,
    production_observation::ProductionSite, production_observation::ProductionSiteRole,
    production_observation::ProductionSnapshot,
};

use crate::map_economy_lens::{
    material_choices, project_material_locations, MapLens, MaterialGoodKey, MaterialLensKind,
};

use super::staffing_difference;
use crate::workforce::{
    validate_staffing_balance, validate_staffing_period, StaffingError, StaffingIdentity,
};

fn owners(snapshot: &ProductionSnapshot) -> Result<BTreeMap<&str, &ProductionSite>, &'static str> {
    let mut owners = BTreeMap::new();
    for site in &snapshot.sites {
        if owners.insert(site.id.as_str(), site).is_some() {
            return Err("duplicate owner identity");
        }
    }
    if owners.is_empty() {
        return Err("no modeled owners disclosed");
    }
    Ok(owners)
}

fn compatible_owners(
    current: &ProductionSnapshot,
    compared: &ProductionSnapshot,
) -> Result<(), &'static str> {
    let current = owners(current)?;
    let compared = owners(compared)?;
    if current.len() != compared.len()
        || current.iter().any(|(id, site)| {
            compared.get(id).is_none_or(|other| {
                (
                    site.location,
                    site.sector_code.as_deref(),
                    site.roles.iter().collect::<BTreeSet<_>>(),
                    site.industry_code.as_deref(),
                    site.function.as_str(),
                ) != (
                    other.location,
                    other.sector_code.as_deref(),
                    other.roles.iter().collect::<BTreeSet<_>>(),
                    other.industry_code.as_deref(),
                    other.function.as_str(),
                )
            })
        })
    {
        return Err("owner, location, source or role coverage differs");
    }
    Ok(())
}

struct WorkforceTotals<'a> {
    principals: BTreeSet<StaffingIdentity<'a>>,
    employed: u64,
    reserve: u64,
}

fn workforce(
    snapshot: &ProductionSnapshot,
    tick: u64,
) -> Result<WorkforceTotals<'_>, &'static str> {
    let owners = owners(snapshot)?;
    let mut identities = BTreeSet::new();
    let mut pools = BTreeSet::new();
    let mut staffed = BTreeSet::new();
    let (mut employed, mut reserve) = (0_u64, 0_u64);
    for account in &snapshot.staffing_accounts {
        if !identities.insert(StaffingIdentity::from(account)) || !pools.insert(&account.pool_id) {
            return Err("duplicate workforce principal");
        }
        if !owners.contains_key(account.site_id.as_str()) {
            return Err("workforce owner is not disclosed");
        }
        validate_staffing_period(account, tick).map_err(StaffingError::message)?;
        validate_staffing_balance(account).map_err(StaffingError::message)?;
        staffed.insert(account.site_id.as_str());
        employed = employed
            .checked_add(account.employed)
            .ok_or("workforce quantity overflow")?;
        reserve = reserve
            .checked_add(account.reserve)
            .ok_or("workforce quantity overflow")?;
    }
    if staffed.len() != owners.len() {
        return Err("staffing accounts are missing for modeled owners");
    }
    Ok(WorkforceTotals {
        principals: identities,
        employed,
        reserve,
    })
}

fn write_workforce(
    output: &mut String,
    current: &ProductionSnapshot,
    compared: &ProductionSnapshot,
    tick: u64,
) -> Result<(), &'static str> {
    compatible_owners(current, compared)?;
    let left = workforce(current, tick)?;
    let right = workforce(compared, tick)?;
    if left.principals != right.principals {
        return Err("workforce principal, owner or labor unit coverage differs");
    }
    output.push_str(if tick == 0 {
        "Foundation workforce / Designed\n"
    } else {
        "Closing workforce / Derived\n"
    });
    staffing_difference(
        output,
        "All modeled employed",
        left.employed,
        right.employed,
    );
    staffing_difference(output, "All modeled reserve", left.reserve, right.reserve);
    Ok(())
}

#[derive(PartialEq, Eq, PartialOrd, Ord)]
enum MaterialPrincipal<'a> {
    Process(&'a str, &'a str),
    Stock(&'a str),
    Route(&'a str, &'a str, &'a str),
}

fn material_principals<'a>(
    snapshot: &'a ProductionSnapshot,
    kind: MaterialLensKind,
    good: &MaterialGoodKey,
) -> Result<BTreeSet<MaterialPrincipal<'a>>, &'static str> {
    let mut rows = Vec::new();
    match kind {
        MaterialLensKind::ProducedThisPeriod => {
            for owner in &snapshot.sites {
                rows.extend(
                    owner
                        .processes
                        .iter()
                        .filter(|row| {
                            row.output_good_id == good.good_id && row.output_unit_id == good.unit_id
                        })
                        .map(|row| MaterialPrincipal::Process(&owner.id, &row.id)),
                );
            }
        }
        MaterialLensKind::OnHand => {
            for owner in &snapshot.sites {
                rows.extend(
                    owner
                        .inventory
                        .iter()
                        .filter(|row| row.good_id == good.good_id && row.unit_id == good.unit_id)
                        .map(|_| MaterialPrincipal::Stock(&owner.id)),
                );
            }
        }
        MaterialLensKind::InboundInTransit => {
            rows.extend(
                snapshot
                    .routes
                    .iter()
                    .filter(|row| row.good_id == good.good_id && row.unit_id == good.unit_id)
                    .map(|row| {
                        MaterialPrincipal::Route(&row.id, &row.supplier_site_id, &row.buyer_site_id)
                    }),
            );
            let mut lots = BTreeSet::new();
            for lot in snapshot
                .freight
                .iter()
                .filter(|row| row.good_id == good.good_id && row.unit_id == good.unit_id)
            {
                if !lots.insert(&lot.id) {
                    return Err("duplicate freight lot identity");
                }
            }
        }
    }
    let mut identities = BTreeSet::new();
    for row in rows {
        if !identities.insert(row) {
            return Err("duplicate selected-material principal");
        }
    }
    if identities.is_empty() {
        return Err("no account for this exact good and unit");
    }
    Ok(identities)
}

fn material_total(
    snapshot: &ObserverEconomySnapshot,
    lens: &MapLens,
) -> Result<(String, u64), &'static str> {
    let MapLens::Material {
        kind,
        good: Some(good),
    } = lens
    else {
        return Err("Select an exact good and unit in World's material lens");
    };
    let choice = material_choices(snapshot, *kind)
        .map_err(|_| "inconsistent material identity")?
        .into_iter()
        .find(|choice| choice.key == *good)
        .ok_or("exact good and unit are not disclosed")?;
    let production = snapshot
        .production
        .as_ref()
        .ok_or("production is missing")?;
    let locations =
        project_material_locations(production, *kind, good).map_err(|error| match error {
            crate::map_economy_lens::MapLensError::Identity => "inconsistent material identity",
            crate::map_economy_lens::MapLensError::Arithmetic => "material quantity overflow",
        })?;
    if locations.is_empty() {
        return Err("no account for this exact good and unit");
    }
    let total = locations.values().try_fold(0_u64, |total, row| {
        let value = row.ok_or("no completed production receipt for the selected period")?;
        total.checked_add(value).ok_or("material quantity overflow")
    })?;
    Ok((choice.unit, total))
}

fn write_material(
    output: &mut String,
    current: &ObserverEconomySnapshot,
    compared: &ObserverEconomySnapshot,
    lens: &MapLens,
) -> Result<(), &'static str> {
    let MapLens::Material {
        kind,
        good: Some(good),
    } = lens
    else {
        return Err("Select an exact good and unit in World's material lens");
    };
    let left = current
        .production
        .as_ref()
        .ok_or("current production is missing")?;
    let right = compared
        .production
        .as_ref()
        .ok_or("compared production is missing")?;
    compatible_owners(left, right)?;
    if material_principals(left, *kind, good)? != material_principals(right, *kind, good)? {
        return Err("selected-material owner or principal coverage differs");
    }
    if current.resolve_tick == 0 && *kind == MaterialLensKind::ProducedThisPeriod {
        return Err("foundation; no completed production period");
    }
    let (unit, value) = material_total(current, lens)?;
    let (_, other) = material_total(compared, lens)?;
    write_quantity(output, kind.label(), value, other, &unit);
    Ok(())
}

fn write_quantity(output: &mut String, label: &str, current: u64, compared: u64, unit: &str) {
    writeln!(output, "{label}: {current} / {compared} {unit}").expect("String write");
}

#[derive(PartialEq, Eq, PartialOrd, Ord)]
struct RetailIdentity<'a> {
    location: babylon_kernel::economic_location::EconomicLocation,
    principal: &'a str,
}

fn retail_accounts<'a>(
    snapshot: &'a ProductionSnapshot,
    good: &MaterialGoodKey,
) -> Result<BTreeMap<RetailIdentity<'a>, &'a ProductionFinalDemandAccount>, &'static str> {
    let owners = owners(snapshot)?;
    let stocks = retailer_stocks(snapshot, good)?;
    let mut rows = BTreeMap::new();
    let mut order_ids = BTreeSet::new();
    for row in snapshot
        .final_demand_accounts
        .iter()
        .filter(|row| row.good_id == good.good_id && row.unit_id == good.unit_id)
    {
        if rows
            .insert(
                RetailIdentity {
                    location: row.location,
                    principal: &row.demand_principal_id,
                },
                row,
            )
            .is_some()
        {
            return Err("duplicate resident final-demand principal");
        }
        let retailers: BTreeSet<_> = row.retailer_site_ids.iter().collect();
        if retailers.is_empty()
            || retailers.len() != row.retailer_site_ids.len()
            || retailers.iter().any(|id| {
                owners.get(id.as_str()).is_none_or(|owner| {
                    !owner.roles.contains(&ProductionSiteRole::Retail)
                        || owner.location != row.location
                })
            })
        {
            return Err("retail owner coverage is missing or inconsistent");
        }
        if selected_retail_stock(&stocks, row.retailer_site_ids.iter().map(String::as_str))?
            != row.retail_stock_on_hand
        {
            return Err("resident account stock differs from disclosed retailer inventory");
        }
        validate_listed_orders(row, &retailers, &mut order_ids)?;
    }
    if rows.is_empty() {
        return Err("no final-demand account for this exact good and unit");
    }
    Ok(rows)
}

fn validate_listed_orders<'a>(
    row: &'a ProductionFinalDemandAccount,
    retailers: &BTreeSet<&String>,
    order_ids: &mut BTreeSet<&'a String>,
) -> Result<(), &'static str> {
    let mut ordered_retailers = BTreeSet::new();
    let (mut fulfilled, mut outstanding, mut expired) = (0_u64, 0_u64, 0_u64);
    for order in &row.orders {
        if !order_ids.insert(&order.order_id) {
            return Err("duplicate final-demand order principal");
        }
        ordered_retailers.insert(&order.retailer_site_id);
        if order
            .fulfilled
            .checked_add(order.outstanding)
            .and_then(|value| value.checked_add(order.expired))
            != Some(order.ordered)
        {
            return Err("final-demand order quantities do not conserve");
        }
        fulfilled = fulfilled
            .checked_add(order.fulfilled)
            .ok_or("retail quantity overflow")?;
        outstanding = outstanding
            .checked_add(order.outstanding)
            .ok_or("retail quantity overflow")?;
        expired = expired
            .checked_add(order.expired)
            .ok_or("retail quantity overflow")?;
    }
    if !ordered_retailers.is_subset(retailers)
        || fulfilled > row.fulfilled
        || expired > row.expired
        || outstanding != row.outstanding
        || !u64::try_from(row.orders.len()).is_ok_and(|count| count <= row.total_order_count)
        || (u64::try_from(row.orders.len()).ok() == Some(row.total_order_count)
            && (fulfilled != row.fulfilled || expired != row.expired))
        || row
            .fulfilled
            .checked_add(outstanding)
            .and_then(|value| value.checked_add(row.expired))
            != Some(row.ordered)
    {
        return Err("county final-demand account does not match its orders");
    }
    Ok(())
}

fn retailer_stocks<'a>(
    snapshot: &'a ProductionSnapshot,
    good: &MaterialGoodKey,
) -> Result<BTreeMap<&'a str, u64>, &'static str> {
    let mut result = BTreeMap::new();
    for site in &snapshot.sites {
        let mut rows = site
            .inventory
            .iter()
            .filter(|row| row.good_id == good.good_id && row.unit_id == good.unit_id);
        let quantity = rows.next().map_or(0, |row| row.quantity);
        if rows.next().is_some() || result.insert(site.id.as_str(), quantity).is_some() {
            return Err("duplicate retailer stock principal");
        }
    }
    Ok(result)
}

fn selected_retail_stock<'a>(
    stocks: &BTreeMap<&str, u64>,
    retailers: impl Iterator<Item = &'a str>,
) -> Result<u64, &'static str> {
    retailers
        .collect::<BTreeSet<_>>()
        .into_iter()
        .try_fold(0_u64, |sum, id| {
            sum.checked_add(*stocks.get(id).ok_or("retailer stock owner missing")?)
                .ok_or("retail quantity overflow")
        })
}

#[derive(Default)]
struct RetailTotals {
    fulfilled: u64,
    newly_fulfilled: u64,
    stock: u64,
}

impl RetailTotals {
    fn add(&mut self, row: &ProductionFinalDemandAccount, tick: u64) -> Result<(), &'static str> {
        let newly_fulfilled = match (&row.completed, tick) {
            (None, 0) if row.fulfilled == 0 => 0,
            (Some(done), tick)
                if tick > 0
                    && done.period == tick
                    && done.closing_fulfilled == row.fulfilled
                    && done.opening_fulfilled.checked_add(done.newly_fulfilled)
                        == Some(done.closing_fulfilled) =>
            {
                done.newly_fulfilled
            }
            _ => {
                return Err("final-demand receipt is missing or does not match the selected period")
            }
        };
        self.fulfilled = self
            .fulfilled
            .checked_add(row.fulfilled)
            .ok_or("retail quantity overflow")?;
        self.newly_fulfilled = self
            .newly_fulfilled
            .checked_add(newly_fulfilled)
            .ok_or("retail quantity overflow")?;
        Ok(())
    }
}

fn write_retail(
    output: &mut String,
    current: &ProductionSnapshot,
    compared: &ProductionSnapshot,
    good: &MaterialGoodKey,
    tick: u64,
    unit: &str,
) -> Result<(), &'static str> {
    compatible_owners(current, compared)?;
    let left = retail_accounts(current, good)?;
    let right = retail_accounts(compared, good)?;
    if left.keys().ne(right.keys()) {
        return Err("county or final-demand principal coverage differs");
    }
    let stock = selected_retail_stock(
        &retailer_stocks(current, good)?,
        left.values()
            .flat_map(|row| row.retailer_site_ids.iter().map(String::as_str)),
    )?;
    let other_stock = selected_retail_stock(
        &retailer_stocks(compared, good)?,
        right
            .values()
            .flat_map(|row| row.retailer_site_ids.iter().map(String::as_str)),
    )?;
    let (mut totals, mut other_totals) = (
        RetailTotals {
            stock,
            ..RetailTotals::default()
        },
        RetailTotals {
            stock: other_stock,
            ..RetailTotals::default()
        },
    );
    for (key, row) in left {
        let other = right[&key];
        if row.retailer_site_ids.iter().collect::<BTreeSet<_>>()
            != other.retailer_site_ids.iter().collect::<BTreeSet<_>>()
        {
            return Err("retailer principal coverage differs");
        }
        totals.add(row, tick)?;
        other_totals.add(other, tick)?;
    }
    write_quantity(
        output,
        "Delivered to end buyers to date",
        totals.fulfilled,
        other_totals.fulfilled,
        unit,
    );
    if tick == 0 {
        output.push_str("Foundation; no completed retail deliveries.\n");
    } else {
        write_quantity(
            output,
            "Delivered to end buyers this period",
            totals.newly_fulfilled,
            other_totals.newly_fulfilled,
            unit,
        );
    }
    write_quantity(
        output,
        "Unsold retail stock",
        totals.stock,
        other_totals.stock,
        unit,
    );
    Ok(())
}

pub(super) fn write(
    output: &mut String,
    current: &ObserverEconomySnapshot,
    compared: &ObserverEconomySnapshot,
    lens: &MapLens,
) {
    let (Some(left), Some(right)) = (&current.production, &compared.production) else {
        return;
    };
    let locations: BTreeSet<_> = left.sites.iter().map(|site| site.location).collect();
    let county_count = locations
        .iter()
        .filter(|location| {
            matches!(
                location,
                babylon_kernel::economic_location::EconomicLocation::County(_)
            )
        })
        .count();
    writeln!(
        output,
        "MODELED CAMPAIGN TOTALS / {} owners / {} counties / {} external locations",
        left.sites.len(),
        county_count,
        locations.len() - county_count
    )
    .expect("String write");
    if let Err(error) = write_workforce(output, left, right, current.resolve_tick) {
        writeln!(output, "Aggregate workforce unavailable: {error}.").expect("String write");
    }
    let MapLens::Material {
        kind,
        good: Some(good),
    } = lens
    else {
        output.push_str("Select an exact good and unit in World's material lens to compare physical totals.\n\n");
        return;
    };
    let choice = crate::map_economy_lens::material_choices(current, *kind)
        .ok()
        .and_then(|choices| choices.into_iter().find(|choice| choice.key == *good));
    let Some(choice) = choice else {
        output
            .push_str("Selected material unavailable: exact good and unit are not disclosed.\n\n");
        return;
    };
    writeln!(
        output,
        "Selected material / {} / {}",
        choice.label, choice.unit
    )
    .expect("String write");
    if let Err(error) = write_material(output, current, compared, lens) {
        writeln!(output, "Selected material unavailable: {error}.").expect("String write");
    }
    if let Err(error) = write_retail(
        output,
        left,
        right,
        good,
        current.resolve_tick,
        &choice.unit,
    ) {
        writeln!(output, "Retail totals unavailable: {error}.").expect("String write");
    }
    output.push('\n');
}
